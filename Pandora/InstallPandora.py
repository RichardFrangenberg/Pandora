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
# MIT License
#
# Copyright (c) 2016-2018 Richard Frangenberg
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



import os, shutil, _winreg, win32com, sys, imp, subprocess, csv
from PySide.QtCore import *
from PySide.QtGui import *
from win32com.shell import shellcon
import win32com.shell.shell as shell
import win32con, win32event, win32process

import InstallList

sys.path.append(os.path.join(os.path.dirname(__file__), 'PandoraFiles' , 'Scripts'))

from UserInterfacesPandora import qdarkstyle


def copyfiles(pandoraPath, patch):
	try:
		if patch:
			sys.path.append(os.path.join(pandoraPath, "PythonLibs", "Python27"))
		else:
			sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PandoraFiles", "PythonLibs", "Python27"))

		try:
			import psutil
		except:
			pass
		else:
			PROCNAMES = ['PandoraTray.exe', 'PandoraRenderHandler.exe', 'PandoraSettings.exe', 'PandoraSlave.exe', "PandoraCoordinator.exe"]
			for proc in psutil.process_iter():
				if proc.name() in PROCNAMES:
					p = psutil.Process(proc.pid)

					try:
						if not 'SYSTEM' in p.username():
							proc.kill()
							print "closed Pandora process"
					except:
						pass

		if os.path.exists(pandoraPath):
			if not patch:
				print "remove old files.."

				while True:
					try:
						if os.path.exists(pandoraPath):
							shutil.rmtree(pandoraPath)
						break
					except WindowsError:
						msg = QMessageBox(QMessageBox.Warning, "Remove old files", "Could not remove old files.\n\nMake sure all dependent programms are closed.", QMessageBox.Cancel)
						msg.addButton("Retry", QMessageBox.YesRole)
						msg.setFocus()
						action = msg.exec_()

						if action != 0:
							msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Could not install new Pandora files.", QMessageBox.Ok)
							msg.setFocus()
							msg.exec_()
							return False

		elif patch:
			msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Pandora is not installed. Please install Pandora before you install this patch.", QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False


		print "copy new files.."

		if patch:
			while True:
				try:
					if os.path.exists(os.path.join(pandoraPath, "Scripts")):
						shutil.rmtree(os.path.join(pandoraPath, "Scripts"))
					break
				except WindowsError:
					msg = QMessageBox(QMessageBox.Warning, "Remove old files", "Could not remove old files.\n\nMake sure all dependent programms are closed.", QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					msg.setFocus()
					action = msg.exec_()

					if action != 0:
						msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Could not install new Pandora files.", QMessageBox.Ok)
						msg.setFocus()
						msg.exec_()
						return False

			shutil.copytree(os.path.dirname(os.path.abspath(__file__)) + "\\PandoraFiles\\Scripts", pandoraPath + "\\Scripts")
		else:
			while True:
				try:
					shutil.copytree(os.path.dirname(os.path.abspath(__file__)) + "\\PandoraFiles", pandoraPath)
					break
				except WindowsError:
					msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Could not copy new files.", QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					msg.setFocus()
					action = msg.exec_()

					if action != 0:
						msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Could not install new Pandora files.", QMessageBox.Ok)
						msg.setFocus()
						msg.exec_()
						return False

		return True

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()
		return False


def writeMaxFiles(maxpath):
	try:
		if not maxpath.endswith("startup") or not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(maxpath)), "usermacros")):
			msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Invalid 3dsMax path: %s.\n\nThe path has to be the 3dsMax startup folder, which usually looks like this: (with your username and 3dsMax version):\n\nC:\\Users\\Username\\AppData\\Local\\Autodesk\\3dsMax\\2019 - 64bit\\ENU\\scripts\\startup" % maxpath, QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False

		print "write max files: %s" % maxpath
		initPandora = maxpath + "\\initPandora.ms"
		if os.path.exists(initPandora):
			os.remove(initPandora)

		origInitFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Max", "initPandora.ms")
		shutil.copy2(origInitFile, initPandora)

		initPy = maxpath + "\\python\\initPandora.py"

		if not os.path.exists(os.path.dirname(initPy)):
			os.mkdir(os.path.dirname(initPy))

		if os.path.exists(initPy):
			os.remove(initPy)

		origInitFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Max", "initPandora.py")
		shutil.copy2(origInitFile, initPy)

		pandoraMenu = maxpath + "\\PandoraMenu.ms"
		if os.path.exists(pandoraMenu):
			os.remove(pandoraMenu)

		origMenuFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Max", "PandoraMenu.ms")
		shutil.copy2(origMenuFile, pandoraMenu)

		macroPath= os.path.abspath(os.path.join(maxpath, os.pardir, os.pardir) + "\\usermacros\\PandoraMacros.mcr")

		if os.path.exists(macroPath):
			os.remove(macroPath)

		origMacroFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Max", "PandoraMacros.mcr")
		shutil.copy2(origMacroFile, macroPath)

		return True

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred during the 3ds Max installation.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()
		return False


