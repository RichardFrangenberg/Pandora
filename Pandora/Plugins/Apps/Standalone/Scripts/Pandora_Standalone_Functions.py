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
# Copyright (C) 2016-2020 Richard Frangenberg
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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

import os, sys, traceback, time, shutil
from functools import wraps


class Pandora_Standalone_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Pandora_Plugin_Standalone %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].plugin.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self, origin):
        return

    @err_decorator
    def getCurrentFileName(self, origin, path=True):
        return ""

    @err_decorator
    def setRCStyle(self, origin, rcmenu):
        pass

    @err_decorator
    def openScene(self, origin, filepath):
        return False

    @err_decorator
    def saveScene(self, origin, filepath, underscore=True):
        return

    @err_decorator
    def onPandoraSettingsOpen(self, origin):
        pass

    @err_decorator
    def createWinStartMenu(self, origin):
        startMenuPath = os.path.join(
            os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs"
        )
        trayStartup = os.path.join(startMenuPath, "Startup", "Pandora Tray.lnk")
        trayStartMenu = os.path.join(startMenuPath, "Pandora", "Pandora Tray.lnk")
        trayLnk = os.path.join(self.core.pandoraRoot, "Tools", "Pandora Tray.lnk")

        toolList = [
            "Pandora Tray",
            "Pandora Render Handler",
            "Pandora Slave",
            "Pandora Coordinator",
            "Pandora Settings",
        ]

        for i in [trayStartMenu, trayStartup]:
            if not os.path.exists(os.path.dirname(i)):
                try:
                    os.makedirs(os.path.dirname(i))
                except:
                    pass

        if os.path.exists(trayStartup):
            os.remove(trayStartup)

        if os.path.exists(trayLnk):
            if os.path.exists(os.path.dirname(trayStartup)):
                shutil.copy2(trayLnk, trayStartup)
            else:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Pandora",
                    "could not create PandoraTray autostart entry",
                )

        for i in toolList:
            source = os.path.join(self.core.pandoraRoot, "Tools", i + ".lnk")
            target = os.path.join(startMenuPath, "Pandora", i + ".lnk")
            if not os.path.exists(os.path.dirname(source)):
                os.makedirs(os.path.dirname(source))

            self.core.createShortcut(
                source,
                vTarget=("%s\\Python37\\%s.exe" % (self.core.pandoraRoot, i)),
                args=('"%s\\Scripts\\%s.py"' % (self.core.pandoraRoot, i.replace(" ", ""))),
            )
            if os.path.exists(source) and os.path.exists(os.path.dirname(target)):
                shutil.copy2(source, target)
            else:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Pandora",
                    "could not create %s startmenu entry" % i,
                )
