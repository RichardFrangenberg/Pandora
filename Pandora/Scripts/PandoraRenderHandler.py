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


import sys, os, io, subprocess, time, shutil, traceback, socket, threading, logging
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

if psVersion == 1:
    import RenderHandler_ui
else:
    import RenderHandler_ui_ps2 as RenderHandler_ui

if sys.version[0] == "3":
    import winreg as _winreg

    pVersion = 3
else:
    import _winreg

    pVersion = 2

import qdarkstyle


logger = logging.getLogger(__name__)


class RenderHandler(QMainWindow, RenderHandler_ui.Ui_mw_RenderHandler):
    def __init__(self, core):
        QMainWindow.__init__(self)
        self.setupUi(self)

        try:
            self.core = core
            self.core.parentWindow(self)

            pConfig = self.core.getConfig(getConf=True)

            ucData = {}
            ucData["localMode"] = ["globals", "localMode"]
            ucData["rootPath"] = ["globals", "rootPath"]
            ucData["submissionPath"] = ["submissions", "submissionPath"]

            ucData = self.core.getConfig(data=ucData)

            if ucData["localMode"] == True:
                self.localMode = True
            else:
                self.localMode = False

            if self.localMode:
                if ucData["rootPath"] is not None:
                    rootPath = ucData["rootPath"]
                    self.sourceDir = os.path.join(
                        rootPath, "Workstations", "WS_" + socket.gethostname(), ""
                    )
                    if not os.path.exists(self.sourceDir):
                        try:
                            os.makedirs(self.sourceDir)
                        except:
                            pass
                else:
                    self.sourceDir = ""
            else:
                if ucData["submissionPath"] is not None:
                    self.sourceDir = ucData["submissionPath"]
                else:
                    self.core.setConfig("submissions", "submissionPath", "")
                    self.sourceDir = ""

            if not os.path.exists(self.sourceDir):
                QMessageBox.warning(
                    self,
                    "Warning",
                    "No Pandora submission folder specified in the Pandora config",
                )

            self.remoteLogDir = os.path.join(
                os.path.dirname(os.path.dirname(self.sourceDir)), "Logs"
            )
            self.cacheBase = os.path.join(
                os.path.dirname(self.core.configPath),
                "temp",
                "RenderHandler_cache",
            )

            self.localLogDir = os.path.join(
                os.path.dirname(self.core.configPath),
                "temp",
                "RenderHandler_logs",
            )

            self.logDir = self.localLogDir

            self.writeSettings = True

            self.getRVpath()

            self.loadLayout()
            self.connectEvents()
            if self.actionLocalLogs.isChecked():
                self.updateLogCache()
            self.updateJobs()
            self.updateSlaves()
            self.refreshLastContactTime()
            self.loadLayout(preUpdate=False)
            self.showCoord()
            self.checkCoordConnected()
            self.core.callback(
                name="onRenderHandlerOpen", types=["curApp", "custom"], args=[self]
            )

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - Renderhandler %s:\n%s\n\n%s" % (
                time.strftime("%d.%m.%y %X"),
                self.core.version,
                "".join(traceback.format_stack()),
                traceback.format_exc(),
            )
            self.core.writeErrorLog(erStr)

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Renderhandler %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].core.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def loadLayout(self, preUpdate=True):
        if preUpdate:
            self.actionRefresh = QAction("Refresh", self)
            self.menubar.addAction(self.actionRefresh)

            helpMenu = QMenu("Help")

            self.actionWebsite = QAction("Documentation", self)
            self.actionWebsite.triggered.connect(
                lambda: self.core.openWebsite("documentation")
            )
            helpMenu.addAction(self.actionWebsite)

            self.actionWebsite = QAction("Visit website", self)
            self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
            helpMenu.addAction(self.actionWebsite)

            self.actionSendFeedback = QAction("Send feedback/feature requests...", self)
            self.actionSendFeedback.triggered.connect(self.core.sendFeedback)
            helpMenu.addAction(self.actionSendFeedback)

            self.actionUpdateSlaves = QAction("Update slaves...", self)
            self.actionUpdateSlaves.triggered.connect(self.updatePandoraSlaves)
            helpMenu.addAction(self.actionUpdateSlaves)

            self.actionAbout = QAction("About...", self)
            self.actionAbout.triggered.connect(self.core.showAbout)
            helpMenu.addAction(self.actionAbout)

            self.menubar.addMenu(helpMenu)

            getattr(self.core.appPlugin, "setRCStyle", lambda x, y: None)(self, helpMenu)

            self.tw_jobs.setColumnCount(10)
            self.tw_jobs.setHorizontalHeaderLabels(
                [
                    "Name",
                    "Status",
                    "Progress",
                    "Prio",
                    "Frames",
                    "Sumit Date",
                    "Project",
                    "User",
                    "Program",
                    "settingsPath",
                ]
            )
            self.tw_jobs.setColumnHidden(9, True)
            self.tw_jobs.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
            if psVersion == 1:
                self.tw_jobs.verticalHeader().setResizeMode(QHeaderView.Fixed)
            else:
                self.tw_jobs.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            #self.tw_jobs.verticalHeader().setDefaultSectionSize(0)
            font = self.tw_jobs.font()
            font.setPointSize(8)
            self.tw_jobs.setFont(font)
            self.tw_jobs.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}")
            self.tw_coordSettings.setStyleSheet(
                self.styleSheet().replace("QCheckBox::indicator", "QTableWidget::indicator")
            )
            self.tw_slaveSettings.setStyleSheet(
                self.styleSheet().replace("QCheckBox::indicator", "QTableWidget::indicator")
            )
            self.tw_jobSettings.setStyleSheet(
                self.styleSheet().replace("QCheckBox::indicator", "QTableWidget::indicator")
            )

            self.tw_taskList.setColumnCount(7)
            self.tw_taskList.setHorizontalHeaderLabels(
                ["Num", "Frames", "Status", "Slave", "Rendertime", "Start", "End"]
            )
            self.tw_taskList.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

            self.tw_taskList.verticalHeader().setDefaultSectionSize(17)
            font = self.tw_taskList.font()
            font.setPointSize(8)
            self.tw_taskList.setFont(font)
            self.tw_taskList.verticalHeader().setStyleSheet(
                "QHeaderView { font-size: 6pt;}"
            )

            self.tw_jobSettings.setColumnCount(2)
            self.tw_jobSettings.setHorizontalHeaderLabels(["Name", "Value"])
            self.tw_jobSettings.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
            self.tw_jobSettings.verticalHeader().setDefaultSectionSize(25)
            font = self.tw_jobSettings.font()
            font.setPointSize(8)
            self.tw_jobSettings.setFont(font)
            self.tw_jobSettings.verticalHeader().setStyleSheet(
                "QHeaderView { font-size: 6pt;}"
            )

            self.tw_slaves.setColumnCount(9)
            self.tw_slaves.setHorizontalHeaderLabels(
                [
                    "Name",
                    "Status",
                    "Task",
                    "last Contact",
                    "Warnings",
                    "RAM",
                    "Cores",
                    "LogPath",
                    "Version",
                ]
            )
            self.tw_slaves.setColumnHidden(7, True)
            self.tw_slaves.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
            self.tw_slaves.verticalHeader().setDefaultSectionSize(17)
            font = self.tw_slaves.font()
            font.setPointSize(8)
            self.tw_slaves.setFont(font)
            self.tw_slaves.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}")

            self.tw_slaveSettings.setColumnCount(2)
            self.tw_slaveSettings.setHorizontalHeaderLabels(["Name", "Value"])
            self.tw_slaveSettings.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
            self.tw_slaveSettings.verticalHeader().setDefaultSectionSize(25)
            font = self.tw_slaveSettings.font()
            font.setPointSize(8)
            self.tw_slaveSettings.setFont(font)
            self.tw_slaveSettings.verticalHeader().setStyleSheet(
                "QHeaderView { font-size: 6pt;}"
            )
            if psVersion == 1:
                self.tw_slaveWarnings.verticalHeader().setResizeMode(
                    QHeaderView.ResizeToContents
                )
            else:
                self.tw_slaveWarnings.verticalHeader().setSectionResizeMode(
                    QHeaderView.ResizeToContents
                )

            self.tw_coordSettings.setColumnCount(2)
            self.tw_coordSettings.setHorizontalHeaderLabels(["Name", "Value"])
            self.tw_coordSettings.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
            self.tw_coordSettings.verticalHeader().setDefaultSectionSize(25)
            font = self.tw_coordSettings.font()
            font.setPointSize(8)
            self.tw_coordSettings.setFont(font)
            self.tw_coordSettings.verticalHeader().setStyleSheet(
                "QHeaderView { font-size: 6pt;}"
            )
            if psVersion == 1:
                self.tw_coordWarnings.verticalHeader().setResizeMode(
                    QHeaderView.ResizeToContents
                )
            else:
                self.tw_coordWarnings.verticalHeader().setSectionResizeMode(
                    QHeaderView.ResizeToContents
                )

            self.l_logLimit = QLabel("LogLimit:")
            self.sp_logLimit = QSpinBox()
            self.sp_logLimit.setRange(0, 99999)
            llimit = self.core.getConfig("renderHandler", "logLimit")
            if llimit is not None:
                self.sp_logLimit.setValue(llimit)
            else:
                self.sp_logLimit.setValue(500)

            self.sp_logLimit.editingFinished.connect(self.refresh)
            self.w_logLimit = QWidget()
            lo = QHBoxLayout()
            lo.addWidget(self.l_logLimit)
            lo.addWidget(self.sp_logLimit)
            self.w_logLimit.setLayout(lo)
            self.waLogLimit = QWidgetAction(self)
            self.waLogLimit.setDefaultWidget(self.w_logLimit)
            self.menuOptions.addAction(self.waLogLimit)

            self.l_refInt = QLabel("Refresh Interval:")
            self.sp_refInt = QSpinBox()
            self.sp_refInt.setRange(1, 99999)

            self.refreshPeriod = 10
            refreshT = self.core.getConfig("renderHandler", "refreshTime")
            if refreshT is not None:
                self.refreshPeriod = refreshT

            self.sp_refInt.setValue(self.refreshPeriod)

            self.sp_refInt.editingFinished.connect(self.updateRefInterval)
            self.w_refInt = QWidget()
            lo = QHBoxLayout()
            lo.addWidget(self.l_refInt)
            lo.addWidget(self.sp_refInt)
            self.w_refInt.setLayout(lo)
            self.waRefInt = QWidgetAction(self)
            self.waRefInt.setDefaultWidget(self.w_refInt)
            self.menuOptions.addAction(self.waRefInt)

            self.actionAutoUpdate = QAction("Auto Update", self)
            self.actionAutoUpdate.setCheckable(True)

            aupdate = self.core.getConfig("renderHandler", "autoUpdate")
            if aupdate is not None:
                self.actionAutoUpdate.setChecked(aupdate)
            else:
                self.actionAutoUpdate.setChecked(True)

            self.menuOptions.addAction(self.actionAutoUpdate)

            self.actionLocalLogs = QAction("Use local logcache", self)
            self.actionLocalLogs.setCheckable(True)

            localLogs = self.core.getConfig("renderHandler", "localLogCache")
            if localLogs is not None:
                self.actionLocalLogs.setChecked(localLogs)
            else:
                self.actionLocalLogs.setChecked(False)

            if self.actionLocalLogs.isChecked():
                self.logDir = self.localLogDir
            else:
                self.logDir = self.remoteLogDir

            self.menuOptions.addAction(self.actionLocalLogs)

            self.actionShowCoord = QAction("Show Coordinator", self)
            self.actionShowCoord.setCheckable(True)

            scoord = self.core.getConfig("renderHandler", "showCoordinator")
            if scoord == True:
                self.actionShowCoord.setChecked(scoord)
                self.showCoord()

            self.menuOptions.addAction(self.actionShowCoord)

            self.actionSettings = QAction("Pandora Settings...", self)
            self.actionSettings.triggered.connect(self.core.openSettings)
            self.menuOptions.addAction(self.actionSettings)

            self.statusLabel = QLabel()
            self.statusBar().addWidget(self.statusLabel)
        else:

            if self.tw_jobs.rowCount() > 0:
                self.tw_jobs.selectRow(0)

            if self.tw_slaves.rowCount() > 0:
                self.tw_slaves.selectRow(0)

            self.l_refreshCounter = QLabel()
            self.statusBar().addWidget(self.l_refreshCounter)

            self.seconds = self.refreshPeriod
            self.refreshTimer = QTimer()
            self.refreshTimer.timeout.connect(self.timeoutSlot)
            self.refreshTimer.setInterval(1000)
            if self.actionAutoUpdate.isChecked():
                self.refreshTimer.start()

            wsize = self.core.getConfig("renderHandler", "windowSize")
            if wsize is not None and wsize != "":
                self.resize(wsize[0], wsize[1])
            else:
                screenW = QApplication.desktop().screenGeometry().width()
                screenH = QApplication.desktop().screenGeometry().height()
                space = 100
                # if screenH < (self.height()+space):
                self.resize(self.width(), screenH - space - 50)

                # if screenW < (self.width()+space):
                self.resize(screenW - space, self.height())

        self.core.callback(
            name="onPrismRenderHandlerOpen", types=["curApp", "custom"], args=[self]
        )

    @err_decorator
    def closeEvent(self, event):
        cData = []
        cData.append(["renderHandler", "windowSize", [self.width(), self.height()]])
        cData.append(["renderHandler", "logLimit", self.sp_logLimit.value()])
        cData.append(["renderHandler", "showCoordinator", self.actionShowCoord.isChecked()])
        cData.append(["renderHandler", "refreshTime", self.refreshPeriod])
        cData.append(["renderHandler", "autoUpdate", self.actionAutoUpdate.isChecked()])
        cData.append(["renderHandler", "localLogCache", self.actionLocalLogs.isChecked()])
        self.core.setConfig(data=cData)

        self.refreshTimer.stop()
        self.core.callback(
            name="onRenderHandlerClose", types=["curApp", "custom"], args=[self]
        )

    @err_decorator
    def timeoutSlot(self):
        self.seconds -= 1
        self.l_refreshCounter.setText("Refresh in %s seconds." % self.seconds)
        if self.seconds == 0:
            self.seconds = self.refreshPeriod
            self.refresh()
            self.l_refreshCounter.setText("Refresh in %s seconds." % self.seconds)

    @err_decorator
    def updatePandoraSlaves(self):
        message = "Do you want to download the latest Pandora version and install it on all renderslaves?"

        msg = QMessageBox(QMessageBox.Question, "Pandora", message, QMessageBox.No)
        msg.addButton("Yes", QMessageBox.YesRole)
        self.core.parentWindow(msg)
        result = msg.exec_()

        if result == 0:
            zipFile = self.core.updatePandora(source="github", downloadOnly=True) or ""

            if not zipFile:
                return

            cmdDir = os.path.join(self.sourceDir, "Commands")

            if not os.path.exists(cmdDir):
                try:
                    os.makedirs(cmdDir)
                except:
                    QMessageBox.warning(
                        self, "Warning", "Could not create command folder: " % cmdDir
                    )
                    return

            shutil.copy2(zipFile, cmdDir)

    @err_decorator
    def connectEvents(self):
        self.tw_jobs.itemSelectionChanged.connect(self.jobChanged)
        self.tw_jobs.customContextMenuRequested.connect(lambda x: self.rclList("j", x))
        self.tw_taskList.customContextMenuRequested.connect(lambda x: self.rclList("tl", x))
        self.te_coordLog.customContextMenuRequested.connect(lambda x: self.rclList("cl", x))
        self.tw_jobSettings.itemChanged.connect(lambda x: self.setSetting("js", x))
        self.tw_jobSettings.customContextMenuRequested.connect(
            lambda x: self.rclList("js", x)
        )
        self.tw_slaves.itemSelectionChanged.connect(self.slaveChanged)
        self.tw_slaves.customContextMenuRequested.connect(lambda x: self.rclList("s", x))
        self.te_slaveLog.customContextMenuRequested.connect(lambda x: self.rclList("sl", x))
        self.tw_slaveSettings.customContextMenuRequested.connect(
            lambda x: self.rclList("ss", x)
        )
        self.tw_slaveSettings.itemChanged.connect(lambda x: self.setSetting("ss", x))
        self.sp_slaveFilter.valueChanged.connect(self.updateSlaveLog)
        self.tw_slaveWarnings.customContextMenuRequested.connect(
            lambda x: self.rclList("sw", x)
        )
        self.tw_slaveWarnings.itemDoubleClicked.connect(
            lambda x: self.showWarning("Slave", x)
        )
        self.sp_coordFilter.valueChanged.connect(self.updateCoordLog)
        self.tw_coordSettings.itemChanged.connect(lambda x: self.setSetting("cs", x))
        self.tw_coordSettings.customContextMenuRequested.connect(
            lambda x: self.rclList("cs", x)
        )
        self.tw_coordWarnings.customContextMenuRequested.connect(
            lambda x: self.rclList("cw", x)
        )
        self.tw_coordWarnings.itemDoubleClicked.connect(
            lambda x: self.showWarning("Coordinator", x)
        )
        self.actionShowCoord.toggled.connect(self.showCoord)
        self.actionAutoUpdate.toggled.connect(self.autoUpdate)
        self.actionLocalLogs.toggled.connect(self.localLogs)
        self.actionRefresh.triggered.connect(self.refresh)

    @err_decorator
    def showCoord(self, checked=False):
        checked = self.actionShowCoord.isChecked()

        if checked:
            self.tb_jobs.insertTab(2, self.t_coordLog, "Coordinator Log")
            self.tb_jobs.insertTab(3, self.t_coordSettings, "Coordinator Settings")
            self.tb_jobs.insertTab(4, self.t_coordWarnings, "Coordinator Warnings")
            self.updateCoordLog()
            self.updateCoordSettings()
            self.updateCoordWarnings()
        else:
            self.tb_jobs.removeTab(self.tb_jobs.indexOf(self.t_coordLog))
            self.tb_jobs.removeTab(self.tb_jobs.indexOf(self.t_coordSettings))
            self.tb_jobs.removeTab(self.tb_jobs.indexOf(self.t_coordWarnings))

    @err_decorator
    def autoUpdate(self, checked):
        if checked:
            self.seconds = self.refreshPeriod
            self.refreshTimer.start()
        else:
            self.refreshTimer.stop()
            self.l_refreshCounter.setText("")

    @err_decorator
    def localLogs(self, checked):
        if checked:
            self.logDir = self.localLogDir
        else:
            self.logDir = self.remoteLogDir

    @err_decorator
    def updateRefInterval(self):
        self.seconds = self.refreshPeriod = self.sp_refInt.value()

    @err_decorator
    def refresh(self):
        self.statusBar().showMessage("refreshing...")
        self.refreshTimer.stop()
        if self.actionLocalLogs.isChecked():
            self.updateLogCache()

        self.l_refreshCounter.setText("")
        if self.tw_jobs.rowCount() > 0:
            selJobs = []
            for i in self.tw_jobs.selectedIndexes():
                jobName = self.tw_jobs.item(i.row(), 0).text()
                if jobName not in selJobs:
                    selJobs.append(jobName)

            curJobSliderPos = self.tw_jobs.verticalScrollBar().value()
        if self.tw_jobs.rowCount() > 0:
            selTaks = []
            for i in self.tw_taskList.selectedIndexes():
                taskName = self.tw_taskList.item(i.row(), 0).text()
                if taskName not in selTaks:
                    selTaks.append(taskName)

            curTaskSliderPos = self.tw_taskList.verticalScrollBar().value()
        if self.tw_slaves.rowCount() > 0:
            curSlaveRow = self.tw_slaves.currentIndex().row()
            if curSlaveRow != -1:
                curSlaveName = self.tw_slaves.item(curSlaveRow, 0).text()
            curSlaveSliderPos = self.tw_slaves.verticalScrollBar().value()

        sLogSliderPos = self.te_slaveLog.verticalScrollBar().value()

        updateJobs = True
        updateSlaves = True
        updateCoord = True

        try:
            fparent = QApplication.focusWidget().parent().parent()
            if fparent == self.tw_jobSettings:
                updateJobs = False
            elif fparent == self.tw_slaveSettings:
                updateSlaves = False
            elif fparent == self.tw_coordSettings:
                updateCoord = False
        except:
            pass

        if updateJobs:
            self.updateJobs()
            self.updateTaskList()
            self.updateJobSettings()

        if updateSlaves:
            self.updateSlaves()
            self.updateSlaveSettings()
            self.updateSlaveWarnings()

        if updateCoord and self.actionShowCoord.isChecked():
            self.updateCoordLog()
            self.updateCoordSettings()
            self.updateCoordWarnings()

        if "selJobs" in locals() and updateJobs:
            self.tw_jobs.setSelectionMode(QAbstractItemView.MultiSelection)
            for i in range(self.tw_jobs.rowCount()):
                if self.tw_jobs.item(i, 0).text() in selJobs:
                    self.tw_jobs.selectRow(i)
            self.tw_jobs.setSelectionMode(QAbstractItemView.ExtendedSelection)

        if "curJobSliderPos" in locals() and updateJobs:
            self.tw_jobs.verticalScrollBar().setValue(curJobSliderPos)

        if "selTaks" in locals() and updateJobs:
            self.tw_taskList.setSelectionMode(QAbstractItemView.MultiSelection)
            for i in range(self.tw_taskList.rowCount()):
                if self.tw_taskList.item(i, 0).text() in selTaks:
                    self.tw_taskList.selectRow(i)
            self.tw_taskList.setSelectionMode(QAbstractItemView.ExtendedSelection)

        if "curTaskSliderPos" in locals() and updateJobs:
            self.tw_taskList.verticalScrollBar().setValue(curTaskSliderPos)

        if "curSlaveName" in locals() and updateSlaves:
            for i in range(self.tw_slaves.rowCount()):
                if self.tw_slaves.item(i, 0).text() == curSlaveName:
                    self.tw_slaves.selectRow(i)
                    break

        if "curSlaveSliderPos" in locals() and updateSlaves:
            self.tw_slaves.verticalScrollBar().setValue(curSlaveSliderPos)

        self.te_slaveLog.verticalScrollBar().setValue(sLogSliderPos)

        self.refreshLastContactTime()
        self.clearCache()

        self.statusBar().clearMessage()
        self.checkCoordConnected()
        self.seconds = self.refreshPeriod
        if self.actionAutoUpdate.isChecked():
            self.refreshTimer.start()

    @err_decorator
    def jobChanged(self):
        self.updateTaskList()
        self.updateJobSettings()

        selItems = self.tw_jobs.selectedItems()
        if not selItems or [x.row() for x in selItems if x.row() != selItems[0].row()]:
            selColor = Qt.white
        else:
            selColor = selItems[0].foreground().color()

        p = QPalette()
        p.setColor(QPalette.Active, QPalette.HighlightedText, selColor)
        p.setColor(QPalette.Inactive, QPalette.HighlightedText, selColor)
        self.tw_jobs.setPalette(p)

    @err_decorator
    def slaveChanged(self):
        self.updateSlaveLog()
        self.updateSlaveSettings()
        self.updateSlaveWarnings()

    @err_decorator
    def updateJobs(self):
        self.tw_jobs.setRowCount(0)
        self.tw_jobs.setSortingEnabled(False)
        jobDir = os.path.join(self.logDir, "Jobs")
        if os.path.isdir(jobDir):
            for i in os.listdir(jobDir):
                settingsPath = os.path.join(jobDir, i)
                if not (os.path.isfile(settingsPath) and i.endswith(".json")):
                    continue

                if (
                    self.getConfig(configPath=settingsPath, getConf=True, silent=True)
                    == "Error"
                ):
                    continue

                rc = self.tw_jobs.rowCount()
                self.tw_jobs.insertRow(rc)
                self.tw_jobs.setRowHeight(rc, 15)

                settingsPathItem = QTableWidgetItem(settingsPath)
                self.tw_jobs.setItem(rc, 9, settingsPathItem)
                self.updateJobData(rc)

        self.tw_jobs.resizeColumnsToContents()
        self.tw_jobs.horizontalHeader().setStretchLastSection(True)
        self.tw_jobs.setColumnWidth(1, 60)
        self.tw_jobs.setColumnWidth(2, 60)
        self.tw_jobs.setColumnWidth(3, 30)
        self.tw_jobs.setColumnWidth(0, 400)
        self.tw_jobs.setSortingEnabled(True)
        self.tw_jobs.sortByColumn(5, Qt.DescendingOrder)

    @err_decorator
    def updateJobData(self, rc):
        jobPath = self.tw_jobs.item(rc, 9).text()
        if not (os.path.isfile(jobPath) and jobPath.endswith(".json")):
            self.updateJobs()
            return

        self.tw_jobs.setSortingEnabled(False)

        jobName = QTableWidgetItem(os.path.splitext(os.path.basename(jobPath))[0])
        self.tw_jobs.setItem(rc, 0, jobName)

        rowColorStyle = "ready"

        jsconfig = self.getConfig(configPath=jobPath, getConf=True)
        jcData = {}
        jcData["priority"] = ["jobglobals", "priority"]
        jcData["frameRange"] = ["information", "frameRange"]
        jcData["submitDate"] = ["information", "submitDate"]
        jcData["projectName"] = ["information", "projectName"]
        jcData["userName"] = ["information", "userName"]
        jcData["program"] = ["information", "program"]
        jcData = self.getConfig(configPath=jobPath, data=jcData)

        if "jobtasks" in jsconfig:
            finNum = 0
            notfinNum = 0
            status = "unknown"
            for taskData in jsconfig["jobtasks"].values():
                if taskData[2] == "finished":
                    finNum += 1
                    if status == "unknown":
                        status = "finished"
                elif taskData[2] == "rendering":
                    notfinNum += 1
                    if status != "error":
                        status = "rendering"
                elif taskData[2] == "error":
                    notfinNum += 1
                    status = "error"
                elif taskData[2] == "disabled":
                    notfinNum += 1
                    if status not in ["rendering", "error", "ready", "assigned"]:
                        status = "disabled"
                elif taskData[2] == "ready":
                    notfinNum += 1
                    if status not in ["rendering", "error", "assigned"]:
                        status = "ready"
                elif taskData[2] == "assigned":
                    notfinNum += 1
                    if status not in ["rendering", "error"]:
                        status = "assigned"
                else:
                    notfinNum += 1
                    if status not in ["rendering", "error"]:
                        status = taskData[2]

            rowColorStyle = status

            statusItem = QTableWidgetItem(status)
            self.tw_jobs.setItem(rc, 1, statusItem)

            progress = int(100 / float(finNum + notfinNum) * float(finNum))

            progressItem = QTableWidgetItem(str(progress) + " %")
            self.tw_jobs.setItem(rc, 2, progressItem)

        if jcData:
            if jcData["priority"] is not None:
                jobPrio = jcData["priority"]
                jobPrioItem = QTableWidgetItem(str(jobPrio))
                self.tw_jobs.setItem(rc, 3, jobPrioItem)

            if jcData["frameRange"] is not None:
                framerange = jcData["frameRange"]
                framerangeItem = QTableWidgetItem(framerange)
                self.tw_jobs.setItem(rc, 4, framerangeItem)

            if jcData["submitDate"] is not None:
                submitDate = jcData["submitDate"]
                submitdateItem = QTableWidgetItem(submitDate)
                submitdateItem.setData(
                    0, QDateTime.fromString(submitDate, "dd.MM.yy, hh:mm:ss").addYears(100)
                )
                submitdateItem.setToolTip(submitDate)
                self.tw_jobs.setItem(rc, 5, submitdateItem)

            if jcData["projectName"] is not None:
                pName = jcData["projectName"]
                pNameItem = QTableWidgetItem(pName)
                self.tw_jobs.setItem(rc, 6, pNameItem)

            if jcData["userName"] is not None:
                uName = jcData["userName"]
                uNameItem = QTableWidgetItem(uName)
                self.tw_jobs.setItem(rc, 7, uNameItem)

            if jcData["program"] is not None:
                pName = jcData["program"]
                pNameItem = QTableWidgetItem(pName)
                self.tw_jobs.setItem(rc, 8, pNameItem)

        if rowColorStyle not in ["ready", "assigned"]:
            cc = self.tw_jobs.columnCount()
            for i in range(cc):
                item = self.tw_jobs.item(rc, i)
                if item is None:
                    item = QTableWidgetItem("")
                    self.tw_jobs.setItem(rc, i, item)
                if rowColorStyle == "rendering":
                    item.setForeground(QBrush(QColor(80, 210, 80)))
                elif rowColorStyle == "finished":
                    item.setForeground(QBrush(QColor(80, 180, 220)))
                elif rowColorStyle == "disabled":
                    item.setForeground(QBrush(QColor(90, 90, 90)))
                elif rowColorStyle == "error":
                    item.setForeground(QBrush(QColor(240, 50, 50)))
                else:
                    item.setForeground(QBrush(Qt.white))

        self.tw_jobs.setSortingEnabled(True)

    @err_decorator
    def updateSlaves(self):
        self.tw_slaves.setRowCount(0)
        self.tw_slaves.setSortingEnabled(False)
        slaveDir = os.path.join(self.logDir, "Slaves")

        activeSlaves = {}
        actSlvPath = os.path.join(self.logDir, "Coordinator", "ActiveSlaves.json")

        if os.path.exists(actSlvPath):
            activeSlaves = self.getConfig(configPath=actSlvPath, getConf=True)

        if os.path.isdir(slaveDir):
            corruptSlaves = []
            for i in os.listdir(slaveDir):
                try:
                    slaveLogPath = os.path.join(slaveDir, i)
                    if (
                        i.startswith("slaveLog_")
                        and i.endswith(".txt")
                        and os.path.isfile(slaveLogPath)
                    ):
                        rc = self.tw_slaves.rowCount()
                        slaveName = i[len("slaveLog_") : -len(".txt")]
                        slaveSettingsPath = (
                            slaveLogPath.replace("slaveLog_", "slaveSettings_")[:-3]
                            + "json"
                        )
                        slaveWarningsPath = (
                            slaveLogPath.replace("slaveLog_", "slaveWarnings_")[:-3]
                            + "json"
                        )
                        self.tw_slaves.insertRow(rc)
                        self.tw_slaves.setItem(rc, 0, QTableWidgetItem(slaveName))

                        rowColorStyle = "idle"
                        slaveStatusItem = None

                        if os.path.exists(slaveSettingsPath):
                            scData = {}
                            scData["status"] = ["slaveinfo", "status"]
                            scData["curtasks"] = ["slaveinfo", "curtasks"]
                            scData["cpucount"] = ["slaveinfo", "cpucount"]
                            scData["ram"] = ["slaveinfo", "ram"]
                            scData["slaveScriptVersion"] = [
                                "slaveinfo",
                                "slaveScriptVersion",
                            ]
                            scData = self.getConfig(
                                configPath=slaveSettingsPath, data=scData
                            )

                            if scData["status"] is not None:
                                slaveStatus = scData["status"]
                                rowColorStyle = slaveStatus
                                slaveStatusItem = QTableWidgetItem(slaveStatus)
                                self.tw_slaves.setItem(rc, 1, slaveStatusItem)

                            if scData["curtasks"] is not None:
                                curtasks = scData["curtasks"]
                                curTasksStr = self.getTasksStr(scData["curtasks"])
                                slaveJob = QTableWidgetItem(curTasksStr)
                                self.tw_slaves.setItem(rc, 2, slaveJob)

                            if scData["cpucount"] is not None:
                                cpuCount = scData["cpucount"]
                                slaveCPU = QTableWidgetItem(str(cpuCount))
                                self.tw_slaves.setItem(rc, 6, slaveCPU)

                            if scData["ram"] is not None:
                                ram = scData["ram"]
                                slaveRam = QTableWidgetItem(str(ram) + " Gb")
                                self.tw_slaves.setItem(rc, 5, slaveRam)

                            if scData["slaveScriptVersion"] is not None:
                                scriptVersion = scData["slaveScriptVersion"]
                                slaveVersion = QTableWidgetItem(scriptVersion)
                                self.tw_slaves.setItem(rc, 8, slaveVersion)

                        if os.path.exists(slaveWarningsPath):
                            options = self.getConfig(
                                cat="warnings",
                                configPath=slaveWarningsPath,
                                getOptions=True,
                                silent=True,
                            )
                            if options == "Error":
                                numWarns = options
                            else:
                                numWarns = len(options)
                            warns = QTableWidgetItem(str(numWarns))
                            self.tw_slaves.setItem(rc, 4, warns)

                        last_timeMin = 9999
                        if slaveName in activeSlaves:
                            slaveLastTime = activeSlaves[slaveName]
                            last_timeMin = int((time.time() - slaveLastTime) / 60)

                            last_timeH = last_timeMin // 60
                            last_timeM = last_timeMin - last_timeH * 60
                            last_timeD = last_timeH // 24
                            last_timeH = last_timeH - last_timeD * 24
                            last_time = ""
                            if last_timeD > 0:
                                last_time += "%sd " % last_timeD
                            if last_timeH > 0:
                                last_time += "%sh " % last_timeH
                            if last_timeM > 0 or last_timeMin == 0:
                                last_time += "%s min." % last_timeM

                            lastContact = QTableWidgetItem(last_time)
                            self.tw_slaves.setItem(rc, 3, lastContact)

                        if last_timeMin > 30 or rowColorStyle == "shut down":
                            rowColorStyle = "offline"
                            if slaveStatusItem is not None and slaveStatusItem.text() in [
                                "idle",
                                "rendering",
                                "paused",
                            ]:
                                slaveStatusItem.setText("not responding")

                        if rowColorStyle != "idle":
                            cc = self.tw_slaves.columnCount()
                            for k in range(cc):
                                item = self.tw_slaves.item(rc, k)
                                if item is None:
                                    item = QTableWidgetItem("")
                                    self.tw_slaves.setItem(rc, k, item)
                                if rowColorStyle == "rendering":
                                    item.setForeground(QBrush(QColor(80, 210, 80)))
                                elif rowColorStyle == "offline":
                                    item.setForeground(QBrush(QColor(90, 90, 90)))

                        slavePathItem = QTableWidgetItem(slaveLogPath)
                        self.tw_slaves.setItem(rc, 7, slavePathItem)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    erStr = "%s ERROR - Renderhandler %s:\n%s" % (
                        time.strftime("%d.%m.%y %X"),
                        self.core.version,
                        traceback.format_exc(),
                    )
                    self.core.writeErrorLog(erStr)

            if len(corruptSlaves) > 0:
                mString = "The slavesettings file is corrupt:\n\n"
                for i in corruptSlaves:
                    mString += i + "\n"

            #   QMessageBox.information(self,"File corrupt", mString)

        self.tw_slaves.resizeColumnsToContents()
        self.tw_slaves.horizontalHeader().setStretchLastSection(True)
        self.tw_slaves.setColumnWidth(1, 100)
        self.tw_slaves.setColumnWidth(0, 130)
        self.tw_slaves.setColumnWidth(3, 80)
        self.tw_slaves.setColumnWidth(4, 60)
        self.tw_slaves.setColumnWidth(5, 40)
        self.tw_slaves.setColumnWidth(8, 60)
        self.tw_slaves.setColumnWidth(2, 350)
        self.tw_slaves.setSortingEnabled(True)
        self.tw_slaves.sortByColumn(0, Qt.AscendingOrder)

    @err_decorator
    def getTasksStr(self, tasks):
        if tasks:
            if len(tasks) > 1:
                curTasksStr = "%s tasks - " % len(tasks)
            else:
                curTasksStr = ""

            for task in tasks:
                curTasksStr += "%s (%s)" % (task["jobname"], task["taskname"])
        else:
            curTasksStr = ""

        return curTasksStr

    @err_decorator
    def updateTaskList(self):
        self.tw_taskList.setRowCount(0)
        self.tw_taskList.setSortingEnabled(False)

        selJobs = []
        for i in self.tw_jobs.selectedIndexes():
            jobName = self.tw_jobs.item(i.row(), 0).text()
            if jobName not in selJobs:
                selJobs.append(jobName)

        if len(selJobs) != 1:
            return False

        jobName = self.tw_jobs.item(self.tw_jobs.currentRow(), 0).text()
        jobConf = os.path.join(self.logDir, "Jobs", "%s.json" % jobName)

        jconfig = self.getConfig(configPath=jobConf, getConf=True)

        if "jobtasks" in jconfig:
            for idx, i in enumerate(sorted(jconfig["jobtasks"])):
                taskData = jconfig["jobtasks"][i]

                if not (
                    type(taskData) == list and (len(taskData) == 5 or len(taskData) == 7)
                ):
                    continue

                rc = self.tw_taskList.rowCount()
                self.tw_taskList.insertRow(rc)
                taskNum = QTableWidgetItem(format(idx, "02"))
                self.tw_taskList.setItem(rc, 0, taskNum)
                taskRange = QTableWidgetItem(str(taskData[0]) + "-" + str(taskData[1]))
                self.tw_taskList.setItem(rc, 1, taskRange)
                taskStatus = QTableWidgetItem(taskData[2])
                self.tw_taskList.setItem(rc, 2, taskStatus)
                rowColorStyle = taskData[2]
                slaveName = QTableWidgetItem(taskData[3])
                self.tw_taskList.setItem(rc, 3, slaveName)
                taskTime = QTableWidgetItem(taskData[4])
                self.tw_taskList.setItem(rc, 4, taskTime)
                if len(taskData) == 7:
                    try:
                        if taskData[5] == "":
                            taskStart = QTableWidgetItem(taskData[5])
                        else:
                            taskStart = QTableWidgetItem(
                                time.strftime(
                                    "%d.%m.%y %X", time.localtime(float(taskData[5]))
                                )
                            )

                        if taskData[6] == "":
                            taskEnd = QTableWidgetItem(taskData[6])
                        else:
                            taskEnd = QTableWidgetItem(
                                time.strftime(
                                    "%d.%m.%y %X", time.localtime(float(taskData[6]))
                                )
                            )
                    except:
                        taskStart = QTableWidgetItem(taskData[5])
                        taskEnd = QTableWidgetItem(taskData[6])
                    self.tw_taskList.setItem(rc, 5, taskStart)
                    self.tw_taskList.setItem(rc, 6, taskEnd)

                if rowColorStyle != "ready":
                    cc = self.tw_taskList.columnCount()
                    for i in range(cc):
                        item = self.tw_taskList.item(rc, i)
                        if item is None:
                            item = QTableWidgetItem("")
                            self.tw_taskList.setItem(rc, i, item)
                        if rowColorStyle == "rendering":
                            item.setForeground(QBrush(QColor(80, 210, 80)))
                        elif rowColorStyle == "finished":
                            item.setForeground(QBrush(QColor(80, 180, 220)))
                        elif rowColorStyle == "disabled":
                            item.setForeground(QBrush(QColor(90, 90, 90)))
                        elif rowColorStyle == "error":
                            item.setForeground(QBrush(QColor(240, 50, 50)))

        self.tw_taskList.resizeColumnsToContents()
        self.tw_taskList.setColumnWidth(6, 50)
        self.tw_taskList.setSortingEnabled(True)
        if (
            self.tw_taskList.horizontalHeader().sortIndicatorSection()
            == self.tw_taskList.columnCount()
        ):
            self.tw_taskList.sortByColumn(0, Qt.AscendingOrder)

    @err_decorator
    def updateJobSettings(self):
        sliderPos = self.tw_jobSettings.verticalScrollBar().value()
        self.tw_jobSettings.setRowCount(0)
        jobSettings = []
        jobInfo = []

        selJobs = []
        for i in self.tw_jobs.selectedIndexes():
            jobName = self.tw_jobs.item(i.row(), 0).text()
            if jobName not in selJobs:
                selJobs.append(jobName)

        if len(selJobs) == 1:
            settingsPath = self.tw_jobs.item(self.tw_jobs.currentRow(), 9).text()

            if os.path.exists(settingsPath):
                jsConfig = self.getConfig(configPath=settingsPath, getConf=True)

                if "jobglobals" in jsConfig:
                    for i in jsConfig["jobglobals"]:
                        if i == "uploadOutput" and self.localMode:
                            continue

                        settingVal = jsConfig["jobglobals"][i]
                        jobSettings.append([i, settingVal])

                if "information" in jsConfig:
                    for i in jsConfig["information"]:
                        settingVal = jsConfig["information"][i]
                        jobInfo.append([i, settingVal])

        self.writeSettings = False

        jobSettings = sorted(jobSettings)
        res = [x for x in jobSettings if x[0] in ["height", "width"]]
        if len(res) == 2:
            idx = jobSettings.index(res[0])
            widthSetting = jobSettings.pop(jobSettings.index(res[1]))
            jobSettings.insert(idx, widthSetting)

        for i in jobSettings:
            rc = self.tw_jobSettings.rowCount()
            self.tw_jobSettings.insertRow(rc)
            settingName = QTableWidgetItem(i[0])
            settingName.setFlags(settingName.flags() ^ Qt.ItemIsEditable)
            self.tw_jobSettings.setItem(rc, 0, settingName)
            if i[0] in ["uploadOutput"]:
                settingVal = QTableWidgetItem()
                if i[1] == True:
                    settingVal.setCheckState(Qt.Checked)
                else:
                    settingVal.setCheckState(Qt.Unchecked)
            elif i[0] in ["priority", "width", "height", "taskTimeout", "concurrentTasks"]:
                settingVal = QTableWidgetItem()
                spinner = QSpinBox()
                if i[0] in ["width", "height", "taskTimeout", "concurrentTasks"]:
                    spinner.setMaximum(9999)
                    spinner.setMinimum(1)
                try:
                    val = i[1]
                except:
                    val = 0
                spinner.setValue(val)
                spinner.editingFinished.connect(
                    lambda x=settingVal, sp=spinner: self.setSetting(
                        stype="js", item=x, widget=sp
                    )
                )
                self.tw_jobSettings.setCellWidget(rc, 1, spinner)
            elif i[0] in ["listSlaves"]:
                settingVal = QTableWidgetItem()
                label = QLabel(i[1])
                label.mouseDprEvent = label.mouseDoubleClickEvent
                label.mouseDoubleClickEvent = lambda x, l=label, it=settingVal: self.mouseClickEvent(
                    x, "listSlaves", l, it
                )
                self.tw_jobSettings.setCellWidget(rc, 1, label)
            else:
                settingVal = QTableWidgetItem(str(i[1]))
            self.tw_jobSettings.setItem(rc, 1, settingVal)

        if len(jobInfo) > 0:
            jobInfo = [["", ""], ["Information:", ""]] + jobInfo

        for i in sorted(jobInfo):
            rc = self.tw_jobSettings.rowCount()
            self.tw_jobSettings.insertRow(rc)
            settingName = QTableWidgetItem(i[0])
            settingName.setFlags(settingName.flags() ^ Qt.ItemIsEditable)
            self.tw_jobSettings.setItem(rc, 0, settingName)
            if pVersion == 2:
                strVal = unicode(i[1])
            else:
                strVal = str(i[1])

            settingVal = QTableWidgetItem(strVal)
            settingVal.setFlags(settingVal.flags() ^ Qt.ItemIsEditable)
            self.tw_jobSettings.setItem(rc, 1, settingVal)

        self.tw_jobSettings.setColumnWidth(0, 150)
        self.writeSettings = True
        self.tw_jobSettings.verticalScrollBar().setValue(sliderPos)

    @err_decorator
    def updateSlaveSettings(self):
        sliderPos = self.tw_slaveSettings.verticalScrollBar().value()
        self.tw_slaveSettings.setRowCount(0)
        slaveSettings = []
        slaveInfo = []
        if self.tw_slaves.currentRow() != -1:
            pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
            if pItem is None:
                return

            settingsPath = (
                self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                .text()
                .replace("slaveLog_", "slaveSettings_")[:-3]
                + "json"
            )
            if os.path.exists(settingsPath):
                ssconfig = self.getConfig(configPath=settingsPath, getConf=True)

                if "settings" in ssconfig:
                    for i in ssconfig["settings"]:
                        if i == "connectionTimeout" and self.localMode:
                            continue

                        settingVal = ssconfig["settings"][i]
                        slaveSettings.append([i, settingVal])

        self.writeSettings = False

        for i in sorted(slaveSettings):
            rc = self.tw_slaveSettings.rowCount()
            self.tw_slaveSettings.insertRow(rc)
            settingName = QTableWidgetItem(i[0])
            settingName.setFlags(settingName.flags() ^ Qt.ItemIsEditable)
            self.tw_slaveSettings.setItem(rc, 0, settingName)
            if i[0] in [
                "cursorCheck",
                "enabled",
                "debugMode",
                "showSlaveWindow",
                "showInterruptWindow",
            ]:
                settingVal = QTableWidgetItem()
                if i[1] == True:
                    settingVal.setCheckState(Qt.Checked)
                else:
                    settingVal.setCheckState(Qt.Unchecked)
            elif i[0] in ["updateTime", "maxCPU", "connectionTimeout", "preRenderWaitTime", "maxConcurrentTasks"]:
                settingVal = QTableWidgetItem()
                spinner = QSpinBox()
                try:
                    val = i[1]
                except:
                    val = 0
                spinner.setValue(val)
                spinner.editingFinished.connect(
                    lambda x=settingVal, sp=spinner: self.setSetting(
                        stype="ss", item=x, widget=sp
                    )
                )
                self.tw_slaveSettings.setCellWidget(rc, 1, spinner)
            elif i[0] in ["slaveGroup"]:
                settingVal = QTableWidgetItem()
                label = QLabel(str(i[1]))
                label.mouseDprEvent = label.mouseDoubleClickEvent
                label.mouseDoubleClickEvent = lambda x, l=label, it=settingVal: self.mouseClickEvent(
                    x, "slaveGroup", l, it
                )
                self.tw_slaveSettings.setCellWidget(rc, 1, label)
            elif i[0] in ["restPeriod"]:
                settingVal = QTableWidgetItem()
                ckbActive = QCheckBox()
                spinnerStart = QSpinBox()
                spinnerEnd = QSpinBox()
                mainW = QWidget()
                layout = QHBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(ckbActive)
                layout.addWidget(spinnerStart)
                layout.addWidget(spinnerEnd)
                mainW.setLayout(layout)
                try:
                    val = i[1]
                    active = val[0]
                    start = val[1]
                    end = val[2]
                except:
                    active = False
                    start = 0
                    end = 0

                ckbActive.setChecked(active)
                spinnerStart.setValue(start)
                spinnerEnd.setValue(end)
                ckbActive.toggled.connect(
                    lambda y, x=settingVal, sp=[
                        ckbActive,
                        spinnerStart,
                        spinnerEnd,
                    ]: self.setSetting(stype="ss", item=x, widget=sp)
                )
                spinnerStart.editingFinished.connect(
                    lambda x=settingVal, sp=[
                        ckbActive,
                        spinnerStart,
                        spinnerEnd,
                    ]: self.setSetting(stype="ss", item=x, widget=sp)
                )
                spinnerEnd.editingFinished.connect(
                    lambda x=settingVal, sp=[
                        ckbActive,
                        spinnerStart,
                        spinnerEnd,
                    ]: self.setSetting(stype="ss", item=x, widget=sp)
                )
                self.tw_slaveSettings.setCellWidget(rc, 1, mainW)
            elif i[0] in ["command", "corecommand"]:
                settingVal = QTableWidgetItem()
                e_command = QLineEdit()
                e_command.setContextMenuPolicy(Qt.CustomContextMenu)
                e_command.customContextMenuRequested.connect(
                    lambda x, eText=e_command: self.rclList("scmd", x, twItem=eText)
                )
                e_command.editingFinished.connect(
                    lambda x=settingVal, ed=e_command: self.setSetting(
                        stype="ss", item=x, widget=ed
                    )
                )
                self.tw_slaveSettings.setCellWidget(rc, 1, e_command)
            else:
                settingVal = QTableWidgetItem(str(i[1]))
            self.tw_slaveSettings.setItem(rc, 1, settingVal)

        self.tw_slaveSettings.setColumnWidth(0, 150)
        self.writeSettings = True

        self.tw_slaveSettings.verticalScrollBar().setValue(sliderPos)

    @err_decorator
    def updateCoordSettings(self):
        self.tw_coordSettings.setRowCount(0)
        coordSettings = []
        settingsPath = os.path.join(self.logDir, "Coordinator", "Coordinator_Settings.json")
        if os.path.exists(settingsPath):
            ssconfig = self.getConfig(configPath=settingsPath, getConf=True)

            if ssconfig and "settings" in ssconfig:
                for i in ssconfig["settings"]:
                    if i in ["restartGDrive", "notifySlaveInterval"] and self.localMode:
                        continue

                    if i in ["repository"]:
                        continue

                    settingVal = ssconfig["settings"][i]
                    coordSettings.append([i, settingVal])

        self.writeSettings = False
        for i in sorted(coordSettings):
            rc = self.tw_coordSettings.rowCount()
            self.tw_coordSettings.insertRow(rc)
            settingName = QTableWidgetItem(i[0])
            settingName.setFlags(settingName.flags() ^ Qt.ItemIsEditable)
            self.tw_coordSettings.setItem(rc, 0, settingName)
            if i[0] in ["coordUpdateTime", "notifySlaveInterval"]:
                settingVal = QTableWidgetItem()
                spinner = QSpinBox()
                try:
                    val = int(i[1])
                except:
                    val = 0
                spinner.setValue(val)
                spinner.editingFinished.connect(
                    lambda x=settingVal, sp=spinner: self.setSetting(
                        stype="cs", item=x, widget=sp
                    )
                )
                self.tw_coordSettings.setCellWidget(rc, 1, spinner)
            elif i[0] in ["debugMode", "restartGDrive"]:
                settingVal = QTableWidgetItem()
                if i[1] == True:
                    settingVal.setCheckState(Qt.Checked)
                else:
                    settingVal.setCheckState(Qt.Unchecked)
            elif i[0] in ["command"]:
                settingVal = QTableWidgetItem()
                e_command = QLineEdit()
                e_command.setContextMenuPolicy(Qt.CustomContextMenu)
                e_command.customContextMenuRequested.connect(
                    lambda x, eText=e_command: self.rclList("ccmd", x, twItem=eText)
                )
                e_command.editingFinished.connect(
                    lambda x=settingVal, ed=e_command: self.setSetting(
                        stype="cs", item=x, widget=ed
                    )
                )
                self.tw_coordSettings.setCellWidget(rc, 1, e_command)
            else:
                settingVal = QTableWidgetItem(i[1])
            self.tw_coordSettings.setItem(rc, 1, settingVal)

        self.tw_coordSettings.resizeColumnsToContents()
        self.tw_coordSettings.setColumnWidth(0, 150)
        self.writeSettings = True

    @err_decorator
    def updateSlaveWarnings(self):
        sliderPos = self.tw_slaveWarnings.verticalScrollBar().value()
        self.tw_slaveWarnings.setRowCount(0)
        slaveWarns = []
        if self.tw_slaves.currentRow() != -1:
            pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
            if pItem is None:
                return

            warningsPath = (
                self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                .text()
                .replace("slaveLog_", "slaveWarnings_")[:-3]
                + "json"
            )
            if os.path.exists(warningsPath):
                swconfig = self.getConfig(
                    configPath=warningsPath, getConf=True, silent=True
                )

                if swconfig == "Error":
                    rc = self.tw_slaveWarnings.rowCount()
                    self.tw_slaveWarnings.insertRow(rc)
                    item = QTableWidgetItem("Unable to read:")
                    self.tw_slaveWarnings.setItem(rc, 0, item)
                    item = QTableWidgetItem(warningsPath)
                    self.tw_slaveWarnings.setItem(rc, 1, item)

                if "warnings" in swconfig:
                    for i in swconfig["warnings"]:
                        try:
                            warnVal = swconfig["warnings"][i]
                            slaveWarns.append(warnVal)
                        except:
                            continue

        for idx, i in enumerate(reversed(sorted(slaveWarns, key=lambda x: x[1]))):
            rc = self.tw_slaveWarnings.rowCount()
            self.tw_slaveWarnings.insertRow(rc)

            if i[2] == 1:
                fbrush = QBrush(QColor(80, 180, 220))
            elif i[2] == 2:
                fbrush = QBrush(QColor(Qt.yellow))
            elif i[2] == 3:
                fbrush = QBrush(QColor(Qt.red))
            else:
                fbrush = QBrush(QColor(Qt.white))

            timeStr = time.strftime("%d.%m.%y %X", time.localtime(i[1]))
            warnName = QTableWidgetItem(timeStr)
            warnName.setForeground(fbrush)
            self.tw_slaveWarnings.setItem(rc, 0, warnName)

            warnItem = QTableWidgetItem(str(i[0]))
            warnItem.setForeground(fbrush)
            self.tw_slaveWarnings.setItem(rc, 1, warnItem)

            if idx == self.sp_logLimit.value():
                break

        self.tw_slaveWarnings.setColumnWidth(0, 150)

        self.tw_slaveWarnings.verticalScrollBar().setValue(sliderPos)

    @err_decorator
    def updateCoordWarnings(self):
        sliderPos = self.tw_coordWarnings.verticalScrollBar().value()
        self.tw_coordWarnings.setRowCount(0)
        coordWarns = []

        warnDir = os.path.join(self.logDir, "Coordinator")
        if not os.path.exists(warnDir):
            return

        warningsPath = self.getCoordWarnPath()

        if os.path.exists(warningsPath):
            wconfig = self.getConfig(configPath=warningsPath, getConf=True)

            if "warnings" in wconfig:
                for i in wconfig["warnings"]:
                    warnVal = wconfig["warnings"][i]
                    coordWarns.append(warnVal)

        for i in reversed(sorted(coordWarns, key=lambda x: x[1])):
            rc = self.tw_coordWarnings.rowCount()
            self.tw_coordWarnings.insertRow(rc)

            if i[2] == 1:
                fbrush = QBrush(QColor(80, 180, 220))
            elif i[2] == 2:
                fbrush = QBrush(QColor(Qt.yellow))
            elif i[2] == 3:
                fbrush = QBrush(QColor(Qt.red))
            else:
                fbrush = QBrush(QColor(Qt.white))

            timeStr = time.strftime("%d.%m.%y %X", time.localtime(i[1]))
            warnName = QTableWidgetItem(timeStr)
            warnName.setForeground(fbrush)
            self.tw_coordWarnings.setItem(rc, 0, warnName)

            warnItem = QTableWidgetItem(i[0])
            warnItem.setForeground(fbrush)
            self.tw_coordWarnings.setItem(rc, 1, warnItem)

        self.tw_coordWarnings.setColumnWidth(0, 150)

        self.tw_coordWarnings.verticalScrollBar().setValue(sliderPos)

    @err_decorator
    def setSetting(self, stype, item, widget=None):
        if not self.writeSettings:
            return

        settingsPath = None
        settingVal = None
        settingName = item.tableWidget().item(item.row(), 0).text()

        selJobs = []
        for i in self.tw_jobs.selectedIndexes():
            jobName = self.tw_jobs.item(i.row(), 0).text()
            if jobName not in selJobs:
                selJobs.append(jobName)

        if stype == "js" and len(selJobs) == 1:
            settingType = "Job"
            section = "jobglobals"
            settingsPath = self.tw_jobs.item(self.tw_jobs.currentRow(), 9).text()

            jcode = self.getConfig("information", "jobcode", configPath=settingsPath)

            if jcode is not None:
                parentName = jcode
            else:
                parentName = self.tw_jobs.item(self.tw_jobs.currentRow(), 0).text()

            if settingName in ["uploadOutput"]:
                settingVal = item.checkState() == Qt.Checked
            elif settingName in ["priority", "width", "height", "taskTimeout", "concurrentTasks"]:
                settingVal = widget.value()
            elif settingName in ["listSlaves"]:
                settingVal = widget.text()
        elif stype == "ss" and self.tw_slaves.currentRow() != -1:
            settingType = "Slave"
            section = "settings"
            parentName = self.tw_slaves.item(self.tw_slaves.currentRow(), 0).text()
            settingsPath = (
                self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                .text()
                .replace("slaveLog_", "slaveSettings_")[:-3]
                + "json"
            )
            if settingName in [
                "cursorCheck",
                "enabled",
                "debugMode",
                "showSlaveWindow",
                "showInterruptWindow",
            ]:
                settingVal = item.checkState() == Qt.Checked
            elif settingName in [
                "updateTime",
                "maxCPU",
                "connectionTimeout",
                "preRenderWaitTime",
                "maxConcurrentTasks",
            ]:
                settingVal = widget.value()
            elif settingName in ["slaveGroup"]:
                settingVal = eval(widget.text())
            elif settingName in ["slaveGroup", "command", "corecommand"]:
                settingVal = widget.text()
            elif settingName in ["restPeriod"]:
                settingVal = [
                    widget[0].checkState() == Qt.Checked,
                    widget[1].value(),
                    widget[2].value(),
                ]
        elif stype == "cs":
            settingType = "Coordinator"
            section = "settings"
            parentName = ""
            settingsPath = os.path.join(
                self.logDir, "Coordinator", "Coordinator_Settings.json"
            )
            if settingName in ["coordUpdateTime", "notifySlaveInterval"]:
                settingVal = widget.value()
            elif settingName in ["debugMode", "restartGDrive"]:
                settingVal = item.checkState() == Qt.Checked
            elif settingName in ["command"]:
                settingVal = widget.text()

        if settingVal is None:
            settingVal = item.text()

        cmd = ["setSetting", settingType, parentName, settingName, settingVal]

        val = self.getConfig(section, cmd[3], configPath=settingsPath)
        if val == settingVal:
            return

        self.writeCmd(cmd)

        if settingsPath is not None and os.path.exists(settingsPath):
            self.modifyConfig(section, settingName, settingVal, configPath=settingsPath)

            if section == "jobglobals" and settingName == "priority":
                self.updateJobData(self.tw_jobs.currentRow())

    @err_decorator
    def modifyConfig(
        self,
        cat=None,
        param=None,
        val=None,
        data=None,
        configPath=None,
        delete=False,
        confData=None,
        clear=False,
    ):
        if configPath is None:
            cachePath = None
        else:
            cachePath = os.path.join(
                self.cacheBase,
                os.path.basename(os.path.dirname(configPath)),
                os.path.basename(configPath),
            )
            if not os.path.exists(os.path.dirname(cachePath)):
                try:
                    os.makedirs(os.path.dirname(cachePath))
                except:
                    return

            if not os.path.exists(cachePath) and os.path.exists(configPath):
                try:
                    shutil.copy2(configPath, cachePath)
                except:
                    pass

        if clear:
            try:
                open(cachePath, "w").close()
            except:
                pass
        else:
            self.core.setConfig(
                cat=cat,
                param=param,
                val=val,
                data=data,
                configPath=cachePath,
                delete=delete,
                confData=confData,
            )

    @err_decorator
    def getConfig(
        self,
        cat=None,
        param=None,
        data=None,
        configPath=None,
        getOptions=False,
        getItems=False,
        getConf=False,
        silent=False,
        readlines=False,
    ):
        cachePath = configPath
        if configPath is not None and configPath.replace("/", "\\").startswith(
            self.logDir.replace("/", "\\")
        ):
            cPath = configPath.replace("/", "\\").replace(
                self.logDir.replace("/", "\\"), self.cacheBase
            )
            if os.path.exists(cPath):
                cachePath = cPath

        if not os.path.exists(cachePath):
            return ""

        if readlines:
            try:
                with io.open(cachePath, "r", encoding="utf-16") as logFile:
                    try:
                        logLines = logFile.readlines()
                    except:
                        logLines = []
            except:
                logLines = []

            return logLines
        else:
            return self.core.getConfig(
                cat=cat,
                param=param,
                data=data,
                configPath=cachePath,
                getOptions=getOptions,
                getItems=getItems,
                getConf=getConf,
                silent=silent,
            )

    @err_decorator
    def writeCmd(self, cmd):
        cmdDir = os.path.join(self.sourceDir, "Commands")

        if not os.path.exists(cmdDir):
            try:
                os.makedirs(cmdDir)
            except:
                QMessageBox.warning(
                    self, "Warning", "Could not create command folder: " % cmdDir
                )
                return

        curNum = 1

        for i in os.listdir(cmdDir):
            if not i.startswith("handlerOut_"):
                continue

            num = i.split("_")[1]
            if pVersion == 2:
                if not unicode(num).isnumeric():
                    continue
            else:
                if not num.isnumeric():
                    continue

            if int(num) >= curNum:
                curNum = int(num) + 1

        cmdFile = os.path.join(
            cmdDir, "handlerOut_%s_%s.txt" % (format(curNum, "04"), time.time())
        )

        try:
            with open(cmdFile, "w") as cFile:
                cFile.write(str(cmd))
        except Exception as e:
            if e.errno == 13:
                self.core.popup("Permission denied to write to file:\n\n%s" % cmdFile)
            else:
                raise

    @err_decorator
    def updateLogCache(self):
        if hasattr(self, "updateLogThread") and self.updateLogThread.is_alive():
            return

        self.updateLogThread = threading.Thread(target=self.getExternalLogs)
        self.updateLogThread.start()

    def getExternalLogs(self):
        logCache = os.path.join(self.remoteLogDir, "Coordinator", "LogCache.json")

        remoteLogs = []
        if os.path.exists(logCache):
            cache = self.core.getConfig(configPath=logCache, getConf=True) or []
            for log in cache:
                localPath = os.path.join(self.logDir, log["path"].lstrip(os.path.sep))

                if os.path.exists(localPath) and int(os.path.getmtime(localPath)) == log["mtime"]:
                    continue

                remotePath = os.path.join(self.remoteLogDir, log["path"].lstrip(os.path.sep))
                remoteLogs.append(remotePath)
        else:
            if os.path.exists(self.remoteLogDir):
                for root, folders, files in os.walk(self.remoteLogDir):
                    for file in files:
                        path = os.path.join(root, file)

                        localLog = path.replace(self.remoteLogDir, self.logDir)
                        if os.path.exists(localLog) and int(os.path.getmtime(localLog)) == int(os.path.getmtime(path)):
                            continue

                        remoteLogs.append(path)

        for remoteLog in remoteLogs:
            localLog = remoteLog.replace(self.remoteLogDir, self.logDir)
            try:
                if not os.path.exists(os.path.dirname(localLog)):
                    os.makedirs(os.path.dirname(localLog))

                shutil.copy2(remoteLog, localLog)
                #print("copy log %s" % localLog)
            except Exception:
                logger.warning("failed to copy log %s to %s" % (remoteLog, localLog))

    @err_decorator
    def mouseClickEvent(self, event, stype, widget, item):
        if event.button() == Qt.LeftButton:
            if stype == "listSlaves":
                if self.refreshTimer.isActive():
                    self.refreshTimer.stop()

                import PandoraSlaveAssignment

                self.sa = PandoraSlaveAssignment.PandoraSlaveAssignment(
                    core=self.core, curSlaves=widget.text()
                )
                self.core.parentWindow(self.sa)
                result = self.sa.exec_()

                if result == QDialog.Accepted:
                    selSlaves = ""
                    if self.sa.rb_exclude.isChecked():
                        selSlaves = "exclude "
                    if self.sa.rb_all.isChecked():
                        selSlaves += "All"
                    elif self.sa.rb_group.isChecked():
                        selSlaves += "groups: "
                        for i in self.sa.activeGroups:
                            selSlaves += i + ", "

                        if selSlaves.endswith(", "):
                            selSlaves = selSlaves[:-2]

                    elif self.sa.rb_custom.isChecked():
                        slavesList = [x.text() for x in self.sa.lw_slaves.selectedItems()]
                        for i in slavesList:
                            selSlaves += i + ", "

                        if selSlaves.endswith(", "):
                            selSlaves = selSlaves[:-2]

                    widget.setText(selSlaves)
                    self.setSetting(stype="js", item=item, widget=widget)

                if self.actionAutoUpdate.isChecked():
                    self.refreshTimer.start()

                widget.mouseDprEvent(event)
            elif stype == "slaveGroup":
                if self.refreshTimer.isActive():
                    self.refreshTimer.stop()

                sList = QDialog(windowTitle="Select slave groups")
                layout = QVBoxLayout()
                lw_slaves = QListWidget()
                lw_slaves.setSelectionMode(QAbstractItemView.ExtendedSelection)
                e_output = QLineEdit()
                try:
                    curGroups = eval(widget.text())
                except:
                    curGroups = []

                slaveGroups = []

                for i in range(self.tw_slaves.rowCount()):

                    pItem = self.tw_slaves.item(i, 7)
                    if pItem is None:
                        continue

                    slaveSettingsPath = (
                        pItem.text().replace("slaveLog_", "slaveSettings_")[:-3] + "json"
                    )

                    if os.path.exists(slaveSettingsPath):
                        val = self.getConfig(
                            "settings", "slaveGroup", configPath=slaveSettingsPath
                        )

                        if val is not None:
                            try:
                                sGroups = val
                            except:
                                sGroups = []
                            for i in sGroups:
                                if i not in slaveGroups:
                                    slaveGroups.append(i)

                outStr = ""
                for i in slaveGroups:
                    gItem = QListWidgetItem(i)
                    lw_slaves.addItem(gItem)
                    if gItem.text() in curGroups:
                        gItem.setSelected(True)
                    outStr += "%s," % i

                e_output.setText(outStr)
                bb_close = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                layout.addWidget(lw_slaves)
                layout.addWidget(e_output)
                layout.addWidget(bb_close)
                sList.setLayout(layout)
                sList.resize(500, 300)
                lw_slaves.itemSelectionChanged.connect(
                    lambda: e_output.setText(
                        ",".join([str(x.text()) for x in lw_slaves.selectedItems()])
                    )
                )
                bb_close.accepted.connect(sList.accept)
                bb_close.rejected.connect(sList.reject)

                self.core.parentWindow(sList)

                result = sList.exec_()

                if result == QDialog.Accepted:
                    widget.setText(
                        str(
                            [
                                str(x)
                                for x in e_output.text().replace(" ", "").split(",")
                                if x != ""
                            ]
                        )
                    )
                    self.setSetting(stype="ss", item=item, widget=widget)
                widget.mouseDprEvent(event)

                if self.actionAutoUpdate.isChecked():
                    self.refreshTimer.start()

    @err_decorator
    def updateSlaveLog(self, filterLvl=0):
        logData = ""
        self.l_slaveLogSize.setText("")
        if self.tw_slaves.currentRow() != -1:
            pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
            if pItem is None:
                return

            logPath = pItem.text()

            if os.path.exists(logPath):
                try:
                    lvl = self.sp_slaveFilter.value()
                    logLines = self.getConfig(configPath=logPath, readlines=True)

                    if self.sp_logLimit.value() == 0 or self.sp_logLimit.value() > len(
                        logLines
                    ):
                        limit = len(logLines)
                    else:
                        limit = self.sp_logLimit.value()

                    if lvl == 0:
                        for i in logLines[-limit:]:
                            logData += self.colorLogLine(i)
                    else:
                        for i in logLines[-limit:]:
                            if (
                                len(i) < 3
                                or (i[0] == "[" and i[2] == "]" and int(i[1]) >= lvl)
                                or (i[0] != "[" and i[2] != "]")
                            ):
                                logData += self.colorLogLine(i)

                    self.l_slaveLogSize.setText(
                        "Logsize: %.2fmb"
                        % float(os.stat(logPath).st_size / 1024.0 / 1024.0)
                    )
                except:
                    QMessageBox.warning(self, "Warning", "Corrupt logfile")

        self.te_slaveLog.setText(logData)
        self.te_slaveLog.moveCursor(QTextCursor.End)

    @err_decorator
    def updateCoordLog(self, filterLvl=0):
        sliderPos = self.te_coordLog.verticalScrollBar().value()

        logData = ""
        self.l_slaveLogSize.setText("")

        logPath = self.getCoordLogPath()

        if os.path.exists(logPath):
            logLines = self.getConfig(configPath=logPath, readlines=True) or []

            lvl = self.sp_coordFilter.value()
            if self.sp_logLimit.value() == 0 or self.sp_logLimit.value() > len(logLines):
                limit = len(logLines)
            else:
                limit = self.sp_logLimit.value()

            if lvl == 0:
                for i in logLines[-limit:]:
                    logData += self.colorLogLine(i)
            else:
                for i in logLines[-limit:]:
                    if (
                        len(i) < 3
                        or (i[0] == "[" and i[2] == "]" and int(i[1]) >= lvl)
                        or (i[0] != "[" and i[2] != "]")
                    ):
                        logData += self.colorLogLine(i)

            if os.path.exists(logPath):
                size = float(os.stat(logPath).st_size / 1024.0 / 1024.0)
            else:
                size = 0

            self.l_coordLogSize.setText(
                "Logsize: %.2fmb" % size
            )

        self.te_coordLog.setText(logData)
        self.te_coordLog.moveCursor(QTextCursor.End)

        self.te_coordLog.verticalScrollBar().setValue(sliderPos)

    @err_decorator
    def getCoordLogPath(self):
        logDir = os.path.join(self.logDir, "Coordinator")
        if not os.path.exists(logDir):
            return ""

        for i in os.listdir(logDir):
            if i.startswith("Coordinator_Log_") and i.endswith(".txt"):
                logPath = os.path.join(logDir, i)
                break
        else:
            return ""

        return logPath

    @err_decorator
    def getCoordWarnPath(self):
        warnDir = os.path.join(self.logDir, "Coordinator")
        if not os.path.exists(warnDir):
            return ""

        for i in os.listdir(warnDir):
            if i.startswith("Coordinator_Warnings_") and i.endswith(".json"):
                warningsPath = os.path.join(warnDir, i)
                break
        else:
            return ""

        return warningsPath

    @err_decorator
    def colorLogLine(self, textLine, level=0):
        if (
            len(textLine) > 2
            and textLine[0] == "["
            and textLine[2] == "]"
            and int(textLine[1]) in range(1, 4)
        ):
            level = int(textLine[1])

        if level == 1:
            lineStr = '<div style="color:#a0caea;">%s</div>' % textLine
        elif level == 2:
            lineStr = '<div style="color:yellow;">%s</div>' % textLine
        elif level == 3:
            lineStr = '<div style="color:red;">%s</div>' % textLine
        else:
            lineStr = '<div style="color:white;">%s</div>' % textLine

        return lineStr

    @err_decorator
    def clearCache(self):
        if not os.path.exists(self.cacheBase):
            return

        delFiles = []

        for i in os.walk(self.cacheBase):
            for f in i[2]:
                fpath = os.path.join(i[0], f)
                try:
                    sourcePath = fpath.replace(self.cacheBase, self.logDir)
                except:
                    continue

                ftime = os.path.getmtime(fpath)

                if not os.path.exists(sourcePath):
                    delFiles.append(fpath)
                    continue

                stime = os.path.getmtime(sourcePath)

                if (time.time() - ftime) > 10 and stime > ftime:
                    delFiles.append(fpath)
                    continue

                if (time.time() - ftime) > 60 * 15 and self.lastContactTime < 5:
                    delFiles.append(fpath)
                    continue

        for i in delFiles:
            try:
                os.remove(fpath)
            except:
                pass

    @err_decorator
    def checkCoordConnected(self):
        if self.lastContactTime > 5:
            self.statusLabel.setText("NOT CONNECTED")
        else:
            self.statusLabel.setText("")

    @err_decorator
    def refreshLastContactTime(self):
        cPath = os.path.join(self.logDir, "Coordinator", "ActiveSlaves.json")

        if os.path.exists(cPath):
            file_mod_time = os.stat(cPath).st_mtime
            last_timeMin = int((time.time() - file_mod_time) / 60)
        else:
            last_timeMin = 999

        self.lastContactTime = last_timeMin

    @err_decorator
    def rclList(self, listType, pos, twItem=None):
        rcmenu = QMenu()

        if listType == "cl":
            coordLog = lambda: self.core.openFile(self.getCoordLogPath())
            logAct = QAction("Open Log", self)
            logAct.triggered.connect(coordLog)
            rcmenu.addAction(logAct)
            clearLogAct = QAction("Clear Log", self)
            clearLogAct.triggered.connect(lambda: self.clearLog(coord=True))
            rcmenu.addAction(clearLogAct)
            coordFolder = lambda: self.core.openFile(
                os.path.join(self.logDir, "Coordinator")
            )
            folderAct = QAction("Open Folder", self)
            folderAct.triggered.connect(coordFolder)
            rcmenu.addAction(folderAct)
        elif listType == "cs":
            coordSettings = lambda: self.core.openFile(
                os.path.join(self.logDir, "Coordinator", "Coordinator_Settings.json")
            )
            fileAct = QAction("Open Settings", self)
            fileAct.triggered.connect(coordSettings)
            rcmenu.addAction(fileAct)
            coordFolder = lambda: self.core.openFile(
                os.path.join(self.logDir, "Coordinator")
            )
            folderAct = QAction("Open Folder", self)
            folderAct.triggered.connect(coordFolder)
            rcmenu.addAction(folderAct)
        elif listType == "ccmd":
            if not self.localMode:
                ucAct = QAction("Search uncollected renderings", self)
                ucAct.triggered.connect(
                    lambda: twItem.setText("self.searchUncollectedRnd()")
                )
                rcmenu.addAction(ucAct)
        elif listType == "cw":
            dwAct = QAction("Delete", self)
            curItem = self.tw_coordWarnings.itemFromIndex(
                self.tw_coordWarnings.indexAt(pos)
            )
            if curItem is not None:
                curRow = curItem.row()
                dwAct.triggered.connect(lambda: self.deleteWarning(curRow, "Coordinator"))
                rcmenu.addAction(dwAct)

            cwAct = QAction("Clear all", self)
            cwAct.triggered.connect(lambda: self.clearWarnings("Coordinator"))
            rcmenu.addAction(cwAct)

        selJobs = []
        for i in self.tw_jobs.selectedIndexes():
            jobName = self.tw_jobs.item(i.row(), 0).text()
            if jobName not in selJobs:
                selJobs.append(jobName)

        if self.tw_jobs.rowCount() > 0 and len(selJobs) > 0:

            jobSettings = self.tw_jobs.item(self.tw_jobs.currentRow(), 9).text()
            if os.path.exists(jobSettings):
                jobSettings = lambda: self.core.openFile(
                    self.tw_jobs.item(self.tw_jobs.currentRow(), 9).text()
                )
            else:
                jobSettings = lambda: self.core.openFile("")
            jobFolder = lambda: self.core.openFile(
                os.path.dirname(self.tw_jobs.item(self.tw_jobs.currentRow(), 9).text())
            )

            if listType == "j":
                if not self.localMode:
                    colAct = QAction("Collect Output", self)
                    colAct.triggered.connect(self.collectOutput)
                    rcmenu.addAction(colAct)

                    rcmenu.addSeparator()

                restartAct = QAction("Restart", self)
                restartAct.triggered.connect(lambda: self.restartTask(selJobs=True))
                rcmenu.addAction(restartAct)

                enableAct = QAction("Enable", self)
                enableAct.triggered.connect(
                    lambda: self.disableTask(selJobs=True, enable=True)
                )
                rcmenu.addAction(enableAct)

                disableAct = QAction("Disable", self)
                disableAct.triggered.connect(lambda: self.disableTask(selJobs=True))
                rcmenu.addAction(disableAct)

                deleteAct = QAction("Delete", self)
                deleteAct.triggered.connect(self.deleteJob)
                rcmenu.addAction(deleteAct)

                rcmenu.addSeparator()

                fileAct = QAction("Open Settings", self)
                fileAct.triggered.connect(jobSettings)
                fileAct.setEnabled(len(selJobs) == 1)
                rcmenu.addAction(fileAct)

                jConfPath = self.tw_jobs.item(self.tw_jobs.currentRow(), 9).text()
                outpath = self.getConfig("information", "outputPath", configPath=jConfPath)

                if outpath is not None:
                    outAct = QAction("Open Output", self)
                    if os.path.splitext(os.path.basename(outpath))[1] != "":
                        outpath = os.path.dirname(outpath)

                    if os.path.basename(outpath) == "beauty":
                        outpath = os.path.dirname(outpath)

                    projectName = self.getConfig(
                        "information", "projectName", configPath=jConfPath
                    )

                    if not self.localMode:
                        outpath = os.path.join(
                            os.path.dirname(os.path.dirname(self.sourceDir)),
                            outpath[outpath.find("\\%s\\" % projectName) + 1 :],
                        )

                    if os.path.exists(outpath) and len(selJobs) == 1:
                        for i in os.walk(outpath):
                            dirs = i[1]
                            if len(dirs) == 1:
                                outpath = os.path.join(outpath, dirs[0])
                            else:
                                break

                        outAct.triggered.connect(lambda: self.core.openFile(outpath))
                    else:
                        outAct.setEnabled(False)
                    rcmenu.addAction(outAct)

                    rvAct = QAction("Play beauty in RV", self)

                    beautyPath = outpath
                    if os.path.exists(os.path.join(outpath, "beauty")):
                        beautyPath = os.path.join(outpath, "beauty")

                    rvAct.triggered.connect(lambda: self.playRV(beautyPath))
                    if (
                        len(selJobs) != 1
                        or not os.path.exists(beautyPath)
                        or len(os.listdir(beautyPath)) == 0
                        or self.rv is None
                    ):
                        rvAct.setEnabled(False)

                    rcmenu.addAction(rvAct)

            elif listType == "tl":
                tasks = {}
                for i in self.tw_taskList.selectedItems():
                    tNum = int(self.tw_taskList.item(i.row(), 0).text())
                    if tNum not in tasks:
                        tasks[tNum] = i.row()

                restartAct = QAction("Restart", self)
                restartAct.triggered.connect(
                    lambda: self.restartTask(self.tw_jobs.currentRow(), tasks.keys())
                )
                restartAct.setEnabled(False)
                for i in tasks:
                    if self.tw_taskList.item(tasks[i], 3).text() != "unassigned":
                        restartAct.setEnabled(True)
                rcmenu.addAction(restartAct)

                enableAct = QAction("Enable", self)
                enableAct.triggered.connect(
                    lambda: self.disableTask(
                        self.tw_jobs.currentRow(), tasks.keys(), enable=True
                    )
                )
                enableAct.setEnabled(False)
                for i in tasks:
                    if self.tw_taskList.item(tasks[i], 2).text() == "disabled":
                        enableAct.setEnabled(True)
                rcmenu.addAction(enableAct)

                disableAct = QAction("Disable", self)
                disableAct.triggered.connect(
                    lambda: self.disableTask(self.tw_jobs.currentRow(), tasks.keys())
                )
                disableAct.setEnabled(False)
                for i in tasks:
                    if self.tw_taskList.item(tasks[i], 2).text() != "disabled":
                        disableAct.setEnabled(True)
                rcmenu.addAction(disableAct)

                rcmenu.addSeparator()

                fileAct = QAction("Open Settings", self)
                fileAct.triggered.connect(jobSettings)
                rcmenu.addAction(fileAct)
                folderAct = QAction("Open Folder", self)
                folderAct.triggered.connect(jobFolder)
                rcmenu.addAction(folderAct)

            elif listType == "js":
                fileAct = QAction("Open Settings", self)
                fileAct.triggered.connect(jobSettings)
                rcmenu.addAction(fileAct)
                folderAct = QAction("Open Folder", self)
                folderAct.triggered.connect(jobFolder)
                rcmenu.addAction(folderAct)

        if self.tw_slaves.rowCount() > 0 and listType in ["s", "sl", "ss", "scmd", "sw"]:

            pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
            if pItem is None:
                return

            slaveName = self.tw_slaves.item(self.tw_slaves.currentRow(), 0).text()

            slaveLog = pItem.text()
            if os.path.exists(slaveLog):
                slaveLog = lambda: self.core.openFile(
                    self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text()
                )
            else:
                slaveLog = lambda: self.core.openFile("")
            slaveSettings = (
                self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                .text()
                .replace("slaveLog_", "slaveSettings_")[:-3]
                + "json"
            )
            if os.path.exists(slaveSettings):
                slaveSettings = lambda: self.core.openFile(
                    self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                    .text()
                    .replace("slaveLog_", "slaveSettings_")[:-3]
                    + "json"
                )
            else:
                slaveSettings = lambda: self.core.openFile("")
            slaveFolder = lambda: self.core.openFile(
                os.path.dirname(self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text())
            )

            if listType == "s":
                logAct = QAction("Open Log", self)
                logAct.triggered.connect(slaveLog)
                rcmenu.addAction(logAct)
                fileAct = QAction("Open Settings", self)
                fileAct.triggered.connect(slaveSettings)
                rcmenu.addAction(fileAct)
                folderAct = QAction("Open Folder", self)
                folderAct.triggered.connect(slaveFolder)
                rcmenu.addAction(folderAct)
                restartAct = QAction("Restart Slave", self)
                restartAct.triggered.connect(lambda: self.restartSlave(slaveName))
                rcmenu.addAction(restartAct)

            elif listType == "sl":
                logAct = QAction("Open Log", self)
                logAct.triggered.connect(slaveLog)
                rcmenu.addAction(logAct)
                clearLogAct = QAction("Clear Log", self)
                clearLogAct.triggered.connect(self.clearLog)
                rcmenu.addAction(clearLogAct)
                folderAct = QAction("Open Folder", self)
                folderAct.triggered.connect(slaveFolder)
                rcmenu.addAction(folderAct)

            elif listType == "ss":
                fileAct = QAction("Open Settings", self)
                fileAct.triggered.connect(slaveSettings)
                rcmenu.addAction(fileAct)
                folderAct = QAction("Open Folder", self)
                folderAct.triggered.connect(slaveFolder)
                rcmenu.addAction(folderAct)

            elif listType == "scmd":
                tvAct = QAction("Start Teamviewer", self)
                tvAct.triggered.connect(lambda: twItem.setText("self.startTeamviewer()"))
                tvAct.triggered.connect(self.teamviewerRequested)
                rcmenu.addAction(tvAct)
                rsAct = QAction("Restart PC", self)
                rsAct.triggered.connect(
                    lambda: twItem.setText("self.shutdownPC(restart=True)")
                )
                rcmenu.addAction(rsAct)
                sdAct = QAction("Shutdown PC", self)
                sdAct.triggered.connect(lambda: twItem.setText("self.shutdownPC()"))
                rcmenu.addAction(sdAct)
                srAct = QAction("Stop Render", self)
                srAct.triggered.connect(lambda: twItem.setText("self.stopRender()"))
                rcmenu.addAction(srAct)
                if not self.localMode:
                    ucAct = QAction("Upload current job output", self)
                    ucAct.triggered.connect(lambda: twItem.setText("self.uploadCurJob()"))
                    rcmenu.addAction(ucAct)

            elif listType == "sw":
                dwAct = QAction("Delete", self)
                curItem = self.tw_slaveWarnings.itemFromIndex(
                    self.tw_slaveWarnings.indexAt(pos)
                )
                if curItem is not None:

                    curRow = curItem.row()
                    dwAct.triggered.connect(lambda: self.deleteWarning(curRow, "Slave"))
                    rcmenu.addAction(dwAct)

                cwAct = QAction("Clear all", self)
                cwAct.triggered.connect(lambda: self.clearWarnings("Slave"))
                rcmenu.addAction(cwAct)

        if rcmenu.isEmpty():
            return False

        getattr(self.core.appPlugin, "setRCStyle", lambda x, y: None)(self, rcmenu)

        rcmenu.exec_(QCursor.pos())

    @err_decorator
    def deleteWarning(self, row, warnType):
        if warnType == "Slave":
            if self.tw_slaves.currentRow() == -1:
                return

            pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
            if pItem is None:
                return

            warningsPath = (
                self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                .text()
                .replace("slaveLog_", "slaveWarnings_")[:-3]
                + "json"
            )
            if not os.path.exists(warningsPath):
                return

            text = self.tw_slaveWarnings.item(row, 1).text()

        elif warnType == "Coordinator":
            warningsPath = self.getCoordWarnPath()
            if not os.path.exists(warningsPath):
                return

            text = self.tw_coordWarnings.item(row, 1).text()

        warnNum = "warning" + str(row)
        warnData = self.getConfig(configPath=warningsPath, getConf=True)
        warnVal = []
        for i in warnData["warnings"]:
            if str(warnData["warnings"][i][0]) == str(text):
                warnVal = warnData["warnings"][i]

        if warnVal == []:
            return

        message = "Do you really want to delete this warning:\n\n"
        if warnType == "Slave":
            curSlave = self.tw_slaves.item(self.tw_slaves.currentRow(), 0).text()
            message = message[:-3] + " on slave %s:\n\n" % curSlave
        else:
            curSlave = ""

        message += "%s\n\n%s\n" % (
            time.strftime("%d.%m.%y %X", time.localtime(warnVal[1])),
            warnVal[0],
        )
        delMsg = QMessageBox(
            QMessageBox.Question, "Delete warning", message, QMessageBox.No
        )
        delMsg.addButton("Yes", QMessageBox.YesRole)
        self.core.parentWindow(delMsg)
        result = delMsg.exec_()

        if result == 0:
            self.writeCmd(["deleteWarning", warnType, curSlave, warnVal[0], warnVal[1]])

            warns = self.getConfig("warnings", configPath=warningsPath, getItems=True)

            warnings = []
            for i in sorted(warns.values()):
                warnings.append(i)

            warnings = [
                x for x in warnings if not (x[0] == warnVal[0] and x[1] == warnVal[1])
            ]

            cData = []
            for i in warns:
                cData.append(["warnings", i, ""])

            self.modifyConfig(configPath=warningsPath, data=cData, delete=True)

            cData = []
            for idx, val in enumerate(warnings):
                cData.append(["warnings", "warning%s" % idx, val])

            self.modifyConfig(data=cData, configPath=warningsPath)

            if warnType == "Slave":
                self.updateSlaveWarnings()
            elif warnType == "Coordinator":
                self.updateCoordWarnings()

    @err_decorator
    def clearWarnings(self, warnType):
        if warnType == "Slave":
            if self.tw_slaves.currentRow() == -1:
                return

            pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
            if pItem is None:
                return

            warningsPath = (
                self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                .text()
                .replace("slaveLog_", "slaveWarnings_")[:-3]
                + "json"
            )
            if not os.path.exists(warningsPath):
                return

        elif warnType == "Coordinator":
            warningsPath = self.getCoordWarnPath()
            if not os.path.exists(warningsPath):
                return

        message = "Do you really want to delete all warnings of "
        if warnType == "Slave":
            curSlave = self.tw_slaves.item(self.tw_slaves.currentRow(), 0).text()
            message += 'slave "%s"?' % curSlave
        else:
            message += "the coordinator?"
            curSlave = ""

        delMsg = QMessageBox(
            QMessageBox.Question, "Clear warnings", message, QMessageBox.No
        )
        delMsg.addButton("Yes", QMessageBox.YesRole)
        self.core.parentWindow(delMsg)
        result = delMsg.exec_()

        if result == 0:
            self.writeCmd(["clearWarnings", warnType, curSlave])

            warningConfig = {"warnings": {}}

            self.modifyConfig(configPath=warningsPath, confData=warningConfig)

            if warnType == "Slave":
                self.updateSlaveWarnings()
            elif warnType == "Coordinator":
                self.updateCoordWarnings()

    @err_decorator
    def showWarning(self, warnType, item):
        if warnType == "Slave":
            if self.tw_slaves.currentRow() == -1:
                return

            pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
            if pItem is None:
                return

            warningsPath = (
                self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
                .text()
                .replace("slaveLog_", "slaveWarnings_")[:-3]
                + "json"
            )
            if not os.path.exists(warningsPath):
                return

        elif warnType == "Coordinator":
            warningsPath = self.getCoordWarnPath()
            if not os.path.exists(warningsPath):
                return

        text = item.text()
        warnNum = "warning" + str(item.row())
        warnData = self.getConfig(configPath=warningsPath, getConf=True)
        warnVal = []
        for i in warnData["warnings"]:
            if str(warnData["warnings"][i][0]) == str(text):
                warnVal = warnData["warnings"][i]

        if warnVal == []:
            return

        if warnData is None:
            QMessageBox.warning(self, "Warning", "Corrupt warning file")
            return

        message = "%s\n\n%s\n" % (
            time.strftime("%d.%m.%y %X", time.localtime(warnVal[1])),
            warnVal[0],
        )
        QMessageBox.information(self, "Warning", message)

    @err_decorator
    def teamviewerRequested(self):
        ssDir = os.path.join(self.sourceDir, "Screenshots")
        if not os.path.exists(ssDir):
            os.makedirs(ssDir)

        self.core.openFile(ssDir)

    @err_decorator
    def restartSlave(self, slaveName):
        cmd = ["setSetting", "Slave", slaveName, "command", "self.restartLogic()"]
        self.writeCmd(cmd)

    @err_decorator
    def clearLog(self, coord=False):
        if coord:
            logType = "Coordinator"
            logName = ""
            logPath = self.getCoordLogPath()
            refresh = self.updateCoordLog
        else:
            logType = "Slave"

            curSlave = self.tw_slaves.item(self.tw_slaves.currentRow(), 0)
            if curSlave is None:
                return

            logPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text()

            logName = curSlave.text()
            refresh = self.updateSlaveLog

        self.writeCmd(["clearLog", logType, logName])

        self.modifyConfig(configPath=logPath, clear=True)

        refresh()

    @err_decorator
    def collectOutput(self):
        selJobs = []
        for i in self.tw_jobs.selectedIndexes():
            jobName = self.tw_jobs.item(i.row(), 0).text()
            if jobName not in selJobs:
                selJobs.append(jobName)

        for curJobName in selJobs:
            jobConf = os.path.join(self.logDir, "Jobs", "%s.json" % curJobName)

            jCode = self.getConfig("information", "jobcode", configPath=jobConf)

            if jCode is not None:
                jobCode = jCode
            else:
                jobCode = curJobName

            self.writeCmd(["collectJob", jobCode])

        QMessageBox.information(self, "CollectOutput", "Collect request was sent.")

    @err_decorator
    def deleteJob(self):
        selJobs = []
        for i in self.tw_jobs.selectedIndexes():
            jobName = self.tw_jobs.item(i.row(), 0).text()
            if jobName not in selJobs:
                selJobs.append(jobName)

        message = "Do you really want to delete the selected jobs?"
        delMsg = QMessageBox(QMessageBox.Question, "Delete Job", message, QMessageBox.No)
        delMsg.addButton("Yes", QMessageBox.YesRole)
        self.core.parentWindow(delMsg)
        result = delMsg.exec_()

        if result == 0:
            for curJobName in selJobs:
                jobConf = os.path.join(self.logDir, "Jobs", "%s.json" % curJobName)

                jCode = self.getConfig("information", "jobcode", configPath=jobConf)

                if jCode is not None:
                    jobCode = jCode
                else:
                    jobCode = curJobName

                self.writeCmd(["deleteJob", jobCode])

                self.modifyConfig(configPath=jobConf, clear=True)

            self.updateJobs()

    @err_decorator
    def restartTask(self, job=None, tasks=None, selJobs=False):
        if selJobs:
            taskItems = []
            selJobNames = []
            for i in self.tw_jobs.selectedIndexes():
                jobName = self.tw_jobs.item(i.row(), 0).text()
                if jobName not in selJobNames:
                    selJobNames.append(jobName)
                    jobConf = os.path.join(self.logDir, "Jobs", "%s.json" % jobName)
                    jobTasks = [
                        int(x[4:])
                        for x in self.getConfig(
                            "jobtasks", getOptions=True, configPath=jobConf
                        )
                    ]
                    taskItems.append([jobName, jobTasks, i.row()])
        else:
            taskItems = [
                [self.tw_jobs.item(job, 0).text(), tasks, self.tw_jobs.currentRow()]
            ]

        for jobName, tasks, jobRow in taskItems:
            jobConf = os.path.join(self.logDir, "Jobs", "%s.json" % jobName)

            jCode = self.getConfig("information", "jobcode", configPath=jobConf)

            if jCode is not None:
                jobCode = jCode
            else:
                jobCode = jobName

            cData = []

            for i in tasks:
                self.writeCmd(["restartTask", jobCode, i])
                taskData = self.getConfig("jobtasks", "task%04d" % i, configPath=jobConf)
                if taskData is not None:
                    taskData[2] = "ready"
                    taskData[3] = "unassigned"
                    taskData[4] = ""
                    taskData[5] = ""
                    taskData[6] = ""
                    cData.append(["jobtasks", "task%04d" % i, taskData])

            self.modifyConfig(configPath=jobConf, data=cData)
            self.updateJobData(jobRow)

        self.updateTaskList()

    @err_decorator
    def disableTask(self, job=None, tasks=None, selJobs=False, enable=False):
        if selJobs:
            taskItems = []
            selJobNames = []
            for i in self.tw_jobs.selectedIndexes():
                jobName = self.tw_jobs.item(i.row(), 0).text()
                if jobName not in selJobNames:
                    selJobNames.append(jobName)
                    jobConf = os.path.join(self.logDir, "Jobs", "%s.json" % jobName)
                    jobTasks = [
                        int(x[4:])
                        for x in self.getConfig(
                            "jobtasks", getOptions=True, configPath=jobConf
                        )
                    ]
                    taskItems.append([jobName, jobTasks, i.row()])
        else:
            taskItems = [
                [self.tw_jobs.item(job, 0).text(), tasks, self.tw_jobs.currentRow()]
            ]

        for jobName, tasks, jobRow in taskItems:
            jobConf = os.path.join(self.logDir, "Jobs", "%s.json" % jobName)

            jCode = self.getConfig("information", "jobcode", configPath=jobConf)

            if jCode is not None:
                jobCode = jCode
            else:
                jobCode = jobName

            cData = []

            for i in tasks:
                self.writeCmd(["disableTask", jobCode, i, enable])

                taskData = self.getConfig("jobtasks", "task%04d" % i, configPath=jobConf)
                if taskData is not None:
                    if (
                        taskData[2] in ["ready", "rendering", "assigned"] and not enable
                    ) or (taskData[2] == "disabled" and enable):
                        if enable:
                            taskData[2] = "ready"
                            taskData[3] = "unassigned"
                        else:
                            taskData[2] = "disabled"
                            taskData[3] = "unassigned"
                        cData.append(["jobtasks", "task%04d" % i, taskData])

            self.modifyConfig(configPath=jobConf, data=cData)
            self.updateJobData(jobRow)

        self.updateTaskList()

    @err_decorator
    def playRV(self, path):
        sequence = [x for x in os.listdir(path) if x.endswith(".exr")]
        if sequence == []:
            QMessageBox.warning(
                self, "Warning", "There are no .exr files in the outputfolder."
            )
            return

        subprocess.Popen(
            [self.rv, os.path.join(path, sequence[0][:-8] + "@@@@" + sequence[0][-4:])]
        )

    @err_decorator
    def getRVpath(self):
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\rv.exe",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            self.rv = _winreg.QueryValue(key, None)
        except:
            self.rv = None


if __name__ == "__main__":
    qApp = QApplication(sys.argv)
    qApp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
    handlerIcon = QIcon(
        os.path.dirname(os.path.abspath(__file__)) + "\\UserInterfacesPandora\\rh_tray.ico"
    )
    qApp.setWindowIcon(handlerIcon)
    import PandoraCore

    pc = PandoraCore.PandoraCore()
    pc.openRenderHandler()
    qApp.exec_()
