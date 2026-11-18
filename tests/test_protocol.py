import pytest

import PandoraProtocol


def test_valid_command_is_parsed():
    text = '["taskUpdate", "abc", "t1", "finished", 1.5, 2, 3, 4]'
    assert PandoraProtocol.parseCommand(text) == ["taskUpdate", "abc", "t1", "finished", 1.5, 2, 3, 4]


def test_command_with_nested_data_is_parsed():
    text = "['setSetting', 'Slave', 'r1', 'slaveGroup', ['gpu', 'cpu']]\n"
    assert PandoraProtocol.parseCommand(text)[4] == ["gpu", "cpu"]


@pytest.mark.parametrize(
    "text",
    [
        '__import__("os").system("echo pwned")',
        '[__import__("os").system("echo pwned")]',
        '["taskUpd',
        '"just a string"',
        "[]",
        "",
        "{'a': 1}",
    ],
)
def test_invalid_commands_are_rejected(text):
    assert PandoraProtocol.parseCommand(text) is None


def test_call_without_arguments():
    assert PandoraProtocol.parseCall("self.searchUncollectedRnd()") == ("searchUncollectedRnd", [], {})


def test_call_with_arguments():
    assert PandoraProtocol.parseCall("self.collectOutput(jobCode='a')") == ("collectOutput", [], {"jobCode": "a"})
    assert PandoraProtocol.parseCall("self.shutdownPC(True);") == ("shutdownPC", [True], {})


@pytest.mark.parametrize(
    "text",
    [
        "self.a.b()",
        "os.system('x')",
        "self.f(open('x'))",
        "self.f(); self.g()",
        "self.__class__",
        "self.f(**{'a': 1})",
        "import os",
        "self.f(x=__import__('os'))",
        "",
    ],
)
def test_everything_but_a_plain_method_call_is_rejected(text):
    assert PandoraProtocol.parseCall(text) is None


class Target(object):
    def __init__(self):
        self.calls = []

    def searchUncollectedRnd(self):
        self.calls.append("search")

    def collectOutput(self, slave=None, jobCode=None):
        self.calls.append(("collect", slave, jobCode))

    def setConfig(self, *args):
        self.calls.append("setConfig")

    def _private(self):
        self.calls.append("private")


def test_allowed_call_runs():
    target = Target()
    assert PandoraProtocol.runCall(target, "self.searchUncollectedRnd()", PandoraProtocol.COORDINATOR_COMMANDS)
    assert PandoraProtocol.runCall(target, "self.collectOutput(jobCode='j1')", PandoraProtocol.COORDINATOR_COMMANDS)
    assert target.calls == ["search", ("collect", None, "j1")]


def test_call_outside_allow_list_does_not_run():
    target = Target()
    assert not PandoraProtocol.runCall(target, "self.setConfig('a', 'b', 1)", PandoraProtocol.COORDINATOR_COMMANDS)
    assert not PandoraProtocol.runCall(target, "self._private()", ("_private",))
    assert not PandoraProtocol.runCall(target, "self.missing()", ("missing",))
    assert target.calls == []
