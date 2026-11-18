import json
import os
import socket
import sys
import textwrap
import threading
import time

import pytest

os.environ["PANDORA_HEADLESS"] = "1"

import PandoraCoordinator
import PandoraHeadless
import PandoraPaths
import PandoraProtocol
import PandoraSlave

HOST = socket.gethostname()

# a DCC plugin, which "renders" by writing one file per frame with Python
FAKE_PLUGIN = '''
import os, sys


class Pandora_Fake_unloaded(object):
    def __init__(self, core):
        self.core = core
        self.pluginName = "Fake"

    def startJob(self, origin, jobData={}):
        # the script is passed as a file, because the Windows shell cannot pass multiline arguments
        scriptPath = os.path.join(os.path.dirname(jobData["scenefile"]), "render.py")
        with open(scriptPath, "w") as f:
            f.write(
                "import os, sys\\n"
                "out, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])\\n"
                "os.makedirs(os.path.dirname(out), exist_ok=True)\\n"
                "for f in range(start, end + 1):\\n"
                "    open(out.replace('####', '%04d' % f), 'w').write('frame')\\n"
                "print('rendered')\\n"
            )

        args = [
            sys.executable,
            scriptPath,
            jobData["outputPath"],
            str(jobData["taskStartframe"]),
            str(jobData["taskEndframe"]),
        ]
        return origin.startRenderThread(pOpenArgs=args, jData=jobData, prog="fake")
'''


