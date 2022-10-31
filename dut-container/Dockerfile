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