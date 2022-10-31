# Tested Software Version
1. Ubuntu host: 20.04
2. docker: Docker version 20.10.21, build baeda1f
3. Python: Python 3.8.10
4. docker-py: docker-6.0.0

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

