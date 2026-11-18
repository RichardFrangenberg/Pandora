import json
import os
import sys
import threading
import time

import pytest

import PandoraCoordinator
import PandoraProtocol


@pytest.fixture
def makeCoordinator(fakeRoot, tmp_path, monkeypatch):
    """Creates a coordinator on a fake root, which is configured through the environment."""
    monkeypatch.setenv("PANDORA_ROOT", str(fakeRoot))
    monkeypatch.setenv("PANDORA_CONFIG", str(tmp_path / "userprefs" / "Pandora.json"))
    monkeypatch.delenv("PANDORA_LOCAL_MODE", raising=False)
    monkeypatch.delenv("PANDORA_REPOSITORY", raising=False)
    monkeypatch.delenv("PANDORA_LOG_STDOUT", raising=False)

    def create():
        return PandoraCoordinator.PandoraCoordinator(start=False)

    return create


def writeJson(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def readJson(path):
    return json.loads(path.read_text())


def addSlave(root, name, active=True, groups=None):
    slaveDir = root / "Slaves" / ("S_%s" % name)
    (slaveDir / "Communication").mkdir(parents=True)
    settings = {"settings": {"maxConcurrentTasks": 1, "slaveGroup": groups or []}}
    writeJson(slaveDir / ("slaveSettings_%s.json" % name), settings)
    activeFile = slaveDir / ("slaveActive_%s" % name)
    activeFile.write_text("")
    if not active:
        old = time.time() - 60 * 60
        os.utime(str(activeFile), (old, old))

    return slaveDir


def addJob(root, code, name="Test Job", listSlaves="All", tasks=1):
    jobDir = root / "JobRepository" / "Jobs" / code
    (jobDir / "JobFiles").mkdir(parents=True)
    (jobDir / "JobFiles" / "scene.hip").write_text("scene")
    jobTasks = {}
    for i in range(tasks):
        jobTasks["task%04d" % i] = [i * 10 + 1, i * 10 + 10, "ready", "unassigned", "", "", ""]

    writeJson(
        jobDir / "PandoraJob.json",
        {
            "information": {"jobName": name, "sceneName": "scene.hip", "fileCount": 1},
            "jobglobals": {"priority": 50, "listSlaves": listSlaves},
            "jobtasks": jobTasks,
        },
    )
    prioFile = root / "JobRepository" / "PriorityList.json"
    prios = readJson(prioFile) if prioFile.exists() else {}
    prios[code] = {"priority": 50}
    writeJson(prioFile, prios)
    return jobDir


def slaveCommands(slaveDir):
    comDir = slaveDir / "Communication"
    return [
        PandoraProtocol.parseCommand(p.read_text())
        for p in sorted(comDir.iterdir())
        if p.name.startswith("slaveIn_")
    ]


def addWorkstationCommand(root, text, age=0, name="handlerOut_0001_1.txt"):
    cmdDir = root / "Workstations" / "WS_ws1" / "Commands"
    cmdDir.mkdir(parents=True, exist_ok=True)
    cmdFile = cmdDir / name
    cmdFile.write_text(text)
    if age:
        old = time.time() - age
        os.utime(str(cmdFile), (old, old))

    return cmdFile


def test_setup_from_environment(makeCoordinator, fakeRoot):
    coord = makeCoordinator()
    assert coord.coordBasePath == os.path.join(str(fakeRoot), "Scripts", "PandoraCoordinator")
    assert coord.localMode is True
    assert coord.repPath == os.path.join(str(fakeRoot), "JobRepository")
    assert (fakeRoot / "Scripts" / "PandoraCoordinator" / "heartbeat").exists()


def test_environment_wins_over_shared_settings(makeCoordinator, fakeRoot, monkeypatch):
    writeJson(
        fakeRoot / "Scripts" / "PandoraCoordinator" / "Coordinator_Settings.json",
        {"settings": {"localMode": True, "command": "", "debugMode": False, "repository": ""}},
    )
    monkeypatch.setenv("PANDORA_LOCAL_MODE", "false")
    assert makeCoordinator().localMode is False


def test_shared_settings_apply_without_environment(makeCoordinator, fakeRoot):
    writeJson(
        fakeRoot / "Scripts" / "PandoraCoordinator" / "Coordinator_Settings.json",
        {"settings": {"localMode": False, "command": "", "debugMode": False, "repository": ""}},
    )
    assert makeCoordinator().localMode is False


def test_user_preferences_are_used_without_environment(fakeRoot, tmp_path, monkeypatch):
    config = tmp_path / "userprefs" / "Pandora.json"
    writeJson(
        config,
        {
            "globals": {"localMode": True, "rootPath": str(fakeRoot)},
            "coordinator": {"enabled": True},
        },
    )
    monkeypatch.delenv("PANDORA_ROOT", raising=False)
    monkeypatch.setenv("PANDORA_CONFIG", str(config))
    coord = PandoraCoordinator.PandoraCoordinator(start=False)
    assert coord.coordBasePath == os.path.join(str(fakeRoot), "Scripts", "PandoraCoordinator")


def test_repository_setting_is_mapped_to_this_os(makeCoordinator, fakeRoot, tmp_path):
    repository = tmp_path / "storage" / "Repository"
    repository.mkdir(parents=True)
    coordDir = fakeRoot / "Scripts" / "PandoraCoordinator"
    local = str(tmp_path / "storage").replace("\\", "/")
    writeJson(
        coordDir / "PathMapping.json",
        {"mappings": [{"windows": "R:/", "linux": "/mnt/unused", "darwin": "/Volumes/unused"}]},
    )
    # the mapping of the current platform points to the real folder
    rules = readJson(coordDir / "PathMapping.json")
    foreign = "windows" if sys.platform != "win32" else "linux"
    foreignPrefix = "R:/" if foreign == "windows" else "/mnt/storage"
    import PandoraPaths

    rules["mappings"][0] = {foreign: foreignPrefix, PandoraPaths.getPlatform(): local}
    writeJson(coordDir / "PathMapping.json", rules)
    writeJson(
        coordDir / "Coordinator_Settings.json",
        {"settings": {"command": "", "debugMode": False, "repository": foreignPrefix.rstrip("/") + "/Repository"}},
    )

    coord = makeCoordinator()
    assert os.path.normpath(coord.repPath) == os.path.normpath(str(repository))


def test_malformed_path_mapping_does_not_stop_the_coordinator(makeCoordinator, fakeRoot):
    (fakeRoot / "Scripts" / "PandoraCoordinator" / "PathMapping.json").write_text("{broken")
    coord = makeCoordinator()
    coord.startCoordination()
    assert coord.pathMappings == []


def test_cycle_runs_on_empty_root(makeCoordinator, fakeRoot):
    coord = makeCoordinator()
    coord.startCoordination()
    assert (fakeRoot / "Scripts" / "PandoraCoordinator" / "Coordinator_Settings.json").exists()


def test_workstation_command_is_handled_and_removed(makeCoordinator, fakeRoot):
    cmdFile = addWorkstationCommand(fakeRoot, '["clearWarnings", "Coordinator", ""]')
    coord = makeCoordinator()
    coord.startCoordination()
    assert not cmdFile.exists()


def test_malicious_command_file_does_not_execute(makeCoordinator, fakeRoot, tmp_path):
    marker = tmp_path / "pwned"
    code = '__import__("pathlib").Path(%r).touch()' % str(marker)
    cmdFile = addWorkstationCommand(fakeRoot, code, age=120)
    coord = makeCoordinator()
    coord.startCoordination()
    assert not marker.exists()
    assert not cmdFile.exists()


def test_half_written_command_is_kept_for_the_next_cycle(makeCoordinator, fakeRoot):
    cmdFile = addWorkstationCommand(fakeRoot, '["taskUpd')
    coord = makeCoordinator()
    coord.startCoordination()
    assert cmdFile.exists()

    cmdFile.write_text('["clearWarnings", "Coordinator", ""]')
    coord.startCoordination()
    assert not cmdFile.exists()


def test_command_setting_only_runs_allowed_methods(makeCoordinator, fakeRoot):
    coord = makeCoordinator()
    coord.setConfig("settings", "command", "self.setConfig('settings', 'hacked', 1)")
    coord.startCoordination()
    settings = readJson(fakeRoot / "Scripts" / "PandoraCoordinator" / "Coordinator_Settings.json")
    assert "hacked" not in settings["settings"]
    assert settings["settings"]["command"] == ""


def test_command_setting_runs_allowed_method(makeCoordinator, monkeypatch):
    coord = makeCoordinator()
    calls = []
    monkeypatch.setattr(coord, "searchUncollectedRnd", lambda: calls.append(1))
    coord.setConfig("settings", "command", "self.searchUncollectedRnd()")
    coord.startCoordination()
    assert calls == [1]


def test_job_is_assigned_to_the_active_slave(makeCoordinator, fakeRoot):
    active = addSlave(fakeRoot, "render1")
    inactive = addSlave(fakeRoot, "render2", active=False)
    jobDir = addJob(fakeRoot, "job1")

    coord = makeCoordinator()
    coord.startCoordination()

    commands = slaveCommands(active)
    assert len(commands) == 1
    assert commands[0] == ["renderTask", "job1", "Test Job", "task0000"]
    assert slaveCommands(inactive) == []
    assert (active / "AssignedJobs" / "job1" / "JobFiles" / "scene.hip").exists()

    task = readJson(jobDir / "PandoraJob.json")["jobtasks"]["task0000"]
    assert task[2] == "assigned"
    assert task[3] == "render1"


def test_job_respects_the_slave_list(makeCoordinator, fakeRoot):
    first = addSlave(fakeRoot, "render1")
    second = addSlave(fakeRoot, "render2")
    addJob(fakeRoot, "job1", listSlaves="render2")

    coord = makeCoordinator()
    coord.startCoordination()

    assert slaveCommands(first) == []
    assert len(slaveCommands(second)) == 1


def test_slave_task_update_changes_the_job(makeCoordinator, fakeRoot):
    slave = addSlave(fakeRoot, "render1")
    jobDir = addJob(fakeRoot, "job1")
    coord = makeCoordinator()
    coord.startCoordination()

    update = ["taskUpdate", "job1", "task0000", "rendering", "", time.time(), ""]
    (slave / "Communication" / "slaveOut_0001_1.txt").write_text(str(update))
    coord.startCoordination()

    assert not (slave / "Communication" / "slaveOut_0001_1.txt").exists()
    assert readJson(jobDir / "PandoraJob.json")["jobtasks"]["task0000"][2] == "rendering"


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permissions and a non-root user",
)
def test_unwritable_root_exits_with_an_error(makeCoordinator, fakeRoot, capsys):
    coordDir = fakeRoot / "Scripts" / "PandoraCoordinator"
    os.chmod(str(coordDir), 0o500)
    try:
        with pytest.raises(SystemExit) as exc:
            makeCoordinator()
    finally:
        os.chmod(str(coordDir), 0o700)

    assert exc.value.code == 1
    assert "not writable" in capsys.readouterr().err


def test_invalid_local_mode_exits_with_an_error(makeCoordinator, monkeypatch, capsys):
    monkeypatch.setenv("PANDORA_LOCAL_MODE", "maybe")
    with pytest.raises(SystemExit) as exc:
        makeCoordinator()

    assert exc.value.code == 1
    assert "PANDORA_LOCAL_MODE" in capsys.readouterr().err


def test_run_stops_when_closed(makeCoordinator, fakeRoot):
    coord = makeCoordinator()
    heartbeat = fakeRoot / "Scripts" / "PandoraCoordinator" / "heartbeat"
    heartbeat.unlink()

    timer = threading.Timer(1.5, coord.stop)
    timer.start()
    start = time.time()
    thread = threading.Thread(target=coord.run)
    thread.start()
    thread.join(15)
    timer.cancel()

    assert not thread.is_alive()
    assert time.time() - start < 10
    assert heartbeat.exists()


def test_exit_command_file_stops_the_coordinator(makeCoordinator, fakeRoot):
    coord = makeCoordinator()
    (fakeRoot / "Scripts" / "PandoraCoordinator" / "command.txt").write_text("exit")
    thread = threading.Thread(target=coord.run)
    thread.start()
    thread.join(15)
    assert not thread.is_alive()
