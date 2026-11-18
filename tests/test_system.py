import os
import sys

import PandoraSystem


def test_total_memory_is_detected():
    assert PandoraSystem.getTotalMemory() > 0


def test_shutdown_commands():
    assert PandoraSystem.getShutdownCommand(platform="windows") == ["shutdown", "-t", "0", "-f"]
    assert PandoraSystem.getShutdownCommand(True, platform="windows") == ["shutdown", "-t", "0", "-r", "-f"]
    assert PandoraSystem.getShutdownCommand(platform="linux") == ["shutdown", "-h", "now"]
    assert PandoraSystem.getShutdownCommand(True, platform="darwin") == ["shutdown", "-r", "now"]


def makeExecutable(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    return str(path)


def patchLocations(monkeypatch, program, platform, patterns):
    data = dict(PandoraSystem.EXECUTABLES[program])
    data[platform] = patterns
    monkeypatch.setitem(PandoraSystem.EXECUTABLES, program, data)


def noWhich(name):
    return None


def test_requested_version_is_preferred(tmp_path, monkeypatch):
    old = makeExecutable(tmp_path / "hfs19.5.303" / "bin" / "hython")
    makeExecutable(tmp_path / "hfs20.0.547" / "bin" / "hython")
    patchLocations(monkeypatch, "Houdini", "linux", [str(tmp_path / "hfs{version}*" / "bin" / "hython")])

    found = PandoraSystem.findExecutable("Houdini", "19.5.303", platform="linux", env={}, which=noWhich)
    assert found == old


def test_similar_version_is_used_if_the_exact_version_is_missing(tmp_path, monkeypatch):
    similar = makeExecutable(tmp_path / "hfs19.5.640" / "bin" / "hython")
    makeExecutable(tmp_path / "hfs20.0.547" / "bin" / "hython")
    patchLocations(monkeypatch, "Houdini", "linux", [str(tmp_path / "hfs{version}*" / "bin" / "hython")])

    found = PandoraSystem.findExecutable("Houdini", "19.5.303", platform="linux", env={}, which=noWhich)
    assert found == similar


def test_newest_version_is_used_without_a_requested_version(tmp_path, monkeypatch):
    makeExecutable(tmp_path / "hfs9.5.1" / "bin" / "hython")
    newest = makeExecutable(tmp_path / "hfs20.0.547" / "bin" / "hython")
    patchLocations(monkeypatch, "Houdini", "linux", [str(tmp_path / "hfs{version}*" / "bin" / "hython")])

    found = PandoraSystem.findExecutable("Houdini", platform="linux", env={}, which=noWhich)
    assert found == newest


def test_environment_variable_is_used(tmp_path, monkeypatch):
    hython = makeExecutable(tmp_path / "custom" / "bin" / "hython")
    patchLocations(monkeypatch, "Houdini", "linux", [])
    env = {"HFS": str(tmp_path / "custom")}
    assert PandoraSystem.findExecutable("Houdini", platform="linux", env=env, which=noWhich) == hython


def test_path_is_searched(monkeypatch):
    patchLocations(monkeypatch, "Blender", "linux", [])
    found = PandoraSystem.findExecutable(
        "Blender", platform="linux", env={}, which=lambda name: "/usr/bin/" + name
    )
    assert found == "/usr/bin/blender"


def test_unknown_program_or_missing_executable(monkeypatch):
    patchLocations(monkeypatch, "Maya", "linux", [])
    assert PandoraSystem.findExecutable("Maya", platform="linux", env={}, which=noWhich) == ""
    assert PandoraSystem.findExecutable("3dsMax", platform="linux", env={}, which=noWhich) == ""
