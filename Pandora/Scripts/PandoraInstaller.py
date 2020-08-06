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


import os, shutil, sys, platform

if sys.version[0] == "3":
    pVersion = 3
    pyLibs = "Python37"
else:
    pVersion = 2
    pyLibs = "Python27"

pandoraRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", pyLibs))
sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", pyLibs, "win32"))
sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", pyLibs, "win32", "lib"))
sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", pyLibs, "PySide"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))
os.environ['PATH'] = os.path.join(pandoraRoot, "PythonLibs", pyLibs, "pywin32_system32") + os.pathsep + os.environ['PATH']

if platform.system() == "Windows":
    from win32com.shell import shellcon
    import win32com.shell.shell as shell
    import win32con, win32event, win32process

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if psVersion == 1:
    import PandoraInstaller_ui
else:
    import PandoraInstaller_ui_ps2 as PandoraInstaller_ui

from UserInterfacesPandora import qdarkstyle


class PandoraInstaller(QDialog, PandoraInstaller_ui.Ui_dlg_installer):
    def __init__(self, core, uninstall=False):
        QDialog.__init__(self)
        self.core = core

        pnames = self.core.getPluginNames()
        self.plugins = {x: self.core.getPlugin(x) for x in pnames if x != "Standalone"}

        if uninstall:
            self.uninstall()
        else:
            self.setupUi(self)
            try:
                self.documents = shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0)

                self.tw_components.header().resizeSection(0, 200)
                self.tw_components.itemDoubleClicked.connect(self.openBrowse)

                self.refreshUI()

                self.buttonBox.button(QDialogButtonBox.Ok).setText("Install")
                self.buttonBox.accepted.connect(self.install)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                QMessageBox.warning(
                    QWidget(),
                    "Pandora Integration",
                    "Errors occurred during the installation.\n\n%s\n%s\n%s"
                    % (str(e), exc_type, exc_tb.tb_lineno),
                )

    def openBrowse(self, item, column):
        if (
            item.parent().text(0) != "DCC integrations"
            and item.text(0) not in ["Custom"]
            or item.childCount() > 0
        ):
            return

        path = QFileDialog.getExistingDirectory(
            QWidget(), "Select destination folder", item.text(column)
        )
        if path != "":
            item.setText(1, path)
            item.setToolTip(1, path)

    def CompItemClicked(self, item, column):
        if item.text(0) in ["DCC integrations"] or item.childCount == 0:
            return

        isEnabled = item.checkState(0) == Qt.Checked
        for i in range(item.childCount()):
            if isEnabled:
                if item.child(i).text(0) == "Custom" or item.child(i).text(1) != "":
                    item.child(i).setFlags(item.child(i).flags() | Qt.ItemIsEnabled)
            else:
                item.child(i).setFlags(~Qt.ItemIsEnabled)

    def refreshUI(self):
        try:
            if platform.system() == "Windows":
                userFolders = {
                    "LocalAppdata": os.environ["localappdata"],
                    "AppData": os.environ["appdata"],
                    "UserProfile": os.environ["Userprofile"],
                    "Documents": self.documents,
                }

            self.tw_components.clear()
            self.tw_components.itemClicked.connect(self.CompItemClicked)

            if len(self.plugins) > 0:
                integrationsItem = QTreeWidgetItem(["DCC integrations"])
                self.tw_components.addTopLevelItem(integrationsItem)

                for i in sorted(self.plugins):
                    self.plugins[i].updateInstallerUI(userFolders, integrationsItem)

                integrationsItem.setExpanded(True)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                QWidget(),
                "Pandora Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def install(self):
        try:
            print("\n\nInstalling - please wait..")

            dccItems = self.tw_components.findItems(
                "DCC integrations", Qt.MatchExactly | Qt.MatchRecursive
            )
            if len(dccItems) > 0:
                dccItem = dccItems[0]
            else:
                dccItem = None

            result = {}

            if dccItem is not None:
                for i in range(dccItem.childCount()):
                    childItem = dccItem.child(i)
                    if not childItem.text(0) in self.plugins:
                        continue

                    installPaths = self.plugins[childItem.text(0)].installerExecute(
                        childItem, result
                    )
                    if type(installPaths) == list:
                        for k in installPaths:
                            self.core.integrationAdded(childItem.text(0), k)

            self.core.appPlugin.createWinStartMenu(self)

            print("Finished")

            if not False in result.values():
                QMessageBox.information(
                    self.core.messageParent,
                    "Pandora Installation",
                    "Pandora was installed successfully.",
                )
            else:
                msgString = "Some parts failed to install:\n\n"
                for i in result:
                    msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

                msgString = msgString.replace("True", "Success").replace("False", "Error")

                QMessageBox.warning(
                    self.core.messageParent, "Pandora Installation", msgString
                )

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.warning(
                self.core.messageParent,
                "Pandora Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def removePandoraFiles(self):
        try:
            try:
                import psutil
            except:
                pass
            else:
                PROCNAMES = [
                    "Pandora Tray.exe",
                    "Pandora Render Handler.exe",
                    "Pandora Settings.exe",
                    "Pandora Slave.exe",
                    "Pandora Coordinator.exe",
                ]
                for proc in psutil.process_iter():
                    if proc.name() in PROCNAMES:
                        p = psutil.Process(proc.pid)

                        try:
                            if not "SYSTEM" in p.username():
                                proc.kill()
                                print("closed Pandora process")
                        except:
                            pass

            smPath = os.path.join(
                os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs"
            )
            smTray = os.path.join(smPath, "Pandora", "Pandora Tray.lnk")
            smHandler = os.path.join(smPath, "Pandora", "Pandora RenderHandler.lnk")
            smSettings = os.path.join(smPath, "Pandora", "Pandora Settings.lnk")
            smSlave = os.path.join(smPath, "Pandora", "Pandora Slave.lnk")
            smCoordinator = os.path.join(smPath, "Pandora", "Pandora Coordinator.lnk")
            suTray = os.path.join(smPath, "Startup", "Pandora Tray.lnk")

            for i in [smTray, smHandler, smSettings, smSlave, smCoordinator, suTray]:
                if os.path.exists(i):
                    try:
                        os.remove(i)
                    except:
                        pass

            smFolder = os.path.dirname(smTray)
            try:
                shutil.rmtree(smFolder)
            except:
                pass

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.warning(
                self.core.messageParent,
                "Pandora Uninstallation",
                "Error occurred during Pandora files removal:\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def uninstall(self):
        msg = QMessageBox(
            QMessageBox.Question,
            "Pandora Render Manager",
            "Are you sure you want to uninstall Pandora?\n\nThis will delete all Pandora integrations from your PC. Your renderings and scenefiles will remain unaffected.",
            QMessageBox.Cancel,
            parent=self.core.messageParent,
        )
        msg.addButton("Continue", QMessageBox.YesRole)
        action = msg.exec_()

        if action != 0:
            return False

        print("uninstalling...")

        result = {}

        if os.path.exists(self.core.installLocPath):
            cData = self.core.getConfig(configPath=self.core.installLocPath, getConf=True)

            for i in cData:
                if not i in self.plugins:
                    continue

                appPaths = cData[i]

                for k in cData[i]:
                    result["%s integration" % i] = self.plugins[i].removeIntegration(
                        cData[i][k]
                    )

        result["Pandora Files"] = self.removePandoraFiles()

        if not False in result.values():
            msgStr = (
                "All Pandora integrations were removed successfully. To finish the uninstallation delete the Pandora folder:\n\n%s"
                % self.core.pandoraRoot
            )
            QMessageBox.information(
                self.core.messageParent, "Pandora Uninstallation", msgStr
            )
        else:
            msgString = "Some parts failed to uninstall:\n\n"
            for i in result:
                msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

            msgString = (
                msgString.replace("True", "Success")
                .replace("False", "Error")
                .replace("Pandora Files:", "Pandora Files:\t")
            )

            QMessageBox.warning(self.core.messageParent, "Pandora Installation", msgString)
            sys.exit()


def force_elevated():
    try:
        if sys.argv[-1] != "asadmin":
            script = os.path.abspath(sys.argv[0])
            params = " ".join(['"%s"' % script] + sys.argv[1:] + ["asadmin"])
            procInfo = shell.ShellExecuteEx(
                nShow=win32con.SW_SHOWNORMAL,
                fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas",
                lpFile=sys.executable,
                lpParameters=params,
            )

            procHandle = procInfo["hProcess"]
            obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
            rc = win32process.GetExitCodeProcess(procHandle)

            sys.exit()
    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    qApp = QApplication(sys.argv)
    wIcon = QIcon(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "UserInterfacesPandora",
            "pandora_tray.png",
        )
    )
    qApp.setWindowIcon(wIcon)
    qApp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

    if sys.argv[-1] != "asadmin":
        force_elevated()
    else:
        import PandoraCore

        pc = PandoraCore.PandoraCore()
        if sys.argv[-2] == "uninstall":
            pc.openInstaller(uninstall=True)
        else:
            pc.openInstaller()

    sys.exit(qApp.exec_())
