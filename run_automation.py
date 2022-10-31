#!/usr/bin/python3
import docker
import sys
import re
from logging_config import *
from prettytable import PrettyTable


class TestBed(object):
    def __init__(
        self,
        dut_path,
        testing_path,
        dut_container_name,
        testing_container_name,
        test_network_name,
    ):

        self.dut_path = dut_path
        self.testing_path = testing_path

        self.dut_container_name = dut_container_name
        self.testing_container_name = testing_container_name

        self.test_network_name = test_network_name
        self.engine = docker.from_env()

        # Runtime obj
        self.dut_image = None
        self.testing_image = None
        self.test_network = None
        self.dut_container = None
        self.testing_container = None

    def _create_network(self):
        logger.info("Start creating container bridge network...")
        try:
            # Use TEST NET IPv4 block from RFC5737 https://tools.ietf.org/html/rfc5737
            ipam_pool = docker.types.IPAMPool(
                subnet="192.0.2.0/24",
                iprange="192.0.2.0/24",
                gateway="192.0.2.254",
            )
            ipam_config = docker.types.IPAMConfig(
                driver="default", pool_configs=[ipam_pool]
            )
            # Here I will not use enable_ipv6=True to enable IPv6 network as it required adding below special configuration
            # Use 2001:db8::/32 is the TEST NET IPv6 block for doc use based on RFC 3849 https://tools.ietf.org/html/rfc3849
            # {
            #   "ipv6": true,
            #   "fixed-cidr-v6": "2001:db8:1::/64"
            # }
            # to docker deamon configuration.
            # And it also needs to enable ipv6 forwarding on the host:
            # sysctl net.ipv6.conf.default.forwarding=1
            # sysctl net.ipv6.conf.all.forwarding=1
            #
            # These extra config will cause extra efforts to run this automation on another system.
            # Of course, the IPv6 testing should be added in a real test scenario
            self.test_network = self.engine.networks.create(
                name="test_network",
                driver="bridge",
                ipam=ipam_config,
                check_duplicate=True,
            )
            logger.info(f"Test network [{self.test_network.short_id}] created")
        except docker.errors.APIError as E:
            logger.error(f"Container network creation failed! \nERROR: {E}")
            self.clean()

    def _build_image(self):
        logger.info("Start building image...")
        try:
            # image[1] is logging, image[0] is Image
            logger.info("Building dut image...")
            dut_image = self.engine.images.build(
                path=self.dut_path, rm=True, tag="dut-image:latest"
            )
            self.dut_image = dut_image[0]
            logger.info(f"DUT image [{self.dut_image.short_id}] created")

            logger.info("Building testing image...")
            testing_image = self.engine.images.build(
                path=self.testing_path, rm=True, tag="testing-image:latest"
            )
            self.testing_image = testing_image[0]
            logger.info(
                f"Testing image [{self.testing_image.short_id}] created"
            )

            # Write logs to logfile
            with open("./logs/dut_build.log", "w") as f:
                for line in dut_image[1]:
                    f.write(str(line.get("stream")))
            with open("./logs/testing_build.log", "w") as f:
                for line in testing_image[1]:
                    f.write(str(line.get("stream")))

        except docker.errors.APIError as E:
            logger.error(
                f"build error! \n{E} \nplease check manually\n\
                log location:\n ./logs/dut_build.log\n ./logs/testing_build.log"
            )
            self.clean()

    def _create_container(self):
        logger.info("Start creating container...")
        try:
            self.dut_container = self.engine.containers.run(
                self.dut_image.id,
                detach=True,
                network=self.test_network.name,
                name="dut-container",
            )
            self.testing_container = self.engine.containers.run(
                self.testing_image.id,
                detach=True,
                network=self.test_network.name,
                name="testing-container",
            )
            logger.info(
                f"DUT container [{self.dut_container.short_id}] created"
            )
            logger.info(
                f"Testing container [{self.testing_container.short_id}] created"
            )
        except docker.errors.APIError as E:
            logger.error(f"Create container failed! \nERROR: {E}")
            self.clean()

    def _delete_network(self):
        try:
            logger.info(f"Cleaning test network {self.test_network.short_id}")
            self.test_network.remove()
            logger.info("Done!")
        except docker.errors.APIError as E:
            logger.error(
                "test network removed! Please manually solve the problem and remove it! \nERROR: {E}"
            )
            sys.exit(1)

    def _delete_image(self):
        try:
            logger.info(f"Cleaning dut image {self.dut_image.short_id}")
            self.engine.images.remove(self.dut_image.id)

            logger.info(
                f"Cleaning testing image {self.testing_image.short_id}"
            )
            self.engine.images.remove(self.testing_image.id)
        except docker.errors.APIError as E:
            logger.error(f"Delete dut/testing image failed! \nERROR: {E}")
            sys.exit(1)

    def _delete_container(self):
        try:
            logger.info(
                f"Cleaning dut container {self.dut_container.short_id}"
            )
            self.dut_container.stop()
            self.dut_container.remove(force=True)

            logger.info(
                f"Cleaning testing container {self.testing_container.short_id}"
            )
            self.testing_container.stop()
            self.testing_container.remove(force=True)
        except docker.errors.APIError as E:
            logger.error(f"Delete dut/testing container failed! \nERROR: {E}")
            sys.exit(1)

    def start(self):
        logger.info("Start creating test topology...")
        self._build_image()
        self._create_network()
        self._create_container()
        logger.info("Test topology successfully setup!")

    def cleanup(self):
        logger.info("Start cleaning the test topology...")
        self._delete_container()
        self._delete_network()
        self._delete_image()
        logger.info("Test topology cleaned.")


