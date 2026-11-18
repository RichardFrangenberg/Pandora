#!/bin/sh
# Starts the Pandora Coordinator as the user PUID:PGID, so that the files in
# the Pandora root folder belong to the user, who owns the share on the host.
set -e

CMD="python /opt/pandora/PandoraCoordinator.py"

if [ "$(id -u)" = "0" ]; then
    exec gosu "${PUID:-1000}:${PGID:-1000}" $CMD
fi

# the container was started with "user:" / "--user"
exec $CMD
