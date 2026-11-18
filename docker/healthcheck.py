"""Healthcheck of the Pandora Coordinator container.

The coordinator writes a heartbeat file after every cycle. The container is
unhealthy if this file is missing or outdated.
"""

import os
import sys
import time

MAX_AGE = int(os.environ.get("PANDORA_HEALTH_MAX_AGE", "120"))  # seconds

heartbeat = os.path.join(
    os.environ.get("PANDORA_ROOT", "/pandora"), "Scripts", "PandoraCoordinator", "heartbeat"
)

try:
    age = time.time() - os.path.getmtime(heartbeat)
except OSError as e:
    sys.exit("no heartbeat: %s" % e)

if age > MAX_AGE:
    sys.exit("heartbeat is %s seconds old" % int(age))