def getHoudiniPath():
	try:
		key = _winreg.OpenKey(
			_winreg.HKEY_LOCAL_MACHINE,
			"SOFTWARE\\Side Effects Software",
			0,
			_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
		)

		houdiniVersion = (_winreg.QueryValueEx(key, "ActiveVersion"))[0]

		key = _winreg.OpenKey(
			_winreg.HKEY_LOCAL_MACHINE,
			"SOFTWARE\\Side Effects Software\\Houdini " + houdiniVersion,
			0,
			_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
		)

		return (_winreg.QueryValueEx(key, "InstallPath"))[0]
	except:
		return None


def writeHoudiniFiles(houdiniPath):
	try:
		print "write Houdini files: %s" % houdiniPath

		# python rc
		pyrc = houdiniPath + "\\houdini\\python2.7libs\\pythonrc.py"

		if not os.path.exists(os.path.dirname(pyrc)):
			msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Invalid Houdini path: %s.\n\nThe path has to be the Houdini installation folder, which usually looks like this: (with your Houdini version):\n\nC:\\Program Files\\Side Effects Software\\Houdini 16.5.439" % houdiniPath, QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False

		origRCFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Houdini", "pythonrc.py")
		with open(origRCFile, 'r') as mFile:
			initString = mFile.read()

		if os.path.exists(pyrc):
			with open(pyrc, 'r') as rcfile:
				content = rcfile.read()
			if not initString in content:
				if "#>>>PandoraStart" in content and "#<<<PandoraEnd" in content:
					content = content[:content.find("#>>>PandoraStart")] + content[content.find("#<<<PandoraEnd")+12:] + initString
					with open(pyrc, 'w') as rcfile:
						rcfile.write(content)
				else:
					with open(pyrc, 'a') as rcfile:
						rcfile.write(initString)
		else:
			with open(pyrc, 'w') as rcfile:
				rcfile.write(initString)


		# pandoraInit
		initpath = os.path.dirname(pyrc) + "\\PandoraInit.py"

		if os.path.exists(initpath):
			os.remove(initpath)

		if os.path.exists(initpath + "c"):
			os.remove(initpath + "c")

		origInitFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Houdini", "PandoraInit.py")
		shutil.copy2(origInitFile, initpath)

		return True

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred during the Houdini installation.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()
		return False


def writeMayaFiles(mayaPath, userFolders):
	try:
		if not os.path.exists(os.path.join(mayaPath, "scripts")) or not os.path.exists(os.path.join(mayaPath, "prefs", "shelves")):
			msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Invalid Maya path: %s.\n\nThe path has to be the Maya preferences folder, which usually looks like this: (with your username and Maya version):\n\nC:\\Users\\Richard\\Documents\\maya\\2018" % mayaPath, QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False

		print "write maya files: %s" % mayaPath

		origSetupFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Maya", "userSetup.py")
		with open(origSetupFile, 'r') as mFile:
			setupString = mFile.read()

		pandoraSetup = mayaPath + "\\scripts\\userSetup.py"

		if os.path.exists(pandoraSetup):
			with open(pandoraSetup, 'r') as setupfile:
				content = setupfile.read()

			if not setupString in content:
				if "#>>>PandoraStart" in content and "#<<<PandoraEnd" in content:
					content = setupString + content[:content.find("#>>>PandoraStart")] + content[content.find("#<<<PandoraEnd")+12:]
					with open(pandoraSetup, 'w') as rcfile:
						rcfile.write(content)
				else:
					with open(pandoraSetup, 'w') as setupfile:
						setupfile.write(setupString + content)
		else:
			open(pandoraSetup, 'a').close()
			with open(pandoraSetup, 'w') as setupfile:
				setupfile.write(setupString)

		initpath = mayaPath + "\\scripts\\PandoraInit.py"

		if os.path.exists(initpath):
			os.remove(initpath)

		if os.path.exists(initpath + "c"):
			os.remove(initpath + "c")

		origInitFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Maya", "PandoraInit.py")
		shutil.copy2(origInitFile, initpath)

		shelfpath = os.path.join(mayaPath, "prefs", "shelves", "shelf_Pandora.mel")

		if os.path.exists(shelfpath):
			os.remove(shelfpath)
	
		origShelfFile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Maya", "shelf_Pandora.mel")
		shutil.copy2(origShelfFile, shelfpath)
		with open(shelfpath, 'r') as shelffile:
			content = shelffile.read()

		content = content.replace("%localappdata%", userFolders["LocalAppdata"].replace("\\", "\\\\"))
		with open(shelfpath, 'w') as shelffile:
			shelffile.write(content)

		return True

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred during the Maya installation.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()
		return False


