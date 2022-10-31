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