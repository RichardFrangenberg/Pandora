# -*- coding: utf-8 -*-
#
####################################################
#
# Pandora - Renderfarm Manager
#
# https://prism-pipeline.com/pandora/
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2026 Richard Frangenberg and contributors
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Pandora.
#
# Pandora is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pandora is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pandora.  If not, see <https://www.gnu.org/licenses/>.


"""Platform dependent locations and environment overrides for Pandora.

Windows keeps the locations Pandora has always used, so existing
installations are not affected. Linux and macOS use the conventional
locations of those platforms.
"""

import os
import sys


def getPlatform():
    """Returns "windows", "linux" or "darwin"."""
    if sys.platform.startswith("win"):
        return "windows"
    elif sys.platform == "darwin":
        return "darwin"

    return "linux"


def _getHome(env):
    return env.get("HOME") or os.path.expanduser("~")


def getUserConfigDir(platform=None, env=None):
    """Returns the directory, which contains the Pandora user preferences."""
    platform = platform or getPlatform()
    if env is None:
        env = os.environ

    if platform == "windows":
        userProfile = env.get("USERPROFILE") or env.get("userprofile")
        if not userProfile:
            userProfile = os.path.expanduser("~")

        return os.path.join(userProfile, "Documents", "Pandora")
    elif platform == "darwin":
        return os.path.join(_getHome(env), "Library", "Application Support", "Pandora")

    configHome = env.get("XDG_CONFIG_HOME") or os.path.join(_getHome(env), ".config")
    return os.path.join(configHome, "Pandora")


def getUserConfigPath(platform=None, env=None):
    """Returns the path of Pandora.json. PANDORA_CONFIG overrides the default."""
    if env is None:
        env = os.environ

    if env.get("PANDORA_CONFIG"):
        return env["PANDORA_CONFIG"]

    return os.path.join(getUserConfigDir(platform=platform, env=env), "Pandora.json")


def parseBool(value):
    val = str(value).strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    elif val in ("0", "false", "no", "off"):
        return False

    raise ValueError("invalid boolean value: %r" % value)


def getEnvOverrides(env=None):
    """Returns the settings, which are defined through environment variables.

    A key is only present if its variable is set. This allows to run Pandora
    without a Pandora.json, e.g. in a container.
    """
    if env is None:
        env = os.environ

    overrides = {}
    if env.get("PANDORA_ROOT"):
        overrides["rootPath"] = env["PANDORA_ROOT"]

    if env.get("PANDORA_REPOSITORY"):
        overrides["repositoryPath"] = env["PANDORA_REPOSITORY"]

    if env.get("PANDORA_LOCAL_MODE"):
        try:
            overrides["localMode"] = parseBool(env["PANDORA_LOCAL_MODE"])
        except ValueError:
            raise ValueError(
                "PANDORA_LOCAL_MODE must be true or false, not %r"
                % env["PANDORA_LOCAL_MODE"]
            )

    return overrides
