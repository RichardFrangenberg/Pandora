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

import sys, os, threading, shutil, time, socket, traceback, imp, platform, json, random, string, errno, stat

#check if python 2 or python 3 is used
if sys.version[0] == "3":
	import winreg as _winreg
	pVersion = 3
else:
	import _winreg
	pVersion = 2

from functools import wraps
import subprocess


# Pandora core class, which holds various functions
class PandoraCore():
	def __init__(self, app="Standalone"):
		try:
			# set some general variables
			self.version = "v1.0.1.0"
			self.pandoraRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

			# add the custom python libraries to the path variable, so they can be imported
			if pVersion == 2:
				pyLibs = os.path.join(self.pandoraRoot, "PythonLibs", "Python27")
			else:
				pyLibs = os.path.join(self.pandoraRoot, "PythonLibs", "Python35")
				QCoreApplication.addLibraryPath(os.path.join(self.pandoraRoot, "PythonLibs", "Python35", "PySide2", "plugins"))
				
			cpLibs = os.path.join(self.pandoraRoot, "PythonLibs", "CrossPlatform")
			win32Libs = os.path.join(cpLibs, "win32")
			self.pluginPathApp = os.path.join(self.pandoraRoot, "Plugins", "Apps")
			self.pluginPathCustom = os.path.join(self.pandoraRoot, "Plugins", "Custom")
			self.pluginDirs = [self.pluginPathApp, self.pluginPathCustom]

			for i in [cpLibs, pyLibs, win32Libs] + self.pluginDirs:
				if i not in sys.path:
					sys.path.append(i)				

			if platform.system() == "Windows":
				self.configPath = os.path.join(os.environ["userprofile"], "Documents", "Pandora", "Pandora.json")
				self.installLocPath = os.path.join(os.environ["userprofile"], "Documents", "Pandora", "InstallLocations.json")

			self.parentWindows = True

			# if no user config exists, it will be created with default values
			if not os.path.exists(self.configPath):
				self.createUserPrefs()

			self.updatePlugins(app)

			if sys.argv[-1] == "setupStartMenu":
				self.setupStartMenu()
				sys.exit()
			elif sys.argv[-1] == "setupCoordinator":
				self.setupCoordinator()
				sys.exit()
			elif sys.argv[-1] == "setupRenderslave":
				self.setupRenderslave()
				sys.exit()

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
	def updatePlugins(self, current):
		self.unloadedAppPlugins = []
		self.customPlugins = {}
		customPlugins = []

		for k in self.pluginDirs:
			if not os.path.exists(k):
				continue

			for i in os.listdir(k):
				initmodule = "Pandora_%s_init" % i
				initPath = os.path.join(k, i, "Scripts", initmodule + ".py")
				if i == current or not (os.path.exists(initPath) or os.path.exists(initPath.replace("_init", "_init_unloaded"))):
					continue

				sys.path.append(os.path.dirname(initPath))
				pPlug = getattr(__import__("Pandora_%s_init_unloaded" % (i)), "Pandora_%s_unloaded" % i)(self)
				if platform.system() in pPlug.platforms:
					if pPlug.pluginType in ["App"]:
						self.unloadedAppPlugins.append(pPlug)
					elif pPlug.pluginType in ["Custom"]:
						customPlugins.append(pPlug)
	
		sys.path.append(os.path.join(self.pluginPathApp, current, "Scripts"))
		self.appPlugin = getattr(__import__("Pandora_%s_init" % current), "Pandora_Plugin_%s" % current)(self)

		if not self.appPlugin:
			QMessageBox.critical(QWidget(), "Pandora Error", "Pandora could not initialize correctly and may not work correctly in this session.")
			return

		for i in customPlugins:
			self.customPlugins[i.pluginName] = i

		if not self.appPlugin.hasQtParent:
			self.messageParent = QWidget()
			self.parentWindows = False
			if self.appPlugin.pluginName != "Standalone":
				self.messageParent.setWindowFlags(self.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint)

		if self.appPlugin.pluginName != "Standalone":
			self.maxwait = 20
			self.elapsed = 0
			self.timer = QTimer()
			result = self.startup()
			if result == False:
				self.timer.timeout.connect(self.startup)
				self.timer.start(1000)
		else:
			self.startup()


	@err_decorator
	def getPluginNames(self):
		pluginNames = [x.pluginName for x in self.unloadedAppPlugins]
		pluginNames.append(self.appPlugin.pluginName)

		return sorted(pluginNames)


	@err_decorator
	def getPluginData(self, pluginName, data):
		if pluginName == self.appPlugin.pluginName:
			return getattr(self.appPlugin, data, None)
		else:
			for i in self.unloadedAppPlugins:
				if i.pluginName == pluginName:
					return getattr(i, data, None)

		return None


	@err_decorator
	def getPlugin(self, pluginName):
		if pluginName == self.appPlugin.pluginName:
			return self.appPlugin
		else:
			for i in self.unloadedAppPlugins:
				if i.pluginName == pluginName:
					return i

		return None


	@err_decorator
	def integrationAdded(self, appName, path):
		path = self.fixPath(path)
		items = self.getConfig(configPath=self.installLocPath, cat=appName, getItems=True)
		if path in items.values():
			return

		self.setConfig(configPath=self.installLocPath, cat=appName, param="%02d" % (len(items)+1), val=path)


	@err_decorator
	def integrationRemoved(self, appName, path):
		path = self.fixPath(path)
		options = self.getConfig(cat=appName, configPath=self.installLocPath, getItems=True)
		cData = []
		for i in sorted(options):
			cData.append([appName, i, ""])

		self.setConfig(configPath=self.installLocPath, data=cData, delete=True)

		cData = []
		for idx, i in enumerate(sorted(options)):
			if self.fixPath(options[i]) == path:
				continue

			cData.append([appName, "%02d" % (idx+1), options[i]])

		self.setConfig(configPath=self.installLocPath, data=cData)


	@err_decorator
	def setupStartMenu(self):
		if self.appPlugin.pluginName == "Standalone":
			self.appPlugin.createWinStartMenu(self)
			#QMessageBox.information(self.messageParent, "Pandora", "Successfully added start menu entries.")


	@err_decorator
	def setupCoordinator(self):
		if self.appPlugin.pluginName == "Standalone":
			self.setConfig("coordinator", "enabled", True)
			self.startCoordinator(restart=True)
			#QMessageBox.information(self.messageParent, "Pandora", "Successfully setup coordinator.")

			startupPath = os.getenv('APPDATA') + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\"
			coordStartup = startupPath + "PandoraCoordinator.lnk"

			if os.path.exists(coordStartup):
				os.remove(coordStartup)

			if not os.path.exists(coordStartup):
				cPath = os.path.join(self.pandoraRoot, "Tools", "PandoraCoordinator.lnk")
				shutil.copy2(cPath, coordStartup)


	@err_decorator
	def setupRenderslave(self):
		if self.appPlugin.pluginName == "Standalone":
			self.setConfig("slave", "enabled", True)
			self.startRenderSlave(newProc=True, restart=True)
			#QMessageBox.information(self.messageParent, "Pandora", "Successfully setup renderslave.")

			startupPath = os.getenv('APPDATA') + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\"
			slaveStartup = startupPath + "PandoraSlave.lnk"

			if os.path.exists(slaveStartup):
				os.remove(slaveStartup)

			if not os.path.exists(slaveStartup):
				cPath = os.path.join(self.pandoraRoot, "Tools", "PandoraSlave.lnk")
				shutil.copy2(cPath, slaveStartup)


	@err_decorator
	def startup(self):
		if self.appPlugin.hasQtParent:
			self.elapsed += 1
			if self.elapsed > self.maxwait:
				self.timer.stop()

		result = self.appPlugin.startup(self)

		if result is not None:
			return result


	@err_decorator
	def callback(self, name="", types=["custom"], args=[], kwargs={}):
		if "curApp" in types:
			getattr(self.appPlugin, name, lambda *args, **kwargs: None)(*args, **kwargs)

		if "unloadedApps" in types:
			for i in self.unloadedAppPlugins:
				getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)

		if "custom" in types:
			for i in self.customPlugins.values():
				getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)


	@err_decorator
	def createUserPrefs(self):
		if os.path.exists(self.configPath):
			try:
				os.remove(self.configPath)
			except:
				pass

		from win32com.shell import shell, shellcon
		cRoot = os.path.join(shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0), "Pandora", "Root")
		wsPath = os.path.join(cRoot, "Workstations", "WS_" + socket.gethostname())
		sPath = os.path.join(cRoot, "Slaves", "S_" + socket.gethostname())
		localRep = os.path.join(shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0), "PandoraRepository")

		if not os.path.exists(os.path.dirname(self.configPath)):
			os.makedirs(os.path.dirname(self.configPath))

		uconfig = {
			"globals": {
				"localMode": True,
				"rootPath": cRoot,
				"repositoryPath": localRep
			},
			"submissions": {
				"submissionPath": wsPath,
				"userName": ""
			},
			"slave": {
				"enabled": False,
				"slavePath": sPath
			},
			"coordinator": {
				"enabled": False,
				"rootPath": cRoot
			},
			"renderHandler": {
				"refreshTime": 5,
				"logLimit": 500,
				"showCoordinator": True,
				"autoUpdate": True,
				"windowSize": ""
			},
			"dccoverrides": {
			},
			"lastUsedSettings": {
			}

		}

		with open(self.configPath, 'w') as confFile:
			json.dump(uconfig, confFile, indent=4)


	@err_decorator
	def parentWindow(self, win):
		if not self.appPlugin.hasQtParent:
			if self.appPlugin.pluginName != "Standalone":
				win.setWindowFlags(win.windowFlags() ^ Qt.WindowStaysOnTopHint)
	
		if not self.parentWindows:
			return
			
		win.setParent(self.messageParent, Qt.Window)


	@err_decorator
	def showAbout(self):
		QMessageBox.information(self.messageParent, "About", "Pandora: %s\n\nCopyright (C) 2016-2018 Richard Frangenberg\nLicense: GNU GPL-3.0-or-later\n\nhttps://prism-pipeline.com/pandora/" % (self.version))


	@err_decorator
	def sendFeedback(self):
		msg = QDialog()

		dtext = "Message for the developer:\nYou may want to provide contact information (e.g. e-mail) for further discussions."

		msg.setWindowTitle("Send Message")
		l_description = QLabel(dtext)
		te_info = QTextEdit()

		b_send = QPushButton("Send")
		b_ok = QPushButton("Close")

		w_versions = QWidget()
		lay_versions = QHBoxLayout()
		lay_versions.addWidget(b_send)
		lay_versions.addWidget(b_ok)
		lay_versions.setContentsMargins(0,10,10,10)
		w_versions.setLayout(lay_versions)

		bLayout = QVBoxLayout()
		bLayout.addWidget(l_description)
		bLayout.addWidget(te_info)
		bLayout.addWidget(w_versions)
		bLayout.addStretch()
		msg.setLayout(bLayout)
		self.parentWindow(msg)

		b_send.clicked.connect(lambda: self.sendEmail(te_info.toPlainText(), subject="Pandora feedback"))
		b_send.clicked.connect(msg.accept)
		b_ok.clicked.connect(msg.accept)

		action = msg.exec_()


	def openWebsite(self, url):
		if url == "home":
			url = "https://prism-pipeline.com/pandora/"
			
		import webbrowser
		webbrowser.open(url)


	@err_decorator
	def openSubmitter(self):
		if hasattr(self, "ps") and self.ps.isVisible():
			self.ps.close()

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
		if hasattr(self, "RenderHandler") and self.RenderHandler.isVisible():
			self.RenderHandler.close()

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

		self.RenderHandler = PandoraRenderHandler.RenderHandler(core = self)
		self.RenderHandler.show()


	@err_decorator
	def openSettings(self):
		if hasattr(self, "pset") and self.pset.isVisible():
			self.pset.close()

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
	def openInstaller(self, uninstall=False):
		if hasattr(self, "pinst") and self.pinst.isVisible():
			self.pinst.close()

		try:
			del sys.modules["PandoraInstaller"]
		except:
			pass

		try:
			import PandoraInstaller
		except:
			modPath = imp.find_module("PandoraInstaller")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import PandoraInstaller

		self.pinst = PandoraInstaller.PandoraInstaller(core=self, uninstall=uninstall)
		if not uninstall:
			self.pinst.show()


	@err_decorator
	def startRenderSlave(self, newProc=False, restart=False):
		if newProc:
			slavePath = os.path.join(self.pandoraRoot, "Scripts", "PandoraSlave.py")
			pythonPath = os.path.join(self.pandoraRoot, "Python27", "PandoraSlave.exe")
			for i in [slavePath, pythonPath]:
				if not os.path.exists(i):
					QMessageBox.warning(self.messageParent, "Script missing", "%s does not exist." % os.path.basename(i))
					return None

			command = ['%s' % pythonPath, '%s' % slavePath]
			if restart:
				command.append("forcestart")

			subprocess.Popen(command)

		else:
			if hasattr(self, "RenderSlave") or self.appPlugin.pluginName != "Standalone":
				return

			import PandoraSlave

			self.RenderSlave = PandoraSlave.SlaveLogic(core=self)


	@err_decorator
	def stopRenderSlave(self):
		cData = {}
		cData["localMode"] = ["globals", "localMode"]
		cData["rootPath"] = ["globals", "rootPath"]
		cData["slavePath"] = ["slave", "slavePath"]
		cData = self.getConfig(data=cData)

		if cData["localMode"] == True:
			slavepath = os.path.join(cData["rootPath"], "Slaves", "S_" + socket.gethostname())
		else:
			slavepath = cData["slavePath"]

		if slavepath is None:
			return

		if not os.path.exists(slavepath):
			try:
				os.makedirs(slavepath)
			except:
				return

		cmd = ["exitSlave"]

		cmdDir = os.path.join(slavepath, "Communication")
		curNum = 1

		for i in os.listdir(cmdDir):
			if not i.startswith("slaveIn_"):
				continue
		
			num = i.split("_")[1]
			if not unicode(num).isnumeric():
				continue

			if int(num) >= curNum:
				curNum = int(num) + 1

		cmdFile = os.path.join(cmdDir, "slaveIn_%s_%s.txt" % (format(curNum, '04'), time.time()))

		with open(cmdFile, 'w') as cFile:
			cFile.write(str(cmd))


	@err_decorator
	def startCoordinator(self, restart=False):
		coordProc = []
		import psutil

		for x in psutil.pids():
			try:
				if os.path.basename(psutil.Process(x).exe()) == "PandoraCoordinator.exe":
					coordProc.append(x)
			except:
				pass

		if len(coordProc) > 0:
			if restart:
				for pid in coordProc:
					proc = psutil.Process(pid)
					proc.kill()
			else:
				QMessageBox.information(self.messageParent, "PandoraCoordinator", "PandoraCoordinator is already running.")
				return

		coordPath = os.path.join(self.pandoraRoot, "Scripts", "PandoraCoordinator.py")
		pythonPath = os.path.join(self.pandoraRoot, "Python27", "PandoraCoordinator.exe")
		for i in [coordPath, pythonPath]:
			if not os.path.exists(i):
				QMessageBox.warning(self.messageParent, "Script missing", "%s does not exist." % os.path.basename(i))
				return None

		command = ['%s' % pythonPath, '%s' % coordPath]
		subprocess.Popen(command)


	@err_decorator
	def stopCoordinator(self):
		cData = {}
		cData["localMode"] = ["globals", "localMode"]
		cData["rootPath"] = ["globals", "rootPath"]
		cData["slavePath"] = ["coordinator", "rootPath"]
		cData = self.getConfig(data=cData)

		if cData["localMode"] == True:
			coordRoot = cData["rootPath"]
		else:
			coordRoot = cData["slavePath"]
		
		if coordRoot is None:
			return

		if not os.path.exists(coordRoot):
			try:
				os.makedirs(coordRoot)
			except:
				return

		coordBasePath = os.path.join(coordRoot, "Scripts", "PandoraCoordinator")

		if not os.path.exists(coordBasePath):
			os.makedirs(coordBasePath)

		cmdPath = os.path.join(coordBasePath, "command.txt")

		with open(cmdPath, "w") as cmdFile:
			cmdFile.write("exit")


	@err_decorator
	def startTray(self, silent=False):
		if hasattr(self, "PandoraTray") or self.appPlugin.pluginName != "Standalone":
			return

		import PandoraTray

		self.PandoraTray = PandoraTray.PandoraTray(core=self, silent=silent)


	@err_decorator
	def getConfig(self, cat=None, param=None, data=None, configPath=None, getOptions=False, getItems=False, getConf=False):
		if configPath is None:
			configPath = self.configPath

		if configPath is None or configPath == "":
			return
			
		isUserConf = configPath == self.configPath

		if isUserConf and not os.path.exists(configPath):
			self.createUserPrefs()

		if not os.path.exists(os.path.dirname(configPath)):
			return

		if len([x for x in os.listdir(os.path.dirname(configPath)) if x.startswith(os.path.basename(configPath) + ".bak")]):
			self.restoreConfig(configPath)

		userConfig = {}

		try:
			if os.path.exists(configPath):
				with open(configPath, 'r') as f:
					userConfig = json.load(f)
		except:
			if isUserConf:
				warnStr = "The Pandora preferences file seems to be corrupt.\n\nIt will be reset, which means all local Pandora settings will fall back to their defaults."
			else:
				warnStr = "Cannot read the following file:\n\n%s" % configPath
				
			msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.messageParent)
			action = msg.exec_()

			if isUserConf:
				self.createUserPrefs()
				with open(configPath, 'r') as f:
					userConfig = json.load(f)

		if getConf:
			return userConfig

		if getOptions:
			if cat in userConfig:
				return userConfig[cat].keys()
			else:
				return []

		if getItems:
			if cat in userConfig:
				return userConfig[cat]
			else:
				return {}

		returnData = {}
		if data is None:
			rData = {"val":[cat, param]}
		else:
			rData = data

		for i in rData:
			cat = rData[i][0]
			param = rData[i][1]

			if cat in userConfig and param in userConfig[cat]:
				returnData[i] = userConfig[cat][param]
			else:
				returnData[i] = None

		if data is None:
			return returnData["val"]
		else:
			return returnData


	@err_decorator
	def setConfig(self, cat=None, param=None, val=None, data=None, configPath=None, delete=False, confData=None):
		if configPath is None:
			configPath = self.configPath

		isUserConf = configPath == self.configPath

		if isUserConf and not os.path.exists(configPath):
			self.createUserPrefs()

		fcontent = os.listdir(os.path.dirname(configPath))
		if len([x for x in fcontent if x.startswith(os.path.basename(configPath) + ".bak")]):
			self.restoreConfig(configPath)

		if confData is None:
			userConfig = {}
			try:
				if os.path.exists(configPath):
					with open(configPath, 'r') as f:
						userConfig = json.load(f)
			except:
				if isUserConf:
					warnStr = "The Pandora preferences file seems to be corrupt.\n\nIt will be reset, which means all local Pandora settings will fall back to their defaults."
				else:
					warnStr = "Cannot read the following file. It will be reset now:\n\n%s" % configPath

				msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.messageParent)
				action = msg.exec_()

				if isUserConf:
					self.createUserPrefs()
					with open(configPath, 'r') as f:
						userConfig = json.load(f)

			if data is None:
				data = [[cat, param, val]]

			for i in data:
				cat = i[0]
				param = i[1]
				val = i[2]

				if cat not in userConfig:
					userConfig[cat] = {}

				if delete:
					if param in userConfig[cat]:
						del userConfig[cat][param]
					continue

				userConfig[cat][param] = val
		else:
			userConfig = confData

		with open(configPath, 'w') as confFile:
			json.dump(userConfig, confFile, indent=4)

		try:
			with open(configPath, 'r') as f:
				testConfig = json.load(f)
			for i in userConfig:
				for k in userConfig[i]:
					if k not in testConfig[i]:
						raise RuntimeError
		except:
			backupPath = configPath + ".bak" + str(random.randint(1000000,9999999))
			with open(backupPath, 'w') as confFile:
				json.dump(userConfig, confFile, indent=4)


	@err_decorator
	def restoreConfig(self, configPath):
		path = os.path.dirname(configPath)
		backups = []
		for i in os.listdir(path):
			if not i.startswith(os.path.basename(configPath) + "."):
				continue

			try:
				backups.append({"name":i, "time":os.path.getmtime(os.path.join(path,i)), "size":os.stat(os.path.join(path,i)).st_size})
			except Exception:
				return False

		times = [x["time"] for x in backups]

		if len(times) == 0:
			return False

		minTime = min(times)

		validBackup = None
		for i in backups:
			if i["time"] == minTime and (validBackup is None or validBackup["size"] > i["size"]):
				validBackup = i

		if validBackup is None:
			return False

		while True:
			try:
				if os.path.exists(configPath):
					os.remove(configPath)
				break
			except Exception:
				msg = QMessageBox(QMessageBox.Warning, "Restore config", "Could not remove corrupt config in order to restore a backup config:\n\n%s" % configPath, QMessageBox.Cancel)
				msg.addButton("Retry", QMessageBox.YesRole)
				msg.setFocus()
				action = msg.exec_()

				if action != 0:
					return False

		validBuPath = os.path.join(path, validBackup["name"])

		try:
			shutil.copy2(validBuPath, configPath)
		except:
			msg = QMessageBox(QMessageBox.Warning, "Restore config", "Could not restore backup config:\n\n%s" % validBuPath, QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False

		for i in backups:
			buPath = os.path.join(path, i["name"])
			try:
				os.remove(buPath)
			except:
				pass

		return True


	@err_decorator
	def validateStr(self, text, allowChars=[], denyChars=[]):
		invalidChars = [" ", "\\", "/", ":", "*", "?", "\"", "<", ">", "|", "ä", "ö", "ü", "ß"]
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
		currentFileName = self.appPlugin.getCurrentFileName(self, path)
		currentFileName = self.fixPath(currentFileName)

		return currentFileName


	@err_decorator
	def saveScene(self):
		curfile = self.getCurrentFileName()
		filepath = curfile.replace("\\","/")

		outLength = len(filepath)
		if platform.system() == "Windows" and outLength > 260:
			QMessageBox.warning(self.messageParent, "Could not save the file", "The filepath is longer than 260 characters (%s), which is not supported on Windows." % outLength)
			return False

		result = self.appPlugin.saveScene(self, filepath)

		if result == False:
			return False			

		if not os.path.exists(filepath):
			return False

		return filepath


	@err_decorator
	def fixPath(self, path):
		if platform.system() == "Windows":
			path = path.replace("/","\\")

		return path


	@err_decorator
	def openFolder(self, path):
		path = self.fixPath(path)

		if platform.system() == "Windows":
			if os.path.isfile(path):
				cmd = ['explorer', '/select,', path]
			else:
				if path != "" and not os.path.exists(path):
					path = os.path.dirname(path)

				cmd = ['explorer', path]

		if os.path.exists(path):
			subprocess.call(cmd)


	@err_decorator
	def openFile(self,path):
		if os.path.isdir(path):
			self.openFolder(path)
		else:
			try:
				os.startfile(path)
			except:
				QMessageBox.warning(self.messageParent, "Pandora", "Could not open this file:\n\n%s\n\nEventually there is no program associated with this filetype." % path)
				self.openFolder(path)


	@err_decorator
	def copyToClipboard(self, text, fixSlashes=True):
		if fixSlashes:
			text = self.fixPath(text)

		cb = qApp.clipboard()
		cb.setText(text)


	@err_decorator
	def createShortcut(self, vPath, vTarget='', args='', vWorkingDir='', vIcon=''):
		try:
			import win32com.client
		except:
			return
		shell = win32com.client.Dispatch('WScript.Shell')
		shortcut = shell.CreateShortCut(vPath)
		shortcut.Targetpath = vTarget
		shortcut.Arguments = args
		shortcut.WorkingDirectory = vWorkingDir
		if vIcon == '':
			pass
		else:
			shortcut.IconLocation = vIcon
		shortcut.save()


	@err_decorator
	def getDefaultSubmissionData(self):
		jobData = {}
		jobData["projectName"] = "Projectname"
		jobData["jobName"] = "Jobname"
		jobData["startFrame"] = 1001
		jobData["endFrame"] = 1100
		jobData["renderCam"] = ""
		jobData["overrideResolution"] = False
		jobData["resolutionWidth"] = 1920
		jobData["resolutionHeight"] = 1080
		jobData["priority"] = 50
		jobData["framesPerTask"] = 5
		jobData["suspended"] = False
		jobData["submitDependendFiles"] = False
		jobData["uploadOutput"] = True
		jobData["timeout"] = 180
		jobData["useProjectAssets"] = True
		jobData["listSlaves"] = "All"
		jobData["programName"] = self.appPlugin.pluginName
		jobData["outputFolder"] = "C:/Pandora/Renderoutput/"
		jobData["outputPath"] = "C:/Pandora/Renderoutput/Pandora.exr"
		userName = self.getConfig("submissions", "userName")
		if userName is None:
			userName = ""
		jobData["userName"] = userName
		return jobData


	@err_decorator
	def getSubmissionEnabled(self):
		conf = self.getConfig(configPath=self.installLocPath, getConf=True)
		if conf is not None:
			for i in conf:
				if len(conf[i]) > 0:
					return True

		return False


	@err_decorator
	def getSubmissionPath(self):
		osFolder = None
		localMode = True

		cData = {}
		cData["localMode"] = ["globals", "localMode"]
		cData["rootPath"] = ["globals", "rootPath"]
		cData["submissionPath"] = ["submissions", "submissionPath"]
		cData = self.getConfig(data=cData)

		if cData["localMode"] is not None:
			localMode = cData["localMode"]

		if localMode:
			if cData["rootPath"] is not None:
				osFolder = os.path.join(cData["rootPath"], "Workstations", "WS_" + socket.gethostname())
		else:
			osFolder = cData["submissionPath"]

		return osFolder


	@err_decorator
	def getSlaveData(self):
		slaveData = {"slaveNames": [], "slaveGroups":[]}
		slaveDir = os.path.join(os.path.dirname(self.getSubmissionPath()), "Logs", "Slaves")
		if os.path.isdir(slaveDir):
			for i in os.listdir(slaveDir):
				slaveLogPath = os.path.join(slaveDir, i)
				if i.startswith("slaveLog_") and i.endswith(".txt") and os.path.isfile(slaveLogPath):
					slaveName = i[len("slaveLog_"):-len(".txt")]
					slaveSettingsPath = slaveLogPath.replace("slaveLog_", "slaveSettings_")[:-3] + "json"
					slaveData["slaveNames"].append(slaveName)

					if not os.path.exists(slaveSettingsPath):
						continue
						
					sGroups = self.getConfig('settings', "slaveGroup", configPath=slaveSettingsPath)
					if sGroups is not None:
						for k in sGroups:
							if k not in slaveData["slaveGroups"]:
								slaveData["slaveGroups"].append(k)

		return slaveData


	@err_decorator
	def submitJob(self, jobData={}):
		osFolder = self.getSubmissionPath()

		if osFolder is None:
			return "Submission canceled: No Pandora submission folder is configured."

		if osFolder == "":
			return "Submission canceled: No Pandora submission folder is configured."

		if not os.path.exists(osFolder):
			try:
				os.makedirs(osFolder)
			except:
				return "Submission canceled: Pandora submission folder could not be created."

		fileName = self.getCurrentFileName()
		if not os.path.exists(fileName):
			return "Submission canceled: Please save the scene first."

		pluginCheck = self.appPlugin.preSubmitChecks(self, jobData)

		if pluginCheck is not None:
			return pluginCheck

		submitData = self.getDefaultSubmissionData()

		for i in jobData:
			submitData[i] = jobData[i]

		if submitData["projectName"] == "":
			return "Submission canceled: Projectname is invalid."

		if submitData["jobName"] == "":
			return "Submission canceled: Jobname is invalid."

		assignPath = os.path.join(osFolder, "JobSubmissions")

		jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
		jobPath = os.path.join(assignPath, jobCode , "JobFiles")
		while os.path.exists(jobPath):
			jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
			jobPath = os.path.join(assignPath, jobCode , "JobFiles")

		jobConf = os.path.join(os.path.dirname(jobPath), "PandoraJob.json")

		if os.path.exists(jobPath):
			return "Submission canceled: Job already exists"

		self.callback(name="onPreJobSubmitted", types=["curApp", "custom"], args=[self, os.path.dirname(jobPath)])

		self.saveScene()

		os.makedirs(jobPath)

		if submitData["useProjectAssets"]:
			assetPath = os.path.join(assignPath, "ProjectAssets", submitData["projectName"])
			if not os.path.exists(assetPath):
				os.makedirs(assetPath)
		else:
			assetPath = jobPath

		jobFiles = [[os.path.basename(fileName), os.path.getmtime(fileName)]]

		if submitData["submitDependendFiles"]:
			extFiles = self.appPlugin.getExternalFiles(self, isSubmitting=True)			

			tFilesState = "None"

			while True:
				erFiles = []
				while True:
					tFiles = []
					for i in extFiles:
						if not os.path.exists(i):
							continue
							
						tPath = os.path.join(assetPath, os.path.basename(i))
						if os.path.exists(tPath):
							if tFilesState != "Overwrite":
								if tFilesState == "Skip":
									continue
								if tFilesState == "Keep newest":
									if int(os.path.getmtime(i)) <= int(os.path.getmtime(tPath)):
										continue
								else:
									if int(os.path.getmtime(i)) != int(os.path.getmtime(tPath)):
										tFiles.append(i)
									if os.path.basename(i) not in jobFiles:
										jobFiles.append([os.path.basename(i), os.path.getmtime(i)])
									continue

						try:
							shutil.copy2(i, assetPath)
							if os.path.basename(i) not in jobFiles:
								jobFiles.append([os.path.basename(i), os.path.getmtime(i)])
						except:
							erFiles.append(i)

					if len(tFiles) > 0:
						fString = "Some assets already exist in the ProjectAsset folder and have a different modification date:\n\n"
						for i in tFiles:
							fString += "%s\n" % i
						msg = QMessageBox(QMessageBox.Warning, "Pandora job submission", fString, QMessageBox.Cancel)
						msg.addButton("Keep newest", QMessageBox.YesRole)
						msg.addButton("Overwrite", QMessageBox.YesRole)
						msg.addButton("Skip", QMessageBox.YesRole)
						self.parentWindow(msg)
						action = msg.exec_()

						if action == 1:
							extFiles = tFiles
							tFilesState = "Overwrite"
						elif action == 2:
							tFilesState = "Skip"
							break
						elif action != 0:
							if os.path.exists(jobPath):
								try:
									os.remove(jobPath)
								except:
									pass
							return "Submission canceled: Canceled by user"
						else:
							extFiles = tFiles
							tFilesState = "Keep newest"
							
					else:
						tFilesState = "Skip"
						break

						
				if len(erFiles) > 0:
					fString = "An error occurred while copying external files:\n\n"
					for i in erFiles:
						fString += "%s\n" % i
					msg = QMessageBox(QMessageBox.Warning, "Pandora job submission", fString, QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					msg.addButton("Continue", QMessageBox.YesRole)
					self.parentWindow(msg)
					action = msg.exec_()


					if action == 1:
						break
					elif action != 0:
						if os.path.exists(jobPath):
							try:
								os.remove(jobPath)
							except:
								pass
						return "Submission canceled: Canceled by user"
					else:
						extFiles = erFiles
				else:
					break

		while True:
			try:
				copyScene = getattr(self.appPlugin, "copyScene", lambda x,y, z: False)(self, jobPath, submitData["submitDependendFiles"])

				if not copyScene:
					shutil.copy2(fileName, jobPath)
				break
			except Exception as e:
				msg = QMessageBox(QMessageBox.Warning, "Pandora job submission", "An error occurred while copying the scenefile.\n\n%s" % e, QMessageBox.Cancel)
				msg.addButton("Retry", QMessageBox.YesRole)
				msg.addButton("Skip", QMessageBox.YesRole)
				self.parentWindow(msg)
				action = msg.exec_()

				if action == 1:
					break
				elif action != 0:
					return "Submission canceled: Could not copy the scenefile"

		if not submitData["useProjectAssets"] and len(jobFiles) != len(os.listdir(jobPath)):
			return "Submission canceled: The filecount in the jobsubmission folder is not correct. %s of %s" % (len(os.listdir(jobPath)), len(jobFiles))


		cData = []
		cData.append(["jobglobals", "priority", submitData["priority"]])
		cData.append(["jobglobals", "uploadOutput", submitData["uploadOutput"]])
		cData.append(["jobglobals", "listSlaves", submitData["listSlaves"]])
		cData.append(["jobglobals", "taskTimeout", submitData["timeout"]])
		cData.append(["information", "jobName", submitData["jobName"]])
		cData.append(["information", "sceneName", os.path.basename(fileName)])
		cData.append(["information", "projectName", submitData["projectName"]])
		cData.append(["information", "userName", submitData["userName"]])
		cData.append(["information", "submitDate", time.strftime("%d.%m.%y, %X", time.localtime())])
		cData.append(["information", "frameRange", "%s-%s" % (submitData["startFrame"], submitData["endFrame"])])
		cData.append(["information", "outputFolder", submitData["outputFolder"]])
		cData.append(["information", "outputPath", submitData["outputPath"]])
		cData.append(["information", "fileCount", len(jobFiles)])
		cData.append(["information", "program", submitData["programName"]])

		self.appPlugin.getJobConfigParams(self, cData)

		if "renderNode" in submitData:
			cData.append(["jobglobals", "renderNode", submitData["renderNode"]])
		if submitData["renderCam"] not in ["", "Current View"]:
			cData.append(["information", "camera", submitData["renderCam"]])
		if submitData["useProjectAssets"]:
			cData.append(["information", "projectAssets", jobFiles])

		if submitData["overrideResolution"]:
			cData.append(["jobglobals", "width", submitData["resolutionWidth"]])
			cData.append(["jobglobals", "height", submitData["resolutionHeight"]])

		if "jobDependecies" in submitData:
			cData.append(["jobglobals", "jobDependecies", submitData["jobDependecies"]])

		curFrame = submitData["startFrame"]
		tasksNum = 0
		if submitData["suspended"]:
			initState = "disabled"
		else:
			initState = "ready"

		while curFrame <= submitData["endFrame"]:
			taskStart = curFrame
			taskEnd = curFrame + submitData["framesPerTask"] - 1
			if taskEnd > submitData["endFrame"]:
				taskEnd = submitData["endFrame"]
			cData.append(["jobtasks", 'task'+ str("%04d" % tasksNum), [taskStart, taskEnd, initState, "unassigned", "", "", ""]])
			curFrame += submitData["framesPerTask"]
			tasksNum += 1

		self.setConfig(data=cData, configPath=jobConf)
		
		self.callback(name="onPostJobSubmitted", types=["curApp", "custom"], args=[self, os.path.dirname(jobPath)])

		return ["Success", jobCode, jobPath]


	@err_decorator
	def updatePandora(self, filepath="", gitHub=False):
		targetdir = os.path.join(os.environ["temp"], "PandoraUpdate")

		if os.path.exists(targetdir):
			try:
				shutil.rmtree(targetdir, ignore_errors=False, onerror=self.handleRemoveReadonly)
			except:
				QMessageBox.warning(self.messageParent, "Pandora update", "Could not remove temp directory:\n%s" % targetdir)
				return

		if gitHub:
			try:
				from git import Repo
			except:
				QMessageBox.warning(self.messageParent, "Pandora update", "Could not load git. In order to update Pandora from GitHub you need git installed on your computer.")
				return

			waitmsg = QMessageBox(QMessageBox.NoIcon, "Pandora update", "Downloading repository - please wait..", QMessageBox.Cancel)
			waitmsg.buttons()[0].setHidden(True)
			waitmsg.show()
			QCoreApplication.processEvents()

			Repo.clone_from("https://github.com/RichardFrangenberg/Pandora", targetdir)

			updateRoot = os.path.join(os.environ["temp"], "PandoraUpdate", "Pandora")
		else:
			if not os.path.exists(filepath):
				return

			import zipfile

			waitmsg = QMessageBox(QMessageBox.NoIcon, "Pandora update", "Extracting - please wait..", QMessageBox.Cancel)
			waitmsg.buttons()[0].setHidden(True)
			waitmsg.show()
			QCoreApplication.processEvents()

			with zipfile.ZipFile(filepath,"r") as zip_ref:
				zip_ref.extractall(targetdir)

			updateRoot = os.path.join(os.environ["temp"], "PandoraUpdate", "Pandora-development", "Pandora")

		if "waitmsg" in locals() and waitmsg.isVisible():
			waitmsg.close()

		msgText = "Are you sure you want to continue?\n\nThis will overwrite existing files in your Pandora installation folder."
		if psVersion == 1:
			flags = QMessageBox.StandardButton.Yes
			flags |= QMessageBox.StandardButton.No
			result = QMessageBox.question(self.messageParent, "Pandora update", msgText, flags)
		else:
			result = QMessageBox.question(self.messageParent, "Pandora update", msgText)

		if not str(result).endswith(".Yes"):
			return

		for i in os.walk(updateRoot):
			for k in i[2]:
				filepath = os.path.join(i[0], k)
				if not os.path.exists(i[0].replace(updateRoot, self.pandoraRoot)):
					os.makedirs(i[0].replace(updateRoot, self.pandoraRoot))

				shutil.copy2(filepath, filepath.replace(updateRoot, self.pandoraRoot) )

		if os.path.exists(targetdir):
			shutil.rmtree(targetdir, ignore_errors=False, onerror=self.handleRemoveReadonly)
		try:
			import psutil
		except:
			pass
		else:
			PROCNAMES = ['PandoraTray.exe', "PandoraCoordinator.exe", "PandoraRenderHandler.exe", "PandoraSettings.exe", "PandoraSlave.exe"]
			for proc in psutil.process_iter():
				if proc.name() in PROCNAMES:
					if proc.pid == os.getpid():
						continue

					p = psutil.Process(proc.pid)

					try:
						if not 'SYSTEM' in p.username():
							try:
								proc.kill()
							except:
								pass
					except:
						pass

		trayPath = os.path.join(self.pandoraRoot, "Tools", "PandoraTray.lnk")
		if os.path.exists(trayPath):
			subprocess.Popen([trayPath], shell=True)

		msgStr = "Successfully updated Pandora"
		if self.appPlugin.pluginName == "Standalone":
			msgStr += "\n\nPandora will now close. Please restart all your currently open DCC apps."
		else:
			msgStr += "\nPlease restart %s in order to reload Pandora." % self.appPlugin.pluginName

		QMessageBox.information(self.messageParent, "Pandora update", msgStr)

		if self.appPlugin.pluginName == "Standalone":
			sys.exit()


	@err_decorator
	def handleRemoveReadonly(self, func, path, exc):
		excvalue = exc[1]
		if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
			os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
			func(path)
		else:
			raise


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

	browser = RoboBrowser(parser='html.parser', history=True, max_age=0)
	browser.open('https://prism-pipeline.com/contact/', verify=False)

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
""" % (self.pandoraRoot.replace("\\", "\\\\"), self.pandoraRoot.replace("\\", "\\\\"), subject, text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\'", "\\\""))

			pythonPath = os.path.join(self.pandoraRoot, "Python27", "pythonw.exe")
			result = subprocess.Popen([pythonPath, "-c", pStr], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
				except Exception as e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					messageStr = "%s\n\n%s - %s - %s - %s\n\n%s" % (stdOutData, str(e), exc_type, exc_tb.tb_lineno, traceback.format_exc(), text)
					raise RuntimeError(messageStr)

			QMessageBox.information(self.messageParent, "Information", "Sent message successfully.")

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
	page = requests.get('https://prism-pipeline.com/pandora/', verify=False)

	cStr = page.content
	vCode = 'Latest version: ['
	latestVersionStr = cStr[cStr.find(vCode)+len(vCode): cStr.find(']', cStr.find('Latest version: ['))]

	sys.stdout.write(latestVersionStr)

except Exception as e:
	sys.stdout.write('failed %%s' %% e)
""" % (self.pandoraRoot, self.pandoraRoot)

		pythonPath = os.path.join(self.pandoraRoot, "Python27", "pythonw.exe")
		result = subprocess.Popen([pythonPath, "-c", pStr], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdOutData, stderrdata = result.communicate()

		if "failed" in str(stdOutData) or len(str(stdOutData).split(".")) < 3:
			QMessageBox.information(self.messageParent, "Pandora", "Unable to connect to www.prism-pipeline.com. Could not check for updates.")
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
			action = msg.exec_()

			if action == 0:
				self.openWebsite("home")

		else:
			QMessageBox.information(self.messageParent, "Pandora", "The latest version of Pandora is already installed. (%s)" % self.version)


	def writeErrorLog(self, text):
		try:

			ptext = "An unknown Pandora error occured.\nThe error was logged.\nIf you want to help improve Pandora, please send this error to the developer.\n\nYou can contact the pipeline administrator or the developer, if you have any questions on this.\n\n"
		#	print (text)

			text += "\n\n"

			userErPath = os.path.join(os.path.dirname(self.configPath), "ErrorLog_%s.txt" % socket.gethostname())

			try:
				with open(userErPath, "a") as erLog:
					erLog.write(text)
			except:
				pass

			if not hasattr(self, "messageParent"):
				print (text)
				self.messageParent = QWidget()

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


if __name__ == "__main__":
	qApp = QApplication(sys.argv)

	sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))
	from UserInterfacesPandora import qdarkstyle

	qApp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
	handlerIcon = QIcon(os.path.dirname(os.path.abspath(__file__)) + "\\UserInterfacesPandora\\pandora_tray.ico")
	qApp.setWindowIcon(handlerIcon)
	pc = PandoraCore()
	qApp.exec_()