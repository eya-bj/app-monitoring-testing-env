#!/bin/bash

# Start cron in background
cron

# Start SSH server in foreground
exec /usr/sbin/sshd -D