class TestSuite(object):
    def __init__(self, dut_container, testing_container):
        self.dut_container = dut_container
        self.testing_container = testing_container

        self.dut_ipv4 = self._get_ip4(dut_container)
        self.testing_ipv4 = self._get_ip4(testing_container)

        self.test_results = {}

    def _get_ip4(self, container):
        try:
            logger.info(f"Getting container {container.name} IPv4 address...")
            rc, output = container.exec_run(f"ip add")
            logger.debug(f"ip add rc: {rc}, output: {str(output)}")
            ipv4_address = re.search(
                "inet (192\.0\.2\..+?) brd", str(output)
            ).group(1)[:-3]
            return ipv4_address
        except docker.errors.APIError as E:
            logger.error(f"Get IPv4 address failed! \nERROR: {E}")
            return None

    def _write_ctn_log(self, target, content):
        def _write_to_dut():
            with open("./logs/dut_container.log", "ab") as f:
                f.write(content)
                f.write(str.encode("\n"))

        def _write_to_testing():
            with open("./logs/testing_container.log", "ab") as f:
                f.write(content)
                f.write(str.encode("\n"))

        if isinstance(content, str):
            content = str.encode(content)
        if target == "dut":
            _write_to_dut()
        elif target == "testing":
            _write_to_testing()
        elif target == "both":
            _write_to_dut()
            _write_to_testing()
        else:
            logger.error("Unknown log target")

    def test_case_reachability(self):
        """
        Test Case: Container reachability
        Test Owner: zhiqian0923@gmail.com
        Test Purpose: Verify the reachability from Testing machine to DUT
        Prerequisite:
            1. DUT and Testing machine are connected with proper IP configuration
        Test Steps:
            1. use 'ping' to check the reachability from Testing machine to DUT's
            2. Verify there's no packet loss and ping command return 0
        """
        result = None
        try:
            logger.info("Running Test Case [reachability]...")
            self._write_ctn_log("both", "----------[reachability]----------")
            logger.info("Sending 10 ICMP packets to DUT...")

            cmd = f"ping -c 10 {self.dut_ipv4}"
            self._write_ctn_log("testing", cmd)

            rc, output = self.testing_container.exec_run(cmd)
            logger.info(f"ping rc: {rc}")
            logger.debug(f"ping output: {str(output)}")
            self._write_ctn_log("testing", output)

            if rc == 0 and "0% packet loss" in str(output):
                logger.info("found '0% packet loss' in the ping output")
                result = "PASS"
            else:
                logger.info(f"ping failed! rc: {rc}")
                result = "FAIL"
        except docker.errors.APIError as E:
            logger.error("Run commands in container failed!")
        finally:
            self.test_results["reachability"] = result
            logger.info(f"Test Case [reachability]: {result}")

    def test_case_ssh(self):
        """
        Test Case: SSH Availability
        Test Owner: zhiqian0923@gmail.com
        Test Purpose: Verify the DUT has SSH up&running and we can establish a SSH connection from Testing machine.
        Prerequisite:
            1. DUT and Testing machine are connected with proper IP configuration
            2. DUT has configured SSH server
            3. DUT has a user 'testuser' with passwod 'test' and a home directory
            4. DUT has a file called 'verify' with content 'i_am_dut' inside. 'verify' file should under 'testuser' home directory
        Test Steps:
            1. SSH from Testing machine with user:testuser and password:test to the DUT
            2. Read the 'verify' file from testuser home directory, check the content
        """
        result = None
        try:
            logger.info("Running Test Case [ssh availability]...")
            self._write_ctn_log(
                "both", "----------[ssh availability]----------"
            )
            logger.info("Establishing SSH connection to DUT...")

            ssh_option = "-o StrictHostKeyChecking=no"
            verify_cmd = "cat verify"
            cmd = f"sshpass -p test ssh {ssh_option} testuser@{self.dut_ipv4} {verify_cmd}"
            self._write_ctn_log("testing", cmd)

            rc, output = self.testing_container.exec_run(cmd)

            logger.info(f"ssh rc: {rc}")
            logger.debug(f"ssh output: {str(output)}")
            self._write_ctn_log("testing", output)

            if rc == 0 and "i_am_dut" in str(output):
                logger.info("found 'i_am_dut' identifier in the output")
                result = "PASS"
            else:
                logger.info(
                    f"ssh not return {rc} or cannot see 'i_am_dut' identifier"
                )
                result = "FAIL"

            rc, output = self.dut_container.exec_run("cat /var/log/auth.log")
            self._write_ctn_log("dut", output)
        except docker.errors.APIError as E:
            logger.error("Run commands in container failed!")
        finally:
            self.test_results["ssh_availability"] = result
            logger.info(f"Test Case [ssh availability]: {result}")

    def test_case_http(self):
        """
        Test Case: HTTP Availability
        Test Owner: zhiqian0923@gmail.com
        Test Purpose: Verify the DUT has HTTP service up&running and we can query the HTTP server
        Prerequisite:
            1. DUT and Testing machine are connected with proper IP configuration
            2. DUT has nginx server running on port 80
            3. The nginx server serve the nginx default index.html
        Test Steps:
            1. Use 'curl' tool query the DUT's 80 port
            2. Verify that we can get the nginx default index.html content
        """
        result = None
        try:
            logger.info("Running Test Case [http availability]...")
            self._write_ctn_log(
                "both", "----------[http availability]----------"
            )
            logger.info("Sending http GET query to DUT 80 port using curl...")

            cmd = f"curl {self.dut_ipv4}:80"
            self._write_ctn_log("testing", cmd)

            rc, output = self.testing_container.exec_run(cmd)

            check_output = "If you see this page, the nginx web server is successfully installed"
            logger.info(f"curl rc: {rc}")
            logger.debug(f"curl output: {str(output)}")
            self._write_ctn_log("testing", output)

            if rc == 0 and check_output in str(output):
                logger.info("HTTP server responds looks good:)")
                logger.info(f"found '{check_output}' in the output")
                result = "PASS"
            else:
                logger.info("HTTP respond is not expected!")
                result = "FAIL"

            rc, output = self.dut_container.exec_run(
                "cat /var/log/nginx/access.log"
            )
            self._write_ctn_log("dut", output)
        except docker.errors.APIError as E:
            logger.error("Run commands in container failed!")
        finally:
            self.test_results["http_availability"] = result
            logger.info(f"Test Case [http availability]: {result}")

    def print_results(self):
        result_table = PrettyTable(["Test Case", "Result"])
        result_table.title = "Test Results"
        for test, result in self.test_results.items():
            result_table.add_row([test, result])

        logfile_table = PrettyTable(["Log", "Path"])
        logfile_table.title = "Log Info"
        logfile = {
            "dut_image_build": "dut_build.log",
            "testing_image_build": "testing_build.log",
            "dut_container": "dut_container.log",
            "testing_container": "testing_container.log",
            "debug_info": "debug.log",
        }

        for logitem, logpath in logfile.items():
            logfile_table.add_row([logitem, f"./logs/{logpath}"])

        print(logfile_table)
        print(result_table)


def main():

    # Init the test bed and start all required container/network
    test_topo = TestBed(
        "./dut-container",
        "./test-container",
        "dut-container",
        "testing-container",
        "test_network",
    )
    test_topo.start()

    # Load actual test suite with containers and run test cases
    all_test_cases = TestSuite(
        test_topo.dut_container, test_topo.testing_container
    )
    all_test_cases.test_case_reachability()
    all_test_cases.test_case_ssh()
    all_test_cases.test_case_http()

    # cleanup the container/network/images we created for testing
    test_topo.cleanup()

    # print a short Test Report
    all_test_cases.print_results()


if __name__ == "__main__":
    main()