def writeJson(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def readJson(path):
    return json.loads(path.read_text())


@pytest.fixture
def farm(fakeRoot, tmp_path, monkeypatch):
    """A Pandora root with a local repository, configured through the environment."""
    monkeypatch.setenv("PANDORA_ROOT", str(fakeRoot))
    monkeypatch.setenv("PANDORA_REPOSITORY", str(tmp_path / "Repository"))
    monkeypatch.setenv("PANDORA_CONFIG", str(tmp_path / "prefs" / "Pandora.json"))
    monkeypatch.delenv("PANDORA_LOCAL_MODE", raising=False)

    pluginDir = tmp_path / "plugins"
    (pluginDir / "Fake" / "Scripts").mkdir(parents=True)
    (pluginDir / "Fake" / "Scripts" / "Pandora_Fake_init_unloaded.py").write_text(FAKE_PLUGIN)

    class Farm(object):
        root = fakeRoot
        repository = tmp_path / "Repository"
        output = tmp_path / "Output"
        slaveDir = fakeRoot / "Slaves" / ("S_%s" % HOST)

        def makeSlave(self):
            core = PandoraHeadless.HeadlessCore()
            core.pluginDirs.append(str(pluginDir))
            slave = PandoraSlave.SlaveLogic(core)
            # the machine, which runs the tests, may be busy
            slave.getConfSetting("maxCPU", setval=True, value=101)
            return slave

        def makeCoordinator(self):
            return PandoraCoordinator.PandoraCoordinator(start=False)

        def addJob(self, code="job1", program="Fake", outputFolder=None, frames=(1, 3)):
            outputFolder = outputFolder or str(self.output)
            jobDir = self.repository / "Coordinator" / "Jobs" / code
            (jobDir / "JobFiles").mkdir(parents=True)
            (jobDir / "JobFiles" / "scene.fake").write_text("scene")
            writeJson(
                jobDir / "PandoraJob.json",
                {
                    "information": {
                        "jobName": "Test Job",
                        "sceneName": "scene.fake",
                        "fileCount": 1,
                        "program": program,
                        "projectName": "TestProject",
                        "outputFolder": outputFolder,
                        "outputPath": outputFolder + "/beauty/beauty.####.exr",
                    },
                    "jobglobals": {"priority": 50, "listSlaves": "All"},
                    "jobtasks": {
                        "task0000": [frames[0], frames[1], "ready", "unassigned", "", "", ""]
                    },
                },
            )
            writeJson(self.repository / "Coordinator" / "PriorityList.json", {code: {"priority": 50}})
            return jobDir

        def slaveOutCommands(self):
            comDir = self.slaveDir / "Communication"
            return [
                PandoraProtocol.parseCommand(p.read_text())
                for p in sorted(comDir.iterdir())
                if p.name.startswith("slaveOut_")
            ]

        def waitForTaskUpdate(self, status, timeout=60):
            end = time.time() + timeout
            while time.time() < end:
                for cmd in self.slaveOutCommands():
                    if cmd and cmd[0] == "taskUpdate" and cmd[3] == status:
                        return cmd

                time.sleep(0.2)

            raise AssertionError("no %s update: %s" % (status, self.slaveOutCommands()))

    return Farm()


def test_slave_registers_itself(farm):
    slave = farm.makeSlave()
    slave.checkAssignments()

    settings = readJson(farm.slaveDir / ("slaveSettings_%s.json" % HOST))
    assert settings["slaveinfo"]["status"] == "idle"
    assert settings["slaveinfo"]["cpucount"] >= 1
    assert settings["slaveinfo"]["ram"] > 0
    assert (farm.slaveDir / ("slaveActive_%s" % HOST)).exists()
    assert (farm.slaveDir / "Communication").is_dir()


def test_job_is_rendered_from_submission_to_finished_task(farm):
    jobDir = farm.addJob(frames=(1, 3))
    slave = farm.makeSlave()
    coord = farm.makeCoordinator()

    slave.checkAssignments()  # the slave becomes active
    coord.startCoordination()  # the coordinator assigns the task
    slave.checkAssignments()  # the slave starts rendering
    update = farm.waitForTaskUpdate("finished")
    coord.startCoordination()  # the coordinator registers the result

    rendered = sorted(p.name for p in (farm.output / "beauty").iterdir())
    assert rendered == ["beauty.0001.exr", "beauty.0002.exr", "beauty.0003.exr"]
    assert update[1] == "job1" and update[2] == "task0000"

    task = readJson(jobDir / "PandoraJob.json")["jobtasks"]["task0000"]
    assert task[2] == "finished"
    assert task[3] == HOST
    assert slave.slaveState == "idle"
    assert slave.curTasks == []


def test_job_paths_from_another_os_are_mapped(farm):
    local = str(farm.output).replace("\\\\", "/")
    foreign = "linux" if PandoraPaths.getPlatform() == "windows" else "windows"
    foreignPrefix = "/mnt/renders" if foreign == "linux" else "R:/renders"
    writeJson(
        farm.root / "Scripts" / "PandoraCoordinator" / "PathMapping.json",
        {"mappings": [{foreign: foreignPrefix, PandoraPaths.getPlatform(): local}]},
    )
    farm.addJob(outputFolder=foreignPrefix, frames=(5, 5))
    slave = farm.makeSlave()
    coord = farm.makeCoordinator()

    slave.checkAssignments()
    coord.startCoordination()
    slave.checkAssignments()
    farm.waitForTaskUpdate("finished")

    assert (farm.output / "beauty" / "beauty.0005.exr").exists()


def test_unknown_program_gives_the_task_back(farm):
    farm.addJob(program="DoesNotExist")
    slave = farm.makeSlave()
    coord = farm.makeCoordinator()

    slave.checkAssignments()
    coord.startCoordination()
    slave.checkAssignments()

    farm.waitForTaskUpdate("ready", timeout=10)
    assert slave.curTasks == []


def test_malicious_command_file_does_not_execute(farm, tmp_path):
    slave = farm.makeSlave()
    marker = tmp_path / "pwned"
    cmdFile = farm.slaveDir / "Communication" / "slaveIn_0001_1.txt"
    cmdFile.write_text('__import__("pathlib").Path(%r).touch()' % str(marker))
    old = time.time() - 120
    os.utime(str(cmdFile), (old, old))

    slave.checkAssignments()
    assert not marker.exists()
    assert not cmdFile.exists()


def test_half_written_command_is_kept(farm):
    slave = farm.makeSlave()
    cmdFile = farm.slaveDir / "Communication" / "slaveIn_0001_1.txt"
    cmdFile.write_text('["setSetting", "maxCP')
    slave.checkAssignments()
    assert cmdFile.exists()

    cmdFile.write_text('["setSetting", "updateTime", 7]')
    slave.checkAssignments()
    assert not cmdFile.exists()
    assert slave.getConfSetting("updateTime") == 7


def test_command_setting_only_runs_allowed_methods(farm, tmp_path):
    slave = farm.makeSlave()
    marker = tmp_path / "pwned"
    slave.getConfSetting(
        "command", setval=True, value='__import__("pathlib").Path(%r).touch()' % str(marker)
    )
    slave.checkAssignments()
    assert not marker.exists()

    slave.getConfSetting("command", setval=True, value="self.setConfig('settings', 'hacked', 1)")
    slave.checkAssignments()
    assert slave.getConfSetting("hacked") is None

    slave.getConfSetting("command", setval=True, value="self.pauseSlave(15)")
    slave.checkAssignments()
    assert slave.slaveState == "paused"
    assert slave.getConfSetting("command") == ""


def test_coordinator_forwards_render_handler_command_to_slave(farm):
    slave = farm.makeSlave()
    coord = farm.makeCoordinator()
    slave.checkAssignments()

    cmdDir = farm.root / "Workstations" / "WS_ws1" / "Commands"
    cmdDir.mkdir(parents=True)
    cmd = ["setSetting", "Slave", HOST, "command", "self.pauseSlave(15)"]
    (cmdDir / "handlerOut_0001_1.txt").write_text(str(cmd))

    coord.startCoordination()
    slave.checkAssignments()  # receives the setting
    slave.checkAssignments()  # executes it
    assert slave.slaveState == "paused"


def test_run_stops_and_marks_the_slave_as_shut_down(farm):
    slave = farm.makeSlave()
    timer = threading.Timer(1.5, slave.stop)
    timer.start()
    thread = threading.Thread(target=slave.run)
    thread.start()
    thread.join(30)
    timer.cancel()

    assert not thread.is_alive()
    settings = readJson(farm.slaveDir / ("slaveSettings_%s.json" % HOST))
    assert settings["slaveinfo"]["status"] == "shut down"


def test_missing_settings_exit_with_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PANDORA_CONFIG", str(tmp_path / "prefs" / "Pandora.json"))
    for key in ("PANDORA_ROOT", "PANDORA_REPOSITORY", "PANDORA_LOCAL_MODE"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(SystemExit) as exc:
        PandoraSlave.SlaveLogic(PandoraHeadless.HeadlessCore())

    assert exc.value.code == 1
    assert "repository path is not defined" in capsys.readouterr().err
