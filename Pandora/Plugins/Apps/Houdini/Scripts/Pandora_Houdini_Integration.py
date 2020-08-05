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

import os, sys
import traceback, time, platform, shutil

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from functools import wraps


class Pandora_Houdini_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.examplePath = ""
        if platform.system() == "Windows":
            for i in ["18.0", "17.5", "17.0", "16.5", "16.0"]:
                path = os.environ["userprofile"] + "\\Documents\\houdini" + i
                if os.path.exists(path):
                    self.examplePath = path
                    break

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Pandora_Plugin_Houdini_Integration %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].plugin.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                if hasattr(args[0].core, "writeErrorLog"):
                    args[0].core.writeErrorLog(erStr)
                else:
                    QMessageBox.warning(
                        args[0].core.messageParent, "Pandora Integration", erStr
                    )

        return func_wrapper

    @err_decorator
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            defaultpath = os.path.join(self.getInstallPath(), "bin", "hython.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_decorator
    def getInstallPath(self, version=None):
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Side Effects Software",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            if version is None:
                validVersion = (_winreg.QueryValueEx(key, "ActiveVersion"))[0]
            else:
                houVersions = []
                try:
                    i = 0
                    while True:
                        houVers = _winreg.EnumKey(key, i)
                        if houVers.startswith("Houdini "):
                            houVersions.append(houVers.replace("Houdini ", ""))
                        i += 1
                except WindowsError:
                    pass

                simVersions = []
                for i in houVersions:
                    versData = i.split(".")
                    if (
                        len(versData) == 3
                        and versData[0] == version.split(".")[0]
                        and versData[1] == version.split(".")[1]
                    ):
                        simVersions.append(i)

                if version in houVersions:
                    validVersion = version
                elif len(simVersions) > 0:
                    validVersion = simVersions[-1]
                elif len(houVersions) > 0:
                    validVersion = houVersions[-1]
                else:
                    self.writeLog("No Houdini found in registry", 0)
                    return None

            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Side Effects Software\\Houdini " + validVersion,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            installDir = (_winreg.QueryValueEx(key, "InstallPath"))[0]
            if installDir is None:
                return ""
            else:
                return installDir
        except:
            return ""

    @err_decorator
    def integrationAdd(self, origin):
        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, "Select Houdini folder", self.examplePath
        )

        if path == "":
            return False

        result = self.writeHoudiniFiles(path)

        if result:
            QMessageBox.information(
                self.core.messageParent,
                "Pandora Integration",
                "Pandora integration was added successfully",
            )
            return path

        return result

    @err_decorator
    def integrationRemove(self, origin, installPath):
        result = self.removeIntegration(installPath)

        if result:
            QMessageBox.information(
                self.core.messageParent,
                "Pandora Integration",
                "Pandora integration was removed successfully",
            )

        return result

    def writeHoudiniFiles(self, houdiniPath):
        try:

            # python rc
            pyrc = os.path.join(houdiniPath, "python2.7libs", "pythonrc.py")

            if not os.path.exists(houdiniPath):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Pandora Installation",
                    "Invalid Houdini path: %s.\n\nThe path has to be the Houdini preferences folder, which usually looks like this: (with your Houdini version):\n\n%s"
                    % (houdiniPath, self.examplePath),
                )
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )

            packagePath = os.path.join(houdiniPath, "packages", "Pandora.json")

            if os.path.exists(packagePath):
                os.remove(packagePath)

            if not os.path.exists(os.path.dirname(packagePath)):
                os.makedirs(os.path.dirname(packagePath))

            origpackagePath = os.path.join(integrationBase, "Pandora.json")
            shutil.copy2(origpackagePath, packagePath)

            with open(packagePath, "r") as init:
                initStr = init.read()

            with open(packagePath, "w") as init:
                initStr = initStr.replace(
                    "PANDORAROOT", "%s" % self.core.pandoraRoot.replace("\\", "/")
                )
                init.write(initStr)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the installation of the Houdini integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Pandora Integration", msgStr)
            return False

    def removeIntegration(self, installPath):
        try:
            packagePath = os.path.join(installBase, "packages", "Pandora.json")

            for i in [
                packagePath,
            ]:
                if os.path.exists(i):
                    os.remove(i)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Houdini integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Pandora Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders, pItem):
        try:
            houItem = QTreeWidgetItem(["Houdini"])
            pItem.addChild(houItem)

            houdiniPath = self.examplePath

            if houdiniPath != None and os.path.exists(houdiniPath):
                houItem.setCheckState(0, Qt.Checked)
                houItem.setText(1, houdiniPath)
                houItem.setToolTip(0, houdiniPath)
            else:
                houItem.setCheckState(0, Qt.Unchecked)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Pandora Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, houItem, result):
        try:
            installLocs = []

            if houItem.checkState(0) == Qt.Checked and os.path.exists(houItem.text(1)):
                result["Houdini integration"] = self.writeHoudiniFiles(houItem.text(1))
                if result["Houdini integration"]:
                    installLocs.append(houItem.text(1))

            return installLocs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Pandora Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False
