#!/bin/bash

# Get the host IP for X11
IP=$(ifconfig | grep inet | grep -v inet6 | grep -v 127.0.0.1 | head -n 1 | awk '{print $2}')

# Run the command passed to this script ($@) inside the container
docker run --rm --platform linux/amd64 \
    --network=host \
    --user $(id -u):$(id -g) \
    --env=LIBGL_ALWAYS_INDIRECT=1 \
    --env=DISPLAY=$IP:0 \
    --volume="$PWD:$PWD" \
    --workdir="$PWD" \
    mbari/mbsystem "$@"