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


"""Translates paths between operating systems.

A renderfarm with Windows, Linux and macOS machines sees the same storage
under different paths. The mapping rules are stored in PathMapping.json:

{"mappings": [
    {"windows": "P:/", "linux": "/mnt/projects", "darwin": "/Volumes/projects"}
]}
"""

import os
import json

import PandoraPaths


PLATFORMS = ("windows", "linux", "darwin")
MAPPING_FILE = "PathMapping.json"

_loadErrors = []


def getLoadErrors():
    """Returns the errors of the last loadMappings call."""
    return list(_loadErrors)


def getMappingFiles(coordBasePath, userConfigDir):
    """The mapping of this machine has priority over the mapping of the farm."""
    return [
        os.path.join(userConfigDir, MAPPING_FILE),
        os.path.join(coordBasePath, MAPPING_FILE),
    ]


def loadMappings(paths):
    del _loadErrors[:]
    mappings = []
    for path in paths:
        if not path or not os.path.exists(path):
            continue

        try:
            with open(path, "r") as f:
                data = json.load(f)

            rules = data.get("mappings", [])
            if not isinstance(rules, list):
                raise ValueError('"mappings" is not a list')

            for rule in rules:
                if not isinstance(rule, dict):
                    raise ValueError("mapping is not an object: %r" % (rule,))

                mappings.append(rule)
        except Exception as e:
            _loadErrors.append("Cannot read path mapping %s: %s" % (path, e))

    return mappings


def _normalize(path):
    return path.replace("\\", "/")


def _stripPrefix(prefix):
    prefix = _normalize(prefix)
    # keep "/" and "//" intact, they are meaningful roots
    stripped = prefix.rstrip("/")
    return stripped if stripped else prefix


def _matchPrefix(path, prefix, caseSensitive):
    """Returns the remainder of path behind prefix or None if it doesn't match."""
    cPath = path if caseSensitive else path.lower()
    cPrefix = prefix if caseSensitive else prefix.lower()
    if not cPath.startswith(cPrefix):
        return None

    rest = path[len(prefix):]
    if rest and not rest.startswith("/") and not prefix.endswith("/"):
        # "P:/proj" must not match "P:/projects"
        return None

    return rest


def mapPath(path, mappings, targetOs=None):
    """Converts path to its location on targetOs (default: this machine)."""
    if not path or not mappings:
        return path

    targetOs = targetOs or PandoraPaths.getPlatform()
    nPath = _normalize(path)

    best = None
    for rule in mappings:
        target = rule.get(targetOs)
        if not target:
            continue

        for platform in PLATFORMS:
            source = rule.get(platform)
            if not source:
                continue

            prefix = _stripPrefix(source)
            rest = _matchPrefix(nPath, prefix, caseSensitive=platform != "windows")
            if rest is None:
                continue

            if best is None or len(prefix) > len(best[0]):
                best = (prefix, rest, target)

    if best is None:
        return path

    prefix, rest, target = best
    mapped = _stripPrefix(target)
    if rest:
        mapped = mapped.rstrip("/") + "/" + rest.lstrip("/")
    elif nPath.endswith("/") and not mapped.endswith("/"):
        mapped += "/"

    if targetOs == "windows":
        mapped = mapped.replace("/", "\\")
        # "P:" is the current directory on the drive, "P:\" is its root
        if len(mapped) == 2 and mapped[1] == ":":
            mapped += "\\"

    return mapped
