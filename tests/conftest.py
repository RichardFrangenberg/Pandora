import os
import sys

import pytest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Pandora", "Scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


@pytest.fixture
def fakeRoot(tmp_path):
    """An empty Pandora root folder with the structure the coordinator expects."""
    root = tmp_path / "PandoraRoot"
    for folder in ("Scripts/PandoraCoordinator", "Slaves", "Workstations"):
        (root / folder).mkdir(parents=True)

    return root
