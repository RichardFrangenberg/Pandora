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
# Copyright (C) 2016-2018 Richard Frangenberg
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

import sys, os, io, subprocess, time, shutil, traceback, socket
from functools import wraps

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))
if psVersion == 1:
	import RenderHandler_ui
else:
	import RenderHandler_ui_ps2 as RenderHandler_ui

if sys.version[0] == "3":
	from configparser import ConfigParser
	import winreg as _winreg
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	import _winreg
	pVersion = 2

from UserInterfacesPandora import qdarkstyle

class RenderHandler(QMainWindow, RenderHandler_ui.Ui_mw_RenderHandler):
	def __init__(self, core):
		QMainWindow.__init__(self)
		self.setupUi(self)

		try:
			self.core = core
			self.core.parentWindow(self)

			self.configPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Config", "Pandora.ini")

			self.pconfig = ConfigParser()
			self.pconfig.read(self.configPath)

			lmode = self.core.getConfig("globals", "localmode")
			if lmode == "True":
				self.localmode = True
			else:
				self.localmode = False

			if self.localmode:
				if self.pconfig.has_option("globals", "rootpath"):
					rootPath = self.pconfig.get("globals", "rootpath")
					self.sourceDir = os.path.join(rootPath, "PandoraFarm", "Workstations", "WS_" + socket.gethostname(), "")
					if not os.path.exists(self.sourceDir):
						try:
							os.makedirs(self.sourceDir)
						except:
							pass
			else:
				if self.pconfig.has_option("submissions", "submissionpath"):
					self.sourceDir = self.pconfig.get("submissions", "submissionpath")
				else:
					if not self.pconfig.has_section("submissions"):
						self.pconfig.add_section("submissions")

					self.pconfig.set("submissions", "submissionpath", "")

					with open(self.configPath, 'w') as inifile:
						self.pconfig.write(inifile)

					self.sourceDir = ""

			if not os.path.exists(self.sourceDir):
				QMessageBox.warning(self,"Warning", "No Pandora submission folder specified in the Pandora config")

			self.logDir = os.path.join(os.path.dirname(os.path.dirname(self.sourceDir)), "Logs")

			self.writeSettings = True

			self.getRVpath()

			self.loadLayout()
			self.connectEvents()
			self.updateJobs()
			self.updateSlaves()
			self.loadLayout(preUpdate=False)
			self.showCoord()
			self.checkCoordConnected()


		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			erStr = ("%s ERROR - Renderhandler %s:\n%s\n\n%s" % (time.strftime("%d.%m.%y %X"), self.core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
			self.core.writeErrorLog(erStr)


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Renderhandler %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def loadLayout(self, preUpdate=True):
		if preUpdate:
			self.actionRefresh = QAction("Refresh", self)
			self.menubar.addAction(self.actionRefresh)

			helpMenu = QMenu("Help")

			self.actionWebsite = QAction("Visit website", self)
			self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
			helpMenu.addAction(self.actionWebsite)

			self.actionSendFeedback = QAction("Send feedback/feature requests...", self)
			self.actionSendFeedback.triggered.connect(self.core.sendFeedback)
			helpMenu.addAction(self.actionSendFeedback)

			self.actionAbout = QAction("About...", self)
			self.actionAbout.triggered.connect(self.core.showAbout)
			helpMenu.addAction(self.actionAbout)
		
			self.menubar.addMenu(helpMenu)

			self.setRCStyle(helpMenu)

			self.tw_jobs.setColumnCount(10)
			self.tw_jobs.setHorizontalHeaderLabels(["Name", "Status", "Progress", "Prio", "Frames", "Sumit Date", "Project", "User", "Program", "settingsPath"])
			self.tw_jobs.setColumnHidden(9, True)
			self.tw_jobs.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
			self.tw_jobs.verticalHeader().setDefaultSectionSize(17);
			font = self.tw_jobs.font()
			font.setPointSize(8)
			self.tw_jobs.setFont(font)
			self.tw_jobs.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}");
			self.tw_coordSettings.setStyleSheet(self.styleSheet().replace("QCheckBox::indicator", "QTableWidget::indicator"))
			self.tw_slaveSettings.setStyleSheet(self.styleSheet().replace("QCheckBox::indicator", "QTableWidget::indicator"))
			self.tw_jobSettings.setStyleSheet(self.styleSheet().replace("QCheckBox::indicator", "QTableWidget::indicator"))
			

			self.tw_taskList.setColumnCount(7)
			self.tw_taskList.setHorizontalHeaderLabels(["Num", "Frames", "Status", "Slave", "Rendertime", "Start", "End"])
			self.tw_taskList.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
			if self.core.app == 2:
				self.tw_taskList.verticalHeader().setFixedWidth(20)
				self.tw_taskList.verticalHeader().setDefaultSectionSize(20)
			else:
				self.tw_taskList.verticalHeader().setDefaultSectionSize(17);
			font = self.tw_taskList.font()
			font.setPointSize(8)
			self.tw_taskList.setFont(font)
			self.tw_taskList.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}");

			self.tw_jobSettings.setColumnCount(2)
			self.tw_jobSettings.setHorizontalHeaderLabels(["Name", "Value"])
			self.tw_jobSettings.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
			self.tw_jobSettings.verticalHeader().setDefaultSectionSize(25);
			font = self.tw_jobSettings.font()
			font.setPointSize(8)
			self.tw_jobSettings.setFont(font)
			self.tw_jobSettings.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}");

			self.tw_slaves.setColumnCount(9)
			self.tw_slaves.setHorizontalHeaderLabels(["Name", "Status", "Job", "last Contact", "Warnings", "RAM", "Cores", "LogPath", "Version"])
			self.tw_slaves.setColumnHidden(7, True)
			self.tw_slaves.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
			if self.core.app == 2:
				self.tw_slaves.verticalHeader().setFixedWidth(20)
				self.tw_slaves.verticalHeader().setDefaultSectionSize(20)
			else:
				self.tw_slaves.verticalHeader().setDefaultSectionSize(17)
			font = self.tw_slaves.font()
			font.setPointSize(8)
			self.tw_slaves.setFont(font)
			self.tw_slaves.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}");

			self.tw_slaveSettings.setColumnCount(2)
			self.tw_slaveSettings.setHorizontalHeaderLabels(["Name", "Value"])
			self.tw_slaveSettings.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
			self.tw_slaveSettings.verticalHeader().setDefaultSectionSize(25);
			font = self.tw_slaveSettings.font()
			font.setPointSize(8)
			self.tw_slaveSettings.setFont(font)
			self.tw_slaveSettings.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}")
			if psVersion == 1:
				self.tw_slaveWarnings.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
			else:
				self.tw_slaveWarnings.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

			self.tw_coordSettings.setColumnCount(2)
			self.tw_coordSettings.setHorizontalHeaderLabels(["Name", "Value"])
			self.tw_coordSettings.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
			self.tw_coordSettings.verticalHeader().setDefaultSectionSize(25);
			font = self.tw_coordSettings.font()
			font.setPointSize(8)
			self.tw_coordSettings.setFont(font)
			self.tw_coordSettings.verticalHeader().setStyleSheet("QHeaderView { font-size: 6pt;}")
			if psVersion == 1:
				self.tw_coordWarnings.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
			else:
				self.tw_coordWarnings.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

			self.l_logLimit = QLabel("LogLimit:")
			self.sp_logLimit = QSpinBox()
			self.sp_logLimit.setRange(0,99999)
			llimit = self.core.getConfig('renderhandler', 'loglimit')
			if llimit is not None:
				self.sp_logLimit.setValue(eval(llimit))
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
			self.sp_refInt.setRange(1,99999)

			self.refreshPeriod = 10
			refreshT = self.core.getConfig('renderhandler', 'refreshtime')
			if refreshT is not None:
				self.refreshPeriod = eval(refreshT)

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

			aupdate = self.core.getConfig('renderhandler', 'autoupdate')
			if aupdate is not None:
				self.actionAutoUpdate.setChecked(eval(aupdate))
			else:
				self.actionAutoUpdate.setChecked(True)

			self.menuOptions.addAction(self.actionAutoUpdate)

			self.actionShowCoord = QAction("Show Coordinator", self)
			self.actionShowCoord.setCheckable(True)

			scoord = self.core.getConfig('renderhandler', 'showcoordinator')
			if scoord == "True":
				self.actionShowCoord.setChecked(eval(scoord))
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

			wsize = self.core.getConfig('renderhandler', 'windowSize')
			if wsize is not None and wsize != "":
				wsize = eval(wsize)
				self.resize(wsize[0], wsize[1])
			else:
				screenW = QApplication.desktop().screenGeometry().width()
				screenH = QApplication.desktop().screenGeometry().height()
				space = 100
				#if screenH < (self.height()+space):
				self.resize(self.width(), screenH-space-50)

				#if screenW < (self.width()+space):
				self.resize(screenW-space, self.height())

			if self.core.app == 2:
				self.houLoadLayout()


	@err_decorator
	def closeEvent(self, event):
		self.core.setConfig('renderhandler', "windowSize", str([self.width(), self.height()]))
		self.core.setConfig('renderhandler', "loglimit", str(self.sp_logLimit.value()))
		self.core.setConfig('renderhandler', "showcoordinator", str(self.actionShowCoord.isChecked()))
		self.core.setConfig('renderhandler', "refreshtime", str(self.refreshPeriod))
		self.core.setConfig('renderhandler', "autoupdate", str(self.actionAutoUpdate.isChecked()))


	@err_decorator
	def houLoadLayout(self):
		self.splitter_3.setStyleSheet(self.core.executeHouPython("hou.qt.styleSheet()").replace("QLabel", "QSplitter"))
		self.tw_jobs.setStyleSheet(self.core.executeHouPython("hou.qt.styleSheet()").replace("QLabel", "QHeaderView"))
		self.tw_slaves.setStyleSheet(self.core.executeHouPython("hou.qt.styleSheet()").replace("QLabel", "QHeaderView"))
		self.tw_slaveWarnings.setStyleSheet(self.core.executeHouPython("hou.qt.styleSheet()").replace("QLabel", "QHeaderView"))
		self.tw_coordWarnings.setStyleSheet(self.core.executeHouPython("hou.qt.styleSheet()").replace("QLabel", "QHeaderView"))


	@err_decorator
	def setRCStyle(self, rcmenu):
		if self.core.app == 2:
			rcmenu.setStyleSheet(self.parent().styleSheet())


	@err_decorator
	def timeoutSlot(self):
		self.seconds -= 1
		self.l_refreshCounter.setText("Refresh in %s seconds." % self.seconds)
		if self.seconds==0:
			self.seconds = self.refreshPeriod
			self.refresh()
			self.l_refreshCounter.setText("Refresh in %s seconds." % self.seconds)


	@err_decorator
	def connectEvents(self):
		self.tw_jobs.itemSelectionChanged.connect(self.jobChanged)
		self.tw_jobs.customContextMenuRequested.connect(lambda x: self.rclList("j", x))
		self.tw_taskList.customContextMenuRequested.connect(lambda x: self.rclList("tl", x))
		self.te_coordLog.customContextMenuRequested.connect(lambda x: self.rclList("cl", x))
		self.tw_jobSettings.itemChanged.connect(lambda x: self.setSetting("js", x))
		self.tw_jobSettings.customContextMenuRequested.connect(lambda x: self.rclList("js", x))
		self.tw_slaves.itemSelectionChanged.connect(self.slaveChanged)
		self.tw_slaves.customContextMenuRequested.connect(lambda x: self.rclList("s", x))
		self.te_slaveLog.customContextMenuRequested.connect(lambda x: self.rclList("sl", x))
		self.tw_slaveSettings.customContextMenuRequested.connect(lambda x: self.rclList("ss", x))
		self.tw_slaveSettings.itemChanged.connect(lambda x: self.setSetting("ss", x))
		self.sp_slaveFilter.valueChanged.connect(self.updateSlaveLog)
		self.tw_slaveWarnings.customContextMenuRequested.connect(lambda x: self.rclList("sw", x))
		self.tw_slaveWarnings.itemDoubleClicked.connect(lambda x: self.showWarning("Slave", x))
		self.sp_coordFilter.valueChanged.connect(self.updateCoordLog)
		self.tw_coordSettings.itemChanged.connect(lambda x: self.setSetting("cs", x))
		self.tw_coordSettings.customContextMenuRequested.connect(lambda x: self.rclList("cs", x))
		self.tw_coordWarnings.customContextMenuRequested.connect(lambda x: self.rclList("cw", x))
		self.tw_coordWarnings.itemDoubleClicked.connect(lambda x: self.showWarning("Coordinator", x))
		self.actionShowCoord.toggled.connect(self.showCoord)
		self.actionAutoUpdate.toggled.connect(self.autoUpdate)
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
	def updateRefInterval(self):
		self.seconds = self.refreshPeriod = self.sp_refInt.value()


	@err_decorator
	def refresh(self):

		self.statusBar().showMessage("refreshing...")
		self.refreshTimer.stop()
		self.l_refreshCounter.setText("")
		if self.tw_jobs.rowCount() > 0:
			curJobRow = self.tw_jobs.currentIndex().row()
			if curJobRow != -1:
				curJobName = self.tw_jobs.item(curJobRow, 0).text()
			curJobSliderPos = self.tw_jobs.verticalScrollBar().value()
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
			fparent = qapp.focusWidget().parent().parent()
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

		if "curJobName" in locals() and updateJobs:
			for i in range(self.tw_jobs.rowCount()):
				if self.tw_jobs.item(i,0).text() == curJobName:
					self.tw_jobs.selectRow(i)
					break

		if "curJobSliderPos" in locals() and updateJobs:
			self.tw_jobs.verticalScrollBar().setValue(curJobSliderPos)

		if "curSlaveName" in locals() and updateSlaves:
			for i in range(self.tw_slaves.rowCount()):
				if self.tw_slaves.item(i,0).text() == curSlaveName:
					self.tw_slaves.selectRow(i)
					break

		if "curSlaveSliderPos" in locals() and updateSlaves:
			self.tw_slaves.verticalScrollBar().setValue(curSlaveSliderPos)

		self.te_slaveLog.verticalScrollBar().setValue(sLogSliderPos)

		self.statusBar().clearMessage()
		self.checkCoordConnected()
		self.seconds = self.refreshPeriod
		if self.actionAutoUpdate.isChecked():
			self.refreshTimer.start()


	@err_decorator
	def jobChanged(self):
		self.updateTaskList()
		self.updateJobSettings()


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
				settingsPath = os.path.join(jobDir,i)
				if not (os.path.isfile(settingsPath) and i.endswith(".ini")):
					continue

				rc = self.tw_jobs.rowCount()
				self.tw_jobs.insertRow(rc)

				settingsPathItem = QTableWidgetItem(settingsPath)
				self.tw_jobs.setItem(rc, 9, settingsPathItem)
				self.updateJobData(rc)

		self.tw_jobs.resizeColumnsToContents()
		self.tw_jobs.horizontalHeader().setStretchLastSection(True)
		self.tw_jobs.setColumnWidth(1,60)
		self.tw_jobs.setColumnWidth(2,60)
		self.tw_jobs.setColumnWidth(3,30)
		self.tw_jobs.setColumnWidth(0,400)
		self.tw_jobs.setSortingEnabled(True)
		self.tw_jobs.sortByColumn(5, Qt.DescendingOrder)

	@err_decorator
	def updateJobData(self, rc):
		jobPath = self.tw_jobs.item(rc,9).text()
		if not (os.path.isfile(jobPath) and jobPath.endswith(".ini")):
			self.updateJobs()
			return

		self.tw_jobs.setSortingEnabled(False)

		jobName = QTableWidgetItem(os.path.splitext(os.path.basename(jobPath))[0])
		self.tw_jobs.setItem(rc, 0, jobName)

		rowColorStyle = "ready"

		jsconfig = ConfigParser()
		jsconfig.read(jobPath)

		if jsconfig.has_section("jobtasks"):
			finNum = 0
			notfinNum = 0
			status = "unknown"
			for i in jsconfig.options("jobtasks"):
				taskData = eval(jsconfig.get("jobtasks", i))
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

			progress = int(100/float(finNum + notfinNum)*float(finNum))

			progressItem = QTableWidgetItem(str(progress) + " %")
			self.tw_jobs.setItem(rc, 2, progressItem)

		if jsconfig.has_option("jobglobals", "priority"):
			jobPrio = jsconfig.get('jobglobals', "priority")
			jobPrioItem = QTableWidgetItem(jobPrio)
			self.tw_jobs.setItem(rc, 3, jobPrioItem)

		if jsconfig.has_option("information", "framerange"):
			framerange = jsconfig.get('information', "framerange")
			framerangeItem = QTableWidgetItem(framerange)
			self.tw_jobs.setItem(rc, 4, framerangeItem)

		if jsconfig.has_option("information", "submitdate"):
			submitDate = jsconfig.get('information', "submitdate")
			submitdateItem = QTableWidgetItem(submitDate)
			submitdateItem.setData(0, QDateTime.fromString( submitDate, "dd.MM.yy, hh:mm:ss").addYears(100))
			submitdateItem.setToolTip(submitDate)
			self.tw_jobs.setItem(rc, 5, submitdateItem)

		if jsconfig.has_option("information", "projectname"):
			pName = jsconfig.get('information', "projectname")
			pNameItem = QTableWidgetItem(pName)
			self.tw_jobs.setItem(rc, 6, pNameItem)

		if jsconfig.has_option("information", "username"):
			uName = jsconfig.get('information', "username")
			uNameItem = QTableWidgetItem(uName)
			self.tw_jobs.setItem(rc, 7, uNameItem)

		if jsconfig.has_option("information", "program"):
			pName = jsconfig.get('information', "program")
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
					item.setForeground(QBrush(QColor(80,210,80)))
				elif rowColorStyle == "finished":
					item.setForeground(QBrush(QColor(80,180,220)))
				elif rowColorStyle == "disabled":
					item.setForeground(QBrush(QColor(90,90,90)))
				elif rowColorStyle == "error":
					item.setForeground(QBrush(QColor(240,50,50)))

		self.tw_jobs.setSortingEnabled(True)


	@err_decorator
	def updateSlaves(self):
		self.tw_slaves.setRowCount(0)
		self.tw_slaves.setSortingEnabled(False)
		slaveDir = os.path.join(self.logDir, "Slaves")

		activeSlaves = {}
		actSlvPath = os.path.join(self.logDir, "PandoraCoordinator", "ActiveSlaves.txt")
		if os.path.exists(actSlvPath):
			try:
				with open(actSlvPath, "r") as actFile:
					activeSlaves = eval(actFile.read())
			except:
				pass

		if os.path.isdir(slaveDir):
			corruptSlaves = []
			for i in os.listdir(slaveDir):
				try:
					slaveLogPath = os.path.join(slaveDir, i)
					if i.startswith("slaveLog_") and i.endswith(".txt") and os.path.isfile(slaveLogPath):
						rc = self.tw_slaves.rowCount()
						slaveName = i[len("slaveLog_"):-len(".txt")]
						slaveSettingsPath = slaveLogPath.replace("slaveLog_", "slaveSettings_")[:-3] + "ini"
						slaveWarningsPath = slaveLogPath.replace("slaveLog_", "slaveWarnings_")[:-3] + "ini"
						self.tw_slaves.insertRow(rc)
						self.tw_slaves.setItem(rc, 0, QTableWidgetItem(slaveName))

						rowColorStyle = "idle"
						slaveStatusItem = None

						if os.path.exists(slaveSettingsPath):

							sconfig = ConfigParser()
							try:
								sconfig.read(slaveSettingsPath)
							except:
								corruptSlaves.append(slaveName)
								continue

							if sconfig.has_option("slaveinfo", "status"):
								slaveStatus = sconfig.get('slaveinfo', "status")
								rowColorStyle = slaveStatus
								slaveStatusItem = QTableWidgetItem(slaveStatus)
								self.tw_slaves.setItem(rc, 1, slaveStatusItem)

							if sconfig.has_option("slaveinfo", "curjob"):
								curJob = sconfig.get('slaveinfo', "curjob")
								slaveJob = QTableWidgetItem(curJob)
								self.tw_slaves.setItem(rc, 2, slaveJob)

							if sconfig.has_option("slaveinfo", "cpucount"):
								cpuCount = sconfig.get('slaveinfo', "cpucount")
								slaveCPU = QTableWidgetItem(cpuCount)
								self.tw_slaves.setItem(rc, 6, slaveCPU)

							if sconfig.has_option("slaveinfo", "ram"):
								ram = sconfig.get('slaveinfo', "ram")
								slaveRam = QTableWidgetItem(ram + " Gb")
								self.tw_slaves.setItem(rc, 5, slaveRam)

							if sconfig.has_option("slaveinfo", "slaveScriptVersion"):
								scriptVersion = sconfig.get('slaveinfo', "slaveScriptVersion")
								slaveVersion = QTableWidgetItem(scriptVersion)
								self.tw_slaves.setItem(rc, 8, slaveVersion)

						if os.path.exists(slaveWarningsPath):
							wconfig = ConfigParser()
							try:
								wconfig.read(slaveWarningsPath)
							except:
								pass
							else:
								if wconfig.has_section("warnings"):
									numWarns = len(wconfig.options("warnings"))
									warns = QTableWidgetItem(str(numWarns))
									self.tw_slaves.setItem(rc, 4, warns)

						last_timeMin = 9999
						if slaveName in activeSlaves:
							slaveLastTime = activeSlaves[slaveName]
							last_timeMin = int((time.time() - slaveLastTime) / 60)

							last_timeH = last_timeMin/60
							last_timeM = last_timeMin - last_timeH*60
							last_timeD = last_timeH/24
							last_timeH = last_timeH - last_timeD*24
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
							if slaveStatusItem is not None and slaveStatusItem.text() in ["idle", "rendering", "paused"]:
								slaveStatusItem.setText("not responding")

						if rowColorStyle != "idle":
							cc = self.tw_slaves.columnCount()
							for k in range(cc):
								item = self.tw_slaves.item(rc, k)
								if item is None:
									item = QTableWidgetItem("")
									self.tw_slaves.setItem(rc, k, item)
								if rowColorStyle == "rendering":
									item.setForeground(QBrush(QColor(80,210,80)))
								elif rowColorStyle == "offline":
									item.setForeground(QBrush(QColor(90,90,90)))

						slavePathItem = QTableWidgetItem(slaveLogPath)
						self.tw_slaves.setItem(rc, 7, slavePathItem)
				except Exception as e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					erStr = ("%s ERROR - Renderhandler %s:\n%s" % (time.strftime("%d.%m.%y %X"), self.core.version, traceback.format_exc()))
					self.core.writeErrorLog(erStr)

			if len(corruptSlaves) > 0:
				mString = "The slavesettings file is corrupt:\n\n"
				for i in corruptSlaves:
					mString += i + "\n"

			#	QMessageBox.information(self,"File corrupt", mString)


		self.tw_slaves.resizeColumnsToContents()
		self.tw_slaves.horizontalHeader().setStretchLastSection(True)
		self.tw_slaves.setColumnWidth(1,100)
		self.tw_slaves.setColumnWidth(0,130)
		self.tw_slaves.setColumnWidth(3,80)
		self.tw_slaves.setColumnWidth(4,60)
		self.tw_slaves.setColumnWidth(5,40)
		self.tw_slaves.setColumnWidth(8, 60)
		self.tw_slaves.setColumnWidth(2, 350)
		self.tw_slaves.setSortingEnabled(True)
		self.tw_slaves.sortByColumn(0, Qt.AscendingOrder)
		

	@err_decorator
	def updateTaskList(self):
		self.tw_taskList.setRowCount(0)
		self.tw_taskList.setSortingEnabled(False)

		if self.tw_jobs.currentRow() == -1:
			return False

		jobName = self.tw_jobs.item(self.tw_jobs.currentRow(),0).text()
		jobIni = os.path.join(self.logDir, "Jobs", "%s.ini" % jobName)

		jconfig = ConfigParser()
		jconfig.read(jobIni)

		if jconfig.has_section("jobtasks"):
			for idx, i in enumerate(jconfig.options("jobtasks")):
				taskData = eval(jconfig.get("jobtasks", i))

				if not (type(taskData) == list and (len(taskData) == 5 or len(taskData) == 7)):
					continue

				rc = self.tw_taskList.rowCount()
				self.tw_taskList.insertRow(rc)
				taskNum = QTableWidgetItem(format(idx, '02'))
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
							taskStart = QTableWidgetItem(time.strftime("%d.%m.%y %X", time.localtime(float(taskData[5]))))

						if taskData[6] == "":
							taskEnd = QTableWidgetItem(taskData[6])
						else:
							taskEnd = QTableWidgetItem(time.strftime("%d.%m.%y %X", time.localtime(float(taskData[6]))))
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
							item.setForeground(QBrush(QColor(80,210,80)))
						elif rowColorStyle == "finished":
							item.setForeground(QBrush(QColor(80,180,220)))
						elif rowColorStyle == "disabled":
							item.setForeground(QBrush(QColor(90,90,90)))
						elif rowColorStyle == "error":
							item.setForeground(QBrush(QColor(240,50,50)))

		self.tw_taskList.resizeColumnsToContents()
		self.tw_taskList.setColumnWidth(6, 50)
		self.tw_taskList.setSortingEnabled(True)
		if self.tw_taskList.horizontalHeader().sortIndicatorSection() == self.tw_taskList.columnCount():
			self.tw_taskList.sortByColumn(0, Qt.AscendingOrder)


	@err_decorator
	def updateJobSettings(self):
		sliderPos = self.tw_jobSettings.verticalScrollBar().value()
		self.tw_jobSettings.setRowCount(0)
		jobSettings = []
		jobInfo = []
		if self.tw_jobs.currentRow() != -1:
			settingsPath = self.tw_jobs.item(self.tw_jobs.currentRow(),9).text()

			if os.path.exists(settingsPath):
				jsconfig = ConfigParser()
				jsconfig.read(settingsPath)

				if jsconfig.has_section("jobglobals"):
					for i in jsconfig.options("jobglobals"):
						if i == "uploadoutput" and self.localmode:
							continue

						settingVal = jsconfig.get('jobglobals', i)
						jobSettings.append([i, settingVal])

				if jsconfig.has_section("information"):
					for i in jsconfig.options("information"):
						settingVal = jsconfig.get('information', i)
						jobInfo.append([i, settingVal])

		self.writeSettings = False

		jobSettings = sorted(jobSettings)
		res =[x for x in jobSettings if x[0] in ["height", "width"]]
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
			if i[0] in ["uploadoutput"]:
				settingVal = QTableWidgetItem()
				if i[1] == "True":
					settingVal.setCheckState(Qt.Checked)
				else:
					settingVal.setCheckState(Qt.Unchecked)
			elif i[0] in ["priority", "width", "height", "tasktimeout"]:
				settingVal = QTableWidgetItem()
				spinner = QSpinBox()
				if i[0] in ["width", "height", "tasktimeout"]:
					spinner.setMaximum(9999)
					spinner.setMinimum(1)
				try:
					val = eval(i[1])
				except:
					val = 0
				spinner.setValue(val)
				spinner.editingFinished.connect(lambda x=settingVal, sp=spinner: self.setSetting(stype="js", item=x, widget=sp))
				self.tw_jobSettings.setCellWidget(rc, 1, spinner)
			elif i[0] in ["listslaves"]:
				settingVal = QTableWidgetItem()
				label = QLabel(i[1])
				label.mouseDprEvent = label.mouseDoubleClickEvent
				label.mouseDoubleClickEvent = lambda x, l=label, it=settingVal: self.mouseClickEvent(x,"listslaves", l, it)
				self.tw_jobSettings.setCellWidget(rc, 1, label)
			else:
				settingVal = QTableWidgetItem(i[1])
			self.tw_jobSettings.setItem(rc, 1, settingVal)

		if len(jobInfo) > 0:
			jobInfo = [["", ""], ["Information:", ""]] + jobInfo

		for i in sorted(jobInfo):
			rc = self.tw_jobSettings.rowCount()
			self.tw_jobSettings.insertRow(rc)
			settingName = QTableWidgetItem(i[0])
			settingName.setFlags(settingName.flags() ^ Qt.ItemIsEditable)
			self.tw_jobSettings.setItem(rc, 0, settingName)
			settingVal = QTableWidgetItem(i[1])
			settingVal.setFlags(settingVal.flags() ^ Qt.ItemIsEditable)
			self.tw_jobSettings.setItem(rc, 1, settingVal)
		
		self.tw_jobSettings.setColumnWidth(0,150)
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

			settingsPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveSettings_")[:-3] + "ini"
			if os.path.exists(settingsPath):
				ssconfig = ConfigParser()
				try:
					ssconfig.read(settingsPath)
				except:
					QMessageBox.warning(self, "Warning", "Corrupt setting file")
					return

				if ssconfig.has_section("settings"):
					for i in ssconfig.options("settings"):
						if i == "connectiontimeout" and self.localmode:
							continue

						settingVal = ssconfig.get('settings', i)
						slaveSettings.append([i, settingVal])

		self.writeSettings = False

		for i in sorted(slaveSettings):
			rc = self.tw_slaveSettings.rowCount()
			self.tw_slaveSettings.insertRow(rc)
			settingName = QTableWidgetItem(i[0])
			settingName.setFlags(settingName.flags() ^ Qt.ItemIsEditable)
			self.tw_slaveSettings.setItem(rc, 0, settingName)
			if i[0] in ["cursorcheck", "enabled", "debugmode", "showslavewindow", "showinterruptwindow"]:
				settingVal = QTableWidgetItem()
				if i[1] == "True":
					settingVal.setCheckState(Qt.Checked)
				else:
					settingVal.setCheckState(Qt.Unchecked)
			elif i[0] in ["updatetime", "maxcpu", "connectiontimeout", "prerenderwaittime"]:
				settingVal = QTableWidgetItem()
				spinner = QSpinBox()
				try:
					val = eval(i[1])
				except:
					val = 0
				spinner.setValue(val)
				spinner.editingFinished.connect(lambda x=settingVal, sp=spinner: self.setSetting(stype="ss", item=x, widget=sp))
				self.tw_slaveSettings.setCellWidget(rc, 1, spinner)
			elif i[0] in ["slavegroup"]:
				settingVal = QTableWidgetItem()
				label = QLabel(i[1])
				label.mouseDprEvent = label.mouseDoubleClickEvent
				label.mouseDoubleClickEvent = lambda x, l=label, it=settingVal: self.mouseClickEvent(x,"slavegroup", l, it)
				self.tw_slaveSettings.setCellWidget(rc, 1, label)
			elif i[0] in ["restperiod"]:
				settingVal = QTableWidgetItem()
				ckbActive = QCheckBox()
				spinnerStart = QSpinBox()
				spinnerEnd = QSpinBox()
				mainW = QWidget()
				layout = QHBoxLayout()
				layout.setContentsMargins(0,0,0,0)
				layout.addWidget(ckbActive)
				layout.addWidget(spinnerStart)
				layout.addWidget(spinnerEnd)
				mainW.setLayout(layout)
				try:
					val = eval(i[1])
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
				ckbActive.toggled.connect(lambda y, x=settingVal, sp=[ckbActive, spinnerStart, spinnerEnd]: self.setSetting(stype="ss", item=x, widget=sp))
				spinnerStart.editingFinished.connect(lambda x=settingVal, sp=[ckbActive, spinnerStart, spinnerEnd]: self.setSetting(stype="ss", item=x, widget=sp))
				spinnerEnd.editingFinished.connect(lambda x=settingVal, sp=[ckbActive, spinnerStart, spinnerEnd]: self.setSetting(stype="ss", item=x, widget=sp))
				self.tw_slaveSettings.setCellWidget(rc, 1, mainW)
			elif i[0] in ["command", "corecommand"]:
				settingVal = QTableWidgetItem()
				e_command = QLineEdit()
				e_command.setContextMenuPolicy(Qt.CustomContextMenu)
				e_command.customContextMenuRequested.connect(lambda x, eText=e_command: self.rclList("scmd", x, twItem=eText))
				e_command.editingFinished.connect(lambda x=settingVal, ed=e_command: self.setSetting(stype="ss", item=x, widget=ed))
				self.tw_slaveSettings.setCellWidget(rc, 1, e_command)
			else:
				settingVal = QTableWidgetItem(i[1])
			self.tw_slaveSettings.setItem(rc, 1, settingVal)
		
		self.tw_slaveSettings.setColumnWidth(0,150)
		self.writeSettings = True

		self.tw_slaveSettings.verticalScrollBar().setValue(sliderPos)


	@err_decorator
	def updateCoordSettings(self):
		self.tw_coordSettings.setRowCount(0)
		coordSettings = []
		settingsPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Settings.ini")
		if os.path.exists(settingsPath):
			ssconfig = ConfigParser()
			ssconfig.read(settingsPath)
			if ssconfig.has_section("settings"):
				for i in ssconfig.options("settings"):
					if i in ["restartgdrive", "notifyslaveinterval"] and self.localmode:
						continue

					if i in ["repository"]:
						continue

					settingVal = ssconfig.get('settings', i)
					coordSettings.append([i, settingVal])

		self.writeSettings = False
		for i in sorted(coordSettings):
			rc = self.tw_coordSettings.rowCount()
			self.tw_coordSettings.insertRow(rc)
			settingName = QTableWidgetItem(i[0])
			settingName.setFlags(settingName.flags() ^ Qt.ItemIsEditable);
			self.tw_coordSettings.setItem(rc, 0, settingName)
			if i[0] in ["coordupdatetime", "notifyslaveinterval"]:
				settingVal = QTableWidgetItem()
				spinner = QSpinBox()
				try:
					val = eval(i[1])
				except:
					val = 0
				spinner.setValue(val)
				spinner.editingFinished.connect(lambda x=settingVal, sp=spinner: self.setSetting(stype="cs", item=x, widget=sp))
				self.tw_coordSettings.setCellWidget(rc, 1, spinner)
			elif i[0] in ["debugmode", "restartgdrive"]:
				settingVal = QTableWidgetItem()
				if i[1] == "True":
					settingVal.setCheckState(Qt.Checked)
				else:
					settingVal.setCheckState(Qt.Unchecked)
			elif i[0] in ["command"]:
				settingVal = QTableWidgetItem()
				e_command = QLineEdit()
				e_command.setContextMenuPolicy(Qt.CustomContextMenu)
				e_command.customContextMenuRequested.connect(lambda x, eText=e_command: self.rclList("ccmd", x, twItem=eText))
				e_command.editingFinished.connect(lambda x=settingVal, ed=e_command: self.setSetting(stype="cs", item=x, widget=ed))
				self.tw_coordSettings.setCellWidget(rc, 1, e_command)
			else:
				settingVal = QTableWidgetItem(i[1])
			self.tw_coordSettings.setItem(rc, 1, settingVal)
		
		self.tw_coordSettings.resizeColumnsToContents()
		self.tw_coordSettings.setColumnWidth(0,150)
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

			warningsPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveWarnings_")[:-3] + "ini"
			if os.path.exists(warningsPath):
				swconfig = ConfigParser()
				try:
					swconfig.read(warningsPath)
				except:
				#	QMessageBox.warning(self, "Warning", "Corrupt warning file")
					return

				if swconfig.has_section("warnings"):
					for i in swconfig.options("warnings"):
						try:
							warnVal = swconfig.get('warnings', i)
							slaveWarns.append(eval(warnVal))
						except:
							continue

		for idx, i in enumerate(slaveWarns):
			rc = self.tw_slaveWarnings.rowCount()
			self.tw_slaveWarnings.insertRow(rc)

			if i[2] == 1:
				fbrush = QBrush(QColor(80,180,220))
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
		
		self.tw_slaveWarnings.setColumnWidth(0,150)

		self.tw_slaveWarnings.verticalScrollBar().setValue(sliderPos)


	@err_decorator
	def updateCoordWarnings(self):
		sliderPos = self.tw_coordWarnings.verticalScrollBar().value()
		self.tw_coordWarnings.setRowCount(0)
		coordWarns = []

		warningsPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Warnings.ini")
		if os.path.exists(warningsPath):
			wconfig = ConfigParser()
			try:
				wconfig.read(warningsPath)
			except:
			#	QMessageBox.warning(self, "Warning", "Corrupt warning file")
				return

			if wconfig.has_section("warnings"):
				for i in wconfig.options("warnings"):
					warnVal = wconfig.get('warnings', i)
					coordWarns.append(eval(warnVal))

		for i in coordWarns:
			rc = self.tw_coordWarnings.rowCount()
			self.tw_coordWarnings.insertRow(rc)

			if i[2] == 1:
				fbrush = QBrush(QColor(80,180,220))
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
		
		self.tw_coordWarnings.setColumnWidth(0,150)

		self.tw_coordWarnings.verticalScrollBar().setValue(sliderPos)


	@err_decorator
	def setSetting(self, stype, item, widget=None):
		if not self.writeSettings:
			return

		settingVal = None
		settingName = item.tableWidget().item(item.row(), 0).text()

		if stype == "js" and self.tw_jobs.currentRow() != -1:
			settingType = "Job"
			section = "jobglobals"
			settingsPath = self.tw_jobs.item(self.tw_jobs.currentRow(), 9).text()

			jconfig = ConfigParser()
			jconfig.read(settingsPath)

			if jconfig.has_option("information", "jobcode"):
				parentName = jconfig.get("information", "jobcode")
			else:
				parentName = self.tw_jobs.item(self.tw_jobs.currentRow(), 0).text()

			if settingName in ["uploadoutput"]:
				settingVal = item.checkState() == Qt.Checked
			elif settingName in ["priority", "width", "height", "tasktimeout"]:
				settingVal = widget.value()
			elif settingName in ["listslaves"]:
				settingVal = widget.text()
		elif stype == "ss" and self.tw_slaves.currentRow() != -1:
			settingType = "Slave"
			section = "settings"
			parentName = self.tw_slaves.item(self.tw_slaves.currentRow(), 0).text()
			settingsPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveSettings_")[:-3] + "ini"
			if settingName in ["cursorcheck", "enabled", "debugmode", "showslavewindow", "showinterruptwindow"]:
				settingVal = item.checkState() == Qt.Checked
			elif settingName in ["updatetime", "maxcpu", "connectiontimeout", "prerenderwaittime"]:
				settingVal = widget.value()
			elif settingName in ["slavegroup", "command", "corecommand"]:
				settingVal = widget.text()
			elif settingName in ["restperiod"]:
				settingVal = [widget[0].checkState() == Qt.Checked, widget[1].value(), widget[2].value()]
		elif stype == "cs":
			settingType = "Coordinator"
			section = "settings"
			parentName = ""
			settingsPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Settings.ini")
			if settingName in ["coordupdatetime"]:
				settingVal = widget.value()
			elif settingName in ["debugmode", "restartgdrive"]:
				settingVal = item.checkState() == Qt.Checked
			elif settingName in ["command"]:
				settingVal = widget.text()

		if settingVal is None:
			settingVal = item.text()

		cmd = ["setSetting", settingType, parentName, settingName, settingVal]

		if not self.isSettingDifferent(cmd, settingsPath, section):
			return

		self.writeCmd(cmd)

		if settingsPath is not None and os.path.exists(settingsPath):
			sconfig = ConfigParser()
			sconfig.read(settingsPath)

			if sconfig.has_option(section, settingName):
				sconfig.set(section, settingName, settingVal)

				with open(settingsPath, 'w') as inifile:
					sconfig.write(inifile)

				if section == "jobglobals" and settingName == "priority":
					self.updateJobData(self.tw_jobs.currentRow())


	@err_decorator
	def isSettingDifferent(self, cmd, sPath, section):
		sConfig = ConfigParser()
		sConfig.read(sPath)

		if not sConfig.has_option(section, cmd[3]):
			return True

		return sConfig.get(section, cmd[3]) != str(cmd[4])


	@err_decorator
	def writeCmd(self, cmd):
		cmdDir = os.path.join(self.sourceDir, "Commands")

		if not os.path.exists(cmdDir):
			try:
				os.makedirs(cmdDir)
			except:
				QMessageBox.warning(self, "Warning", "Could not create command folder: " % cmdDir)
				return

		curNum = 1

		for i in os.listdir(cmdDir):
			if not i.startswith("handlerOut_"):
				continue
		
			num = i.split("_")[1]
			if not unicode(num).isnumeric():
				continue

			if int(num) >= curNum:
				curNum = int(num) + 1


		cmdFile = os.path.join(cmdDir, "handlerOut_%s_%s.txt" % (format(curNum, '04'),time.time()))

		with open(cmdFile, 'w') as cFile:
			cFile.write(str(cmd))


	@err_decorator
	def mouseClickEvent(self, event, stype, widget, item):
		if event.button() == Qt.LeftButton:
			if stype == "listslaves":
				if self.refreshTimer.isActive():
					self.refreshTimer.stop()

				import PandoraSlaveAssignment
				self.sa = PandoraSlaveAssignment.PandoraSlaveAssignment(core=self.core, curSlaves = widget.text())
				self.sa.setFocus()
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
			elif stype == "slavegroup":
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

					slaveSettingsPath = pItem.text().replace("slaveLog_", "slaveSettings_")[:-3] + "ini"

					if os.path.exists(slaveSettingsPath):
						sconfig = ConfigParser()
						sconfig.read(slaveSettingsPath)

						if sconfig.has_option("settings", "slavegroup"):
							try:
								sGroups = eval(sconfig.get('settings', "slavegroup"))
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
				lw_slaves.itemSelectionChanged.connect(lambda: e_output.setText(",".join([ str(x.text()) for x in lw_slaves.selectedItems()])))
				bb_close.accepted.connect(sList.accept)
				bb_close.rejected.connect(sList.reject)

				lw_slaves.setFocusPolicy(Qt.NoFocus)
				sList.setFocus()
				self.core.parentWindow(sList)

				result = sList.exec_()

				if result == QDialog.Accepted:
					widget.setText(str([str(x) for x in e_output.text().replace(" ", "").split(",") if x != ""]))
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
					with io.open(logPath, 'r', encoding='utf-16') as logFile:
						try:
							logLines = logFile.readlines()
						except:
							logLines = []

					if self.sp_logLimit.value() == 0 or self.sp_logLimit.value() > len(logLines):
						limit = len(logLines)
					else:
						limit = self.sp_logLimit.value()

					if lvl == 0:
						for i in logLines[-limit:]:
							logData += self.colorLogLine(i)
					else:
						for i in logLines[-limit:]:
							if len(i) < 3 or (i[0] == "[" and i[2] == "]" and int(i[1]) >= lvl) or (i[0] != "[" and i[2] != "]"):
								logData += self.colorLogLine(i)
				
					self.l_slaveLogSize.setText("Logsize: %.2fmb" % float(os.stat(logPath).st_size/1024.0/1024.0))
				except:
					QMessageBox.warning(self, "Warning", "Corrupt logfile")

		self.te_slaveLog.setText(logData)
		self.te_slaveLog.moveCursor(QTextCursor.End)


	@err_decorator
	def updateCoordLog(self, filterLvl=0):
		sliderPos = self.te_coordLog.verticalScrollBar().value()

		logData = ""
		self.l_slaveLogSize.setText("")
		logPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Log.txt")

		if os.path.exists(logPath):
			with io.open(logPath, 'r', encoding='utf-16') as logFile:
				lvl = self.sp_coordFilter.value()
				try:
					logLines = logFile.readlines()
				except:
					logLines = []

			if self.sp_logLimit.value() == 0 or self.sp_logLimit.value() > len(logLines):
				limit = len(logLines)
			else:
				limit = self.sp_logLimit.value()

			if lvl == 0:
				for i in logLines[-limit:]:
					logData += self.colorLogLine(i)
			else:
				for i in logLines[-limit:]:
					if len(i) < 3 or (i[0] == "[" and i[2] == "]" and int(i[1]) >= lvl) or (i[0] != "[" and i[2] != "]"):
						logData += self.colorLogLine(i)

			self.l_coordLogSize.setText("Logsize: %.2fmb" % float(os.stat(logPath).st_size/1024.0/1024.0))

		self.te_coordLog.setText(logData)
		self.te_coordLog.moveCursor(QTextCursor.End)

		self.te_coordLog.verticalScrollBar().setValue(sliderPos)


	@err_decorator
	def colorLogLine(self, textLine, level=0):
		if len(textLine) > 2 and textLine[0] == "[" and textLine[2] == "]" and int(textLine[1]) in range(1,4):
			level = int(textLine[1])

		if level == 1:
			lineStr = "<div style=\"color:#a0caea;\">%s</div>" % textLine
		elif level == 2:
			lineStr = "<div style=\"color:yellow;\">%s</div>" % textLine
		elif level == 3:
			lineStr = "<div style=\"color:red;\">%s</div>" % textLine
		else:
			lineStr = "<div style=\"color:white;\">%s</div>" % textLine

		return lineStr


	@err_decorator
	def checkCoordConnected(self):
		cPath = os.path.join(self.logDir, "PandoraCoordinator", "ActiveSlaves.txt")

		if os.path.exists(cPath):
			file_mod_time = os.stat(cPath).st_mtime
			last_timeMin = int((time.time() - file_mod_time) / 60)
		else:
			last_timeMin = 999

		if last_timeMin > 5:
			self.statusLabel.setText("NOT CONNECTED")
		else:
			self.statusLabel.setText("")


	@err_decorator
	def rclList(self, listType, pos, twItem=None):
		rcmenu = QMenu()

		if listType == "cl":
			coordLog = lambda: self.openFile(os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Log.txt"))
			logAct = QAction("Open Log", self)
			logAct.triggered.connect(coordLog)
			rcmenu.addAction(logAct)
			clearLogAct = QAction("Clear Log", self)
			clearLogAct.triggered.connect(lambda: self.clearLog(coord=True))
			rcmenu.addAction(clearLogAct)
			coordFolder = lambda: self.openFile(os.path.join(self.logDir, "PandoraCoordinator"))
			folderAct = QAction("Open Folder", self)
			folderAct.triggered.connect(coordFolder)
			rcmenu.addAction(folderAct)
		elif listType == "cs":
			coordSettings = lambda: self.openFile(os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Settings.ini"))
			fileAct = QAction("Open Settings", self)
			fileAct.triggered.connect(coordSettings)
			rcmenu.addAction(fileAct)
			coordFolder = lambda: self.openFile(os.path.join(self.logDir, "PandoraCoordinator"))
			folderAct = QAction("Open Folder", self)
			folderAct.triggered.connect(coordFolder)
			rcmenu.addAction(folderAct)
		elif listType == "ccmd":
			if not self.localmode:
				ucAct = QAction("Search uncollected renderings", self)
				ucAct.triggered.connect(lambda: twItem.setText("self.searchUncollectedRnd()"))
				rcmenu.addAction(ucAct)
		elif listType == "cw":
			dwAct = QAction("Delete", self)
			curItem = self.tw_coordWarnings.itemFromIndex(self.tw_coordWarnings.indexAt(pos))
			if curItem is not None:
				curRow = curItem.row()
				dwAct.triggered.connect(lambda: self.deleteWarning(curRow, "Coordinator"))
				rcmenu.addAction(dwAct)

			cwAct = QAction("Clear all", self)
			cwAct.triggered.connect(lambda: self.clearWarnings("Coordinator"))
			rcmenu.addAction(cwAct)

		if self.tw_jobs.rowCount() > 0 and self.tw_jobs.currentRow() != -1:

			jobSettings = self.tw_jobs.item(self.tw_jobs.currentRow(),9).text()
			if os.path.exists(jobSettings):
				jobSettings = lambda: self.openFile(self.tw_jobs.item(self.tw_jobs.currentRow(),9).text())
			else:
				jobSettings = lambda: self.openFile("")
			jobFolder = lambda: self.openFile(os.path.dirname(self.tw_jobs.item(self.tw_jobs.currentRow(),9).text()))

			if listType == "j":
				if not self.localmode:
					colAct = QAction("Collect Output", self)	
					colAct.triggered.connect(self.collectOutput)
					rcmenu.addAction(colAct)

					rcmenu.addSeparator()

				enable = False
				disable = False
				restart = False
				tasks = range(self.tw_taskList.rowCount())
				for i in range(self.tw_taskList.rowCount()):
					if self.tw_taskList.item(i, 2).text() == "disabled":
						enable = True
					else:
						disable = True
					if self.tw_taskList.item(i, 3).text() != "unassigned":
						restart = True

				restartAct = QAction("Restart", self)
				restartAct.triggered.connect(lambda: self.restartTask(self.tw_jobs.currentRow(), tasks))
				restartAct.setEnabled(restart)
				rcmenu.addAction(restartAct)

				enableAct = QAction("Enable", self)
				enableAct.triggered.connect(lambda: self.disableTask(self.tw_jobs.currentRow(), tasks, enable=True))
				enableAct.setEnabled(enable)
				rcmenu.addAction(enableAct)

				disableAct = QAction("Disable", self)
				disableAct.triggered.connect(lambda: self.disableTask(self.tw_jobs.currentRow(), tasks))
				disableAct.setEnabled(disable)
				rcmenu.addAction(disableAct)

				deleteAct = QAction("Delete Job", self)
				deleteAct.triggered.connect(self.deleteJob)
				rcmenu.addAction(deleteAct)

				rcmenu.addSeparator()

				fileAct = QAction("Open Settings", self)
				fileAct.triggered.connect(jobSettings)
				rcmenu.addAction(fileAct)

				outAct = QAction("Open Output", self)

				jconfig = ConfigParser()
				jconfig.read(self.tw_jobs.item(self.tw_jobs.currentRow(),9).text())

				outpath = os.path.dirname(jconfig.get('information', "outputpath"))

				if os.path.basename(outpath) == "beauty":
					outpath = os.path.dirname(outpath)

				projectName = jconfig.get('information', "projectname")

				if not self.localmode:
					outpath = os.path.join(os.path.dirname(os.path.dirname(self.sourceDir)), outpath[outpath.find("\\%s\\" % projectName)+1:])

				if os.path.exists(outpath):
					for i in os.walk(outpath):
						dirs = i[1]
						if len(dirs) == 1:
							outpath = os.path.join(outpath, dirs[0])
						else:
							break
						
					outAct.triggered.connect(lambda: self.openFile(outpath))
				else:
					outAct.setEnabled(False)
				rcmenu.addAction(outAct)

				rvAct = QAction("Play beauty in RV", self)

				beautyPath = outpath
				if os.path.exists(os.path.join(outpath, "beauty")):
					beautyPath = os.path.join(outpath, "beauty")

				rvAct.triggered.connect(lambda: self.playRV(beautyPath))
				if not os.path.exists(beautyPath) or len(os.listdir(beautyPath)) == 0:
					rvAct.setEnabled(False)

				rcmenu.addAction(rvAct)

			elif listType == "tl":
				tasks = {}
				for i in self.tw_taskList.selectedItems():
					tNum = int(self.tw_taskList.item(i.row(),0).text())
					if tNum not in tasks:
						tasks[tNum] = i.row()

				restartAct = QAction("Restart", self)
				restartAct.triggered.connect(lambda: self.restartTask(self.tw_jobs.currentRow(), tasks.keys()))
				restartAct.setEnabled(False)
				for i in tasks:
					if self.tw_taskList.item(tasks[i], 3).text() != "unassigned":
						restartAct.setEnabled(True)
				rcmenu.addAction(restartAct)

				enableAct = QAction("Enable", self)
				enableAct.triggered.connect(lambda: self.disableTask(self.tw_jobs.currentRow(), tasks.keys(), enable=True))
				enableAct.setEnabled(False)
				for i in tasks:
					if self.tw_taskList.item(tasks[i], 2).text() == "disabled":
						enableAct.setEnabled(True)
				rcmenu.addAction(enableAct)

				disableAct = QAction("Disable", self)
				disableAct.triggered.connect(lambda: self.disableTask(self.tw_jobs.currentRow(), tasks.keys()))
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
				
			slaveLog = pItem.text()
			if os.path.exists(slaveLog):
				slaveLog = lambda: self.openFile(self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text())
			else:
				slaveLog = lambda: self.openFile("")
			slaveSettings = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveSettings_")[:-3] + "ini"
			if os.path.exists(slaveSettings):
				slaveSettings = lambda: self.openFile(self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveSettings_")[:-3] + "ini")
			else:
				slaveSettings = lambda: self.openFile("")
			slaveFolder = lambda: self.openFile(os.path.dirname(self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text()))

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
				rsAct.triggered.connect(lambda: twItem.setText("self.shutdownPC(restart=True)"))
				rcmenu.addAction(rsAct)
				sdAct = QAction("Shutdown PC", self)
				sdAct.triggered.connect(lambda: twItem.setText("self.shutdownPC()"))
				rcmenu.addAction(sdAct)
				srAct = QAction("Stop Render", self)
				srAct.triggered.connect(lambda: twItem.setText("self.stopRender()"))
				rcmenu.addAction(srAct)
				if not self.localmode:
					ucAct = QAction("Upload current job output", self)
					ucAct.triggered.connect(lambda: twItem.setText("self.uploadCurJob()"))
					rcmenu.addAction(ucAct)

			elif listType == "sw":
				dwAct = QAction("Delete", self)
				curItem = self.tw_slaveWarnings.itemFromIndex(self.tw_slaveWarnings.indexAt(pos))
				if curItem is not None:

					curRow = curItem.row()
					dwAct.triggered.connect(lambda: self.deleteWarning(curRow, "Slave"))
					rcmenu.addAction(dwAct)

				cwAct = QAction("Clear all", self)
				cwAct.triggered.connect(lambda: self.clearWarnings("Slave"))
				rcmenu.addAction(cwAct)

		if rcmenu.isEmpty():
			return False

		self.setRCStyle(rcmenu)

		rcmenu.exec_(QCursor.pos())


	@err_decorator
	def deleteWarning(self, row, warnType):
		if warnType == "Slave":
			if self.tw_slaves.currentRow() == -1:
				return

			pItem = self.tw_slaves.item(self.tw_slaves.currentRow(), 7)
			if pItem is None:
				return

			warningsPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveWarnings_")[:-3] + "ini"
			if not os.path.exists(warningsPath):
				return

		elif warnType == "Coordinator":
			warningsPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Warnings.ini")
			if not os.path.exists(warningsPath):
				return

		wconfig = ConfigParser()
		try:
			wconfig.read(warningsPath)
		except:
			QMessageBox.warning(self, "Warning", "Corrupt warning file")
			return

		warnNum = "warning" + str(row)
		if wconfig.has_option("warnings", warnNum):
			warnVal = eval(wconfig.get('warnings', warnNum))


		message = "Do you really want to delete this warning:\n\n"
		if warnType == "Slave":
			curSlave = self.tw_slaves.item(self.tw_slaves.currentRow(), 0).text()
			message = message[:-3] + " on slave %s:\n\n" % curSlave
		else:
			curSlave = ""

		message += "%s\n\n%s\n" % (time.strftime("%d.%m.%y %X", time.localtime(warnVal[1])), warnVal[0])
		delMsg = QMessageBox(QMessageBox.Question, "Delete warning", message, QMessageBox.No)
		delMsg.addButton("Yes", QMessageBox.YesRole)
		delMsg.setFocus()
		self.core.parentWindow(delMsg)
		result = delMsg.exec_()

		if result == 0:
			self.writeCmd(["deleteWarning", warnType, curSlave, warnVal[0], warnVal[1]])

			warningConfig = ConfigParser()
			warningConfig.read(warningsPath)

			warnings = []
			if warningConfig.has_section("warnings"):
				for i in warningConfig.options("warnings"):
					warnings.append(eval(warningConfig.get("warnings", i)))

				warnings = [x for x in warnings if not (x[0] == warnVal[0] and x[1] == warnVal[1])]

			warningConfig = ConfigParser()
			warningConfig.add_section("warnings")
			for idx, val in enumerate(warnings):
				warningConfig.set("warnings", "warning%s" % idx, val)

			with open(warningsPath, 'w') as inifile:
				warningConfig.write(inifile)

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

			warningsPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveWarnings_")[:-3] + "ini"
			if not os.path.exists(warningsPath):
				return

		elif warnType == "Coordinator":
			warningsPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Warnings.ini")
			if not os.path.exists(warningsPath):
				return

		message = "Do you really want to delete all warnings of "
		if warnType == "Slave":
			curSlave = self.tw_slaves.item(self.tw_slaves.currentRow(), 0).text()
			message += "slave \"%s\"?" % curSlave
		else:
			message += "the coordinator?"
			curSlave = ""

		delMsg = QMessageBox(QMessageBox.Question, "Clear warnings", message, QMessageBox.No)
		delMsg.addButton("Yes", QMessageBox.YesRole)
		delMsg.setFocus()
		self.core.parentWindow(delMsg)
		result = delMsg.exec_()

		if result == 0:
			self.writeCmd(["clearWarnings", warnType, curSlave])

			with open(warningsPath, 'w') as inifile:
				inifile.write("[warnings]")

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

			warningsPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text().replace("slaveLog_", "slaveWarnings_")[:-3] + "ini"
			if not os.path.exists(warningsPath):
				return

		elif warnType == "Coordinator":
			warningsPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Warnings.ini")
			if not os.path.exists(warningsPath):
				return

		wconfig = ConfigParser()
		try:
			wconfig.read(warningsPath)
		except:
			QMessageBox.warning(self, "Warning", "Corrupt warning file")
			return

		warnNum = "warning" + str(item.row())
		if wconfig.has_option("warnings", warnNum):
			warnVal = eval(wconfig.get('warnings', warnNum))

		message = "%s\n\n%s\n" % (time.strftime("%d.%m.%y %X", time.localtime(warnVal[1])), warnVal[0])
		QMessageBox.information(self, "Warning", message)


	@err_decorator
	def teamviewerRequested(self):
		ssDir = os.path.join(self.sourceDir, "Screenshots")
		if not os.path.exists(ssDir):
			os.makedirs(ssDir)

		self.openFile(ssDir)


	@err_decorator
	def clearLog(self, coord=False):
		if coord:
			logType = "Coordinator"
			logName = ""
			logPath = os.path.join(self.logDir, "PandoraCoordinator", "PandoraCoordinator_Log.txt")
			refresh = self.updateCoordLog
		else:
			logType = "Slave"

			curSlave = self.tw_slaves.item(self.tw_slaves.currentRow(),0)
			if curSlave is None:
				return

			logPath = self.tw_slaves.item(self.tw_slaves.currentRow(), 7).text()

			logName = curSlave.text()
			refresh = self.updateSlaveLog

		self.writeCmd(["clearLog", logType, logName])

		try:
			open(logPath, 'w').close()
		except:
			pass

		refresh()


	@err_decorator
	def collectOutput(self):
		curJobName = self.tw_jobs.item(self.tw_jobs.currentRow(),0).text()

		jobIni = os.path.join(self.logDir, "Jobs", "%s.ini" % curJobName)

		jconfig = ConfigParser()
		jconfig.read(jobIni)

		if jconfig.has_option("information", "jobcode"):
			jobCode = jconfig.get("information", "jobcode")
		else:
			jobCode = curJobName

		self.writeCmd(["collectJob", jobCode])
		QMessageBox.information(self,"CollectOutput", "Collect request for job %s was sent." % curJobName)


	@err_decorator
	def deleteJob(self):
		curJobName = self.tw_jobs.item(self.tw_jobs.currentRow(),0).text()
		message = "Do you really want to delete job \"<b>%s</b>\"" % curJobName
		delMsg = QMessageBox(QMessageBox.Question, "Delete Job", message, QMessageBox.No)
		delMsg.addButton("Yes", QMessageBox.YesRole)
		delMsg.setFocus()
		self.core.parentWindow(delMsg)
		result = delMsg.exec_()

		if result == 0:
			jobIni = os.path.join(self.logDir, "Jobs", "%s.ini" % curJobName)

			jconfig = ConfigParser()
			jconfig.read(jobIni)

			if jconfig.has_option("information", "jobcode"):
				jobCode = jconfig.get("information", "jobcode")
			else:
				jobCode = curJobName

			self.writeCmd(["deleteJob", jobCode])

			if os.path.exists(jobIni):
				try:
					os.remove(jobIni)
				except:
					pass

			self.updateJobs()


	@err_decorator
	def restartTask(self, job, tasks):
		jobName = self.tw_jobs.item(job,0).text()
		jobIni = os.path.join(self.logDir, "Jobs", "%s.ini" % jobName)

		jconfig = ConfigParser()
		jconfig.read(jobIni)

		if jconfig.has_option("information", "jobcode"):
			jobCode = jconfig.get("information", "jobcode")
		else:
			jobCode = jobName

		for i in tasks:
			self.writeCmd(["restartTask", jobCode, i])

			if jconfig.has_option("jobtasks", "task%s" % i):
				taskData = eval(jconfig.get('jobtasks', "task%s" % i))
				taskData[2] = "ready"
				taskData[3] = "unassigned"
				taskData[4] = ""
				taskData[5] = ""
				taskData[6] = ""
				jconfig.set('jobtasks', "task%s" % i , str(taskData))

		with open(jobIni, 'w') as inifile:
			jconfig.write(inifile)

		self.updateJobData(self.tw_jobs.currentRow())
		self.updateTaskList()


	@err_decorator
	def disableTask(self, job, tasks, enable=False):
		jobName = self.tw_jobs.item(job,0).text()
		jobIni = os.path.join(self.logDir, "Jobs", "%s.ini" % jobName)

		jconfig = ConfigParser()
		jconfig.read(jobIni)

		if jconfig.has_option("information", "jobcode"):
			jobCode = jconfig.get("information", "jobcode")
		else:
			jobCode = jobName

		for i in tasks:
			self.writeCmd(["disableTask", jobCode, i, enable])

			if jconfig.has_option("jobtasks", "task%s" % i):
				taskData = eval(jconfig.get('jobtasks', "task%s" % i))
				if (taskData[2] in ["ready", "rendering", "assigned"] and not enable) or (taskData[2] == "disabled" and enable):
					if enable:
						taskData[2] = "ready"
						taskData[3] = "unassigned"
					else:
						taskData[2] = "disabled"
						taskData[3] = "unassigned"
					jconfig.set('jobtasks', "task%s" % i , str(taskData))

		with open(jobIni, 'w') as inifile:
			jconfig.write(inifile)

		self.updateJobData(self.tw_jobs.currentRow())
		self.updateTaskList()


	@err_decorator
	def openFile(self,path):
		if os.path.isdir(path):
			subprocess.call(['explorer', path])
		else:
			os.startfile(path)


	@err_decorator
	def playRV(self, path):
		sequence = [x for x in os.listdir(path) if x.endswith(".exr")]
		if sequence != [] and self.rv is not None:
			subprocess.Popen([self.rv, os.path.join(path, sequence[0][:-8] + "@@@@" + sequence[0][-4:])])


	@err_decorator
	def getRVpath(self):
		try:
			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\rv.exe",
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			self.rv = (_winreg.QueryValue(key, None))
		except:
			manuPath = "A:\\Downloads\\rv-win64-x86-64-6\\rv-win64-x86-64-6.2.6\\bin\\rv.exe"
			if os.path.exists(manuPath):
				self.rv = manuPath
			else:
				self.rv = None


if __name__ == "__main__":
	qapp = QApplication(sys.argv)
	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
	handlerIcon = QIcon(os.path.dirname(os.path.abspath(__file__)) + "\\UserInterfacesPandora\\rh_tray.ico")
	qapp.setWindowIcon(handlerIcon)
	import PandoraCore
	pc = PandoraCore.PandoraCore()
	pc.openRenderHandler()
	qapp.exec_()