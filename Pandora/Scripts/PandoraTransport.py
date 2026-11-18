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


"""Transport of the commands between coordinator, slaves and workstations.

The coordinator doesn't access command files directly, but through a
Transport. FileTransport implements the folder structure Pandora has always
used, so it is compatible with existing slaves and workstations. Other
transports (e.g. over the network) can be added without changing the
coordinator logic.

Only commands are transported. Job files, logs, slave states and rendered
images are still accessed directly in the Pandora root folder.
"""

import os
import io
import time


class Transport(object):
    """Interface for the command channels of the coordinator.

    The command handles returned by the list functions are only meaningful
    for the transport, which created them.
    """

    def listWorkstationCommands(self, wsName):
        """Returns handles of the pending commands of a workstation (sorted)."""
        raise NotImplementedError

    def listSlaveCommands(self, slaveName):
        """Returns handles of the pending commands of a slave (sorted)."""
        raise NotImplementedError

    def readCommand(self, handle):
        """Returns the text of a command."""
        raise NotImplementedError

    def getCommandAge(self, handle):
        """Returns the seconds since the command was written."""
        raise NotImplementedError

    def removeCommand(self, handle):
        raise NotImplementedError

    def sendToSlave(self, slaveName, cmd):
        """Sends a command to a slave and returns its handle."""
        raise NotImplementedError


class FileTransport(Transport):
    """Commands are text files in the Pandora root folder.

    <root>/Workstations/WS_<name>/Commands/handlerOut_*     workstation -> coordinator
    <root>/Slaves/S_<name>/Communication/slaveOut_*         slave -> coordinator
    <root>/Slaves/S_<name>/Communication/slaveIn_*          coordinator -> slave
    """

    def __init__(self, rootPath):
        self.rootPath = rootPath

    def getWorkstationCommandDir(self, wsName):
        return os.path.join(self.rootPath, "Workstations", "WS_%s" % wsName, "Commands")

    def getSlaveCommandDir(self, slaveName):
        return os.path.join(self.rootPath, "Slaves", "S_%s" % slaveName, "Communication")

    def _listCommands(self, cmdDir, prefix):
        if not os.path.isdir(cmdDir):
            return []

        return [
            os.path.join(cmdDir, x)
            for x in sorted(os.listdir(cmdDir))
            if x.startswith(prefix)
        ]

    def listWorkstationCommands(self, wsName):
        return self._listCommands(self.getWorkstationCommandDir(wsName), "handlerOut_")

    def listSlaveCommands(self, slaveName):
        return self._listCommands(self.getSlaveCommandDir(slaveName), "slaveOut_")

    def readCommand(self, handle):
        with io.open(handle, "r", errors="replace") as cmdFile:
            return cmdFile.read()

    def getCommandAge(self, handle):
        return time.time() - os.path.getmtime(handle)

    def removeCommand(self, handle):
        os.remove(handle)

    def sendToSlave(self, slaveName, cmd):
        cmdDir = self.getSlaveCommandDir(slaveName)
        if not os.path.exists(cmdDir):
            os.makedirs(cmdDir)

        curNum = 1
        for i in os.listdir(cmdDir):
            if not i.startswith("slaveIn_"):
                continue

            parts = i.split("_")
            if len(parts) < 2 or not parts[1].isdigit():
                continue

            if int(parts[1]) >= curNum:
                curNum = int(parts[1]) + 1

        cmdFile = os.path.join(
            cmdDir, "slaveIn_%s_%s.txt" % (format(curNum, "04"), time.time())
        )

        with open(cmdFile, "w") as cFile:
            cFile.write(str(cmd))

        return cmdFile