def getBlenderPath():
	try:
		key = _winreg.OpenKey(
			_winreg.HKEY_LOCAL_MACHINE,
			"SOFTWARE\\Classes\\blendfile\\shell\\open\\command",
			0,
			_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
		)
		blenderPath = (_winreg.QueryValueEx(key, "" ))[0].split(" \"%1\"")[0].replace("\"", "")

		vpath = os.path.join(os.path.dirname(blenderPath), "2.79")
		if not os.path.exists(vpath):
			vpath = os.path.join(os.path.dirname(blenderPath), "2.78")

		if os.path.exists(vpath):
			return vpath
		else:
			return None

	except:
		return None


def writeBlenderFiles(blenderPath):
	try:
		if not os.path.exists(os.path.join(blenderPath, "scripts", "startup")):
			msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Invalid Blender path: %s.\n\nThe path has to be the Blender version folder in the installation folder, which usually looks like this: (with your Blender version):\n\nC:\\Program Files\\Blender Foundation\\Blender\\2.79" % blenderPath, QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False

		print "write Blender files: %s" % blenderPath

		# pandoraInit
		initpath = os.path.join(blenderPath, "scripts", "startup", "PandoraInit.py")

		if os.path.exists(initpath):
			os.remove(initpath)

		if os.path.exists(initpath + "c"):
			os.remove(initpath + "c")

		baseinitfile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Blender", "PandoraInit.py")
		shutil.copy2(baseinitfile, initpath)

		baseWinfile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Blender", "qminimal.dll")
		winPath = os.path.join(os.path.dirname(blenderPath), "platforms", "qminimal.dll")

		if not os.path.exists(os.path.dirname(winPath)):
			os.mkdir(os.path.dirname(winPath))

		if not os.path.exists(winPath):
			shutil.copy2(baseWinfile, winPath)

		baseWinfile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Blender", "qoffscreen.dll")
		winPath = os.path.join(os.path.dirname(blenderPath), "platforms", "qoffscreen.dll")

		if not os.path.exists(winPath):
			shutil.copy2(baseWinfile, winPath)

		baseWinfile = os.path.join(os.path.dirname(__file__), "IntegrationScripts", "Blender", "qwindows.dll")
		winPath = os.path.join(os.path.dirname(blenderPath), "platforms", "qwindows.dll")

		if not os.path.exists(winPath):
			shutil.copy2(baseWinfile, winPath)

		return True

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred during the Blender installation.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()
		return False


def openBrowse(item, column):
	if item.text(0) not in ["Custom", "Houdini", "Blender"]:
		return

	path = QFileDialog.getExistingDirectory(QWidget(), "Select destination folder", item.text(column))
	if path != "":
		item.setText(1, path)
		item.setToolTip(1, path)


def CompItemClicked(item, column):
	if item.text(0) == "Pandora files":
		if item.checkState(0) == Qt.Checked:
			settingsPath = item.child(0).text(1)
			if os.path.exists(settingsPath):
				item.child(0).setFlags(item.child(0).flags() | Qt.ItemIsEnabled)
		else:
			item.child(0).setFlags(~Qt.ItemIsEnabled)



