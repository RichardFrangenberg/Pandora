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
import traceback, time, platform, shutil, socket
from functools import wraps

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg


class Pandora_Blender_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = self.getInstallPath()

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Pandora_Plugin_Blender_Integration %s:\n%s\n\n%s" % (
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
            execPath = os.path.join(os.path.dirname(self.examplePath), "blender.exe")

        return execPath

    @err_decorator
    def integrationAdd(self, origin):
        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, "Select Blender folder", self.examplePath
        )

        if path == "":
            return False

        result = self.writeBlenderFiles(path)

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

    @err_decorator
    def getInstallPath(self):
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Classes\\blendfile\\shell\\open\\command",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
            blenderPath = (
                (_winreg.QueryValueEx(key, ""))[0].split(' "%1"')[0].replace('"', "")
            )

            if os.path.exists(blenderPath):
                return blenderPath
            else:
                return ""

        except:
            return ""

    def writeBlenderFiles(self, blenderPath):
        try:
            if not os.path.exists(os.path.join(blenderPath, "scripts", "startup")):
                if os.path.exists(blenderPath):
                    for f in os.listdir(blenderPath):
                        try:
                            float(f)
                        except ValueError:
                            pass
                        else:
                            blenderPath = os.path.join(blenderPath, f)

            if not os.path.exists(os.path.join(blenderPath, "scripts", "startup")):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Pandora Integration",
                    "Invalid Blender path: %s.\n\nThe path has to be the Blender version folder in the installation folder, which usually looks like this: (with your Blender version):\n\n%s"
                    % (blenderPath, self.examplePath),
                    QMessageBox.Ok,
                )
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )

            # pandoraInit
            initpath = os.path.join(blenderPath, "scripts", "startup", "PandoraInit.py")
            addedFiles = []

            if os.path.exists(initpath):
                os.remove(initpath)

            if os.path.exists(initpath + "c"):
                os.remove(initpath + "c")

            baseinitfile = os.path.join(integrationBase, "PandoraInit.py")
            shutil.copy2(baseinitfile, initpath)
            addedFiles.append(initpath)

            with open(initpath, "r") as init:
                initStr = init.read()

            with open(initpath, "w") as init:
                initStr = initStr.replace(
                    "PANDORAROOT", '"%s"' % self.core.pandoraRoot.replace("\\", "/")
                )
                init.write(initStr)

            topbarPath = os.path.join(
                blenderPath, "scripts", "startup", "bl_ui", "space_topbar.py"
            )
            hMenuStr = 'layout.menu("TOPBAR_MT_help")'
            fClassStr = "class TOPBAR_MT_file(Menu):"
            hClassName = "TOPBAR_MT_help,"
            baseTopbarFile1 = os.path.join(integrationBase, "space_topbar1.py")

            with open(baseTopbarFile1, "r") as init:
                bTbStr1 = init.read()

            baseTopbarFile2 = os.path.join(integrationBase, "space_topbar2.py")

            with open(baseTopbarFile2, "r") as init:
                bTbStr2 = init.read()

            if not os.path.exists(topbarPath):
                topbarPath = os.path.join(
                    blenderPath, "scripts", "startup", "bl_ui", "space_info.py"
                )
                hMenuStr = 'layout.menu("INFO_MT_help")'
                fClassStr = "class INFO_MT_file(Menu):"
                hClassName = "INFO_MT_help,"

            if os.path.exists(topbarPath):
                with open(topbarPath, "r") as init:
                    tbStr = init.read()

                for i in range(2):
                    if "#>>>PandoraStart" in tbStr and "#<<<PandoraEnd" in tbStr:
                        tbStr = (
                            tbStr[: tbStr.find("#>>>PandoraStart")]
                            + tbStr[tbStr.find("#<<<PandoraEnd") + len("#<<<PandoraEnd") :]
                        )
                tbStr = tbStr.replace("    TOPBAR_MT_pandora,", "")

                tbStr = tbStr.replace(hMenuStr, hMenuStr + bTbStr1)
                tbStr = tbStr.replace(fClassStr, bTbStr2 + fClassStr)
                tbStr = tbStr.replace(hClassName, hClassName + "\n    TOPBAR_MT_pandora,")

                if not os.path.exists(topbarPath + ".bak"):
                    shutil.copy2(topbarPath, topbarPath + ".bak")

                with open(topbarPath, "w") as init:
                    init.write(tbStr)

            if platform.system() == "Windows":
                baseWinfile = os.path.join(integrationBase, "qminimal.dll")
                winPath = os.path.join(
                    os.path.dirname(blenderPath), "platforms", "qminimal.dll"
                )

                if not os.path.exists(os.path.dirname(winPath)):
                    os.mkdir(os.path.dirname(winPath))

                if not os.path.exists(winPath):
                    shutil.copy2(baseWinfile, winPath)

                baseWinfile = os.path.join(integrationBase, "qoffscreen.dll")
                winPath = os.path.join(
                    os.path.dirname(blenderPath), "platforms", "qoffscreen.dll"
                )

                if not os.path.exists(winPath):
                    shutil.copy2(baseWinfile, winPath)

                baseWinfile = os.path.join(integrationBase, "qwindows.dll")
                winPath = os.path.join(
                    os.path.dirname(blenderPath), "platforms", "qwindows.dll"
                )

                if not os.path.exists(winPath):
                    shutil.copy2(baseWinfile, winPath)

                baseWinfile = os.path.join(integrationBase, "python3.dll")
                winPath = os.path.join(os.path.dirname(blenderPath), "python3.dll")

                if not os.path.exists(winPath):
                    shutil.copy2(baseWinfile, winPath)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the installation of the Blender integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Pandora Integration", msgStr)
            return False

    def removeIntegration(self, installPath):
        try:
            if not os.path.exists(os.path.join(installPath, "scripts", "startup")):
                if os.path.exists(installPath):
                    for f in os.listdir(installPath):
                        try:
                            float(f)
                        except ValueError:
                            pass
                        else:
                            installPath = os.path.join(installPath, f)

            initPy = os.path.join(installPath, "scripts", "startup", "PandoraInit.py")

            for i in [initPy]:
                if os.path.exists(i):
                    os.remove(i)

            topbarPath = os.path.join(
                installPath, "scripts", "startup", "bl_ui", "space_topbar.py"
            )

            if not os.path.exists(topbarPath):
                topbarPath = os.path.join(
                    installPath, "scripts", "startup", "bl_ui", "space_info.py"
                )

            if os.path.exists(topbarPath):
                with open(topbarPath, "r") as init:
                    tbStr = init.read()

                for i in range(2):
                    if "#>>>PandoraStart" in tbStr and "#<<<PandoraEnd" in tbStr:
                        tbStr = (
                            tbStr[: tbStr.find("#>>>PandoraStart")]
                            + tbStr[tbStr.find("#<<<PandoraEnd") + len("#<<<PandoraEnd") :]
                        )

                tbStr = tbStr.replace("\n    TOPBAR_MT_pandora,", "")

                with open(topbarPath, "w") as init:
                    init.write(tbStr)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the removal of the Blender integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Pandora Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders, pItem):
        try:
            bldItem = QTreeWidgetItem(["Blender"])
            pItem.addChild(bldItem)

            blenderPath = ""
            if platform.system() == "Windows":
                executable = self.getInstallPath()
                if executable is not None:
                    blenderPath = os.path.join(os.path.dirname(executable), "2.79")

            if os.path.exists(blenderPath):
                bldItem.setCheckState(0, Qt.Checked)
                bldItem.setText(1, blenderPath)
                bldItem.setToolTip(0, blenderPath)
            else:
                bldItem.setCheckState(0, Qt.Unchecked)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Pandora Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, bldItem, result):
        try:
            installLocs = []

            if bldItem.checkState(0) == Qt.Checked and os.path.exists(bldItem.text(1)):
                result["Blender integration"] = self.writeBlenderFiles(bldItem.text(1))
                if result["Blender integration"]:
                    installLocs.append(bldItem.text(1))

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
