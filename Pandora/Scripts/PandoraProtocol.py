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


"""Parses the commands, which Pandora components send to each other.

Commands are text files in a shared folder. They used to be evaluated as
Python code, which allowed everyone with write access to that folder to run
arbitrary code on the receiving machine. The functions in this module accept
the same text, but only as data.
"""

import ast


# methods of the coordinator, which can be called through the "command" setting
COORDINATOR_COMMANDS = (
    "searchUncollectedRnd",
    "collectOutput",
    "notifyWorkstations",
    "notifySlaves",
    "restartGDrive",
)


def parseCommand(text):
    """Returns the command list of a command file or None if it is invalid.

    A command is a non-empty list of literals, e.g. ["deleteJob", "abc123"].
    """
    try:
        command = ast.literal_eval(text.strip())
    except Exception:
        return None

    if not isinstance(command, list) or not command:
        return None

    return command


def parseCall(text):
    """Parses a call like "self.shutdownPC(restart=True)".

    Returns (name, args, kwargs) or None if the text is anything else than a
    single method call on self with literal arguments.
    """
    try:
        tree = ast.parse(text.strip().rstrip(";").strip(), mode="eval")
    except Exception:
        return None

    call = tree.body
    if not isinstance(call, ast.Call):
        return None

    func = call.func
    if not (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "self"
    ):
        return None

    try:
        args = [ast.literal_eval(arg) for arg in call.args]
        kwargs = {}
        for keyword in call.keywords:
            if keyword.arg is None:
                return None

            kwargs[keyword.arg] = ast.literal_eval(keyword.value)
    except Exception:
        return None

    return func.attr, args, kwargs


def runCall(obj, text, allowed):
    """Executes a call on obj if the method is in allowed. Returns if it ran."""
    call = parseCall(text)
    if call is None:
        return False

    name, args, kwargs = call
    if name.startswith("_") or name not in allowed:
        return False

    func = getattr(obj, name, None)
    if not callable(func):
        return False

    func(*args, **kwargs)
    return True