def refreshUI(pList, username):
	lappdata = os.path.join(os.path.dirname(os.environ["Userprofile"]), username, "AppData", "Local")
	uProfile = os.path.join(os.path.dirname(os.environ["Userprofile"]), username)
	userFolders = {"LocalAppdata": lappdata, "UserProfile": uProfile }

	pList.tw_components.clear()

	pandoraFilesItem = QTreeWidgetItem(["Pandora files"])
	pList.tw_components.addTopLevelItem(pandoraFilesItem)
	pandoraFilesItem.setCheckState(0, Qt.Checked)

	keepSettingsItem = QTreeWidgetItem(["Keep old settings"])
	pandoraFilesItem.addChild(keepSettingsItem)
	pandoraFilesItem.setExpanded(True)

	pList.tw_components.itemClicked.connect(CompItemClicked)

	settingsPath = userFolders["LocalAppdata"] + "\\Pandora\\Config\\Pandora.ini"
	settingsPathOld = userFolders["LocalAppdata"] + "\\Pandora\\Config\\PandoraOLD.ini"
	if os.path.exists(settingsPath):
		keepSettingsItem.setCheckState(0, Qt.Checked)
		keepSettingsItem.setText(1, settingsPath)
	elif os.path.exists(settingsPathOld):
		keepSettingsItem.setCheckState(0, Qt.Checked)
		keepSettingsItem.setText(1, settingsPathOld)
	else:
		keepSettingsItem.setCheckState(0, Qt.Unchecked)
		keepSettingsItem.setFlags(~Qt.ItemIsEnabled)

	if pList.chb_shelves.isChecked():
		maxPath = [[userFolders["LocalAppdata"] + "\\Autodesk\\3dsMax\\2017 - 64bit\\ENU\\scripts\\startup", "2017"], [userFolders["LocalAppdata"] + "\\Autodesk\\3dsMax\\2018 - 64bit\\ENU\\scripts\\startup", "2018"], [userFolders["LocalAppdata"] + "\\Autodesk\\3dsMax\\2019 - 64bit\\ENU\\scripts\\startup", "2019"]]

		integrationsItem = QTreeWidgetItem(["DCC integrations"])
		pList.tw_components.addTopLevelItem(integrationsItem)

		maxItem = QTreeWidgetItem(["3ds Max"])
		integrationsItem.addChild(maxItem)
		integrationsItem.setExpanded(True)

		maxcItem = QTreeWidgetItem(["Custom"])
		maxcItem.setToolTip(0, "e.g. \"C:\\Users\\Username\\AppData\\Local\\Autodesk\\3dsMax\\2019 - 64bit\\ENU\\scripts\\startup\"")
		maxcItem.setToolTip(1, "e.g. \"C:\\Users\\Username\\AppData\\Local\\Autodesk\\3dsMax\\2019 - 64bit\\ENU\\scripts\\startup\"")
		maxcItem.setCheckState(0, Qt.Unchecked)
		maxItem.addChild(maxcItem)
		maxItem.setExpanded(True)

		for i in maxPath:
			maxvItem = QTreeWidgetItem([i[1]])
			maxItem.addChild(maxvItem)

			if os.path.exists(i[0]):
				maxvItem.setCheckState(0, Qt.Checked)
				maxvItem.setText(1, i[0])
				maxvItem.setToolTip(0, i[0])
			else:
				maxvItem.setCheckState(0, Qt.Unchecked)
				maxvItem.setFlags(~Qt.ItemIsEnabled)
				
		mayaPath = [userFolders["UserProfile"] + "\\Documents\\maya\\2016", userFolders["UserProfile"] + "\\Documents\\maya\\2017", userFolders["UserProfile"] + "\\Documents\\maya\\2018"]

		mayaItem = QTreeWidgetItem(["Maya"])
		integrationsItem.addChild(mayaItem)

		mayacItem = QTreeWidgetItem(["Custom"])
		mayacItem.setToolTip(0, "e.g. \"C:\\Users\\Username\\Documents\\maya\\2018\"")
		mayacItem.setToolTip(1, "e.g. \"C:\\Users\\Username\\Documents\\maya\\2018\"")
		mayacItem.setCheckState(0, Qt.Unchecked)
		mayaItem.addChild(mayacItem)
		mayaItem.setExpanded(True)

		for i in mayaPath:
			mayavItem = QTreeWidgetItem([i[-4:]])
			mayaItem.addChild(mayavItem)

			if os.path.exists(i):
				mayavItem.setCheckState(0, Qt.Checked)
				mayavItem.setText(1, i)
				mayavItem.setToolTip(0, i)
			else:
				mayavItem.setCheckState(0, Qt.Unchecked)
				mayavItem.setFlags(~Qt.ItemIsEnabled)

		houItem = QTreeWidgetItem(["Houdini"])
		integrationsItem.addChild(houItem)

		houdiniPath = getHoudiniPath()
		if houdiniPath != None:
			houItem.setCheckState(0, Qt.Checked)
			houItem.setText(1, houdiniPath)
			houItem.setToolTip(0, houdiniPath)
		else:
			houItem.setCheckState(0, Qt.Unchecked)

		bldItem = QTreeWidgetItem(["Blender"])
		integrationsItem.addChild(bldItem)

		blenderPath = getBlenderPath()
		if blenderPath != None:
			bldItem.setCheckState(0, Qt.Checked)
			bldItem.setText(1, blenderPath)
			bldItem.setToolTip(0, blenderPath)
		else:
			bldItem.setCheckState(0, Qt.Unchecked)


