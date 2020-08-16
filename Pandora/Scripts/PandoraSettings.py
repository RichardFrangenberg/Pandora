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


import sys, os, subprocess, time, traceback, shutil
from functools import wraps

pandoraRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if sys.version[0] == "3":
    pyLibs = "Python37"
    pVersion = 3
else:
    pyLibs = "Python27"
    pVersion = 2

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    try:
        if "standalone" in sys.argv:
            raise

        from PySide.QtCore import *
        from PySide.QtGui import *

        psVersion = 1
    except:
        sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", pyLibs, "PySide"))
        try:
            from PySide2.QtCore import *
            from PySide2.QtGui import *
            from PySide2.QtWidgets import *

            psVersion = 2
        except:
            from PySide.QtCore import *
            from PySide.QtGui import *

            psVersion = 1

for i in ["PandoraSettings_ui"]:
    try:
        del sys.modules[i]
    except:
        pass

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))

if psVersion == 1:
    import PandoraSettings_ui
else:
    import PandoraSettings_ui_ps2 as PandoraSettings_ui

from UserInterfacesPandora import qdarkstyle


class PandoraSettings(QDialog, PandoraSettings_ui.Ui_dlg_PandoraSettings):
    def __init__(self, core):
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core
        self.core.parentWindow(self)

        self.groupboxes = [self.gb_slave, self.gb_coordinator]

        self.loadUI()
        self.loadSettings()

        self.startSettings = {
            "checkForUpdates": self.chb_checkForUpdates.isChecked(),
            "localMode": self.chb_localMode.isChecked(),
            "lRootPath": self.e_rootPath.text(),
            "cRootpath": self.e_coordinatorRoot.text(),
            "slaveEnabled": self.gb_slave.isChecked(),
            "coordEnabled": self.gb_coordinator.isChecked(),
        }

        self.refreshSlaves()
        self.refreshWorkstations()

        self.connectEvents()

        screenH = QApplication.desktop().screenGeometry().height()
        space = 100
        if screenH < (self.height() + space):
            self.resize(self.width(), screenH - space)

        self.core.callback(
            name="onPandoraSettingsOpen", types=["curApp", "custom"], args=[self]
        )

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - PandoraSettings %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].core.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def connectEvents(self):
        self.e_username.textChanged.connect(
            lambda x: self.validate(self.e_username, x, allowChars=[" "])
        )
        self.b_browseRoot.clicked.connect(lambda: self.browse("proot"))
        self.b_browseRoot.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_rootPath.text())
        )
        self.b_browseRepository.clicked.connect(lambda: self.browse("prepository"))
        self.b_browseRepository.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_repositoryPath.text())
        )

        self.b_browseSubmission.clicked.connect(lambda: self.browse("psubmission"))
        self.b_browseSubmission.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_submissionPath.text())
        )
        self.b_browseSlave.clicked.connect(lambda: self.browse("pslave"))
        self.b_browseSlave.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_slavePath.text())
        )
        self.b_browseCoordinatorRoot.clicked.connect(lambda: self.browse("pcoord"))
        self.b_browseCoordinatorRoot.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_coordinatorRoot.text())
        )

        self.chb_localMode.stateChanged.connect(self.lmodeChanged)
        self.b_updatePandora.clicked.connect(self.showUpdate)

        for i in self.exOverridePlugins:
            self.exOverridePlugins[i]["chb"].stateChanged.connect(
                lambda x, y=i: self.orToggled(y, x)
            )
            self.exOverridePlugins[i]["b"].clicked.connect(
                lambda y=None, x=(i + "OR"): self.browse(x, getFile=True)
            )
            self.exOverridePlugins[i]["b"].customContextMenuRequested.connect(
                lambda x, y=i: self.core.openFolder(self.exOverridePlugins[y]["le"].text())
            )
        for i in self.integrationPlugins:
            self.integrationPlugins[i]["badd"].clicked.connect(
                lambda y=None, x=i: self.integrationAdd(x)
            )
            self.integrationPlugins[i]["bremove"].clicked.connect(
                lambda y=None, x=i: self.integrationRemove(x)
            )

        self.b_addSlave.clicked.connect(lambda: self.addSlave(itemType="slave"))
        self.b_deleteSlave.clicked.connect(lambda: self.deleteSlave(itemType="slave"))
        self.b_refreshSlaves.clicked.connect(self.refreshSlaves)
        self.b_addWS.clicked.connect(lambda: self.addSlave(itemType="workstation"))
        self.b_deleteWS.clicked.connect(lambda: self.deleteSlave(itemType="workstation"))
        self.b_refreshWS.clicked.connect(self.refreshWorkstations)
        self.lw_slaves.itemDoubleClicked.connect(lambda: self.openSlave(itemType="slave"))
        self.lw_slaves.customContextMenuRequested.connect(
            lambda: self.rclicked(ltype="slave")
        )
        self.lw_workstations.itemDoubleClicked.connect(
            lambda: self.openSlave(itemType="workstation")
        )
        self.lw_workstations.customContextMenuRequested.connect(
            lambda: self.rclicked(ltype="workstation")
        )
        self.buttonBox.accepted.connect(self.saveSettings)

    @err_decorator
    def browse(self, bType, getFile=False):
        if bType == "proot":
            windowTitle = "Select Pandora root path"
            uiEdit = self.e_rootPath
        elif bType == "prepository":
            windowTitle = "Select local Pandora repository path"
            uiEdit = self.e_repositoryPath
        elif bType == "psubmission":
            windowTitle = "Select Pandora submission path"
            uiEdit = self.e_submissionPath
        elif bType == "pslave":
            windowTitle = "Select PandoraSlave Root"
            uiEdit = self.e_slavePath
        elif bType.endswith("OR"):
            pName = bType[:-2]
            executableName = self.core.getPluginData(pName, "executableName")
            windowTitle = "Select %s" % executableName
            uiEdit = self.exOverridePlugins[pName]["le"]
        elif bType == "pcoord":
            windowTitle = "Select Pandora Coordinator Root"
            uiEdit = self.e_coordinatorRoot
        else:
            return

        if getFile:
            selectedPath = QFileDialog.getOpenFileName(
                self, windowTitle, uiEdit.text(), "Executable (*.exe)"
            )[0]
        else:
            selectedPath = QFileDialog.getExistingDirectory(
                self, windowTitle, uiEdit.text()
            )

        if selectedPath != "":
            uiEdit.setText(selectedPath.replace("/", "\\"))

    @err_decorator
    def integrationAdd(self, prog):
        if prog == self.core.appPlugin.pluginName:
            result = self.core.appPlugin.integrationAdd(self)
        else:
            for i in self.core.unloadedAppPlugins:
                if i.pluginName == prog:
                    result = i.integrationAdd(self)

        if result:
            self.core.integrationAdded(prog, result)
            self.refreshIntegrations()
            self.tw_settings.insertTab(1, self.tab_submissions, "Submissions")

    @err_decorator
    def integrationRemove(self, prog):
        items = self.integrationPlugins[prog]["lw"].selectedItems()
        if len(items) == 0:
            return

        installPath = items[0].text()

        if prog == self.core.appPlugin.pluginName:
            result = self.core.appPlugin.integrationRemove(self, installPath)
        else:
            for i in self.core.unloadedAppPlugins:
                if i.pluginName == prog:
                    result = i.integrationRemove(self, installPath)

        if result:
            self.core.integrationRemoved(prog, installPath)
            self.refreshIntegrations()
            if not self.core.getSubmissionEnabled():
                self.tw_settings.removeTab(self.tw_settings.indexOf(self.tab_submissions))

    @err_decorator
    def lmodeChanged(self, state):
        self.w_rootPath.setVisible(state)
        self.w_sumitterPath.setVisible(not state)
        self.w_slaveRoot.setVisible(not state)
        self.w_coordinatorRoot.setVisible(not state)
        self.w_farmcomputer.setVisible(not state)

    @err_decorator
    def orToggled(self, prog, state):
        self.exOverridePlugins[prog]["le"].setEnabled(state)
        self.exOverridePlugins[prog]["b"].setEnabled(state)

    @err_decorator
    def rclicked(self, ltype):
        if ltype in ["slave", "workstation"]:
            rcmenu = QMenu()

            exAct = QAction("Open in explorer", self)
            exAct.triggered.connect(lambda: self.openSlave(itemType=ltype, mode="open"))
            rcmenu.addAction(exAct)

            exAct = QAction("Copy path", self)
            exAct.triggered.connect(lambda: self.openSlave(itemType=ltype, mode="copy"))
            rcmenu.addAction(exAct)

            getattr(self.core.appPlugin, "setRCStyle", lambda x, y: None)(self, rcmenu)
            rcmenu.exec_(QCursor.pos())

    @err_decorator
    def addSlave(self, itemType):
        if itemType == "slave":
            basePath = os.path.join(self.e_coordinatorRoot.text(), "Slaves")
            prefix = "S_"
            refresh = self.refreshSlaves
        elif itemType == "workstation":
            basePath = os.path.join(self.e_coordinatorRoot.text(), "Workstations")
            prefix = "WS_"
            refresh = self.refreshWorkstations
        else:
            return

        itemDlg = QDialog()

        itemDlg.setWindowTitle("Create %s" % (itemType))
        l_item = QLabel("%s%s name:" % (itemType[0].upper(), itemType[1:]))
        e_item = QLineEdit()

        w_item = QWidget()
        layItem = QHBoxLayout()
        layItem.addWidget(l_item)
        layItem.addWidget(e_item)
        w_item.setLayout(layItem)

        bb_info = QDialogButtonBox()
        bb_info.addButton("Add", QDialogButtonBox.AcceptRole)
        bb_info.addButton("Cancel", QDialogButtonBox.RejectRole)
        bb_info.accepted.connect(itemDlg.accept)
        bb_info.rejected.connect(itemDlg.reject)

        bLayout = QVBoxLayout()
        bLayout.addWidget(w_item)
        bLayout.addWidget(bb_info)
        itemDlg.setLayout(bLayout)
        itemDlg.resize(300, 70)

        action = itemDlg.exec_()

        if action == 1:
            itemName = e_item.text()

            if itemName == "":
                QMessageBox.warning(
                    self.core.messageParent, "Error", "Invalid %s name" % itemType
                )
                return

            itemPath = os.path.join(basePath, prefix + itemName)

            if os.path.exists(itemPath):
                QMessageBox(
                    self.core.messageParent,
                    "Error",
                    "%s%s %s already exists"
                    % (itemType[0].upper(), itemType[1:], itemName),
                )
                return

            try:
                os.makedirs(itemPath)
            except:
                QMessageBox(
                    self.core.messageParent,
                    "Error",
                    "Could not create %s %s" % (itemType, itemName),
                )
            else:
                refresh()

    @err_decorator
    def deleteSlave(self, itemType):
        if itemType == "slave":
            basePath = os.path.join(self.e_coordinatorRoot.text(), "Slaves")
            prefix = "S_"
            curItem = self.lw_slaves.currentItem()
            refresh = self.refreshSlaves
        elif itemType == "workstation":
            basePath = os.path.join(self.e_coordinatorRoot.text(), "Workstations")
            prefix = "WS_"
            curItem = self.lw_workstations.currentItem()
            refresh = self.refreshWorkstations
        else:
            return

        if curItem is None:
            return

        curName = curItem.text()

        msg = QMessageBox(
            QMessageBox.Question,
            "Pandora",
            "Are you sure you want to delete %s %s?" % (itemType, curName),
            QMessageBox.Cancel,
        )
        msg.addButton("Continue", QMessageBox.YesRole)
        action = msg.exec_()

        if action != 0:
            return False

        itemPath = os.path.join(basePath, prefix + curName)

        if os.path.exists(itemPath):
            while True:
                try:
                    shutil.rmtree(itemPath)
                    break
                except WindowsError:
                    msg = QMessageBox(
                        QMessageBox.Warning,
                        "Delete",
                        "Could not delete %s %s.\n\nMake sure no other programs are using files in this folder:\n%s"
                        % (itemType, curName, itemPath),
                        QMessageBox.Cancel,
                    )
                    msg.addButton("Retry", QMessageBox.YesRole)
                    action = msg.exec_()

                    if action != 0:
                        return False

        refresh()

    @err_decorator
    def refreshSlaves(self):
        self.lw_slaves.clear()

        if not self.gb_coordinator.isChecked() or self.e_coordinatorRoot.text() == "":
            return

        slaveDir = os.path.join(self.e_coordinatorRoot.text(), "Slaves")

        if os.path.exists(slaveDir):
            for i in os.listdir(slaveDir):
                if i.startswith("S_"):
                    item = QListWidgetItem(i[2:])
                    self.lw_slaves.addItem(item)

    @err_decorator
    def refreshWorkstations(self):
        self.lw_workstations.clear()

        if not self.gb_coordinator.isChecked() or self.e_coordinatorRoot.text() == "":
            return

        wsDir = os.path.join(self.e_coordinatorRoot.text(), "Workstations")

        if os.path.exists(wsDir):
            for i in os.listdir(wsDir):
                if i.startswith("WS_"):
                    item = QListWidgetItem(i[3:])
                    self.lw_workstations.addItem(item)

    @err_decorator
    def openSlave(self, itemType, mode="open"):
        if itemType == "slave":
            basePath = os.path.join(self.e_coordinatorRoot.text(), "Slaves")
            prefix = "S_"
            curItem = self.lw_slaves.currentItem()
            refresh = self.refreshSlaves
        elif itemType == "workstation":
            basePath = os.path.join(self.e_coordinatorRoot.text(), "Workstations")
            prefix = "WS_"
            curItem = self.lw_workstations.currentItem()
            refresh = self.refreshWorkstations
        else:
            return

        if curItem is None:
            return

        curName = curItem.text()

        itemPath = os.path.join(basePath, prefix + curName)

        if mode == "open":
            self.core.openFolder(itemPath)
        elif mode == "copy":
            self.core.copyToClipboard(itemPath)

    @err_decorator
    def saveSettings(self):
        openRH = False

        if hasattr(self.core, "RenderHandler") and self.core.RenderHandler.isVisible():
            self.core.RenderHandler.close()
            openRH = True

        cData = []

        cData.append(["globals", "checkForUpdates", self.chb_checkForUpdates.isChecked()])
        cData.append(["globals", "localMode", self.chb_localMode.isChecked()])
        cData.append(["globals", "send_error_reports", self.chb_errorReports.isChecked()])

        rPath = self.e_rootPath.text().replace("/", "\\")
        if rPath != "" and not rPath.endswith("\\"):
            rPath += "\\"
        cData.append(["globals", "rootPath", rPath])

        repPath = self.e_repositoryPath.text().replace("/", "\\")
        if repPath != "" and not repPath.endswith("\\"):
            repPath += "\\"
        cData.append(["globals", "repositoryPath", repPath])

        sPath = self.e_submissionPath.text().replace("/", "\\")
        if sPath != "" and not sPath.endswith("\\"):
            sPath += "\\"
        cData.append(["submissions", "submissionPath", sPath])
        cData.append(["submissions", "userName", self.e_username.text()])
        cData.append(["slave", "enabled", self.gb_slave.isChecked()])

        psPath = self.e_slavePath.text().replace("/", "\\")
        if psPath != "" and not psPath.endswith("\\"):
            psPath += "\\"
        cData.append(["slave", "slavePath", psPath])

        cData.append(["coordinator", "enabled", self.gb_coordinator.isChecked()])
        pcPath = self.e_coordinatorRoot.text().replace("/", "\\")
        if pcPath != "" and not pcPath.endswith("\\"):
            pcPath += "\\"
        cData.append(["coordinator", "rootPath", pcPath])

        for i in self.exOverridePlugins:
            res = self.core.getPlugin(i).pandoraSettings_saveSettings(self)
            if type(res) == list:
                cData += res

        for i in self.exOverridePlugins:
            cData.append(
                [
                    "dccoverrides",
                    "%s_override" % i,
                    self.exOverridePlugins[i]["chb"].isChecked(),
                ]
            )
            cData.append(
                ["dccoverrides", "%s_path" % i, self.exOverridePlugins[i]["le"].text()]
            )

        self.core.setConfig(data=cData)

        startupPath = (
            os.getenv("APPDATA") + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\"
        )
        trayStartup = startupPath + "Pandora Tray.lnk"
        slaveStartup = startupPath + "Pandora Slave.lnk"
        coordStartup = startupPath + "Pandora Coordinator.lnk"

        if os.path.exists(trayStartup):
            os.remove(trayStartup)

        if self.chb_pandoraTrayStartup.isChecked():
            if not os.path.exists(trayStartup):
                trayPath = os.path.join(self.core.pandoraRoot, "Tools", "Pandora Tray.lnk")
                if os.path.exists(trayPath):
                    shutil.copy2(trayPath, startupPath)
                else:
                    self.core.popup("Couldn't setup Pandora autostart. Run Setup_Startmenu.bat from the Pandora installation folder and try again.")
        else:
            if os.path.exists(trayStartup):
                os.remove(trayStartup)

        if self.gb_slave.isChecked() and self.chb_slaveStartup.isChecked():
            if not os.path.exists(slaveStartup):
                sPath = os.path.join(self.core.pandoraRoot, "Tools", "Pandora Slave.lnk")
                if os.path.exists(sPath):
                    shutil.copy2(sPath, slaveStartup)
                else:
                    self.core.popup("Couldn't setup Pandora Slave autostart. Run Setup_Startmenu.bat from the Pandora installation folder and try again.")
        else:
            if os.path.exists(slaveStartup):
                os.remove(slaveStartup)

        if self.gb_coordinator.isChecked() and self.chb_coordinatorStartup.isChecked():
            if not os.path.exists(coordStartup):
                cPath = os.path.join(
                    self.core.pandoraRoot, "Tools", "Pandora Coordinator.lnk"
                )
                if os.path.exists(cPath):
                    shutil.copy2(cPath, coordStartup)
                else:
                    self.core.popup("Couldn't setup Pandora Coordinator autostart. Run Setup_Startmenu.bat from the Pandora installation folder and try again.")
        else:
            if os.path.exists(coordStartup):
                try:
                    os.remove(coordStartup)
                except Exception as e:
                    if e.errno == 32:
                        self.core.popup("Cannot remove file because it is used by another process:\n\n%s" % coordStartup)
                    else:
                        raise

        if self.startSettings["localMode"] == self.chb_localMode.isChecked():
            if self.chb_localMode.isChecked():
                if self.startSettings["lRootPath"] == self.e_rootPath.text():
                    if self.startSettings["slaveEnabled"] != self.gb_slave.isChecked():
                        if self.gb_slave.isChecked():
                            self.core.startRenderSlave(newProc=True)
                        else:
                            self.core.stopRenderSlave()
                    if (
                        self.startSettings["coordEnabled"]
                        != self.gb_coordinator.isChecked()
                    ):
                        if self.gb_coordinator.isChecked():
                            self.core.startCoordinator()
                        else:
                            self.core.stopCoordinator()
                else:
                    if self.gb_slave.isChecked():
                        self.core.startRenderSlave(newProc=True, restart=True)
                    else:
                        self.core.stopRenderSlave()
                    if self.gb_coordinator.isChecked():
                        self.core.startCoordinator(restart=True)
                    else:
                        self.core.stopCoordinator()
            else:
                if self.startSettings["cRootpath"] == self.e_coordinatorRoot.text():
                    if self.startSettings["slaveEnabled"] != self.gb_slave.isChecked():
                        if self.gb_slave.isChecked():
                            self.core.startRenderSlave(newProc=True)
                        else:
                            self.core.stopRenderSlave()
                    if (
                        self.startSettings["coordEnabled"]
                        != self.gb_coordinator.isChecked()
                    ):
                        if self.gb_coordinator.isChecked():
                            self.core.startCoordinator()
                        else:
                            self.core.stopCoordinator()
                else:
                    if self.gb_slave.isChecked():
                        self.core.startRenderSlave(newProc=True, restart=True)
                    else:
                        self.core.stopRenderSlave()
                    if self.gb_coordinator.isChecked():
                        self.core.startCoordinator(restart=True)
                    else:
                        self.core.stopCoordinator()
        else:
            if self.gb_slave.isChecked():
                self.core.startRenderSlave(newProc=True, restart=True)
            else:
                self.core.stopRenderSlave()
            if self.gb_coordinator.isChecked():
                self.core.startCoordinator(restart=True)
            else:
                self.core.stopCoordinator()

        self.core.callback(name="onPandoraSettingsSave", types=["custom"], args=[self])

        if openRH:
            self.core.openRenderHandler()

    @err_decorator
    def loadSettings(self):
        if not os.path.exists(self.core.configPath):
            return

        ucData = {}

        for i in self.exOverridePlugins:
            ucData["%s_override" % i] = ["dccoverrides", "%s_override" % i, "bool"]
            ucData["%s_path" % i] = ["dccoverrides", "%s_path" % i]

        ucData["checkForUpdates"] = ["globals", "checkForUpdates", "bool"]
        ucData["localMode"] = ["globals", "localMode", "bool"]
        ucData["send_error_reports"] = ["globals", "send_error_reports", "bool"]
        ucData["rootPath"] = ["globals", "rootPath"]
        ucData["repositoryPath"] = ["globals", "repositoryPath"]
        ucData["submissionPath"] = ["submissions", "submissionPath"]
        ucData["userName"] = ["submissions", "userName"]
        ucData["sEnabled"] = ["slave", "enabled", "bool"]
        ucData["slavePath"] = ["slave", "slavePath"]
        ucData["cEnabled"] = ["coordinator", "enabled", "bool"]
        ucData["cRootpath"] = ["coordinator", "rootPath"]

        loadFunctions = {}
        for i in self.exOverridePlugins:
            res = self.core.getPlugin(i).pandoraSettings_loadSettings(self)
            if type(res) == tuple:
                loadData, pLoadFunctions = res
                ucData.update(loadData)
                loadFunctions.update(pLoadFunctions)

        ucData = self.core.getConfig(data=ucData)

        if ucData["checkForUpdates"] is not None:
            self.chb_checkForUpdates.setChecked(ucData["checkForUpdates"])

        if ucData["localMode"] is not None:
            self.chb_localMode.setChecked(ucData["localMode"])

        if ucData["send_error_reports"] is not None:
            self.chb_errorReports.setChecked(ucData["send_error_reports"])

        if ucData["rootPath"] is not None:
            self.e_rootPath.setText(ucData["rootPath"])

        if ucData["repositoryPath"] is not None:
            self.e_repositoryPath.setText(ucData["repositoryPath"])

        if not self.core.getSubmissionEnabled():
            self.tw_settings.removeTab(self.tw_settings.indexOf(self.tab_submissions))

        if ucData["submissionPath"] is not None:
            self.e_submissionPath.setText(ucData["submissionPath"])

        if ucData["userName"] is not None:
            uname = ucData["userName"]

            self.e_username.setText(uname)
            self.validate(uiWidget=self.e_username, allowChars=[" "])

        if ucData["sEnabled"] is not None:
            self.gb_slave.setChecked(ucData["sEnabled"])

        if ucData["slavePath"] is not None:
            self.e_slavePath.setText(ucData["slavePath"])

        if ucData["cEnabled"] is not None:
            self.gb_coordinator.setChecked(ucData["cEnabled"])

        if ucData["cRootpath"] is not None:
            self.e_coordinatorRoot.setText(ucData["cRootpath"])

        for i in self.exOverridePlugins:
            if ucData["%s_override" % i] is not None:
                self.exOverridePlugins[i]["chb"].setChecked(ucData["%s_override" % i])

            if ucData["%s_path" % i] is not None:
                self.exOverridePlugins[i]["le"].setText(ucData["%s_path" % i])

            if (
                not self.exOverridePlugins[i]["chb"].isChecked()
                and self.exOverridePlugins[i]["le"].text() == ""
            ):
                execFunc = self.core.getPluginData(i, "getExecutable")
                if execFunc is not None:
                    examplePath = execFunc()
                    if examplePath is not None:
                        if not os.path.exists(examplePath) and os.path.exists(
                            os.path.dirname(examplePath)
                        ):
                            examplePath = os.path.dirname(examplePath)

                        self.exOverridePlugins[i]["le"].setText(examplePath)

            self.exOverridePlugins[i]["le"].setEnabled(
                self.exOverridePlugins[i]["chb"].isChecked()
            )
            self.exOverridePlugins[i]["b"].setEnabled(
                self.exOverridePlugins[i]["chb"].isChecked()
            )

        startupPath = (
            os.getenv("APPDATA") + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\"
        )

        trayStartup = os.path.exists(startupPath + "Pandora Tray.lnk")
        self.chb_pandoraTrayStartup.setChecked(trayStartup)

        slaveStartup = os.path.exists(startupPath + "Pandora Slave.lnk")
        self.chb_slaveStartup.setChecked(slaveStartup)

        coordStartup = os.path.exists(startupPath + "Pandora Coordinator.lnk")
        self.chb_coordinatorStartup.setChecked(coordStartup)

        lmode = self.chb_localMode.isChecked()
        self.w_rootPath.setVisible(lmode)
        self.w_sumitterPath.setVisible(not lmode)
        self.w_slaveRoot.setVisible(not lmode)
        self.w_coordinatorRoot.setVisible(not lmode)
        self.w_farmcomputer.setVisible(not lmode)

    @err_decorator
    def loadUI(self):
        self.exOverridePlugins = {}
        self.integrationPlugins = {}
        self.dccTabs = QTabWidget()

        pluginNames = self.core.getPluginNames()
        for i in pluginNames:
            pAppType = self.core.getPluginData(i, "appType")
            if pAppType != "standalone":
                tab = QWidget()
                w_ovr = QWidget()
                lo_tab = QVBoxLayout()
                lo_ovr = QHBoxLayout()
                tab.setLayout(lo_tab)
                w_ovr.setLayout(lo_ovr)
                lo_tab.setContentsMargins(15, 15, 15, 15)
                lo_ovr.setContentsMargins(0, 9, 0, 9)
                # 	w_ovr.setMinimumSize(0,39)

                if self.core.getPluginData(i, "canOverrideExecuteable") != False:
                    l_ovr = QLabel(
                        "By default Pandora Slave tries to find the correct version of an application to render scenes.\nThe following setting let you override this behaviour by defining an explicit application for rendering."
                    )
                    chb_ovr = QCheckBox("Slave executable override")
                    le_ovr = QLineEdit()
                    b_ovr = QPushButton("...")
                    b_ovr.setMinimumWidth(40)
                    b_ovr.setMaximumWidth(40)
                    b_ovr.setContextMenuPolicy(Qt.CustomContextMenu)

                    lo_ovr.addWidget(chb_ovr)
                    lo_ovr.addWidget(le_ovr)
                    lo_ovr.addWidget(b_ovr)

                    lo_tab.addWidget(l_ovr)
                    lo_tab.addWidget(w_ovr)

                    self.exOverridePlugins[i] = {"chb": chb_ovr, "le": le_ovr, "b": b_ovr}

                gb_integ = QGroupBox("Pandora integrations")
                lo_integ = QVBoxLayout()
                gb_integ.setLayout(lo_integ)
                lw_integ = QListWidget()
                w_integ = QWidget()
                lo_integButtons = QHBoxLayout()
                b_addInteg = QPushButton("Add")
                b_removeInteg = QPushButton("Remove")

                w_integ.setLayout(lo_integButtons)
                lo_integButtons.addStretch()
                lo_integButtons.addWidget(b_addInteg)
                lo_integButtons.addWidget(b_removeInteg)

                lo_integ.addWidget(lw_integ)
                lo_integ.addWidget(w_integ)
                lo_tab.addWidget(gb_integ)

                lw_integ.setSizePolicy(
                    QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                )

                self.integrationPlugins[i] = {
                    "lw": lw_integ,
                    "badd": b_addInteg,
                    "bremove": b_removeInteg,
                }

                self.core.getPlugin(i).pandoraSettings_loadUI(self, tab)

                lo_tab.addStretch()

                self.dccTabs.addTab(tab, i)

        if self.dccTabs.count() > 0:
            self.tab_dccApps.layout().addWidget(self.dccTabs)

        self.refreshIntegrations()

        self.tab_dccApps.layout().addStretch()

    @err_decorator
    def refreshIntegrations(self):
        installConfig = None
        if os.path.exists(self.core.installLocPath):
            installConfig = self.core.getConfig(
                configPath=self.core.installLocPath, getConf=True
            )

        for i in self.integrationPlugins:
            installPaths = []
            if installConfig is not None and i in installConfig:
                for k in installConfig[i]:
                    installPaths.append(installConfig[i][k])

            self.integrationPlugins[i]["lw"].clear()

            for k in installPaths:
                item = QListWidgetItem(k)
                self.integrationPlugins[i]["lw"].addItem(item)

            if len(installPaths) > 0:
                self.integrationPlugins[i]["lw"].setCurrentRow(0)
                self.integrationPlugins[i]["bremove"].setEnabled(True)
            else:
                self.integrationPlugins[i]["bremove"].setEnabled(False)

    @err_decorator
    def showUpdate(self):
        updateDlg = QDialog()
        updateDlg.setWindowTitle("Update Pandora scripts")
        updateDlg.l_options = QLabel(
            "- Update from GitHub: Downloads the latest version from GitHub. This is definitely the latest version, but may include experimental features.\n\n- Update from .zip: Select a .zip file, which contains the Pandora scripts. You can download .zip files with the Pandora scripts from the GitHub repository."
        )
        updateDlg.b_github = QPushButton("Update from GitHub")
        updateDlg.b_zip = QPushButton("Update from .zip")
        lo_update = QVBoxLayout()
        lo_buttons = QHBoxLayout()
        w_buttons = QWidget()
        w_buttons.setLayout(lo_buttons)
        lo_buttons.addWidget(updateDlg.l_options)
        lo_buttons.addWidget(updateDlg.b_github)
        lo_buttons.addWidget(updateDlg.b_zip)
        lo_update.addWidget(updateDlg.l_options)
        lo_update.addWidget(w_buttons)
        updateDlg.setLayout(lo_update)
        self.core.parentWindow(updateDlg)
        updateDlg.b_zip.clicked.connect(updateDlg.accept)
        updateDlg.b_zip.clicked.connect(self.updateFromZip)
        updateDlg.b_github.clicked.connect(updateDlg.accept)
        updateDlg.b_github.clicked.connect(lambda: self.core.updatePandora(source="github"))
        action = updateDlg.exec_()

    @err_decorator
    def updateFromZip(self):
        pZip = QFileDialog.getOpenFileName(
            self, "Select Pandora Zip", self.core.pandoraRoot, "ZIP (*.zip)"
        )[0]

        if pZip != "":
            self.core.updatePandora(filepath=pZip)

    @err_decorator
    def validate(self, uiWidget, origText=None, allowChars=[]):
        if origText is None:
            origText = uiWidget.text()
        text = self.core.validateStr(origText, allowChars=allowChars)

        if len(text) != len(origText):
            cpos = uiWidget.cursorPosition()
            uiWidget.setText(text)
            uiWidget.setCursorPosition(cpos - 1)

    @err_decorator
    def startTray(self):
        command = '"%s\\%s\\Pandora Tray.exe" "%s\\Scripts\\PandoraTray.py"' % (
            pyLibs,
            self.core.pandoraRoot,
            self.core.pandoraRoot,
        )
        subprocess.Popen(command, shell=True)

    @err_decorator
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()


if __name__ == "__main__":
    qApp = QApplication(sys.argv)
    qApp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
    handlerIcon = QIcon(
        os.path.dirname(os.path.abspath(__file__))
        + "\\UserInterfacesPandora\\pandora_tray.ico"
    )
    qApp.setWindowIcon(handlerIcon)
    import PandoraCore

    pc = PandoraCore.PandoraCore()
    pc.openSettings()
    qApp.exec_()
