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

import sys, os, threading, shutil, time, socket, traceback, imp, platform

#check if python 2 or python 3 is used
if sys.version[0] == "3":
	from configparser import ConfigParser
	import winreg as _winreg
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	import _winreg
	pVersion = 2

from functools import wraps
import subprocess

try:
	import PandoraEnterText
except:
	modPath = imp.find_module("PandoraEnterText")[1]
	if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
		os.remove(modPath)
	import PandoraEnterText


# Pandora core class, which holds various functions
class PandoraCore():
	def __init__(self):
		#QWidget.__init__(self)
		self.pandoraIni = ""

		# test in which DCC this script is loaded
		# 1: 3ds Max
		# 2: Houdini
		# 3: Maya
		# 4: Standalone
		# 5: Nuke
		# 6: Blender

		try:
			global MaxPlus
			import MaxPlus
			self.app = 1
		except: 
			try:
				global hou
				import hou
				self.app = 2
			except:
				try:
					from maya import OpenMaya as omya
					global cmds
					import maya.cmds as cmds

					self.app = 3
				except:
					try:
						global bpy
						import bpy
						self.app = 6
					except:
						self.app = 4

		
		try:
			# set some general variables
			self.version = "v1.0.0"

			if platform.system() == "Windows":
				self.pandoraRoot = os.path.join(os.getenv('LocalAppdata'), "Pandora")

			self.configPath = os.path.join(self.pandoraRoot, "Config", "Pandora.ini")

			# add the custom python libraries to the path variable, so they can be imported
			if pVersion == 2:
				pyLibs = os.path.join(self.pandoraRoot, "PythonLibs", "Python27")
			else:
				pyLibs = os.path.join(self.pandoraRoot, "PythonLibs", "Python35")
				QCoreApplication.addLibraryPath(os.path.join(self.pandoraRoot, "PythonLibs", "Python35", "PySide2", "plugins"))
				
			cpLibs = os.path.join(self.pandoraRoot, "PythonLibs", "CrossPlatform")
			win32Libs = os.path.join(cpLibs, "win32")

			if cpLibs not in sys.path:
				sys.path.append(cpLibs)

			if pyLibs not in sys.path:
				sys.path.append(pyLibs)

			if win32Libs not in sys.path:
				sys.path.append(win32Libs)
				

			# if no user ini exists, it will be created with default values
			if not os.path.exists(self.configPath):
				self.createUserPrefs()

			# clean up files from the installation
			if platform.system() == "Windows":
				tmpPath = os.path.join(os.getenv("Tmp"), "Pandora")
				if os.path.exists(tmpPath):
					try:
						shutil.rmtree(tmpPath)
					except:
						pass

			# if this script is loaded inside an DCC, a timer is started to wait for the UI before the startup function is called
			if self.app != 4:
				self.maxwait = 20
				self.elapsed = 0
				self.timer = QTimer()
				self.timer.timeout.connect(self.startup)
				self.timer.start(1000)
			else:
				self.messageParent = QWidget()

			QApplication.restoreOverrideCursor()

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			erStr = ("%s ERROR - PandoraCore init %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), self.version, ''.join(traceback.format_stack()), traceback.format_exc()))
			self.writeErrorLog(erStr)


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - PandoraCore %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def startup(self):
		self.elapsed += 1
		if self.elapsed > self.maxwait:
			self.timer.stop()

		if self.app == 1:
			self.timer.stop()
			if psVersion == 1:
				self.messageParent = MaxPlus.GetQMaxWindow()
			else:
				self.messageParent = MaxPlus.GetQMaxMainWindow()

			self.programName = "3dsMax"
	
		elif self.app == 2:
			if hou.ui.mainQtWindow() is not None:
				self.timer.stop()
				self.messageParent = hou.ui.mainQtWindow()

				if hou.ui.curDesktop().name() == "Technical":
					curShelfSet = "shelf_set_td"
				else:
					curShelfSet = "shelf_set_1"

				curShelves = hou.ShelfSet.shelves(hou.shelves.shelfSets()[curShelfSet])

				shelfName = "pandora-v0.9.0"

				if not shelfName in hou.shelves.shelves():
					news = hou.shelves.newShelf(file_path = hou.shelves.defaultFilePath(), name= shelfName, label="Pandora")
					hou.ShelfSet.setShelves(hou.shelves.shelfSets()[curShelfSet],curShelves + (news,))

					submitterScript = "import PandoraInit\n\nPandoraInit.pandoraCore.openSubmitter()"
					if hou.shelves.tool("pandora_submitter") is not None:
						hou.shelves.tool("pandora_submitter").destroy()
					hou.shelves.newTool(file_path=hou.shelves.defaultFilePath(), name = "pandora_submitter", label ="Submitter",help = "\"\"\"Open the Pandora renderjob submitter\"\"\"", script= submitterScript, icon=os.path.join(self.pandoraRoot, "Scripts", "UserInterfacesPandora", "pandoraSubmitter.png" ))

					renderHandlerScript = "import PandoraInit\n\nPandoraInit.pandoraCore.openRenderHandler()"
					if hou.shelves.tool("pandora_renderhandler") is not None:
						hou.shelves.tool("pandora_renderhandler").destroy()
					hou.shelves.newTool(file_path=hou.shelves.defaultFilePath(), name = "pandora_renderhandler", label ="Render-Handler",help = "\"\"\"Open the Pandora Render-Handler\"\"\"", script= renderHandlerScript, icon=os.path.join(self.pandoraRoot, "Scripts", "UserInterfacesPandora", "pandoraRenderHandler.png"))

					settingsScript = "import PandoraInit\n\nPandoraInit.pandoraCore.openSettings()"
					if hou.shelves.tool("pandora_settings") is not None:
						hou.shelves.tool("pandora_settings").destroy()
					hou.shelves.newTool(file_path=hou.shelves.defaultFilePath(), name = "pandora_settings", label ="Settings",help = "\"\"\"Open the Pandora settings\"\"\"", script= settingsScript, icon=os.path.join(self.pandoraRoot, "Scripts", "UserInterfacesPandora", "pandoraSettings.png"))

					hou.Shelf.setTools(hou.shelves.shelves()[shelfName],( hou.shelves.tool("pandora_submitter"), hou.shelves.tool("pandora_renderhandler"), hou.shelves.tool("pandora_settings")))
				
				else:
					pandoraShelf = hou.shelves.shelves()[shelfName]
					if pandoraShelf not in curShelves:
						hou.ShelfSet.setShelves(hou.shelves.shelfSets()[curShelfSet],curShelves + (pandoraShelf,))

				self.programName = "Houdini"
				
			else:
				return None	
		elif self.app == 3:
			import maya.mel as mel
			import maya.OpenMaya as api

			for obj in qApp.topLevelWidgets():
				if obj.objectName() == 'MayaWindow':
					self.messageParent = obj
					break

			topLevelShelf = mel.eval('string $m = $gShelfTopLevel')
			if cmds.shelfTabLayout(topLevelShelf, query=True, tabLabelIndex=True) == None:
				return None
			self.timer.stop()

			self.programName = "Maya"

		elif self.app == 6:
			self.timer.stop()

			self.messageParent = QWidget()
			self.messageParent.setWindowFlags(self.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint)

			self.programName = "Blender"


	def createUserPrefs(self):
		if os.path.exists(self.configPath):
			try:
				os.remove(self.configPath)
			except:
				pass

		from win32com.shell import shell, shellcon
		localRep = os.path.join(shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0), "PandoraRepository")
		maxpath = self.getMaxPath()
		mayapath = self.getMayaPath()
		houpath = self.getHoudiniPath()
		bldpath = self.getBlenderPath()

		if not os.path.exists(os.path.dirname(self.configPath)):
			os.mkdir(os.path.dirname(self.configPath))

		open(self.configPath, 'a').close()

		uconfig = ConfigParser()
		uconfig.add_section('globals')
		uconfig.add_section('submissions')
		uconfig.add_section('slave')
		uconfig.add_section('coordinator')
		uconfig.add_section('renderhandler')
		uconfig.add_section('dccoverrides')
		uconfig.add_section('lastusedsettings')
		uconfig.set('globals', "localmode", "True")
		uconfig.set('globals', "rootpath", "")
		uconfig.set('globals', "repositorypath", localRep)
		uconfig.set('submissions', "enabled", "False")
		uconfig.set('submissions', "submissionpath", "")
		uconfig.set('submissions', "username", "")
		uconfig.set("slave", "enabled", "False")
		uconfig.set("slave", "slavepath", "")
		uconfig.set("coordinator", "enabled", "False")
		uconfig.set("coordinator", "rootpath", "")
		uconfig.set("renderhandler", "refreshtime", "5")
		uconfig.set("renderhandler", "loglimit", "500")
		uconfig.set("renderhandler", "showcoordinator", "False")
		uconfig.set("renderhandler", "autoupdate", "True")
		uconfig.set("renderhandler", "windowsize", "")
		uconfig.set("dccoverrides", "maxoverride", "False")
		uconfig.set("dccoverrides", "mayaoverride", "False")
		uconfig.set("dccoverrides", "houdinioverride", "False")
		uconfig.set("dccoverrides", "blenderoverride", "False")
		uconfig.set("dccoverrides", "maxpath", maxpath)
		uconfig.set("dccoverrides", "mayapath", mayapath)
		uconfig.set("dccoverrides", "houdinipath", houpath)
		uconfig.set("dccoverrides", "blenderpath", bldpath)

		oldIni = os.getenv('LocalAppdata') + "\\Pandora\\Config\\PandoraOLD.ini"

		# check if an old ini file exists and if yes, copy the values to the new ini
		if os.path.exists(oldIni):
			oconfig = ConfigParser()
			oconfig.read(oldIni)
			for i in oconfig.sections():
				for k in oconfig.options(i):
					if uconfig.has_option(i, k) or i in ["lastusedsettings"]:
						uconfig.set(i, k, oconfig.get(i, k))

		with open(self.configPath, 'w') as inifile:
			uconfig.write(inifile)

		try:
			os.remove(oldIni)
		except:
			pass


	@err_decorator
	def parentWindow(self, win):
		if self.app == 4:
			return

		win.setParent(self.messageParent, Qt.Window)


	@err_decorator
	def getMaxPath(self):
		try:
			try:
				key = _winreg.OpenKey(
					_winreg.HKEY_LOCAL_MACHINE,
					"SOFTWARE\\Autodesk\\3dsMax\\21.0",
					0,
					_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
				)

				installDir = (_winreg.QueryValueEx(key, "Installdir"))[0]
			except:
				try:
					key = _winreg.OpenKey(
						_winreg.HKEY_LOCAL_MACHINE,
						"SOFTWARE\\Autodesk\\3dsMax\\20.0",
						0,
						_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
					)

					installDir = (_winreg.QueryValueEx(key, "Installdir"))[0]
				except:
					key = _winreg.OpenKey(
						_winreg.HKEY_LOCAL_MACHINE,
						"SOFTWARE\\Autodesk\\3dsMax\\19.0",
						0,
						_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
					)

					installDir = (_winreg.QueryValueEx(key, "Installdir"))[0]

			maxExe = os.path.join(installDir, "3dsmaxcmd.exe")
			if os.path.exists(maxExe):
				return maxExe
			else:
				return ""
		except:
			return ""


	@err_decorator
	def getMayaPath(self):
		try:
			key = _winreg.OpenKey(
					_winreg.HKEY_LOCAL_MACHINE,
					"SOFTWARE\\Autodesk\\Maya",
					0,
					_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			mayaVersions = []
			try:
				i = 0
				while True:
					mayaVers = _winreg.EnumKey(key, i)
					if unicode(mayaVers).isnumeric():
						mayaVersions.append(mayaVers)
					i += 1
			except WindowsError:
				pass

			validVersion = mayaVersions[-1]

			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Autodesk\\Maya\\%s\\Setup\\InstallPath" % validVersion,
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			installDir = (_winreg.QueryValueEx(key, "MAYA_INSTALL_LOCATION"))[0]

			mayaExe = os.path.join(installDir, "bin", "Render.exe")
			if os.path.exists(mayaExe):
				return mayaExe
			else:
				return ""

		except Exception as e:
			return ""


	@err_decorator
	def getHoudiniPath(self):
		try:
			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Side Effects Software",
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)
			
			validVersion = (_winreg.QueryValueEx(key, "ActiveVersion"))[0]

			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Side Effects Software\\Houdini " + validVersion,
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			installDir = (_winreg.QueryValueEx(key, "InstallPath"))[0]

			if os.path.exists(installDir):
				return installDir
			else:
				return ""

		except Exception as e:
			return ""


	@err_decorator
	def getBlenderPath(self):
		try:
			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Classes\\blendfile\\shell\\open\\command",
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)
			blenderPath = (_winreg.QueryValueEx(key, "" ))[0].split(" \"%1\"")[0].replace("\"", "")

			if os.path.exists(blenderPath):
				return blenderPath
			else:
				return ""

		except:
			return ""


	@err_decorator
	def showAbout(self):
		msg = QMessageBox(QMessageBox.Information, "About", "Pandora: %s\n\nCopyright (C) 2016-2018 Richard Frangenberg\nLicense: GNU GPL-3.0-or-later\n\nhttps://prism-pipeline.com/pandora/" % (self.version), parent=self.messageParent)
		msg.addButton("Ok", QMessageBox.YesRole)
		
		msg.setFocus()
		action = msg.exec_()

		if action == 1:
			self.updateProject()


	@err_decorator
	def sendFeedback(self):
		fbDlg = PandoraEnterText.PandoraEnterText()
		fbDlg.setModal(True)
		self.parentWindow(fbDlg)
		fbDlg.setWindowTitle("Send Message")
		fbDlg.l_info.setText("Message for the developer:\nYou may want to provide contact information (e.g. e-mail) for further discussions.")
		fbDlg.buttonBox.buttons()[0].setText("Send")
		result = fbDlg.exec_()

		if result == 1:
			self.sendEmail(fbDlg.te_text.toPlainText(), subject="Pandora feedback")


	def openWebsite(self, location):
		if location == "home":
			url = "https://prism-pipeline.com/pandora/"
		else:
			return
			
		import webbrowser
		webbrowser.open(url)


	@err_decorator
	def openSubmitter(self):
		if not self.validateUser():
			self.changeUser()

		if not hasattr(self, "user"):
			return

		if not os.path.exists(self.configPath):
			self.core.createUserPrefs()

		try:
			self.ps.close()
		except:
			pass

		try:
			del sys.modules["PandoraSubmitter"]
		except:
			pass

		try:
			import PandoraSubmitter
		except:
			modPath = imp.find_module("PandoraSubmitter")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import PandoraSubmitter

		self.ps = PandoraSubmitter.PandoraSubmitter(core = self)
		self.ps.show()


	@err_decorator
	def openRenderHandler(self):
		if not os.path.exists(self.configPath):
			self.core.createUserPrefs()

		try:
			self.prh.close()
		except:
			pass

		try:
			del sys.modules["PandoraRenderHandler"]
		except:
			pass

		try:
			import PandoraRenderHandler
		except:
			modPath = imp.find_module("PandoraRenderHandler")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import PandoraRenderHandler

		self.prh = PandoraRenderHandler.RenderHandler(core = self)
		self.prh.show()


	@err_decorator
	def openSettings(self):
		if not os.path.exists(self.configPath):
			self.core.createUserPrefs()

		try:
			self.pset.close()
		except:
			pass

		try:
			del sys.modules["PandoraSettings"]
		except:
			pass

		try:
			import PandoraSettings
		except:
			modPath = imp.find_module("PandoraSettings")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import PandoraSettings

		self.pset = PandoraSettings.PandoraSettings(core = self)
		self.pset.show()


	@err_decorator
	def validateUser(self):		
		uname = self.getConfig("submissions", "username")
		if uname is None:
			return False

		self.user = uname

		return True


	@err_decorator
	def changeUser(self):
		try:
			del sys.modules["PandoraChangeUser"]
		except:
			pass

		try:
			import PandoraChangeUser
		except:
			modPath = imp.find_module("PandoraChangeUser")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import PandoraChangeUser

		self.cu = PandoraChangeUser.PandoraChangeUser(core = self)
		self.cu.setModal(True)
		self.parentWindow(self.cu)

		result = self.cu.exec_()


	@err_decorator
	def executeMaxScript(self, code, returnVal=True):
		if self.app == 1:
			val = MaxPlus.Core.EvalMAXScript(code)

			if returnVal:
				try:
					return val.Get()
				except:
					return None
		else:
			return "Not called in 3ds Max"


	@err_decorator
	def executeHouPython(self, code):
		if self.app == 2:
			return eval(code)
		else:
			return "Not called in Houdini"


	@err_decorator
	def executeMayaPython(self, code, execute = False, logErr=True):
		if self.app == 3:
			if logErr:
				if not execute:
					return eval(code)
				else:
					exec(code)
			else:
				try:
					if not execute:
						return eval(code)
					else:
						exec(code)
				except:
					pass
		else:
			return "Not called in Maya"


	@err_decorator
	def executeBldPython(self, code):
		if self.app == 6:
			return eval(code)
		else:
			return "Not called in Blender"


	@err_decorator
	def getConfig(self, cat, param, ptype="string"):
		pConfig = ConfigParser()
		try:
			pConfig.read(self.configPath)
		except:
			warnStr = "The Pandora preferences file seems to be corrupt.\n\nIt will be reset, which means all local Pandora settings will fall back to their defaults."
			msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()
			self.createUserPrefs()
			pConfig.read(self.configPath)

		if pConfig.has_option(cat, param):
			if ptype == "string":
				return pConfig.get(cat, param)
			elif ptype == "bool":
				return pConfig.getboolean(cat, param)
		else:
			return None


	@err_decorator
	def setConfig(self, cat, param, val):
		pConfig = ConfigParser()
		pConfig.read(self.configPath)

		if not pConfig.has_section(cat):
			pConfig.add_section(cat)

		pConfig.set(cat, param, str(val))

		with open(self.configPath, 'w') as inifile:
			pConfig.write(inifile)


	@err_decorator
	def validateStr(self, text, allowChars=[], denyChars=[]):
		invalidChars = [" ", "\\", "/", ":", "*", "?", "\"", "<", ">", "|", "_", "ä", "ö", "ü", "ß"]
		for i in allowChars:
			if i in invalidChars:
				invalidChars.remove(i)

		for i in denyChars:
			if i not in invalidChars:
				invalidChars.append(i)

		if pVersion == 2:
			validText = ("".join(ch for ch in str(text.encode("ascii", errors="ignore")) if ch not in invalidChars))
		else:
			validText = ("".join(ch for ch in str(text.encode("ascii", errors="ignore").decode()) if ch not in invalidChars))

		return validText


	@err_decorator
	def getCurrentFileName(self, path=True):
		if self.app == 1:
			if path:
				currentFileName = MaxPlus.FileManager.GetFileNameAndPath()
			else:
				currentFileName = MaxPlus.FileManager.GetFileName()
		elif self.app == 2:
			currentFileName = hou.hipFile.path()
		elif self.app == 3:
			if path:
				currentFileName = cmds.file( q=True, sceneName=True )
			else:
				currentFileName = cmds.file( q=True, sceneName=True, shortName=True)
		elif self.app == 4:
			currentFileName = ""
		elif self.app == 6:
			currentFileName = bpy.data.filepath

			if not path:
				currentFileName = os.path.basename(currentFileName)

		currentFileName = self.fixPath(currentFileName)

		return currentFileName


	@err_decorator
	def saveScene(self):
		if not self.validateUser():
			self.changeUser()

		if not hasattr(self, "user"):
			return False

		curfile = self.getCurrentFileName()
		filepath = curfile.replace("\\","/")

		if self.app == 1:
			result = self.executeMaxScript("saveMaxFile \"%s\"" % filepath)
		elif self.app == 2:
			result = hou.hipFile.save(file_name=filepath, save_to_recent_files=True)
		elif self.app == 3:
			cmds.file(rename=filepath)
			try:
				result = cmds.file(save=True)
			except:
				return False
		elif self.app == 6:
			bpy.ops.wm.save_as_mainfile(filepath=filepath)

		return True


	@err_decorator
	def fixPath(self, path):
		if platform.system() == "Windows":
			path = path.replace("/","\\")
		else:
			path = path.replace("\\","/")

		return path


	@err_decorator
	def openFolder(self, path):
		path = self.fixPath(path)

		if os.path.isfile(path):
			path = os.path.dirname(path)

		if platform.system() == "Windows":
			cmd = ['explorer', path]
		else:
			cmd = ["xdg-open", "%s" % path]

		if os.path.exists(path):
			subprocess.call(cmd)


	@err_decorator
	def copyToClipboard(self, text, fixSlashes=True):
		if fixSlashes:
			text = self.fixPath(text)

		cb = qApp.clipboard()
		cb.setText(text)


	@err_decorator
	def getFrameRange(self):
		startframe = 0
		endframe = 0

		if self.app == 1:
			startframe = self.executeMaxScript("animationrange.start.frame")
			endframe = self.executeMaxScript("animationrange.end.frame")
		elif self.app == 2:
			startframe = self.executeHouPython("hou.playbar.playbackRange()[0]")
			endframe = self.executeHouPython("hou.playbar.playbackRange()[1]")
		elif self.app == 3:
			startframe = self.executeMayaPython("cmds.playbackOptions(q=True, minTime=True)")
			endframe = self.executeMayaPython("cmds.playbackOptions(q=True, maxTime=True)")
		elif self.app == 6:
			startframe = self.executeBldPython("bpy.context.scene.frame_start")
			endframe = self.executeBldPython("bpy.context.scene.frame_end")

		return [startframe, endframe]


	@err_decorator
	def sendEmail(self, text, subject="Pandora Error"):
		waitmsg = QMessageBox(QMessageBox.NoIcon, "Sending message", "Sending - please wait..", QMessageBox.Cancel)
		self.parentWindow(waitmsg)
		waitmsg.buttons()[0].setHidden(True)
		waitmsg.show()
		QCoreApplication.processEvents()

		try:
			pStr = """
try:
	import os, sys

	pyLibs = os.path.join('%s', 'PythonLibs', 'Python27')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	from robobrowser import RoboBrowser

	browser = RoboBrowser(parser='html.parser')
	browser.open('https://prism-pipeline.com/contact/')

	signup_form = browser.get_forms()[1]

	signup_form['your-name'].value = 'PandoraMessage'
	signup_form['your-subject'].value = '%s'
	signup_form['your-message'].value = '''%s'''

	signup_form.serialize()

	browser.submit_form(signup_form)
	response = str(browser.parsed)

	if 'Thank you for your message. It has been sent.' in response:
		sys.stdout.write('success')
	else:
	   	sys.stdout.write('failed')
except Exception as e:
	sys.stdout.write('failed %%s' %% e)
""" % (self.pandoraRoot, self.pandoraRoot, subject, text)

			result = subprocess.Popen("%s -c \"%s\"" % (os.path.join(self.pandoraRoot, "Python27", "pythonw.exe"), pStr), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			stdOutData, stderrdata = result.communicate()

			if not "success" in str(stdOutData):
				try:
					import smtplib

					from email.mime.text import MIMEText

					msg = MIMEText(text)

					msg['Subject'] = subject
					msg['From'] = "vfxpipemail@gmail.com"
					msg['To'] = "contact@prism-pipeline.com"

					s = smtplib.SMTP('smtp.gmail.com:587')
					s.ehlo()
					s.starttls()
					s.login("vfxpipemail@gmail.com", "vfxpipeline")
					s.sendmail("vfxpipemail@gmail.com", "contact@prism-pipeline.com", msg.as_string())
					s.quit()
				except:
			   		raise WindowsError(stdOutData)

			msg = QMessageBox(QMessageBox.Information, "Information", "Sent message successfully.", QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()

		except Exception as e:
			mailDlg = QDialog()

			mailDlg.setWindowTitle("Sending message failed.")
			l_info = QLabel("The message couldn't be sent. Maybe there is a problem with the internet connection or the connection was blocked by a firewall.\n\nPlease send an e-mail with the following text to contact@prism-pipeline.com")

			exc_type, exc_obj, exc_tb = sys.exc_info()

			messageStr = "%s - %s - %s - %s\n\n%s" % (str(e), exc_type, exc_tb.tb_lineno, traceback.format_exc(), text)
			messageStr = "<pre>%s</pre>" % messageStr.replace("\n", "<br />").replace("\t", "    ")
			l_warnings = QTextEdit(messageStr)
			l_warnings.setReadOnly(True)
			l_warnings.setAlignment(Qt.AlignTop)

			sa_warns = QScrollArea()
			sa_warns.setWidget(l_warnings)
			sa_warns.setWidgetResizable(True)
		
			bb_warn = QDialogButtonBox()

			bb_warn.addButton("Retry", QDialogButtonBox.AcceptRole)
			bb_warn.addButton("Ok", QDialogButtonBox.RejectRole)

			bb_warn.accepted.connect(mailDlg.accept)
			bb_warn.rejected.connect(mailDlg.reject)

			bLayout = QVBoxLayout()
			bLayout.addWidget(l_info)
			bLayout.addWidget(sa_warns)
			bLayout.addWidget(bb_warn)
			mailDlg.setLayout(bLayout)
			mailDlg.setParent(self.messageParent, Qt.Window)
			mailDlg.resize(750,500)

			action = mailDlg.exec_()

			if action == 1:
				self.sendEmail(text, subject)			


		if "waitmsg" in locals() and waitmsg.isVisible():
			waitmsg.close()


	@err_decorator
	def checkPandoraVersion(self):
		pStr = """
try:
	import os, sys

	pyLibs = os.path.join('%s', 'PythonLibs', 'Python27')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	import requests
	page = requests.get('https://prism-pipeline.com/downloads/')

	cStr = page.content
	vCode = 'Latest version: ['
	latestVersionStr = cStr[cStr.find(vCode)+len(vCode): cStr.find(']', cStr.find('Latest version: ['))]

	sys.stdout.write(latestVersionStr)

except Exception as e:
	sys.stdout.write('failed %%s' %% e)
""" % (self.pandoraRoot, self.pandoraRoot)

		result = subprocess.Popen("%s -c \"%s\"" % (os.path.join(self.pandoraRoot, "Python27", "pythonw.exe"), pStr), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdOutData, stderrdata = result.communicate()

		if "failed" in str(stdOutData) or len(str(stdOutData).split(".")) < 3:
			msg = QMessageBox(QMessageBox.Information, "Pandora", "Unable to connect to www.prism-pipeline.com. Could not check for updates.", QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()
			return

		if pVersion == 3:
			stdOutData = stdOutData.decode("utf-8")

		latestVersion = str(stdOutData).split(".")
		latestVersion = [int(str(x)) for x in latestVersion]

		coreversion = self.version[1:].split(".")
		curVersion = [int(x) for x in coreversion]

		if curVersion[0] < latestVersion[0] or (curVersion[0] == latestVersion[0] and curVersion[1] < latestVersion[1]) or (curVersion[0] == latestVersion[0] and curVersion[1] == latestVersion[1] and curVersion[2] < latestVersion[2]):
			msg = QMessageBox(QMessageBox.Information, "Pandora", "A newer version of Pandora is available.\n\nInstalled version:\t%s\nLatest version:\t\tv%s" % (self.version, stdOutData), QMessageBox.Ok, parent=self.messageParent)
			msg.addButton("Go to downloads page", QMessageBox.YesRole)
			msg.setFocus()
			action = msg.exec_()

			if action == 0:
				self.openWebsite("downloads")

		else:
			msg = QMessageBox(QMessageBox.Information, "Pandora", "The latest version of Pandora is already installed. (%s)" % self.version, QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()


	def writeErrorLog(self, text):
		try:

			ptext = "An unknown Pandora error occured.\nThe error was logged.\nIf you want to help improve Pandora, please send this error to the developer.\n\nYou can contact the pipeline administrator or the developer, if you have any questions on this.\n\n"
		#	print (text)

			text += "\n\n"

			userErPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ErrorLog_%s.txt" % socket.gethostname())

			try:
				open(userErPath, 'a').close()
			except:
				pass

			if os.path.exists(userErPath):
				with open(userErPath, "a") as erLog:
					erLog.write(text)

			msg = QDialog()

			msg.setWindowTitle("Error")
			l_info = QLabel(ptext)

			b_show = QPushButton("Show error message")
			b_send = QPushButton("Send to developer (anonymously)...")
			b_ok = QPushButton("Close")

			w_versions = QWidget()
			lay_versions = QHBoxLayout()
			lay_versions.addWidget(b_show)
			lay_versions.addWidget(b_send)
			lay_versions.addWidget(b_ok)
			lay_versions.setContentsMargins(0,10,10,10)
			w_versions.setLayout(lay_versions)

			bLayout = QVBoxLayout()
			bLayout.addWidget(l_info)
			bLayout.addWidget(w_versions)
			bLayout.addStretch()
			msg.setLayout(bLayout)
			msg.setParent(self.messageParent, Qt.Window)
			msg.setFocus()

			b_show.clicked.connect(lambda: QMessageBox.warning(self.messageParent, "Warning", text))
			b_send.clicked.connect(lambda: self.sendError(text))
			b_send.clicked.connect(msg.accept)
			b_ok.clicked.connect(msg.accept)

			action = msg.exec_()
			
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			print ("ERROR - writeErrorLog - %s - %s - %s\n\n" % (str(e), exc_type, exc_tb.tb_lineno))


	def sendError(self, errorText):
		msg = QDialog()

		dtext = "The technical error description will be sent, but you can add additional information to this message if you like.\nFor example how to reproduce the problem or your e-mail for further discussions and to get notified when the problem is fixed.\n"
		ptext = "Additional information (optional):"

		msg.setWindowTitle("Send error")
		l_description = QLabel(dtext)
		l_info = QLabel(ptext)
		te_info = QTextEdit()

		b_send = QPushButton("Send to developer (anonymously)")
		b_ok = QPushButton("Close")

		w_versions = QWidget()
		lay_versions = QHBoxLayout()
		lay_versions.addWidget(b_send)
		lay_versions.addWidget(b_ok)
		lay_versions.setContentsMargins(0,10,10,10)
		w_versions.setLayout(lay_versions)

		bLayout = QVBoxLayout()
		bLayout.addWidget(l_description)
		bLayout.addWidget(l_info)
		bLayout.addWidget(te_info)
		bLayout.addWidget(w_versions)
		bLayout.addStretch()
		msg.setLayout(bLayout)
		msg.setParent(self.messageParent, Qt.Window)
		msg.setFocus()

		b_send.clicked.connect(lambda: self.sendEmail("%s\n\n\n%s" % (te_info.toPlainText(), errorText)))
		b_send.clicked.connect(msg.accept)
		b_ok.clicked.connect(msg.accept)

		action = msg.exec_()