def install(patch=False, user=""):
	try:
		pList = InstallList.InstallList()
		pList.setModal(True)

		pList.tw_components.header().resizeSection(0,200)
		pList.tw_components.itemDoubleClicked.connect(openBrowse)

		refreshUI(pList, user)

		userDir = os.path.dirname(os.environ["Userprofile"])
		pList.cb_users.addItems([x for x in os.listdir(userDir) if x not in ["All Users", "Default", "Default User"] and os.path.isdir(os.path.join(userDir,x))])
		pList.cb_users.setCurrentIndex(pList.cb_users.findText(user))
		pList.cb_users.currentIndexChanged[str].connect(lambda x:refreshUI(pList, x))
		pList.chb_shelves.toggled.connect(lambda x:refreshUI(pList, pList.cb_users.currentText()))

		pList.buttonBox.button(QDialogButtonBox.Ok).setText("Install")
		pList.buttonBox.button(QDialogButtonBox.Cancel).setFocusPolicy(Qt.NoFocus)

		pList.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
		pList.setFocus()

		result = pList.exec_()

		if result == 0:
			print "Installation canceled"
			return False

		print "\n\nInstalling - please wait.."

		waitmsg = QMessageBox(QMessageBox.NoIcon, "Pandora Installation", "Installing - please wait..", QMessageBox.Cancel)
		waitmsg.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
		waitmsg.setWindowIcon(wIcon)
		waitmsg.buttons()[0].setHidden(True)
		waitmsg.show()
		QCoreApplication.processEvents()

		lappdata = os.path.join(os.path.dirname(os.environ["Userprofile"]), pList.cb_users.currentText(), "AppData", "Local")
		appdata = os.path.join(os.path.dirname(os.environ["Userprofile"]), pList.cb_users.currentText(), "AppData", "Roaming")
		userFolders = {"LocalAppdata": lappdata, "AppData": appdata }

		pandoraFilesItem = pList.tw_components.findItems("Pandora files", Qt.MatchExactly)[0]
		keepSettingsItem = pandoraFilesItem.child(0)
		maxItem = mayaItem = houItem = bldItem = None
		if pList.chb_shelves.isChecked():
			maxItem = pList.tw_components.findItems("3ds Max", Qt.MatchExactly | Qt.MatchRecursive)[0]
			mayaItem = pList.tw_components.findItems("Maya", Qt.MatchExactly | Qt.MatchRecursive)[0]
			houItem = pList.tw_components.findItems("Houdini", Qt.MatchExactly | Qt.MatchRecursive)[0]
			bldItem = pList.tw_components.findItems("Blender", Qt.MatchExactly | Qt.MatchRecursive)[0]

		result = {}

		settingsPath = userFolders["LocalAppdata"] + "\\Pandora\\Config\\Pandora.ini"
		settingsPathOld = userFolders["LocalAppdata"] + "\\Pandora\\Config\\PandoraOLD.ini"

		pandoraPath = userFolders["LocalAppdata"] + "\\Pandora\\"
		if pandoraFilesItem.checkState(0) == Qt.Checked:
			if keepSettingsItem.checkState(0) == Qt.Checked:
				if os.path.exists(settingsPath):
					sPath = settingsPath
				elif os.path.exists(settingsPathOld):
					sPath = settingsPathOld

				from ConfigParser import ConfigParser
				pconfig = ConfigParser()
				try:
					pconfig.read(sPath)
				except:
					os.remove(sPath)

			result["Pandora Files"] = copyfiles(pandoraPath, patch)

			if not result["Pandora Files"]:
				return result

			if keepSettingsItem.checkState(0) == Qt.Checked and "pconfig" in locals():
				writeIni = True
				if not os.path.exists(os.path.dirname(settingsPathOld)):
					try:
						os.makedirs(os.path.dirname(settingsPathOld))
					except:
						writeIni = False

				if writeIni:
					open(settingsPathOld, 'a').close()
					with open(settingsPathOld, 'w') as inifile:
						pconfig.write(inifile)


		installLocs = []

		#max
		maxPaths = []
		if maxItem is not None:
			for i in range(maxItem.childCount()):
				item = maxItem.child(i)
				if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
					maxPaths.append(item.text(1))

			for i in maxPaths:
				result["3ds Max integration"] = writeMaxFiles(i)
				if result["3ds Max integration"]:
					installLocs.append(i)

		#maya
		mayaPaths = []
		if mayaItem is not None:
			for i in range(mayaItem.childCount()):
				item = mayaItem.child(i)
				if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
					mayaPaths.append(item.text(1))

			for i in mayaPaths:
				result["Maya integration"] = writeMayaFiles(i, userFolders)
				if result["Maya integration"]:
					installLocs.append(i)

		#houdini
		if houItem is not None:
			if houItem.checkState(0) == Qt.Checked and os.path.exists(houItem.text(1)):
				result["Houdini integration"] = writeHoudiniFiles(houItem.text(1))
				if result["Houdini integration"]:
					installLocs.append(houItem.text(1))

		# blender
		if bldItem is not None:
			if bldItem.checkState(0) == Qt.Checked and os.path.exists(bldItem.text(1)):
				result["Blender integration"] = writeBlenderFiles(bldItem.text(1))
				if result["Blender integration"]:
					installLocs.append(bldItem.text(1))

		if installLocs != []:
			locFile = pandoraPath + "installLocations.txt"
			locString = ""

			newLocs = []

			if os.path.exists(locFile):
				with open(locFile, 'r') as locationfile:
					lines = locationfile.readlines()
					for loc in installLocs:
						for line in lines:
							if line.replace("\n", "") == loc:
								break
						else:
							newLocs.append(loc)
			else:
				open(locFile, 'w').close()
				newLocs = installLocs

			for i in newLocs:
				locString += i + "\n"

			with open(locFile, 'a') as locationfile:
				locationfile.write(locString)

		trayStartup = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\PandoraTray.lnk"
		trayStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Pandora\\PandoraTray.lnk"
		handlerStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Pandora\\PandoraRenderHandler.lnk"
		settingsStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Pandora\\PandoraSettings.lnk"
		slaveStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Pandora\\PandoraSlave.lnk"
		coordStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Pandora\\PandoraCoordinator.lnk"

		if not os.path.exists(os.path.dirname(trayStartMenu)):
			try:
				os.makedirs(os.path.dirname(trayStartMenu))
			except:
				pass

		if not os.path.exists(os.path.dirname(trayStartup)):
			try:
				os.makedirs(os.path.dirname(trayStartup))
			except:
				pass

		if os.path.exists(trayStartup[:-3]+"lnk"):
			os.remove(trayStartup[:-3]+"lnk")

		trayLnk = os.path.join(userFolders["LocalAppdata"], "Pandora", "Tools", "PandoraTray.lnk")
		rhLnk = os.path.join(userFolders["LocalAppdata"], "Pandora", "Tools", "PandoraRenderHandler.lnk")
		settingsLnk = os.path.join(userFolders["LocalAppdata"], "Pandora", "Tools", "PandoraSettings.lnk")
		slaveLnk = os.path.join(userFolders["LocalAppdata"], "Pandora", "Tools", "PandoraSlave.lnk")
		coordLnk = os.path.join(userFolders["LocalAppdata"], "Pandora", "Tools", "PandoraCoordinator.lnk")

		if os.path.exists(trayLnk):
			if os.path.exists(os.path.dirname(trayStartup)):
				shutil.copy2(trayLnk, trayStartup)
			else:
				print "could not create PandoraTray autostart entry"

			if os.path.exists(os.path.dirname(trayStartMenu)):
				shutil.copy2(trayLnk, trayStartMenu)
			else:
				print "could not create PandoraTray startmenu entry"

		if os.path.exists(rhLnk) and os.path.exists(os.path.dirname(handlerStartMenu)):
			shutil.copy2(rhLnk, handlerStartMenu)
		else:
			print "could not create Pandora Render-Handler startmenu entry"

		if os.path.exists(settingsLnk) and os.path.exists(os.path.dirname(settingsStartMenu)):
			shutil.copy2(settingsLnk, settingsStartMenu)
		else:
			print "could not create Pandora settings startmenu entry"

		if os.path.exists(slaveLnk) and os.path.exists(os.path.dirname(slaveStartMenu)):
			shutil.copy2(slaveLnk, slaveStartMenu)
		else:
			print "could not create Pandora slave startmenu entry"

		if os.path.exists(coordLnk) and os.path.exists(os.path.dirname(coordStartMenu)):
			shutil.copy2(coordLnk, coordStartMenu)
		else:
			print "could not create Pandora coordinator startmenu entry"

		os.system('echo %s\\Pandora\\Tools\\PandoraTray.lnk | clip' % userFolders["LocalAppdata"])

		if "waitmsg" in locals() and waitmsg.isVisible():
			waitmsg.close()

		print "Finished"

		return result

	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()
		return False


