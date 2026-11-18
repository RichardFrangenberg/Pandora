import json

import PandoraHeadless


def makeCore(tmp_path, monkeypatch, **env):
    monkeypatch.setenv("PANDORA_CONFIG", str(tmp_path / "prefs" / "Pandora.json"))
    for key in ("PANDORA_ROOT", "PANDORA_REPOSITORY", "PANDORA_LOCAL_MODE"):
        monkeypatch.delenv(key, raising=False)

    for key, val in env.items():
        monkeypatch.setenv(key, val)

    return PandoraHeadless.HeadlessCore()


def test_environment_replaces_user_preferences(tmp_path, monkeypatch):
    core = makeCore(tmp_path, monkeypatch, PANDORA_ROOT="/pandora", PANDORA_LOCAL_MODE="false")
    assert core.getConfig("globals", "rootPath") == "/pandora"
    assert core.getConfig("globals", "localMode") is False
    assert core.getConfig("globals", "repositoryPath") is None


def test_set_and_get_config(tmp_path, monkeypatch):
    core = makeCore(tmp_path, monkeypatch)
    conf = str(tmp_path / "sub" / "settings.json")
    core.setConfig("settings", "maxCPU", 50, configPath=conf)
    core.setConfig(data=[["settings", "a", 1], ["info", "b", [1, 2]]], configPath=conf)
    assert core.getConfig("settings", "maxCPU", configPath=conf) == 50
    assert core.getConfig(data={"x": ["info", "b"], "y": ["info", "nope"]}, configPath=conf) == {
        "x": [1, 2],
        "y": None,
    }
    assert core.getConfig(configPath=conf, getConf=True)["settings"] == {"maxCPU": 50, "a": 1}
    assert sorted(core.getConfig("settings", configPath=conf, getOptions=True)) == ["a", "maxCPU"]

    core.setConfig("settings", "a", configPath=conf, delete=True)
    assert core.getConfig("settings", "a", configPath=conf) is None

    core.setConfig(configPath=conf, confData={"new": {}})
    assert json.loads((tmp_path / "sub" / "settings.json").read_text()) == {"new": {}}
    assert [p.name for p in (tmp_path / "sub").iterdir()] == ["settings.json"]


def test_unreadable_config(tmp_path, monkeypatch):
    core = makeCore(tmp_path, monkeypatch)
    conf = tmp_path / "broken.json"
    conf.write_text("{broken")
    assert core.getConfig("a", "b", configPath=str(conf), silent=True) == "Error"
    assert core.getConfig("a", "b", configPath=str(conf)) is None
    assert core.setConfig("a", "b", 1, configPath=str(conf), silent=True).startswith("Error")


def test_dcc_plugins_load_without_qt(tmp_path, monkeypatch):
    core = makeCore(tmp_path, monkeypatch)
    for name in ("Blender", "Houdini", "Maya"):
        plugin = core.getPlugin(name)
        assert plugin is not None, name
        assert callable(plugin.startJob)

    assert core.getPlugin("DoesNotExist") is None
