# Tested Software Version
1. Ubuntu host: 20.04
2. docker: Docker version 20.10.21, build baeda1f
3. Python: Python 3.8.10
4. docker-py: docker-6.0.0

# Dockerfile
The DUT(`./dut-container`) and Testing machine(`./test-container`) Dockerfile will be used to craete
images with required service and tools for testing.
The Dockerfiles are read by `run_automation.py` using `docker` SDK `<env>.images.build()` function.
`run_automation.py` will create images using these Dockerfile and cleanup the images after testing.

## DUT container Dockerfile
```Dockerfile
# Build the image from ubuntu base
FROM ubuntu:20.04

# Init apt-get and install required packages
RUN apt-get update
RUN apt-get install -y iproute2 wget curl openssh-client openssh-server nginx iputils-ping rsyslog

# declear ssh and nginx port
EXPOSE 80
EXPOSE 22

# Add a test user for ssh testing
RUN useradd -m testuser
RUN echo 'testuser:test' | chpasswd
COPY ./verify /home/testuser

# Enable SSH logging
RUN sed -i "s/'#LogLevel INFO'/'LogLevel VERBOSE'/g" /etc/ssh/sshd_config
RUN sed -i "s/#LogLevel INFO/LogLevel VERBOSE/g" /etc/ssh/sshd_config

# Change default shell for all user
RUN chsh -s /bin/bash

# pause the container for testing service
CMD ["/bin/bash","-c","service rsyslog start; service ssh start; service nginx start; sleep infinity"]
```

## Testing machine Dockerfile
```Dockerfile
# Build the image from ubuntu base
FROM ubuntu:20.04

# Init apt-get and install required packages
RUN apt-get update
RUN apt-get install -y iproute2 wget curl openssh-client iputils-ping sshpass

# declear ssh port
EXPOSE 22

# Change default shell for all user
RUN chsh -s /bin/bash

# pause the container for testing service
CMD ["sleep", "infinity"]
```

# Run Automation
> Note: This test automation requires privilege access in order to run docker.
        So please make sure you're root OR add `sudo` in front of all below commands.

1. Install required packages
```bash
sudo pip3 install -r requirements.txt
```

2. Run test automation entry script
```bash
sudo python3 run_automation.py
```

