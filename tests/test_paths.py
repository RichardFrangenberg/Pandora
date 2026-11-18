import os

import pytest

import PandoraPaths


def test_windows_keeps_documents_folder():
    env = {"USERPROFILE": os.path.join("C:", "Users", "art")}
    expected = os.path.join("C:", "Users", "art", "Documents", "Pandora")
    assert PandoraPaths.getUserConfigDir("windows", env) == expected


def test_linux_uses_xdg_config_home():
    env = {"HOME": "/home/art", "XDG_CONFIG_HOME": "/cfg"}
    assert PandoraPaths.getUserConfigDir("linux", env) == os.path.join("/cfg", "Pandora")


def test_linux_defaults_to_dot_config():
    env = {"HOME": "/home/art"}
    expected = os.path.join("/home/art", ".config", "Pandora")
    assert PandoraPaths.getUserConfigDir("linux", env) == expected


def test_macos_uses_application_support():
    env = {"HOME": "/Users/art"}
    expected = os.path.join("/Users/art", "Library", "Application Support", "Pandora")
    assert PandoraPaths.getUserConfigDir("darwin", env) == expected


def test_config_path_default_and_override():
    env = {"HOME": "/home/art"}
    assert PandoraPaths.getUserConfigPath("linux", env).endswith(
        os.path.join("Pandora", "Pandora.json")
    )
    env["PANDORA_CONFIG"] = "/etc/pandora/custom.json"
    assert PandoraPaths.getUserConfigPath("linux", env) == "/etc/pandora/custom.json"


def test_platform_is_known():
    assert PandoraPaths.getPlatform() in ("windows", "linux", "darwin")


def test_no_overrides_without_variables():
    assert PandoraPaths.getEnvOverrides({}) == {}


def test_overrides_from_environment():
    env = {
        "PANDORA_ROOT": "/pandora",
        "PANDORA_REPOSITORY": "/pandora/JobRepository",
        "PANDORA_LOCAL_MODE": "False",
    }
    assert PandoraPaths.getEnvOverrides(env) == {
        "rootPath": "/pandora",
        "repositoryPath": "/pandora/JobRepository",
        "localMode": False,
    }


@pytest.mark.parametrize("value", ["1", "true", "YES", "on"])
def test_local_mode_true_values(value):
    assert PandoraPaths.getEnvOverrides({"PANDORA_LOCAL_MODE": value}) == {"localMode": True}


def test_invalid_local_mode_is_an_error():
    with pytest.raises(ValueError):
        PandoraPaths.getEnvOverrides({"PANDORA_LOCAL_MODE": "maybe"})
