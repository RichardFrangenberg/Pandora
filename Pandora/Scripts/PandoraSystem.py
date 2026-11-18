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


"""Functions, which depend on the operating system.

Pandora was written for Windows. The functions in this module provide the
information Pandora needs (memory, shutdown, DCC executables) on Windows,
Linux and macOS.
"""

import os
import glob
import shutil
import subprocess

import PandoraPaths


def getTotalMemory():
    """Returns the installed memory in GB (0 if it cannot be detected)."""
    try:
        import psutil

        return int(round(psutil.virtual_memory().total / float(1024 ** 3)))
    except Exception:
        pass

    try:
        memBytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        return int(round(memBytes / float(1024 ** 3)))
    except Exception:
        return 0


def getShutdownCommand(restart=False, platform=None):
    """Returns the command (argument list), which shuts down or restarts this machine."""
    platform = platform or PandoraPaths.getPlatform()
    if platform == "windows":
        cmd = ["shutdown", "-t", "0", "-f"]
        if restart:
            cmd.insert(3, "-r")

        return cmd

    return ["shutdown", "-r" if restart else "-h", "now"]


def killProcessTree(pid):
    """Kills a process and all processes it started."""
    import psutil

    proc = psutil.Process(pid)
    for child in proc.children(recursive=True):
        try:
            child.kill()
        except Exception:
            pass

    proc.kill()


def startDetached(args):
    """Starts a process, which keeps running when this process exits."""
    kwargs = {}
    if PandoraPaths.getPlatform() == "windows":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # detached, new process group
    else:
        kwargs["start_new_session"] = True

    return subprocess.Popen(args, close_fds=True, **kwargs)


# Default locations of the executables, which render the jobs. {version} is
# replaced by the requested version or by "*" if no version is requested.
EXECUTABLES = {
    "Blender": {
        "names": ["blender"],
        "linux": [
            "/opt/blender*{version}*/blender",
            "/usr/local/blender*{version}*/blender",
            "/snap/bin/blender",
            "/var/lib/snapd/snap/bin/blender",
        ],
        "darwin": [
            "/Applications/Blender*{version}*.app/Contents/MacOS/Blender",
            "/Applications/Blender.app/Contents/MacOS/Blender",
        ],
    },
    "Houdini": {
        "names": ["hython"],
        "env": ["HFS"],
        "envSuffix": ["bin", "hython"],
        "linux": ["/opt/hfs{version}*/bin/hython"],
        "darwin": [
            "/Applications/Houdini/Houdini{version}*/Frameworks/Houdini.framework/Versions/Current/Resources/bin/hython"
        ],
    },
    "Maya": {
        "names": ["Render"],
        "env": ["MAYA_LOCATION"],
        "envSuffix": ["bin", "Render"],
        "linux": ["/usr/autodesk/maya{version}*/bin/Render"],
        "darwin": ["/Applications/Autodesk/maya{version}*/Maya.app/Contents/bin/Render"],
    },
}


def _versionKey(path):
    """Sort key, which orders paths by the numbers they contain (newest last)."""
    numbers = []
    current = ""
    for char in path:
        if char.isdigit():
            current += char
        elif current:
            numbers.append(int(current))
            current = ""

    if current:
        numbers.append(int(current))

    return numbers


def findExecutable(program, version=None, platform=None, env=None, exists=None, which=None):
    """Returns the path of the executable, which renders jobs of a program.

    The executable is searched in the default install locations of the
    requested version, in the environment (e.g. HFS) and in the PATH.
    Returns "" if no executable was found.
    """
    data = EXECUTABLES.get(program)
    if data is None:
        return ""

    platform = platform or PandoraPaths.getPlatform()
    if env is None:
        env = os.environ

    exists = exists or os.path.exists
    which = which or getattr(shutil, "which", None)

    def search(pattern):
        matches = sorted(glob.glob(pattern), key=_versionKey)
        return matches[-1] if matches else ""

    patterns = data.get(platform, [])
    if version:
        # e.g. "19.5.303" -> "19.5.303", "19.5", "19"
        parts = str(version).split(".")
        versions = [".".join(parts[:i]) for i in range(len(parts), 0, -1)]
        for curVersion in versions:
            for pattern in patterns:
                if "{version}" not in pattern:
                    continue

                path = search(pattern.replace("{version}", curVersion))
                if path:
                    return path

    for envVar in data.get("env", []):
        if env.get(envVar):
            path = os.path.join(env[envVar], *data["envSuffix"])
            if exists(path):
                return path

    if which:
        for name in data["names"]:
            path = which(name)
            if path:
                return path

    for pattern in patterns:
        path = search(pattern.replace("{version}", ""))
        if path:
            return path

    return ""