def uninstall(user=""):
	import UninstallPandora

	return UninstallPandora.uninstallPandora(user=user)


def force_elevated(user):
	try:
		if sys.argv[-1] != 'asadmin':
			script = os.path.abspath(sys.argv[0])
			params = ' '.join(["\"%s\"" % script] + sys.argv[1:] + ["\"%s\"" % user, 'asadmin'])
			procInfo = shell.ShellExecuteEx(nShow=win32con.SW_SHOWNORMAL,
								 fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
								 lpVerb='runas',
								 lpFile=sys.executable,
								 lpParameters=params)

			procHandle = procInfo['hProcess']    
			obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
			rc = win32process.GetExitCodeProcess(procHandle)

	except Exception as ex:
		print ex


if __name__ == "__main__":
	qapp = QApplication(sys.argv)
	try:
		wIcon = QIcon(os.path.dirname(os.path.abspath(__file__)) + "\\PandoraFiles\\Scripts\\UserInterfacesPandora\\pandora_tray.ico")
		qapp.setWindowIcon(wIcon)
		qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

		if sys.argv[-1] != 'asadmin':
			force_elevated(user=os.environ["username"])
		else:
			try:
				username = sys.argv[-2]

				isPatch = not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PandoraFiles", "Python27"))

				actionType = "install"
				pandoraPath = os.path.join(os.path.dirname(os.environ["Userprofile"]), username, "AppData", "Local", "Pandora")

				if os.path.exists(pandoraPath):
					msg = QMessageBox(QMessageBox.Question, "Pandora", "An existing Pandora installation was found.\nWhat do you want to do?\n\n(You don't need to uninstall Pandora before you install a new version)", QMessageBox.Cancel)
					msg.addButton("Install", QMessageBox.YesRole)
					msg.addButton("Uninstall", QMessageBox.YesRole)
					msg.setFocus()
					action = msg.exec_()

					if action == 0:
						actionType = "install"
					elif action == 1:
						actionType = "uninstall"
					else:
						actionType = "cancel"

				if actionType == "install":
					result = install(patch=isPatch, user=username)
				elif actionType == "uninstall":
					result = uninstall(user=username)
				else:
					result = False
				
				if result == False:
					msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Installation was canceled", QMessageBox.Ok)
					msg.setFocus()
					msg.exec_()
				elif not False in result.values():
					if actionType == "install":
						msg = QMessageBox(QMessageBox.Information, "Pandora Installation", "Pandora was installed successfully.", QMessageBox.Ok)
						msg.setFocus()
						msg.exec_()
					elif actionType == "uninstall":
						msg = QMessageBox(QMessageBox.Information, "Pandora Uninstallation", "Pandora was uninstalled successfully.\n(You can ignore the \"Run Pandora\" checkbox, which you will see on the installer after you press OK)", QMessageBox.Ok)
						msg.setFocus()
						msg.exec_()
				else:
					msgString = "Some parts failed to %s:\n\n" % actionType
					for i in result:
						msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

					msgString = msgString.replace("True", "Success").replace("False", "Error").replace("Pandora Files:", "Pandora Files:\t")

					msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", msgString, QMessageBox.Ok)
					msg.setFocus()
					msg.exec_()

			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
				msg.setFocus()
				msg.exec_()

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		msg = QMessageBox(QMessageBox.Warning, "Pandora Installation", "Errors occurred.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()

	sys.exit()
	qapp.exec_()