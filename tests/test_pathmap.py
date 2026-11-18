import json

import PandoraPathMap

RULES = [
    {"windows": "P:/", "linux": "/mnt/projects", "darwin": "/Volumes/projects"},
    {"windows": "//nas/pandora", "linux": "/pandora", "darwin": "/Volumes/pandora"},
]


def test_windows_to_linux():
    assert PandoraPathMap.mapPath("P:\\show\\a.hip", RULES, "linux") == "/mnt/projects/show/a.hip"


def test_linux_to_windows_uses_backslashes():
    assert PandoraPathMap.mapPath("/mnt/projects/show/a.hip", RULES, "windows") == "P:\\show\\a.hip"


def test_macos_to_linux():
    assert PandoraPathMap.mapPath("/Volumes/projects/show", RULES, "linux") == "/mnt/projects/show"


def test_linux_to_macos():
    assert PandoraPathMap.mapPath("/pandora/Jobs", RULES, "darwin") == "/Volumes/pandora/Jobs"


def test_windows_to_macos_and_back():
    assert PandoraPathMap.mapPath("P:/show", RULES, "darwin") == "/Volumes/projects/show"
    assert PandoraPathMap.mapPath("/Volumes/projects/show", RULES, "windows") == "P:\\show"


def test_unc_path_with_mixed_case_and_trailing_separator():
    assert PandoraPathMap.mapPath("\\\\NAS\\Pandora\\Jobs\\", RULES, "linux") == "/pandora/Jobs/"


def test_windows_prefix_is_case_insensitive():
    assert PandoraPathMap.mapPath("p:/SHOW", RULES, "linux") == "/mnt/projects/SHOW"


def test_posix_prefix_is_case_sensitive():
    assert PandoraPathMap.mapPath("/MNT/projects/a", RULES, "windows") == "/MNT/projects/a"


def test_drive_root_maps_to_drive_root():
    assert PandoraPathMap.mapPath("/mnt/projects", RULES, "windows") == "P:\\"
    assert PandoraPathMap.mapPath("P:\\", RULES, "linux") == "/mnt/projects/"


def test_prefix_must_end_at_a_folder_boundary():
    rules = [{"windows": "P:/proj", "linux": "/mnt/proj"}]
    assert PandoraPathMap.mapPath("P:/projects/a", rules, "linux") == "P:/projects/a"
    assert PandoraPathMap.mapPath("P:/proj/a", rules, "linux") == "/mnt/proj/a"


def test_longest_prefix_wins():
    rules = [
        {"windows": "P:/", "linux": "/mnt/projects"},
        {"windows": "P:/cache", "linux": "/mnt/fast/cache"},
    ]
    assert PandoraPathMap.mapPath("P:/cache/sim.bgeo", rules, "linux") == "/mnt/fast/cache/sim.bgeo"


def test_path_without_rule_is_unchanged():
    assert PandoraPathMap.mapPath("D:\\other\\a.ma", RULES, "linux") == "D:\\other\\a.ma"
    assert PandoraPathMap.mapPath("", RULES, "linux") == ""
    assert PandoraPathMap.mapPath("P:/a", [], "linux") == "P:/a"


def test_rule_without_target_platform_is_skipped():
    rules = [{"windows": "P:/", "linux": "/mnt/projects"}]
    assert PandoraPathMap.mapPath("P:/a", rules, "darwin") == "P:/a"


def test_load_mappings_machine_file_first(tmp_path):
    machine = tmp_path / "user" / "PathMapping.json"
    farm = tmp_path / "coord" / "PathMapping.json"
    machine.parent.mkdir()
    farm.parent.mkdir()
    machine.write_text(json.dumps({"mappings": [{"windows": "P:/", "linux": "/local"}]}))
    farm.write_text(json.dumps({"mappings": [{"windows": "Q:/", "linux": "/farm"}]}))

    files = PandoraPathMap.getMappingFiles(str(farm.parent), str(machine.parent))
    mappings = PandoraPathMap.loadMappings(files)
    assert [m["linux"] for m in mappings] == ["/local", "/farm"]
    assert PandoraPathMap.getLoadErrors() == []


def test_missing_files_mean_no_mapping(tmp_path):
    assert PandoraPathMap.loadMappings([str(tmp_path / "nope.json")]) == []
    assert PandoraPathMap.getLoadErrors() == []


def test_malformed_file_is_reported_and_ignored(tmp_path):
    broken = tmp_path / "PathMapping.json"
    broken.write_text('{"mappings": [')
    assert PandoraPathMap.loadMappings([str(broken)]) == []
    assert len(PandoraPathMap.getLoadErrors()) == 1


def test_wrong_structure_is_reported(tmp_path):
    wrong = tmp_path / "PathMapping.json"
    wrong.write_text('{"mappings": {"windows": "P:/"}}')
    assert PandoraPathMap.loadMappings([str(wrong)]) == []
    assert len(PandoraPathMap.getLoadErrors()) == 1
