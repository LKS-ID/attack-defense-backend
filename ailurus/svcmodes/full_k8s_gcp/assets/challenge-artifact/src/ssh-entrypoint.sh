#!/bin/sh

ssh-keygen -A
/usr/sbin/sshd

/docker-entrypoint.sh