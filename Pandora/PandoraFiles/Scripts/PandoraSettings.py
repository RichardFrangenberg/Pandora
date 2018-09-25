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
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1
except:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2

import sys, os, subprocess, time, traceback, shutil, socket
from functools import wraps

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

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2

from UserInterfacesPandora import qdarkstyle


class PandoraSettings(QDialog, PandoraSettings_ui.Ui_dlg_PandoraSettings):
	def __init__(self, core):
		QDialog.__init__(self)
		self.setupUi(self)
		self.core = core
		self.core.parentWindow(self)

		ss = QApplication.instance().styleSheet()
		for i in [self.gb_submission, self.gb_slave, self.gb_coordinator]:
			i.setStyleSheet(ss.replace("QCheckBox::indicator", "QGroupBox::indicator"))

		self.configPath = os.path.join(os.getenv("localappdata"), "Pandora", "Config", "Pandora.ini")

		if not os.path.exists(self.configPath):
			self.core.createUserPrefs()

		if self.core.app == 2:
			self.setRcStyle = self.houSetRcStyle
		else:
			self.setRcStyle = lambda x: None

		self.loadSettings()
		self.refreshSlaves()
		self.refreshWorkstations()

		self.connectEvents()
		self.setFocus()

		screenH = QApplication.desktop().screenGeometry().height()
		space = 100 
		if screenH < (self.height()+space):
			self.resize(self.width(), screenH-space)


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - PandoraSettings %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def connectEvents(self):
		self.e_username.textChanged.connect(lambda x: self.validate(self.e_username, x))
		self.b_browseRoot.clicked.connect(lambda: self.browse("proot"))
		self.b_browseRoot.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_rootPath.text()))
		self.b_browseRepository.clicked.connect(lambda: self.browse("prepository"))
		self.b_browseRepository.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_repositoryPath.text()))

		self.b_browseSubmission.clicked.connect(lambda: self.browse("psubmission"))
		self.b_browseSubmission.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_submissionPath.text()))
		self.b_browseSlave.clicked.connect(lambda: self.browse("pslave"))
		self.b_browseSlave.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_slavePath.text()))
		self.b_browseCoordinatorRoot.clicked.connect(lambda: self.browse("pcoord"))
		self.b_browseCoordinatorRoot.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_coordinatorRoot.text()))

		self.chb_localMode.stateChanged.connect(self.lmodeChanged)

		self.chb_overrideMax.stateChanged.connect(lambda x: self.orToggled("max", x))
		self.b_browseMaxOR.clicked.connect(lambda: self.browse("maxOR", getFile=True))
		self.b_browseMaxOR.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_overrideMax.text()))
		self.chb_overrideMaya.stateChanged.connect(lambda x: self.orToggled("maya", x))
		self.b_browseMayaOR.clicked.connect(lambda: self.browse("mayaOR", getFile=True))
		self.b_browseMayaOR.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_overrideMaya.text()))
		self.chb_overrideHoudini.stateChanged.connect(lambda x: self.orToggled("hou", x))
		self.b_browseHoudiniOR.clicked.connect(lambda: self.browse("houOR", getFile=True))
		self.b_browseHoudiniOR.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_overrideHoudini.text()))
		self.chb_overrideBlender.stateChanged.connect(lambda x: self.orToggled("bld", x))
		self.b_browseBlenderOR.clicked.connect(lambda: self.browse("bldOR", getFile=True))
		self.b_browseBlenderOR.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_overrideBlender.text()))

		self.b_addSlave.clicked.connect(lambda: self.addSlave(itemType="slave"))
		self.b_deleteSlave.clicked.connect(lambda: self.deleteSlave(itemType="slave"))
		self.b_refreshSlaves.clicked.connect(self.refreshSlaves)
		self.b_addWS.clicked.connect(lambda: self.addSlave(itemType="workstation"))
		self.b_deleteWS.clicked.connect(lambda: self.deleteSlave(itemType="workstation"))
		self.b_refreshWS.clicked.connect(self.refreshWorkstations)
		self.lw_slaves.itemDoubleClicked.connect(lambda: self.openSlave(itemType="slave"))
		self.lw_slaves.customContextMenuRequested.connect(lambda: self.rclicked(ltype="slave"))
		self.lw_workstations.itemDoubleClicked.connect(lambda: self.openSlave(itemType="workstation"))
		self.lw_workstations.customContextMenuRequested.connect(lambda: self.rclicked(ltype="workstation"))
		self.buttonBox.accepted.connect(self.saveSettings)


	@err_decorator
	def houSetRcStyle(self, rcMenu):
		import hou
		rcMenu.setStyleSheet(hou.qt.styleSheet())


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
		elif bType == "maxOR":
			windowTitle = "Select 3dsmaxcmd.exe"
			uiEdit = self.e_overrideMax
		elif bType == "mayaOR":
			windowTitle = "Select Render.exe"
			uiEdit = self.e_overrideMaya
		elif bType == "houOR":
			windowTitle = "Select hython.exe"
			uiEdit = self.e_overrideHoudini
		elif bType == "bldOR":
			windowTitle = "Select blender.exe"
			uiEdit = self.e_overrideBlender
		elif bType == "pcoord":
			windowTitle = "Select Pandora Coordinator Root"
			uiEdit = self.e_coordinatorRoot
		else:
			return

		if getFile:
			selectedPath = QFileDialog.getOpenFileName(self, windowTitle, uiEdit.text(), "Executable (*.exe)")[0]
		else:
			selectedPath = QFileDialog.getExistingDirectory(self, windowTitle, uiEdit.text())

		if selectedPath != "":
			uiEdit.setText(selectedPath.replace("/","\\"))


	@err_decorator
	def lmodeChanged(self, state):
		self.w_rootPath.setVisible(state)
		self.w_sumitterPath.setVisible(not state)
		self.w_slaveRoot.setVisible(not state)
		self.w_coordinatorRoot.setVisible(not state)
		self.w_farmcomputer.setVisible(not state)

	@err_decorator
	def orToggled(self, prog, state):
		if prog == "max":
			self.e_overrideMax.setEnabled(state)
			self.b_browseMaxOR.setEnabled(state)
		elif prog == "maya":
			self.e_overrideMaya.setEnabled(state)
			self.b_browseMayaOR.setEnabled(state)
		elif prog == "hou":
			self.e_overrideHoudini.setEnabled(state)
			self.b_browseHoudiniOR.setEnabled(state)
		elif prog == "bld":
			self.e_overrideBlender.setEnabled(state)
			self.b_browseBlenderOR.setEnabled(state)


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

			self.setRcStyle(rcmenu)
			rcmenu.exec_(QCursor.pos())


	@err_decorator
	def addSlave(self, itemType):
		if itemType == "slave":
			basePath = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Slaves")
			prefix = "S_"
			refresh = self.refreshSlaves
		elif itemType == "workstation":
			basePath = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Workstations")
			prefix = "WS_"
			refresh = self.refreshWorkstations
		else:
			return

		itemDlg = QDialog()

		itemDlg.setWindowTitle("Create %s" % (itemType))
		l_item = QLabel("%s%s name:" % (itemType[0].upper(),itemType[1:]))
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
		itemDlg.resize(300,70)

		action = itemDlg.exec_()

		if action == 1:
			itemName = e_item.text()

			if itemName == "":
				msg = QMessageBox(QMessageBox.Warning, "Error", "Invalid %s name" % itemType, QMessageBox.Ok)
				msg.setFocus()
				msg.exec_()
				return

			itemPath = os.path.join(basePath, prefix + itemName)

			if os.path.exists(itemPath):
				msg = QMessageBox(QMessageBox.Warning, "Error", "%s%s %s already exists" % (itemType[0].upper(),itemType[1:], itemName), QMessageBox.Ok)
				msg.setFocus()
				msg.exec_()
				return

			try:
				os.makedirs(itemPath)
			except:
				msg = QMessageBox(QMessageBox.Warning, "Error", "Could not create %s %s" % (itemType, itemName), QMessageBox.Ok)
				msg.setFocus()
				msg.exec_()
			else:
				refresh()


	@err_decorator
	def deleteSlave(self, itemType):
		if itemType == "slave":
			basePath = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Slaves")
			prefix = "S_"
			curItem = self.lw_slaves.currentItem()
			refresh = self.refreshSlaves
		elif itemType == "workstation":
			basePath = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Workstations")
			prefix = "WS_"
			curItem = self.lw_workstations.currentItem()
			refresh = self.refreshWorkstations
		else:
			return

		if curItem is None:
			return

		curName = curItem.text()

		msg = QMessageBox(QMessageBox.Question, "Pandora", "Are you sure you want to delete %s %s?" % (itemType, curName), QMessageBox.Cancel)
		msg.addButton("Continue", QMessageBox.YesRole)
		msg.setFocus()
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
					msg = QMessageBox(QMessageBox.Warning, "Delete", "Could not delete %s %s.\n\nMake sure no other programs are using files in this folder:\n%s" %(itemType, curName, itemPath), QMessageBox.Cancel)
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

		slaveDir = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Slaves")

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

		wsDir = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Workstations")

		if os.path.exists(wsDir):
			for i in os.listdir(wsDir):
				if i.startswith("WS_"):
					item = QListWidgetItem(i[3:])
					self.lw_workstations.addItem(item)


	@err_decorator
	def openSlave(self, itemType, mode="open"):
		if itemType == "slave":
			basePath = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Slaves")
			prefix = "S_"
			curItem = self.lw_slaves.currentItem()
			refresh = self.refreshSlaves
		elif itemType == "workstation":
			basePath = os.path.join(self.e_coordinatorRoot.text(), "PandoraFarm", "Workstations")
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
		uconfig = ConfigParser()

		if not os.path.exists(self.configPath):
			self.core.createUserPrefs()
		else:
			uconfig.read(self.configPath)

			if not uconfig.has_section("globals"):
				uconfig.add_section("globals")

			if not uconfig.has_section("submissions"):
				uconfig.add_section("submissions")

			if not uconfig.has_section("slave"):
				uconfig.add_section("slave")

			if not uconfig.has_section("coordinator"):
				uconfig.add_section("coordinator")

			if not uconfig.has_section("dccoverrides"):
				uconfig.add_section("dccoverrides")

		uconfig.set('globals', "localmode", str(self.chb_localMode.isChecked()))

		rPath = self.e_rootPath.text().replace("/","\\")
		if rPath != "" and not rPath.endswith("\\"):
			rPath += "\\"
		uconfig.set('globals', "rootpath", rPath)

		repPath = self.e_repositoryPath.text().replace("/","\\")
		if repPath != "" and not repPath.endswith("\\"):
			repPath += "\\"
		uconfig.set('globals', "repositorypath", repPath)

		uconfig.set('submissions', "enabled", str(self.gb_submission.isChecked()))

		sPath = self.e_submissionPath.text().replace("/","\\")
		if sPath != "" and not sPath.endswith("\\"):
			sPath += "\\"
		uconfig.set('submissions', "submissionpath", sPath)
		uconfig.set('submissions', "username", (self.e_username.text()))

		uconfig.set('slave', "enabled", str(self.gb_slave.isChecked()))
	
		psPath = self.e_slavePath.text().replace("/","\\")
		if psPath != "" and not psPath.endswith("\\"):
			psPath += "\\"
		uconfig.set('slave', "slavepath", psPath)

		uconfig.set("dccoverrides", "maxoverride", str(self.chb_overrideMax.isChecked()))
		uconfig.set("dccoverrides", "mayaoverride", str(self.chb_overrideMaya.isChecked()))
		uconfig.set("dccoverrides", "houdinioverride", str(self.chb_overrideHoudini.isChecked()))
		uconfig.set("dccoverrides", "blenderoverride", str(self.chb_overrideBlender.isChecked()))
		uconfig.set("dccoverrides", "maxpath", str(self.e_overrideMax.text()))
		uconfig.set("dccoverrides", "mayapath", str(self.e_overrideMaya.text()))
		uconfig.set("dccoverrides", "houdinipath", str(self.e_overrideHoudini.text()))
		uconfig.set("dccoverrides", "blenderpath", str(self.e_overrideBlender.text()))

		uconfig.set('coordinator', "enabled", str(self.gb_coordinator.isChecked()))

		pcPath = self.e_coordinatorRoot.text().replace("/","\\")
		if pcPath != "" and not pcPath.endswith("\\"):
			pcPath += "\\"
		uconfig.set('coordinator', "rootpath", pcPath)

		with open(self.configPath, 'w') as inifile:
			uconfig.write(inifile)

		startupPath = os.getenv('APPDATA') + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\"
		trayStartup = startupPath + "PandoraTray.lnk"
		slaveStartup = startupPath + "PandoraSlave.lnk"
		coordStartup = startupPath + "PandoraCoordinator.lnk"

		if os.path.exists(trayStartup[:-3]+"lnk"):
			os.remove(trayStartup[:-3]+"lnk")

		if self.chb_pandoraTrayStartup.isChecked():
			if not os.path.exists(trayStartup):
				trayPath = os.path.join(os.getenv('LocalAppdata'), "Pandora", "Tools", "PandoraTray.lnk")
				shutil.copy2(trayPath, startupPath)
		else:
			if os.path.exists(trayStartup):
				os.remove(trayStartup)

		if self.gb_slave.isChecked() and self.chb_slaveStartup.isChecked():
			if not os.path.exists(slaveStartup):
				sPath = os.path.join(os.getenv('LocalAppdata'), "Pandora", "Tools", "PandoraSlave.lnk")
				shutil.copy2(sPath, slaveStartup)
		else:
			if os.path.exists(slaveStartup):
				os.remove(slaveStartup)

		if self.gb_coordinator.isChecked() and self.chb_coordinatorStartup.isChecked():
			if not os.path.exists(coordStartup):
				cPath = os.path.join(os.getenv('LocalAppdata'), "Pandora", "Tools", "PandoraCoordinator.lnk")
				shutil.copy2(cPath, coordStartup)
		else:
			if os.path.exists(coordStartup):
				os.remove(coordStartup)


	@err_decorator
	def loadSettings(self):
		if not os.path.exists(self.configPath):
		#	QMessageBox.warning(self,"loadSettings", "Pandora config does not exist.")
			return

		uconfig = ConfigParser()
		uconfig.read(self.configPath)

		if uconfig.has_option("globals", "localmode"):
			self.chb_localMode.setChecked(uconfig.getboolean('globals', "localmode"))

		if uconfig.has_option("globals", "rootpath"):
			self.e_rootPath.setText(uconfig.get('globals', "rootpath"))

		if uconfig.has_option("globals", "repositorypath"):
			self.e_repositoryPath.setText(uconfig.get('globals', "repositorypath"))

		if uconfig.has_option("submissions", "enabled"):
			self.gb_submission.setChecked(uconfig.getboolean('submissions', "enabled"))

		if uconfig.has_option("submissions", "submissionpath"):
			self.e_submissionPath.setText(uconfig.get('submissions', "submissionpath"))

		if uconfig.has_option("submissions", "username"):
			uname = uconfig.get('submissions', "username")
			
			self.e_username.setText(uname)
			self.validate(uiWidget=self.e_username)

		if uconfig.has_option("slave", "enabled"):
			self.gb_slave.setChecked(uconfig.getboolean('slave', "enabled"))

		if uconfig.has_option("slave", "slavepath"):
			self.e_slavePath.setText(uconfig.get('slave', "slavepath"))

		if uconfig.has_option("dccoverrides", "maxoverride"):
			self.chb_overrideMax.setChecked(uconfig.getboolean('dccoverrides', "maxoverride"))

		if uconfig.has_option("dccoverrides", "mayaoverride"):
			self.chb_overrideMaya.setChecked(uconfig.getboolean('dccoverrides', "mayaoverride"))

		if uconfig.has_option("dccoverrides", "houdinioverride"):
			self.chb_overrideHoudini.setChecked(uconfig.getboolean('dccoverrides', "houdinioverride"))

		if uconfig.has_option("dccoverrides", "blenderoverride"):
			self.chb_overrideBlender.setChecked(uconfig.getboolean('dccoverrides', "blenderoverride"))

		if uconfig.has_option("dccoverrides", "maxpath"):
			self.e_overrideMax.setText(uconfig.get('dccoverrides', "maxpath"))

		if uconfig.has_option("dccoverrides", "mayapath"):
			self.e_overrideMaya.setText(uconfig.get('dccoverrides', "mayapath"))

		if uconfig.has_option("dccoverrides", "houdinipath"):
			self.e_overrideHoudini.setText(uconfig.get('dccoverrides', "houdinipath"))

		if uconfig.has_option("dccoverrides", "blenderpath"):
			self.e_overrideBlender.setText(uconfig.get('dccoverrides', "blenderpath"))

		if uconfig.has_option("coordinator", "enabled"):
			self.gb_coordinator.setChecked(uconfig.getboolean('coordinator', "enabled"))

		if uconfig.has_option("coordinator", "rootpath"):
			self.e_coordinatorRoot.setText(uconfig.get('coordinator', "rootpath"))

		self.e_overrideMax.setEnabled(self.chb_overrideMax.isChecked())
		self.b_browseMaxOR.setEnabled(self.chb_overrideMax.isChecked())
		self.e_overrideMaya.setEnabled(self.chb_overrideMaya.isChecked())
		self.b_browseMayaOR.setEnabled(self.chb_overrideMaya.isChecked())
		self.e_overrideHoudini.setEnabled(self.chb_overrideHoudini.isChecked())
		self.b_browseHoudiniOR.setEnabled(self.chb_overrideHoudini.isChecked())
		self.e_overrideBlender.setEnabled(self.chb_overrideBlender.isChecked())
		self.b_browseBlenderOR.setEnabled(self.chb_overrideBlender.isChecked())

		startupPath = os.getenv('APPDATA') + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\"

		trayStartup = os.path.exists(startupPath + "PandoraTray.lnk")
		self.chb_pandoraTrayStartup.setChecked(trayStartup)

		slaveStartup = os.path.exists(startupPath + "PandoraSlave.lnk")
		self.chb_slaveStartup.setChecked(slaveStartup)

		coordStartup = os.path.exists(startupPath + "PandoraCoordinator.lnk")
		self.chb_coordinatorStartup.setChecked(coordStartup)

		lmode = self.chb_localMode.isChecked()
		self.w_rootPath.setVisible(lmode)
		self.w_sumitterPath.setVisible(not lmode)
		self.w_slaveRoot.setVisible(not lmode)
		self.w_coordinatorRoot.setVisible(not lmode)
		self.w_farmcomputer.setVisible(not lmode)


	@err_decorator
	def validate(self, uiWidget, origText=None):
		if origText is None:
			origText = uiWidget.text()
		text = self.core.validateStr(origText)

		if len(text) != len(origText):
			cpos = uiWidget.cursorPosition()
			uiWidget.setText(text)
			uiWidget.setCursorPosition(cpos-1)


	@err_decorator
	def startTray(self):
		command = '\"%s\\Pandora\\Python27\\PandoraTray.exe\" \"%s\\Pandora\\Scripts\\PandoraTray.py\"' % (os.getenv('LocalAppdata'), os.getenv('LocalAppdata'))
		subprocess.Popen(command, shell=True)


	@err_decorator
	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()


if __name__ == "__main__":
	qapp = QApplication(sys.argv)
	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
	handlerIcon = QIcon(os.path.dirname(os.path.abspath(__file__)) + "\\UserInterfacesPandora\\pandora_tray.ico")
	qapp.setWindowIcon(handlerIcon)
	import PandoraCore
	pc = PandoraCore.PandoraCore()
	pc.openSettings()
	qapp.exec_()