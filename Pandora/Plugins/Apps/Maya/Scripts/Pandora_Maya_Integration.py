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
from functools import wraps

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg


class Pandora_Maya_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = os.environ["userprofile"] + "\\Documents\\maya\\2020"

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Pandora_Plugin_Maya_Integration %s:\n%s\n\n%s" % (
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
            defaultpath = os.path.join(self.getInstallPath(), "bin", "Render.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_decorator
    def getInstallPath(self, version=None):
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Autodesk\\Maya",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            mayaVersions = []
            try:
                i = 0
                while True:
                    mayaVers = _winreg.EnumKey(key, i)
                    if sys.version[0] == "2":
                        umv = unicode(mayaVers)
                    else:
                        umv = mayaVers

                    if umv.isnumeric():
                        mayaVersions.append(mayaVers)
                    i += 1
            except WindowsError:
                pass

            if version is None:
                validVersion = mayaVersions[-1]
            elif version in mayaVersions:
                validVersion = version
            else:
                for i in mayaVersions:
                    if float(i) > float(version):
                        validVersion = i
                        break
                else:
                    self.writeLog("No valid Maya found in registry", 0)
                    return None

            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Autodesk\\Maya\\%s\\Setup\\InstallPath" % validVersion,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            installDir = (_winreg.QueryValueEx(key, "MAYA_INSTALL_LOCATION"))[0]

            if installDir is None:
                return ""
            else:
                return installDir
        except:
            return ""

    @err_decorator
    def integrationAdd(self, origin):
        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, "Select Maya folder", os.path.dirname(self.examplePath)
        )

        if path == "":
            return False

        result = self.writeMayaFiles(path)

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

    def writeMayaFiles(self, mayaPath):
        try:
            if not os.path.exists(os.path.join(mayaPath, "scripts")) or not os.path.exists(
                os.path.join(mayaPath, "prefs", "shelves")
            ):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Pandora Installation",
                    "Invalid Maya path: %s.\n\nThe path has to be the Maya preferences folder, which usually looks like this: (with your username and Maya version):\n\nC:\\Users\\Richard\\Documents\\maya\\2019"
                    % mayaPath,
                    QMessageBox.Ok,
                )
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            addedFiles = []

            origSetupFile = os.path.join(integrationBase, "userSetup.py")
            with open(origSetupFile, "r") as mFile:
                setupString = mFile.read()

            pandoraSetup = os.path.join(mayaPath, "scripts", "userSetup.py")

            if os.path.exists(pandoraSetup):
                with open(pandoraSetup, "r") as setupfile:
                    content = setupfile.read()

                if not setupString in content:
                    if "#>>>PandoraStart" in content and "#<<<PandoraEnd" in content:
                        content = (
                            setupString
                            + content[: content.find("#>>>PandoraStart")]
                            + content[
                                content.find("#<<<PandoraEnd") + len("#<<<PandoraEnd") :
                            ]
                        )
                        with open(pandoraSetup, "w") as rcfile:
                            rcfile.write(content)
                    else:
                        with open(pandoraSetup, "w") as setupfile:
                            setupfile.write(setupString + content)
            else:
                open(pandoraSetup, "a").close()
                with open(pandoraSetup, "w") as setupfile:
                    setupfile.write(setupString)

            addedFiles.append(pandoraSetup)

            initpath = os.path.join(mayaPath, "scripts", "PandoraInit.py")

            if os.path.exists(initpath):
                os.remove(initpath)

            if os.path.exists(initpath + "c"):
                os.remove(initpath + "c")

            origInitFile = os.path.join(integrationBase, "PandoraInit.py")
            shutil.copy2(origInitFile, initpath)
            addedFiles.append(initpath)

            with open(initpath, "r") as init:
                initStr = init.read()

            with open(initpath, "w") as init:
                initStr = initStr.replace(
                    "PANDORAROOT", '"%s"' % self.core.pandoraRoot.replace("\\", "/")
                )
                init.write(initStr)

            shelfpath = os.path.join(mayaPath, "prefs", "shelves", "shelf_Pandora.mel")

            if os.path.exists(shelfpath):
                os.remove(shelfpath)

            origShelfFile = os.path.join(integrationBase, "shelf_Pandora.mel")
            shutil.copy2(origShelfFile, shelfpath)
            addedFiles.append(shelfpath)

            with open(shelfpath, "r") as init:
                initStr = init.read()

            with open(shelfpath, "w") as init:
                initStr = initStr.replace(
                    "PANDORAROOT", self.core.pandoraRoot.replace("\\", "\\\\")
                )
                init.write(initStr)

            icons = [
                "pandoraSubmitter.png",
                "pandoraRenderHandler.png",
                "pandoraSettings.png",
            ]

            for i in icons:
                iconPath = os.path.abspath(
                    os.path.join(
                        __file__,
                        os.pardir,
                        os.pardir,
                        os.pardir,
                        os.pardir,
                        os.pardir,
                        "Scripts",
                        "UserInterfacesPandora",
                        i,
                    )
                )
                tPath = os.path.join(mayaPath, "prefs", "icons", i)

                if os.path.exists(tPath):
                    os.remove(tPath)

                shutil.copy2(iconPath, tPath)
                addedFiles.append(tPath)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the installation of the Maya integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Pandora Integration", msgStr)
            return False

    def removeIntegration(self, installPath):
        try:
            initPy = os.path.join(installPath, "scripts", "PandoraInit.py")
            initPyc = os.path.join(installPath, "scripts", "PandoraInit.pyc")
            shelfpath = os.path.join(installPath, "prefs", "shelves", "shelf_Pandora.mel")

            for i in [initPy, initPyc, shelfpath]:
                if os.path.exists(i):
                    os.remove(i)

            userSetup = os.path.join(installPath, "scripts", "userSetup.py")

            if os.path.exists(userSetup):
                with open(userSetup, "r") as usFile:
                    text = usFile.read()

                if "#>>>PandoraStart" in text and "#<<<PandoraEnd" in text:
                    text = (
                        text[: text.find("#>>>PandoraStart")]
                        + text[text.find("#<<<PandoraEnd") + len("#<<<PandoraEnd") :]
                    )

                    otherChars = [x for x in text if x != " "]
                    if len(otherChars) == 0:
                        os.remove(userSetup)
                    else:
                        with open(userSetup, "w") as usFile:
                            usFile.write(text)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Maya integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Pandora Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders, pItem):
        try:
            if platform.system() == "Windows":
                mayaPath = [
                    os.path.join(userFolders["Documents"], "maya", "2016"),
                    os.path.join(userFolders["Documents"], "maya", "2017"),
                    os.path.join(userFolders["Documents"], "maya", "2018"),
                    os.path.join(userFolders["Documents"], "maya", "2019"),
                    os.path.join(userFolders["Documents"], "maya", "2020"),
                ]
            elif platform.system() == "Linux":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                mayaPath = [
                    os.path.join("/home", userName, "maya", "2016"),
                    os.path.join("/home", userName, "maya", "2017"),
                    os.path.join("/home", userName, "maya", "2018"),
                    os.path.join("/home", userName, "maya", "2019"),
                    os.path.join("/home", userName, "maya", "2020"),
                ]
            elif platform.system() == "Darwin":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                mayaPath = [
                    "/Users/%s/Library/Preferences/Autodesk/maya/2016" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2017" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2018" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2019" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2020" % userName,
                ]

            mayaItem = QTreeWidgetItem(["Maya"])
            mayaItem.setCheckState(0, Qt.Checked)
            pItem.addChild(mayaItem)

            mayacItem = QTreeWidgetItem(["Custom"])
            mayacItem.setToolTip(0, 'e.g. "%s"' % self.examplePath)
            mayacItem.setToolTip(1, 'e.g. "%s"' % self.examplePath)
            mayacItem.setCheckState(0, Qt.Unchecked)
            mayaItem.addChild(mayacItem)
            # mayaItem.setExpanded(True)

            activeVersion = False
            for i in mayaPath:
                mayavItem = QTreeWidgetItem([i[-4:]])
                mayaItem.addChild(mayavItem)

                if os.path.exists(i):
                    mayavItem.setCheckState(0, Qt.Checked)
                    mayavItem.setText(1, i)
                    mayavItem.setToolTip(0, i)
                    mayacItem.setText(1, i)
                    activeVersion = True
                else:
                    mayavItem.setCheckState(0, Qt.Unchecked)
                    mayavItem.setFlags(~Qt.ItemIsEnabled)

            if not activeVersion:
                mayaItem.setCheckState(0, Qt.Unchecked)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Pandora Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, mayaItem, result):
        try:
            mayaPaths = []
            installLocs = []

            if mayaItem.checkState(0) != Qt.Checked:
                return installLocs

            for i in range(mayaItem.childCount()):
                item = mayaItem.child(i)
                if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
                    mayaPaths.append(item.text(1))

            for i in mayaPaths:
                result["Maya integration"] = self.writeMayaFiles(i)
                if result["Maya integration"]:
                    installLocs.append(i)

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
