import re

import PandoraProtocol
import PandoraTransport


def test_workstation_commands_are_filtered_and_sorted(fakeRoot):
    cmdDir = fakeRoot / "Workstations" / "WS_ws1" / "Commands"
    cmdDir.mkdir(parents=True)
    for name in ("handlerOut_0002_5.txt", "handlerOut_0001_4.txt", "Pandora_update.zip", "notes.txt"):
        (cmdDir / name).write_text("[]")

    transport = PandoraTransport.FileTransport(str(fakeRoot))
    names = [h.replace("\\", "/").split("/")[-1] for h in transport.listWorkstationCommands("ws1")]
    assert names == ["handlerOut_0001_4.txt", "handlerOut_0002_5.txt"]


def test_slave_commands_only_list_outgoing_files(fakeRoot):
    cmdDir = fakeRoot / "Slaves" / "S_r1" / "Communication"
    cmdDir.mkdir(parents=True)
    (cmdDir / "slaveOut_0001_1.txt").write_text("[]")
    (cmdDir / "slaveIn_0001_1.txt").write_text("[]")

    transport = PandoraTransport.FileTransport(str(fakeRoot))
    handles = transport.listSlaveCommands("r1")
    assert len(handles) == 1
    assert handles[0].endswith("slaveOut_0001_1.txt")


def test_missing_folders_have_no_commands(fakeRoot):
    transport = PandoraTransport.FileTransport(str(fakeRoot))
    assert transport.listWorkstationCommands("unknown") == []
    assert transport.listSlaveCommands("unknown") == []


def test_send_to_slave_uses_the_legacy_file_format(fakeRoot):
    transport = PandoraTransport.FileTransport(str(fakeRoot))
    cmd = ["renderTask", "job1", "Job 1", "task0"]
    handle = transport.sendToSlave("r1", cmd)

    cmdDir = fakeRoot / "Slaves" / "S_r1" / "Communication"
    files = [p.name for p in cmdDir.iterdir()]
    assert len(files) == 1
    assert re.match(r"^slaveIn_0001_\d+(\.\d+)?\.txt$", files[0])
    assert (cmdDir / files[0]).read_text() == str(cmd)
    assert PandoraProtocol.parseCommand(transport.readCommand(handle)) == cmd


def test_send_to_slave_increments_the_number(fakeRoot):
    cmdDir = fakeRoot / "Slaves" / "S_r1" / "Communication"
    cmdDir.mkdir(parents=True)
    (cmdDir / "slaveIn_0007_1.5.txt").write_text("[]")
    (cmdDir / "slaveIn_x_1.txt").write_text("[]")
    (cmdDir / "slaveOut_0040_1.txt").write_text("[]")

    transport = PandoraTransport.FileTransport(str(fakeRoot))
    handle = transport.sendToSlave("r1", ["checkConnection"])
    assert "slaveIn_0008_" in handle


def test_read_age_and_remove(fakeRoot):
    cmdDir = fakeRoot / "Workstations" / "WS_ws1" / "Commands"
    cmdDir.mkdir(parents=True)
    (cmdDir / "handlerOut_0001_1.txt").write_text('["deleteJob", "abc"]')

    transport = PandoraTransport.FileTransport(str(fakeRoot))
    handle = transport.listWorkstationCommands("ws1")[0]
    assert transport.readCommand(handle) == '["deleteJob", "abc"]'
    assert 0 <= transport.getCommandAge(handle) < 60
    transport.removeCommand(handle)
    assert transport.listWorkstationCommands("ws1") == []
