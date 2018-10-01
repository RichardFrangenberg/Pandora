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




from PySide.QtCore import *
from PySide.QtGui import *
import sys, os, _winreg, shutil, time, io, multiprocessing, threading, socket, subprocess, traceback
from ConfigParser import ConfigParser
from functools import wraps

pndPath = os.path.join(os.getenv('localappdata'), "Pandora", "PythonLibs", "Renderslave")
sys.path.append(pndPath)
sys.path.append(os.path.join(os.getenv('localappdata'), "Pandora", "Scripts"))

from UserInterfacesPandora import qdarkstyle
import psutil
from PIL import ImageGrab


# custom messagebox, which closes after some seconds. It is used to ask wether this PC is currently used by a person.
class counterMessageBox(QMessageBox):

	def __init__(self, prerenderwaittime):
		QMessageBox.__init__(self)

		# definde the amount of seconds after which the messagebox closes
		self.seconds = prerenderwaittime

		# set up text and buttons of the messagebox
		QMessageBox.setText(self,"Do you want to use this PC now? Otherwise this PC will start rendering.\n\nRendering starts in %s seconds" % self.seconds)
		QMessageBox.setWindowTitle(self,"Pandora RenderSlave")

		self.addButton("Yes, I want to use this PC", QMessageBox.YesRole)
		self.addButton("No, this PC can start rendering", QMessageBox.NoRole)

		# starts a timer, which updates the remaining seconds on the messagebox
		self.t = QTimer()
		self.t.timeout.connect(self.timeoutSlot)
		self.t.start(1000) # amount of milliseconds after which the timer is executed


	# called every second. updates the remaining time and closes if the time is 0.
	def timeoutSlot(self):
		self.seconds -= 1
		QMessageBox.setText(self,"Do you want to use this PC now? Otherwise this PC will start rendering.\n\nRendering starts in %s seconds" % self.seconds)
		
		if self.seconds==0:
			self.t.stop()
			QMessageBox.close(self)


# main class for handling rendering
class SlaveLogic(QDialog):

	def __init__(self):
		QDialog.__init__(self)
		self.slaveLogicVersion = "v1.0.0"

		# define some initial variables
		self.slaveState = "idle"			# slave render status
		self.debugMode = False				# if slave is in debug mode, more information will be printed to the log file
		self.updateTime = 10				# interval in seconds after which the slave checks for new render jobs or commands
		self.useRestPeriod = True 			# restperiod defines a time in which the slave does not render
		self.startRP = 9					# start time of rest period
		self.endRP = 18 					# end time of rest period
		self.maxCPU = 30 					# the CPU usage has to be lower than this value before the rendering starts. This prevents the slave from starting a render, when the PC is currently rendering locally.
		self.prerenderwaittime = 0

		self.cursorCheckPos = None			# cursor position  to check if the PC is currently used
		self.parentWidget = QWidget()		# used as a parent for UIs

		self.userAsked = False 				# defines wether the user was already asked if it is ok to start rendering
		self.interrupted = False			# holds wether the current rendering was interrupted
		self.renderTasks = []				# stores new job assigments from the coordinator
		self.curjob = {"code": "", "name": ""}					# render job, which is currently rendered by the slave
		self.curTask = ""					# render task, which is currently rendered by the slave
		self.curJobData = {}				# job information from the job, which is currently rendered by the slave
		self.waitingForFiles = False
#		self.lastConnectionTime = time.time()
#		self.connectionTimeout = 15

		self.pandoraConfigPath = os.path.join(os.getenv("localappdata"), "Pandora", "Config", "Pandora.ini")

		if not os.path.exists(self.pandoraConfigPath):
			self.createDefaultPConfig(self.pandoraConfigPath)

		lConfig = ConfigParser()
		lConfig.read(self.pandoraConfigPath)

		if not lConfig.has_section("slave"):
			lConfig.add_section("slave")

	#	if lConfig.has_option("slave", "enabled") and not lConfig.getboolean("slave", "enabled"):
	#		print "slave is disabled. Closing slave"
	#		return

		if lConfig.has_option("globals", "localmode"):
			self.localmode = lConfig.getboolean("globals", "localmode")
		else:
			self.localmode = True

		if not lConfig.has_option("globals", "repositorypath"):
			QMessageBox.warning(self, "Warning", "Pandora repository path is not defined.")
			return

		repoDir = lConfig.get("globals", "repositorypath")
		repoDir = os.path.join(repoDir, "Slave")
		if not os.path.exists(repoDir):
			try:
				os.makedirs(repoDir)
			except:
				pass

		if not os.path.exists(repoDir):
			QMessageBox.warning(self, "Warning", "Pandora repository path doesn't exist.\n\n%s" % repoDir)
			return
	
		self.localSlavePath = repoDir

		if self.localmode:
			if not lConfig.has_option("globals", "rootpath"):
				QMessageBox.warning(self, "Warning", "Pandora root path is not defined.")
				return

			rootPath = lConfig.get("globals", "rootpath")
			if not os.path.exists(rootPath):
				QMessageBox.warning(self, "Warning", "Pandora root path doesn't exist.")
				return

			self.slavePath = os.path.join(rootPath, "PandoraFarm", "Slaves", "S_" + socket.gethostname())
		else:
			if not lConfig.has_option("slave", "slavepath"):
				QMessageBox.warning(self, "Warning", "No slave root folder specified in the Pandora config")
				return
			else:
				self.slavePath = lConfig.get("slave", "slavepath")

		if lConfig.has_option("submissions", "enabled"):
			self.isWorkstation = lConfig.getboolean("submissions", "enabled")
		else:
			self.isWorkstation = False

		self.slaveIni = os.path.join(self.slavePath, "slaveSettings_%s.ini" % socket.gethostname())			# path for the file with the RenderSlave settings
		self.slaveLog = os.path.join(self.slavePath, "slaveLog_%s.txt" % socket.gethostname())							# path for the RenderSlave Log file
		self.slaveWarningsIni = os.path.join(self.slavePath, "slaveWarnings_%s.ini" % socket.gethostname())
		self.slaveComPath = os.path.join(self.slavePath, "Communication")												# path where the in- and out-commands are stored

		# create the communication folder if it doesn't exist already
		if not os.path.exists(self.slaveComPath):
			try:
				os.makedirs(self.slaveComPath)
			except:
				self.writeLog("could not create Communication folder for %s" % socket.gethostname(), 2)

		if not os.path.exists(self.slaveWarningsIni):
			warningConfig = ConfigParser()
			warningConfig.add_section("warnings")

			with open(self.slaveWarningsIni, 'w') as inifile:
				warningConfig.write(inifile)

		# save the default slave settings to the settings file if they don't exist already
		self.createSettings(complement=True)
		self.setSlaveInfo()
	#	self.getGDrivePath()

		slaveEnabled = self.getIniSetting("enabled", stype="bool")
		if slaveEnabled is None:
			self.getIniSetting("enabled", setval=True, value=True)
			slaveEnabled = True
		elif slaveEnabled and self.slaveState == "disabled":
			self.setState("idle")
		elif not slaveEnabled:
			self.setState("disabled")

		self.createTrayIcon()
		self.trayIcon.show()

		showslavewindow = self.getIniSetting("showslavewindow", stype="bool")

		# display a messagebox, which informs the user, that this PC is a RenderSlave
		if not self.isWorkstation and showslavewindow:
			self.msgStart = QMessageBox(QMessageBox.Information, "Pandora RenderSlave", "<b>Please don't shut down this PC, when you leave.</b>", QMessageBox.Ok)
			self.msgStart.setInformativeText("This PC is part of a renderfarm and will start rendering, when nobody is working on it.")
			self.msgStart.buttons()[0].setHidden(True)
			self.msgStart.setWindowIcon(self.slaveIcon)
			self.msgStart.setFocus()
			self.msgStart.show()

		self.writeLog("SlaveLogic started - %s" % self.slaveLogicVersion, 1)

		self.logicTimer = QTimer()
		self.logicTimer.setSingleShot(True)
		self.logicTimer.timeout.connect(self.checkAssignments)

		self.checkAssignments()


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Pandora RenderSlave %s:\n%s\n\n%s\n%s - %s" % (time.strftime("%d.%m.%y %X"), args[0].slaveLogicVersion, ''.join(traceback.format_stack()), traceback.format_exc(), args, kwargs))
				args[0].writeLog(erStr, 3)
				if func == args[0].checkAssignments:
					args[0].logicTimer.start(args[0].updateTime*1000)

		return func_wrapper


	@err_decorator
	def createDefaultPConfig(self, configPath):
		if os.path.exists(configPath):
			try:
				os.remove(configPath)
			except:
				pass

		if not os.path.exists(os.path.dirname(configPath)):
			os.mkdir(os.path.dirname(configPath))

		open(configPath, 'a').close()

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
		uconfig.set("dccoverrides", "maxpath", "")
		uconfig.set("dccoverrides", "mayapath", "")
		uconfig.set("dccoverrides", "houdinipath", "")
		uconfig.set("dccoverrides", "blenderpath", "")

		oldIni = os.getenv('LocalAppdata') + "\\Pandora\\Config\\PandoraOLD.ini"

		# check if an old ini file exists and if yes, copy the values to the new ini
		if os.path.exists(oldIni):
			oconfig = ConfigParser()
			oconfig.read(oldIni)
			for i in oconfig.sections():
				for k in oconfig.options(i):
					if uconfig.has_option(i, k) or i in ["lastusedsettings"]:
						uconfig.set(i, k, oconfig.get(i, k))

		with open(configPath, 'w') as inifile:
			uconfig.write(inifile)

		try:
			os.remove(oldIni)
		except:
			pass


	def openPandoraSettings(self):
		try:
			PROCNAME = 'PandoraSettings.exe'
			for proc in psutil.process_iter():
				if proc.name() == PROCNAME:
					p = psutil.Process(proc.pid)

					if not 'SYSTEM' in p.username():
						proc.kill()

			settingsPath = os.path.dirname(__file__) + "\\PandoraSettings.py"
			if not os.path.exists(settingsPath):
				self.trayIcon.showMessage("Script missing", "PandoraSettings.py does not exist.", icon = QSystemTrayIcon.Warning)
				return None

			command = '\"%s\\Pandora\\Tools\\PandoraSettings.lnk\"' % os.environ["localappdata"]
		
			self.settingsProc = subprocess.Popen(command, shell=True)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.trayIcon.showMessage("Unknown Error", "openPandoraSettings - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)



	# creates the tray icon, which gives the user some options to control the slave
	@err_decorator
	def createTrayIcon(self):
		self.trayIconMenu = QMenu(self.parentWidget)
		self.wAction = QWidgetAction(self.parentWidget)
		self.statusLabel = QLabel("Status:\n\n\n")
		self.statusLabel.setAlignment(Qt.AlignCenter)
		self.wAction.setDefaultWidget(self.statusLabel)
		self.trayIconMenu.addAction(self.wAction)
		self.trayIconMenu.addSeparator()
		self.activateAction = QAction("Activate now", self.parentWidget)
		self.activateAction.triggered.connect(self.activateSlave)
		self.trayIconMenu.addAction(self.activateAction)
		self.pauseMenu = QMenu("Pause", self.parentWidget)
		self.pause1Action = QAction("15 min.", self.parentWidget)
		self.pause1Action.triggered.connect(lambda: self.pauseSlave(2))
		self.pauseMenu.addAction(self.pause1Action)
		self.pause2Action = QAction("1h", self.parentWidget)
		self.pause2Action.triggered.connect(lambda: self.pauseSlave(60))
		self.pauseMenu.addAction(self.pause2Action)
		self.pause3Action = QAction("3h", self.parentWidget)
		self.pause3Action.triggered.connect(lambda: self.pauseSlave(180))
		self.pauseMenu.addAction(self.pause3Action)
		self.pause4Action = QAction("6h", self.parentWidget)
		self.pause4Action.triggered.connect(lambda: self.pauseSlave(360))
		self.pauseMenu.addAction(self.pause4Action)
		self.trayIconMenu.addMenu(self.pauseMenu)
		self.enableAction = QAction("Enabled", self.parentWidget, checkable = True, checked = self.slaveState!="disabled")
		self.enableAction.triggered[bool].connect(self.setSlave)
		self.trayIconMenu.addAction(self.enableAction)
		self.restartAction = QAction("Restart ", self.parentWidget, triggered=self.restartLogic)
		self.trayIconMenu.addAction(self.restartAction)
		self.trayIconMenu.addSeparator()
		self.folderAction = QAction("Open Slave Repository", self.parentWidget , triggered=lambda: self.openFolder(self.localSlavePath))
		self.trayIconMenu.addAction(self.folderAction)
		self.folderAction = QAction("Open Slave Root", self.parentWidget , triggered=lambda: self.openFolder(self.slavePath))
		self.trayIconMenu.addAction(self.folderAction)
		self.folderAction = QAction("Show Log", self.parentWidget , triggered=lambda: self.openFolder(self.slaveLog))
		self.trayIconMenu.addAction(self.folderAction)
		self.trayIconMenu.addSeparator()
		self.settingsAction = QAction("Pandora Settings...", self.parentWidget, triggered=self.openPandoraSettings)
		self.trayIconMenu.addAction(self.settingsAction)
		self.trayIconMenu.addSeparator()
		self.exitAction = QAction("Exit", self.parentWidget , triggered=self.exitLogic)
		self.trayIconMenu.addAction(self.exitAction)

		self.trayIcon = QSystemTrayIcon()
		self.trayIcon.setContextMenu(self.trayIconMenu)
		self.trayIcon.setToolTip(" Pandora RenderSlave")

		self.trayIcon.activated.connect(self.trayActivated)

		self.slaveIcon = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
		self.slaveIcon = QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserInterfacesPandora", "pandora_slave.ico"))

		self.trayIcon.setIcon(self.slaveIcon)
		self.setWindowIcon(self.slaveIcon)


	# called when the user open the tray icon option. updates and displays the current slave status
	@err_decorator
	def trayActivated(self, reason):
		if reason == QSystemTrayIcon.Context:
			statusText = "Status:\n%s" % self.slaveState
			if self.slaveState == "paused":
				pauseMin = QDateTime.currentDateTime().secsTo(self.pauseEnd)/60
				hourPause = pauseMin/60
				pauseMin = pauseMin - hourPause*60
				if hourPause > 0:
					statusText += " (%sh %smin.)" % (hourPause, pauseMin)
				else:
					statusText += " (%s min.)" % pauseMin

			self.enableAction.setChecked(self.slaveState != "disabled")
					
			statusText += "\n"
			self.statusLabel.setText(statusText)


	# called from the tray icon. Forces the slave to emmediatly check for renderjobs/commands
	@err_decorator
	def activateSlave(self):
		self.setState("idle")
		self.enableAction.setChecked(True)
		self.checkAssignments()


	# called from the tray icon. Enables/Disables the slave
	@err_decorator
	def setSlave(self, enabled):
		if enabled:
			self.setState("idle")
			self.getIniSetting("enabled", setval=True, value="True")
		else:
			self.stopRender()
			self.getIniSetting("enabled", setval=True, value="False")
			self.setState("disabled")
			self.writeLog("slave disabled", 1)

		self.checkAssignments()


	# called from the tray icon or methods. Pauses the slave
	@err_decorator
	def pauseSlave(self, duration, stop=True):
		if stop:
			self.stopRender()
		
		self.setState("paused")

		self.pauseEnd = QDateTime.currentDateTime().addSecs(duration * 60)

		self.enableAction.setChecked(True)
		#self.logicTimer.start(duration*60*1000)
		self.writeLog("slave paused for %s minutes" % duration, 1)


	# restarts or closes the slave
	@err_decorator
	def restartLogic(self, restart=True):
		self.stopRender()
		if hasattr(self, "msgStart") and self.msgStart.isVisible():
			self.msgStart.close()

		if restart:
			self.setState("restarting")
			self.writeLog("slave restarting", 1)
			dirName = os.path.dirname(os.path.abspath(__file__))
			pwExe = os.path.join(os.getenv('localappdata'), "Pandora", "Python27", "PandoraSlave.exe")
			os.system("start %s %s %s" % (pwExe, os.path.abspath(__file__), "forcestart"))
		else:
			self.setState("shut down")
			sys.stdout.write("Exit Slave\n")
	
		qapp.quit()
		sys.exit()


#	# restarts "backup and sync" from google
#	@err_decorator
#	def restartGDrive(self):
#		self.writeLog("restart gdrive", 1)
#		PROCNAME = 'googledrivesync.exe'
#		for proc in psutil.process_iter():
#			if proc.name() == PROCNAME:
#				p = psutil.Process(proc.pid)
#
#				if not 'SYSTEM' in p.username():
#					proc.kill()
#
#		if os.path.exists(self.gdrive):
#			subprocess.Popen(self.gdrive)


	# searches for the installation path of "backup and sync" from google in the registry
#	@err_decorator
#	def getGDrivePath(self):
#		try:
#			key = _winreg.OpenKey(
#				_winreg.HKEY_LOCAL_MACHINE,
#				"SOFTWARE\Google\Drive",
#				0,
#				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
#			)
#
#			self.gdrive = (_winreg.QueryValueEx(key, "InstallLocation"))[0]
#			if not os.path.exists(self.gdrive):
#				self.gdrive = ""
#		except:
#			self.gdrive = ""
#
#		self.writeLog("set gdrive path to: %s" % self.gdrive)


	# closes the slave
	@err_decorator
	def exitLogic(self):
		self.writeLog("exit slave", 1)
		#self.getIniSetting("enabled", setval=True, value="False")
		self.restartLogic(restart=False)


	# used to ignore the event, when the user tries to close a messagebox with the "X"
	@err_decorator
	def ignoreEvent(self, event):
		self.writeLog("ignore event", 1)
		event.ignore()


	# writes text to a log file. A higher level means more importance.
	@err_decorator
	def writeLog(self, text, level=0, writeWarning=True):
		try:
			if not os.path.exists(self.slaveLog):
				try:
					if not os.path.exists(os.path.dirname(self.slaveLog)):
						os.makedirs(os.path.dirname(self.slaveLog))
					open(self.slaveLog, 'a').close()
				except:
					return None

			if level==0 and not self.debugMode:
				return

			elif level > 1 and writeWarning:
				self.writeWarning(text, level)

		#	print text

			with io.open(self.slaveLog, 'a', encoding='utf-16') as log:
				log.write(unicode("[%s] %s : %s\n" % (level, time.strftime("%d.%m.%y %X"), text)))
		except:
			pass


	# writes warning to a file. A higher level means more importance.
	@err_decorator
	def writeWarning(self, text, level=1):
		if not os.path.exists(self.slaveWarningsIni):
			try:
				if not os.path.exists(os.path.dirname(self.slaveWarningsIni)):
					os.makedirs(os.path.dirname(self.slaveWarningsIni))
				open(self.slaveWarningsIni, 'a').close()
			except:
				self.writeLog("cannot create warningIni", 2)
				self.writeLog(text, level)
				return None

		warningConfig = ConfigParser()
		try:
			warningConfig.read(self.slaveWarningsIni)
		except:
			self.writeLog("could not read warnings", 2, writeWarning=False)

		warnings = []
		if warningConfig.has_section("warnings"):
			for i in warningConfig.options("warnings"):
				try:
					warnings.append(eval(warningConfig.get("warnings", i)))
				except:
					self.writeLog("invalid warning: %s" % warningConfig.get("warnings", i), 2, writeWarning=False)

			warnings = [x for x in warnings if x[0] != text]

		warnings.insert(0, [text, time.time(), level])

		warningConfig = ConfigParser()
		warningConfig.add_section("warnings")
		for idx, val in enumerate(warnings):
			warningConfig.set("warnings", "warning%s" % idx, val)

		try:	
			with open(self.slaveWarningsIni, 'w') as inifile:
				warningConfig.write(inifile)
		except:
			pass


	# writes slave infos to file
	@err_decorator
	def setSlaveInfo(self):
		self.getIniSetting("status", section="slaveinfo", setval=True, value=self.slaveState)
		if self.curjob["name"] != "" or self.curTask != "":
			curJobStr = "%s (%s)" % (self.curjob["name"], self.curTask)
		else:
			curJobStr = ""

		self.getIniSetting("curjob", section="slaveinfo", setval=True, value=curJobStr)
		self.getIniSetting("cpucount", section="slaveinfo", setval=True, value=str(multiprocessing.cpu_count()))
		self.getIniSetting("slaveScriptVersion", section="slaveinfo", setval=True, value=self.slaveLogicVersion)

		process = os.popen('wmic memorychip get capacity')
		result = process.read()
		process.close()
		totalMem = 0
		for m in result.split("  \r\n")[1:-1]:
			totalMem += int(m)

		self.getIniSetting("ram", section="slaveinfo", setval=True, value=str(totalMem / (1024**3)))
					

	# reads a slave setting from file and returns the value
	@err_decorator
	def getIniSetting(self,setting, section="settings", stype="string", setval=False, value=""):
		if not os.path.exists(self.slaveIni) :
			self.createSettings()
		else:
			self.slaveConfig = ConfigParser()
			try:
				self.slaveConfig.read(self.slaveIni)
			except:
				self.writeLog("unable to read slaveSettings. restarting logic", 1)
				self.restartLogic()

			if not self.slaveConfig.has_section(section):
				self.slaveConfig.add_section(section)

		if setval:
			self.slaveConfig.set(section, setting, value)
			with open(self.slaveIni, 'w') as inifile:
				self.slaveConfig.write(inifile)

			if setting == "debugmode":
				self.debugMode = value

			if setting == "cursorcheck" and value == "False":
				self.cursorCheckPos = None
				if self.slaveState == "userActive":
					self.setState("idle")

		else:
			if not self.slaveConfig.has_option(section, setting):
				return None

			if stype == "string":
				return self.slaveConfig.get(section, setting)
			elif stype == "int":
				return self.slaveConfig.getint(section, setting)
			elif stype == "float":
				return self.slaveConfig.getfloat(section, setting)
			elif stype == "bool":
				self.boolconf = self.slaveConfig.get(section, setting)
				return self.slaveConfig.getboolean(section, setting)


	@err_decorator
	def getPConfig(self, cat, param, ptype="string"):
		pConfig = ConfigParser()
		try:
			pConfig.read(self.pandoraConfigPath)
		except:
			warnStr = "The Pandora preferences file seems to be corrupt.\n\nIt will be reset, which means all local Pandora settings will fall back to their defaults."
			msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()
			self.createDefaultPConfig()
			pConfig.read(self.pandoraConfigPath)

		if pConfig.has_option(cat, param):
			if ptype == "string":
				return pConfig.get(cat, param)
			elif ptype == "bool":
				return pConfig.getboolean(cat, param)
		else:
			return None


	# shutdown this PC
	@err_decorator
	def shutdownPC(self, restart):
		self.stopRender()
		self.writeLog("restarting PC", 1)
		self.setState("restarting")

		cmd = "shutdown -t 0 -f"

		if restart:
			cmd = "shutdown -t 0 -r -f"

		os.system(cmd)


	# clears the log file
	@err_decorator
	def clearLog(self):
		try:
			open(self.slaveLog, 'w').close()
			self.writeLog("SlaveLog cleared", 1)
		except:
			self.writeLog("ERROR - Could not clear log: %s" % self.slaveLog, 3)


	# starts teamviewer portable
	@err_decorator
	def startTeamviewer(self):
		self.writeLog("starting Teamviewer", 1)
		tvPath = os.path.join(os.getenv("localappdata"), "Pandora", "Tools", "TeamViewerPortable", "TeamViewer.exe")
		if not os.path.exists(tvPath):
			self.writeLog("WARNING - teamviewer.exe not found.", 2)
			return

		subprocess.Popen(tvPath)
		time.sleep(5)

		self.writeScreenshot()


	# makes a screenshot and save it. Usefull to get the teamviewer password
	@err_decorator
	def writeScreenshot(self):
		filename = "ScreenShot_%s.jpg" % socket.gethostname()
		img=ImageGrab.grab()
		saveas=os.path.join(self.slavePath, filename)
		img.save(saveas)


	# writes out a command to the coordinator
	@err_decorator
	def communicateOut(self, cmd):
		curNum = 1

		for i in os.listdir(self.slaveComPath):
			if not i.startswith("slaveOut_"):
				continue
		
			num = i.split("_")[1]
			if not unicode(num).isnumeric():
				continue

			if int(num) >= curNum:
				curNum = int(num) + 1


		cmdFile = os.path.join(self.slaveComPath, "slaveOut_%s_%s.txt" % (format(curNum, '04'), time.time()))

		open(cmdFile, 'a').close()
		with open(cmdFile, 'w') as cFile:
			cFile.write(str(cmd))

		self.writeLog("communicate out: %s" % cmd, 0)


	# opens a specified folder in the windows explorer
	@err_decorator
	def openFolder(self,path):
		if os.path.exists(path):
			if os.path.isdir(path):
				subprocess.call(['explorer', path.replace("/","\\")])
			else:
				subprocess.call(['start', '', '%s' % path.replace("/","\\")], shell=True)


	# removes a file
	@err_decorator
	def remove(self, filepath):
		try:
			os.remove(filepath)
		except:
			self.writeLog("ERROR - cannot remove file: " % filepath, 3)


	# writes the slave settings to file
	@err_decorator
	def createSettings(self, complement=False):
		sections = ["settings", "slaveinfo"]
		defaultSettings = [	["updatetime", "10"], 
							["restperiod", "[False, 9, 18]"],
							["maxcpu", "30"],
							["command", ""],
							["cursorcheck", "False"],
							["slavegroup", "[]"],
							["enabled", "True"],
							["debugmode", "False"],
							["connectionTimeout", "15"],
							["prerenderwaittime", "0"],
							["showslavewindow", "False"],
							["showinterruptwindow", "True"]
						]

		open(self.slaveIni, 'a').close()
		self.slaveConfig = ConfigParser()
		self.slaveConfig.read(self.slaveIni)
		for i in sections:
			if not self.slaveConfig.has_section(i):
				self.slaveConfig.add_section(i)

		for i in defaultSettings:
			if not complement or not self.slaveConfig.has_option("settings", i[0]):
				self.slaveConfig.set("settings", i[0], i[1])

		with open(self.slaveIni, 'w') as inifile:
			self.slaveConfig.write(inifile)


	# sets the slavestate and writes it to file
	@err_decorator
	def setState(self, state):
		if self.slaveState != state:
			self.slaveState = state
			self.getIniSetting("status", section='slaveinfo', setval=True, value=self.slaveState)


	# checks if the slave can start rendering
	@err_decorator
	def checkAssignments(self):
		self.writeLog("start checking assignments")
		self.writeActive()	

		debug = self.getIniSetting("debugMode", stype="bool")
		if debug is None:
			self.getIniSetting("debugmode", setval=True, value="False")
			self.debugMode = False
		else:
			self.debugMode = debug

		slaveEnabled = self.getIniSetting("enabled", stype="bool")
		if slaveEnabled is None:
			self.getIniSetting("enabled", setval=True, value=True)
			slaveEnabled = True
		elif slaveEnabled and self.slaveState == "disabled":
			self.setState("idle")
		elif not slaveEnabled:
			self.setState("disabled")
		
		if not (os.path.exists(self.slavePath)):
			self.writeWarning("paths don't exist", 3)
			self.logicTimer.start(self.updateTime*1000)
			return False

		newUTime = self.getIniSetting("updatetime", stype="int")
		if newUTime is None:
			self.getIniSetting("updatetime", setval=True, value=self.updateTime)
		elif newUTime != self.updateTime:
				self.writeLog("updating updateTime from %s to %s" % (self.updateTime, newUTime), 1)
				self.updateTime = newUTime

		if self.cursorCheckPos is None:
			if not self.waitingForFiles:
				for i in self.renderTasks:
					if not (i["name"] == self.curjob["name"] and i["task"] == self.curTask):
						self.writeLog("giving back assignment of %s from job %s" % (i["task"], i["name"]))
						self.communicateOut(["taskUpdate", i["code"], i["task"], "ready", "", "", ""])
				self.renderTasks = []
			self.checkCmds()

		self.checkCommandSetting()

#		timeout = self.getIniSetting("connectionTimeout", stype="int")
#		if timeout is None:
#			self.getIniSetting("connectionTimeout", setval=True, value=self.connectionTimeout)
#		else:
#			self.connectionTimeout = timeout
#
#		if (time.time() - self.lastConnectionTime) > (60 * self.connectionTimeout):
#			self.restartGDrive()
#			self.lastConnectionTime = time.time()

		if self.slaveState != "rendering":
			self.checkForUpdates()

		if self.slaveState == "userActive":
			cresult = self.checkCursor()
			if cresult > 0:
				self.logicTimer.start(cresult*1000)
				return False

		if self.checkRest():
			if self.slaveState == "idle":
				self.setState("rest")
		elif self.slaveState == "rest":
			self.setState("idle")

		if self.slaveState == "paused" and QDateTime.currentDateTime() > self.pauseEnd:
			self.writeLog("Pause ended. Changed slavestate to idle.")
			self.setState("idle")

		if slaveEnabled and len(self.renderTasks) > 0:
			rcheck = self.preRenderCheck()
			if not rcheck[0]:
				self.writeLog("preRenderCheck not passed")
				if rcheck[1] > 0:
					self.logicTimer.start(rcheck[1]*1000)
				return

			self.startRenderJob(self.renderTasks[0])

		if self.slaveState != "idle":
			self.logicTimer.start(self.updateTime*1000)
			return

		if self.waitingForFiles:
#			self.writeLog("DEBUG - waiting for files")
			self.logicTimer.start(30*1000)
			return

		self.writeLog("no task assigned")
		if hasattr(self, "msg") and self.msg.isVisible():
			self.msg.closeEvent = self.msg.origCloseEvent
			self.msg.close()

		self.userAsked = False

		self.logicTimer.start(self.updateTime*1000)


	# tells the server that this slave is currently running
	@err_decorator
	def writeActive(self):
		slaveActive = self.slavePath + "\\slaveActive_%s" % socket.gethostname()					# path for the RenderSlave active file. The modifing date is used to tell wether the slave is running

		if os.path.exists(slaveActive) and float(os.stat(slaveActive).st_size/1024.0) > 10:
			open(slaveActive, "w").close()

		with open(slaveActive, "a") as actFile:
			actFile.write(" ")


	# open a questionbox, which asks the user if this PC should start rendering.
	@err_decorator
	def openActiveQuestion(self):
		if hasattr(self, "questionMsg") and self.questionMsg.isVisible():
			self.writeLog("Question window is already open")
			return 0

		if self.getIniSetting("prerenderwaittime") is None:
			self.getIniSetting("prerenderwaittime", setval=True, value=self.prerenderwaittime)
		else:
			self.prerenderwaittime = self.getIniSetting("prerenderwaittime", stype="int")

		if self.prerenderwaittime <= 0:
			return 1

		self.writeLog("open Question window")

		self.questionMsg = counterMessageBox(self.prerenderwaittime)
		self.questionMsg.setWindowIcon(self.slaveIcon)
		self.questionMsg.setWindowFlags(self.questionMsg.windowFlags() | Qt.WindowStaysOnTopHint)
		self.questionMsg.setFocus()
		result = self.questionMsg.exec_()

		if result == 0:
			self.writeLog("User pressed active button - slave paused for 60 min", 1)
			if hasattr(self, "msg") and self.msg.isVisible():
				self.msg.closeEvent = self.msg.origCloseEvent
				self.msg.close()

			self.communicateOut(["taskUpdate", self.curjob["code"], self.curTask, "ready", "", "", ""])
			self.pauseSlave(60)

		return result


	# evaluates the command parameter in the settings file
	@err_decorator
	def checkCommandSetting(self):
		val = self.getIniSetting("command")
		self.getIniSetting("command", setval=True)
		if val is not None and val != "":
			self.writeLog("checkCommands - execute: %s" % val, 1)
			try:
				exec(val)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR - checkCommandSetting - %s - %s - %s - %s" % (val, str(e), exc_type, exc_tb.tb_lineno), 3)


	# evaluates command files in the communication folder
	@err_decorator
	def checkCmds(self):
		if not os.path.exists(self.slaveComPath):
			self.writeWarning("Communication path does not exist", 2)
			self.logicTimer.start(self.updateTime*1000)
			return False

		for i in sorted(os.listdir(self.slaveComPath)):
			if not i.startswith("slaveIn_"):
				continue

			cmFile = os.path.join(self.slaveComPath, i)
			with open(cmFile, 'r') as comFile:
				cmdText = comFile.read()

			command = None
			try:
				command = eval(cmdText)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR - checkCmds - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), 3)

			self.handleCmd(command, cmFile)

#			self.lastConnectionTime = time.time()

			self.remove(cmFile)


	# handles different types of commands
	@err_decorator
	def handleCmd(self, command, cmFile):
		self.writeLog("handle cmd: %s" % command)

		if command is not None and type(command) == list:
			if command[0] == "clearLog":
				self.clearLog()

			elif command[0] == "setSetting":
				settingName = command[1]
				settingVal = command[2]

				section = "settings"

				if not os.path.exists(self.slaveIni):
					self.writeLog("ERROR - handle cmd - slaveIni doesn't exist.", 2)
					return

				self.getIniSetting(settingName, setval=True, value=settingVal)

				self.writeLog("set config setting - %s: %s" % (settingName, settingVal), 1)


			elif command[0] == "renderTask":
				if time.time() - os.path.getmtime(cmFile) < 60*15:
					self.renderTasks.append({"code": command[1], "name": command[2], "task": command[3]})
				else:
					self.communicateOut(["taskUpdate", command[1], command[3], "ready", "", "", ""])
					self.writeLog("render job expired - %s: %s" % (command[1], command[2]), 1)

			elif command[0] == "cancelTask":
				cJobCode = command[1]
				cTaskNum = command[2]

				self.renderTasks = [x for x in self.renderTasks if not (x["code"] == cJobCode and x["task"] == cTaskNum)]

				if self.curjob["code"] == cJobCode and self.curTask == cTaskNum:
					self.writeLog("cancel task command recieved: %s - %s" % (cJobCode, cTaskNum), 1)
					self.stopRender()

			elif command[0] == "deleteWarning":
				warnText = command[1]
				warnTime = command[2]

				if not os.path.exists(self.slaveWarningsIni):
					self.writeLog("ERROR - handle cmd - slave warningfile doesn't exist.", 2)
					return None

				warningConfig = ConfigParser()
				warningConfig.read(self.slaveWarningsIni)

				warnings = []
				if warningConfig.has_section("warnings"):
					for i in warningConfig.options("warnings"):
						warnings.append(eval(warningConfig.get("warnings", i)))

					warnPrev = len(warnings)
					warnings = [x for x in warnings if not (x[0] == warnText and x[1] == warnTime)]

					if warnPrev != len(warnings):
						self.writeLog("warning deleted", 1)

				warningConfig = ConfigParser()
				warningConfig.add_section("warnings")
				for idx, val in enumerate(warnings):
					warningConfig.set("warnings", "warning%s" % idx, val)

				with open(self.slaveWarningsIni, 'w') as inifile:
					warningConfig.write(inifile)

			elif command[0] == "clearWarnings":
				if not os.path.exists(self.slaveWarningsIni):
					self.writeLog("ERROR - handle cmd - slave warningfile doesn't exist.", 2)
					return None

				with open(self.slaveWarningsIni, 'w') as inifile:
					inifile.write("[warnings]")

			elif command[0] == "checkConnection":
				pass
			elif command[0] == "exitSlave":
				self.remove(cmFile)
				self.exitLogic()
			else:
				self.writeLog("unknown command: %s" % command, 1)


	# checks wether this PC is allowed to start rendering
	@err_decorator
	def preRenderCheck(self):
		# enabled/paused
		if self.slaveState == "disabled":
			self.writeLog("slave is disabled", 1)
			return [False, 0]
		elif self.slaveState == "paused":
			if QDateTime.currentDateTime() < self.pauseEnd:
				return [False, self.updateTime]


		# still rendering
		if self.slaveState == "rendering":
			self.writeLog("still rendering")
			return [False, self.updateTime]


		#restperiod
		if self.checkRest():
			self.setState("rest")
			self.writeLog("slave in rest period")
			return [False, self.updateTime]


		# max CPU usage		
		if self.getIniSetting("maxCPU") is None:
			self.getIniSetting("maxCPU", setval=True, value=self.maxCPU)
		else:
			self.maxCPU = self.getIniSetting("maxCPU", stype="int")

		response = psutil.cpu_percent(interval=1)
		try:
			if response > self.maxCPU:
				self.writeLog("processor usage is over %s%%" % self.maxCPU, 1)
				return [False, self.updateTime]
		except:
			self.writeLog("unable to measure processor usage. %s" % response, 2)


		# cursor check
		cresult = self.checkCursor()
		if cresult > 0:
			return [False, cresult]


		return [True]


	# checks if the rest period is active
	@err_decorator
	def checkRest(self):
		if self.getIniSetting("restPeriod") is None:
			self.getIniSetting("restPeriod", setval=True, value=str([self.useRestPeriod, self.startRP, self.endRP]))
		else:
			curRest = self.getIniSetting("restPeriod")
			try:
				restData = eval(curRest)
				self.useRestPeriod = restData[0]
				self.startRP = restData[1]
				self.endRP = restData[2]
			except:
				self.writeLog("unable to read rest period: %s" % curRest, 2)

		restActive = self.useRestPeriod and int(time.strftime("%H")) in range(self.startRP, self.endRP)
		return restActive


	# checks if the pc is beeing used by comparing the cursor position over time
	@err_decorator
	def checkCursor(self):
		if self.getIniSetting("cursorcheck", stype="bool"):
			self.writeLog("startCursorCheck")
			if self.cursorCheckPos is None:
				self.cursorCheckPos = QCursor.pos()
				return 15

			self.userMovedMouse = not (self.cursorCheckPos.x() == QCursor.pos().x() and self.cursorCheckPos.y() == QCursor.pos().y())
			if self.userMovedMouse:
				level = 1
				self.writeLog("cursorCheck positions: [%s, %s] - [%s, %s]" % (self.cursorCheckPos.x(), self.cursorCheckPos.y(), QCursor.pos().x(), QCursor.pos().y()), 0)
			else:
				level = 0

			self.cursorCheckPos = None

			self.writeLog("endcursorCheck - User active: %s" % self.userMovedMouse, level)
			if self.userMovedMouse:
				self.setState("userActive")
				return self.updateTime
			else:
				self.setState("idle")
		elif self.slaveState == "userActive":
			self.setState("idle")

		return 0


	# starts a render job
	@err_decorator
	def startRenderJob(self, command):
		jobCode = command["code"]
		jobName = command["name"]
		taskName = command["task"]

		if self.interrupted:
			self.interrupted = False

		localPath = os.path.join(self.localSlavePath, "Jobs", jobCode, "JobFiles")
		jobPath = os.path.join(self.slavePath, "AssignedJobs", jobCode, "JobFiles")

		jobConfig = ConfigParser()
		jobIni = os.path.join(os.path.dirname(jobPath), "PandoraJob.ini")
		if not os.path.exists(jobIni):
			self.writeLog("Warning - JobIni does not exist %s" % jobCode, 2)
			return

		jobConfig.read(jobIni)

		jobData = {}
		for k in jobConfig.options("jobglobals"):
			jobData[k] = jobConfig.get("jobglobals", k)

		for k in jobConfig.options("information"):
			jobData[k] = jobConfig.get("information", k)

		if jobConfig.has_option("jobtasks", taskName):
			taskData = eval(jobConfig.get("jobtasks", taskName))
		else:
			self.writeLog("could not find assigned task", 2)
			return

		if "jobname" in jobData:
			jobName = jobData["jobname"]
		else:
			self.writeLog("Warning - No jobname in %s config" % jobCode, 2)
			return True

		if "scenename" in jobData:
			sceneName = jobData["scenename"]
		else:
			self.writeLog("Warning - No scenename in %s config" % jobName, 2)
			return True

		if "program" not in jobData:
			self.writeLog("Warning - No program is defined in %s config" % jobName, 2)
			return True

		if "projectname" not in jobData:
			self.writeLog("Warning - No Projectname is defined in %s config" % jobName, 2)
			return True

		if "outputbase" not in jobData:
			self.writeLog("Warning - No Outputbase is defined in %s config" % jobName, 2)
			return True

		if "jobdependecies" in jobData:
			depsFinished = [True]
			jobDeps = eval(jobData["jobdependecies"])
			for jDep in jobDeps:
				if len(jDep) == 2:
					depName = jDep[0]
					if self.localmode:
						depConf = os.path.join(os.path.join(self.localSlavePath, "Jobs", depName, "PandoraJob.ini"))
						if not os.path.exists(depConf):
							self.writeLog("Warning - dependent JobIni does not exist %s" % depConf, 2)
							return

						depConfig = ConfigParser()
						depConfig.read(depConf)

						if depConfig.has_option("information", "outputpath") and depConfig.get("information", "outputpath") != "":
							depPath = os.path.dirname(depConfig.get("information", "outputpath"))
						else:
							return
					else:
						depPath = os.path.join(os.path.join(self.localSlavePath, "RenderOutput", depName))

					if not os.path.exists(depPath):
						self.writeLog("Warning - For job %s the dependent job %s is missing." % (jobName, depName), 2)
						return True

		sceneFile = os.path.join(localPath, sceneName)
		self.waitingForFiles = False

		if "filecount" in jobData:
			expNum = int(jobData["filecount"])

			if "projectassets" in jobData:
				passets = eval(jobData["projectassets"])[1:]
				pName = jobData["projectname"]
				paFolder = os.path.join(self.slavePath, "ProjectAssets", pName)

				epAssets = []
				for m in passets:
					aPath = os.path.join(paFolder, m[0])

					if not os.path.exists(aPath) or int(os.path.getmtime(aPath)) != int(m[1]):
						self.writeLog("Project asset missing or outdated: %s" % (aPath))
						continue

					epAssets.append(aPath)
						
				expNum -= len(epAssets)

			if os.path.exists(jobPath):
				curNum = len(os.listdir(jobPath))
			else:
				curNum = 0

			if curNum < expNum:
				self.writeLog("Not all required files are already available. %s %s from %s" % (sceneName, curNum, expNum), 1)
				self.waitingForFiles = True
				return

		if self.localmode:
			basePath = jobData["outputbase"]
		else:
			basePath = os.path.join(self.localSlavePath, "RenderOutput", jobCode, jobData["projectname"])

		self.curjob = {"code": jobCode, "name": jobName}
		self.curTask = taskName
		self.curJobData = jobData

		if not self.userAsked:
			result = self.openActiveQuestion()
			if result == 0:
				return True

		showinterruptwindow = self.getIniSetting("showinterruptwindow", stype="bool")
		if self.getIniSetting("showinterruptwindow") is None:
			self.getIniSetting("showinterruptwindow", setval=True, value="True")
		else:
			showinterruptwindow = self.getIniSetting("showinterruptwindow", stype="bool")

		if showinterruptwindow and not (hasattr(self, "msg") and self.msg.isVisible()):
			self.msg = QMessageBox(QMessageBox.Information, "Pandora RenderSlave", "Please press OK if you want to use this PC.")
			bugButton = self.msg.addButton("bug", QMessageBox.RejectRole)
			self.msg.addButton("OK", QMessageBox.AcceptRole)
			self.msg.accepted.connect(lambda: self.stopRender(msgPressed=True))
			self.msg.setModal(True)
			self.msg.setWindowIcon(self.slaveIcon)
			self.msg.origCloseEvent = self.msg.closeEvent
			self.msg.closeEvent = self.ignoreEvent
			self.msg.setWindowFlags(self.msg.windowFlags() | Qt.WindowStaysOnTopHint)
			bugButton.setVisible(False)
			self.msg.setFocus()
			self.msg.show()

		if not os.path.exists(localPath):
			shutil.copytree(os.path.join(self.slavePath, "AssignedJobs", jobCode), os.path.dirname(localPath))

		if "projectassets" in jobData:
			for k in epAssets:
				try:
					shutil.copy2(k, localPath)
				except:
					self.writeLog("Could not copy file to Job folder: %s %s %s" % (jobData["projectname"], k, jobName), 2)

		self.taskStartTime = time.time()

		self.setState("rendering")
		self.getIniSetting("curjob", section='slaveinfo', setval=True, value="%s (%s)" % (jobName, taskName))

		self.communicateOut(["taskUpdate", jobCode, taskName, self.slaveState, "", self.taskStartTime, ""])

		self.userAsked = True
		self.taskFailed = False

		self.writeLog("starting %s from job %s" % (taskName, jobName), 1)

		if jobData["program"] == "Houdini":
			result = self.houStartJob(sceneFile=sceneFile, startFrame=taskData[0], endFrame=taskData[1], jobData=jobData)
		elif jobData["program"] == "3dsMax":
			result = self.maxStartJob(sceneFile=sceneFile, startFrame=taskData[0], endFrame=taskData[1], jobData=jobData)
		elif jobData["program"] == "Maya":
			result = self.mayaStartJob(sceneFile=sceneFile, startFrame=taskData[0], endFrame=taskData[1], jobData=jobData)
		elif jobData["program"] == "Blender":
			result = self.bldStartJob(sceneFile=sceneFile, startFrame=taskData[0], endFrame=taskData[1], jobData=jobData)
		else:
			self.writeLog("unknown scene type: %s" % os.path.splitext(sceneName)[1], 2)
			self.renderingFailed()
			self.setState("idle")

		return True


	# stops any renderjob if there is one active
	@err_decorator
	def stopRender(self, msgPressed=False):
		self.userAsked = False
		self.interrupted = True
		self.cursorCheckPos = None

		try:
			proc = psutil.Process(self.renderProc.pid)
			for child in proc.children():
				child.kill()
			proc.kill()
		except:
			self.interrupted = False

		if hasattr(self, "msg") and self.msg.isVisible():
			self.msg.closeEvent = self.msg.origCloseEvent
			self.msg.close()

		if hasattr(self, "questionMsg") and self.questionMsg.isVisible():
			self.questionMsg.close()

		if self.slaveState == "rendering":
			self.setState("idle")

		self.writeLog("stopRender - msgPressed = %s" % msgPressed, 1)

		if msgPressed:
			self.pauseSlave(60, stop=False)


	# check for newer script versions
	@err_decorator
	def checkForUpdates(self):
		#logic update
		latestFile = self.slavePath + "\\Scripts\\%s\\PandoraSlaveLogic.py" % socket.gethostname()
		if not os.path.exists(latestFile):
			latestFile = os.path.join(os.path.dirname(os.path.dirname(latestFile)), os.path.basename(latestFile))

		if os.path.exists(latestFile):
			curFileDate = int(os.path.getmtime(os.path.abspath(__file__)))
			latestFileDate = int(os.path.getmtime(latestFile))

			if curFileDate < latestFileDate:
				self.writeLog("restart for updating", 1)
				shutil.copy2(latestFile, os.path.abspath(__file__))
				self.restartLogic()
			elif curFileDate > latestFileDate:
				self.writeWarning("local SlaveLogic.py is newer than the global", 2)

		#startHouJob update
		latestFile = self.slavePath + "\\Scripts\\%s\\PandoraStartHouJob.py" % socket.gethostname()
		if not os.path.exists(latestFile):
			latestFile = os.path.join(os.path.dirname(os.path.dirname(latestFile)), os.path.basename(latestFile))

		curFile = os.path.dirname(os.path.abspath(__file__)) + "\\PandoraStartHouJob.py"
		if os.path.exists(curFile):
			curFileDate = int(os.path.getmtime(curFile))
		else:
			curFileDate = 0

		if os.path.exists(latestFile):
			latestFileDate = int(os.path.getmtime(latestFile))

			if curFileDate < latestFileDate:
				self.writeLog("updating 'PandoraStartHouJob.py'", 1)
				try:
					shutil.copy2(latestFile, curFile)
				except:
					pass

			elif curFileDate > latestFileDate:
				self.writeWarning("local PandoraStartHouJob.py is newer than the global", 2)


	# start the thread for the rendering process
	@err_decorator
	def startRenderThread(self, pOpenArgs, jData, prog, decode=False):
		def runInThread(popenArgs, jobData, prog, decode):
			try:
				self.writeLog("call " + prog, 1)
			#	self.writeLog(popenArgs, 1)
				self.renderProc = subprocess.Popen(popenArgs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

				def readStdout(prog, decode):
					try:
						for line in iter(self.renderProc.stdout.readline, ''):
							if decode:
								line = line.replace('\x00', "")

							if "Error" in line or "ERROR" in line:
								#if prog == "maya" and (" No module named rsmaya.xgen" in line or " (kInvalidParameter): No element at given index" in line):
								#	self.writeLog(line, 2)
								#else:
								logLevel = 2
								#	self.taskFailed = True
							else:
								logLevel = 1

								#reduce blender logdata
								if prog == "blender" and line.startswith("Fra:") and " | Time:" in line and " | Scene" in line:
									continue

							self.writeLog(line.strip(), logLevel)

					except Exception as e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						self.writeLog("ERROR - readStdout - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), 3)

				def readStderr(prog, decode):
					try:
						for line in iter(self.renderProc.stderr.readline, ''):
							if decode:
								line = line.replace('\x00', "")

							line = line.strip()

							if line == "" or (prog == "maya" and line.startswith("Starting \"") and line.endswith("mayabatch.exe\"")):
								continue

							line = "stderr - " + line

							if prog == "max":
								self.writeLog(line, 2)
							elif prog == "maya":
								if " (kInvalidParameter): No element at given index" in line:
									self.writeLog(line, 1)
								else:
									self.writeLog(line, 2)
							elif prog == "houdini":
								if "Unable to load HFS OpenCL platform." in line:
									self.writeLog(line, 1)
								else:
									self.writeLog(line, 2)
							elif prog == "blender":
								if ("AL lib: (EE) UpdateDeviceParams: Failed to set 44100hz, got 48000hz instead" in line) or ("Could not open" in line) or ("Unable to open" in line) or ("Warning: edge " in line and "appears twice, correcting" in line):
									self.writeLog(line, 1)
								else:
									self.writeLog(line, 2)
							else:
								self.writeLog(line, 3)
								self.taskFailed = True

					except Exception as e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						self.writeLog("ERROR - readStderr - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), 3)

				rothread = threading.Thread(target=readStdout, args=(prog, decode))
				rothread.start()
				rethread = threading.Thread(target=readStderr, args=(prog, decode))
				rethread.start()
			
				self.renderProc.wait()
			#	self.writeLog(self.renderProc.communicate()[0].decode('utf-16'))
				self.finishedJob(jobData)
				return

			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR - runInThread - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), 3)
				self.renderingFailed()

		thread = threading.Thread(target=runInThread, args=(pOpenArgs, jData, prog, decode))
		thread.start()

		self.writeLog("thread started", 0)


	# find the location where Houdini is installed
	def getHoudiniPath(self, version=None):
		try:
			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Side Effects Software",
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)
			if version is None:
				validVersion = (_winreg.QueryValueEx(key, "ActiveVersion"))[0]
			else:
				houVersions = []
				try:
					i = 0
					while True:
						houVers = _winreg.EnumKey(key, i)
						if houVers.startswith("Houdini "):
							houVersions.append(houVers.replace("Houdini ", ""))
						i += 1
				except WindowsError:
					pass

				simVersions = []
				for i in houVersions:
					versData = i.split(".")
					if len(versData) == 3 and versData[0] == version.split(".")[0] and versData[1] == version.split(".")[1]:
						simVersions.append(i)

				if version in houVersions:
					validVersion = version
				elif len(simVersions) > 0:
					validVersion = simVersions[-1]
				elif len(houVersions) > 0:
					validVersion = houVersions[-1]
				else:
					self.writeLog("No Houdini found in registry", 0)
					return None

			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Side Effects Software\\Houdini " + validVersion,
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			return (_winreg.QueryValueEx(key, "InstallPath"))[0]

		except Exception as e:
			return None


	# find the location where 3ds Max is installed
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

			return installDir
		except:
			return None


	# find the location where Maya is installed
	def getMayaPath(self, version=None):
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
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			installDir = (_winreg.QueryValueEx(key, "MAYA_INSTALL_LOCATION"))[0]

			return installDir

		except Exception as e:
			return None


	# find the location where Blender is installed
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
				return None

		except:
			return None


	# start a Houdini render job
	@err_decorator
	def houStartJob(self, sceneFile="", startFrame=0, endFrame=0, jobData={}):
		self.writeLog("starting houdini job. " + self.curjob["name"], 0)

		houOverride = self.getPConfig("dccoverrides", "houdinioverride")
		houOverridePath = self.getPConfig("dccoverrides", "houdinipath")

		if houOverride == "True" and houOverridePath is not None and os.path.exists(houOverridePath):
			houPath = houOverridePath
		else:
			if "programversion" in jobData:
				houPath = self.getHoudiniPath(jobData["programversion"])
			else:
				houPath = self.getHoudiniPath()

			if houPath is None:
				self.writeLog("no Houdini installation found", 3)
				self.renderingFailed()
				return "skipped"

			houPath = os.path.join(houPath, "bin\\hython.exe")

		if "rendernode" not in jobData:
			self.writeLog("no renderNode specified", 2)
			self.renderingFailed()
			return False

		if "outputpath" in jobData:
			curOutput = jobData["outputpath"]
			if self.localmode:
				newOutput = curOutput
			else:
				newOutput = os.path.join(self.localSlavePath, "RenderOutput", self.curjob["code"], os.path.basename(os.path.dirname(curOutput)), os.path.basename(curOutput))
			outName = "-o %s" % newOutput.replace("\\", "/")
			try:
				os.makedirs(os.path.dirname(newOutput))
			except:
				pass
		else:
			self.writeLog("no outputpath specified", 2)
			self.renderingFailed()
			return False

		if not os.path.exists(sceneFile):
			self.writeLog("scenefile does not exist", 2)
			self.renderingFailed()
			return False

		if "savedbasepath" not in jobData:
			self.writeLog("savedBasePath is not defined", 2)
			self.renderingFailed()
			return False

		jobData["localmode"] = self.localmode

		popenArgs = [houPath, os.path.join(os.path.dirname(__file__), "PandoraStartHouJob.py"), sceneFile.replace("\\", "/"), str(startFrame), str(endFrame), str(jobData), str([self.localSlavePath, self.slavePath])]

		thread = self.startRenderThread(pOpenArgs=popenArgs, jData=jobData, prog="houdini")
		return thread


	# start a 3ds Max render job
	@err_decorator
	def maxStartJob(self, sceneFile="", startFrame=0, endFrame=0, jobData={}):
		self.writeLog("starting max job. " + self.curjob["name"], 0)

		maxOverride = self.getPConfig("dccoverrides", "maxoverride")
		maxOverridePath = self.getPConfig("dccoverrides", "maxpath")

		if maxOverride == "True" and maxOverridePath is not None and os.path.exists(maxOverridePath):
			maxPath = maxOverridePath
		else:
			maxPath = self.getMaxPath()

			if maxPath is None:
				self.writeLog("no 3ds Max installation found", 3)
				self.renderingFailed()
				return "skipped"

			maxPath = "%s" % os.path.join(maxPath, "3dsmaxcmd.exe")

		if "outputpath" in jobData:
			curOutput = jobData["outputpath"]
			if self.localmode:
				newOutput = curOutput
			else:
				newOutput = os.path.join(self.localSlavePath, "RenderOutput", self.curjob["code"], os.path.basename(os.path.dirname(curOutput)), os.path.basename(curOutput))
			outName = "-o=%s" % newOutput
			try:
				os.makedirs(os.path.dirname(newOutput))
			except:
				pass
		else:
			self.writeLog("no outputpath specified", 2)
			self.renderingFailed()
			return False

		if not os.path.exists(sceneFile):
			self.writeLog("scenefile does not exist", 2)
			self.renderingFailed()
			return False

		if "savedbasepath" not in jobData:
			self.writeLog("savedBasePath is not defined", 2)
			self.renderingFailed()
			return False

		preRendScript = """
rmg = maxOps.GetRenderElementMgr #Production
for i=0 to (rmg.NumRenderElements() - 1) do(
curElement = rmg.GetRenderElement i
curName = curElement.elementName
curPath = rmg.GetRenderElementFilename i
curFile = filenamefrompath curPath
newPath = \"%s\" + curFile 
newPath = substituteString newPath \"ELEMENTNAME\" curName
rmg.SetRenderElementFilename i newPath
makeDir (getFilenamePath newPath)
)""" % ( os.path.dirname(os.path.dirname(newOutput)).replace("\\", "\\\\") + "\\\\ELEMENTNAME\\\\")

		preScriptPath = os.path.join(os.path.dirname(os.path.dirname(sceneFile)), "preRenderScript.ms")

		open(preScriptPath, 'a').close()
		with open(preScriptPath, 'w') as scriptfile:
			scriptfile.write(preRendScript)

		popenArgs = [maxPath, outName, "-frames=%s-%s" %(str(startFrame), str(endFrame))]

		if "width" in jobData:
			popenArgs.append("-width=%s" % jobData["width"])

		if "height" in jobData:
			popenArgs.append("-height=%s" % jobData["height"])

		if "camera" in jobData:
			popenArgs.append("-cam=%s" % jobData["camera"])

		popenArgs += ["-gammaCorrection=1", "-preRenderScript=%s" % preScriptPath, sceneFile]

		invalidChars = ["#", "&"]
		for i in invalidChars:
			if i in sceneFile or i in maxPath or i in outName:
				self.writeLog("invalid characters found in the scenepath or in the outputpath: %s" % i, 2)
				self.renderingFailed()
				return False

		thread = self.startRenderThread(pOpenArgs=popenArgs, jData=jobData, prog="max", decode=True)
		return thread


	# start a Maya render job
	@err_decorator
	def mayaStartJob(self, sceneFile="", startFrame=0, endFrame=0, jobData={}):
		self.writeLog("starting maya job. " + self.curjob["name"], 0)

		mayaOverride = self.getPConfig("dccoverrides", "mayaoverride")
		mayaOverridePath = self.getPConfig("dccoverrides", "mayapath")

		if mayaOverride == "True" and mayaOverridePath is not None and os.path.exists(mayaOverridePath):
			mayaPath = mayaOverridePath
		else:
			if "programversion" in jobData:
				mayaPath = self.getMayaPath(jobData["programversion"])
			else:
				mayaPath = self.getMayaPath()

			if mayaPath is None:
				self.writeLog("no Maya installation found", 3)
				self.renderingFailed()
				return "skipped"

			mayaPath = "%s" % os.path.join(mayaPath, "bin", "Render.exe")

		if "outputpath" in jobData:
			curOutput = jobData["outputpath"]
			if self.localmode:
				newOutputDir = os.path.dirname(curOutput)
			else:
				newOutputDir = os.path.join(self.localSlavePath, "RenderOutput", self.curjob["code"], os.path.basename(os.path.dirname(curOutput)))
			newOutputFile = os.path.splitext(os.path.basename(curOutput))[0]
			try:
				os.makedirs(newOutputDir)
			except:
				pass
		else:
			self.writeLog("no outputpath specified", 2)
			self.renderingFailed()
			return False

		if not os.path.exists(sceneFile):
			self.writeLog("scenefile does not exist", 2)
			self.renderingFailed()
			return False

		if "savedbasepath" not in jobData:
			self.writeLog("savedBasePath is not defined", 2)
			self.renderingFailed()
			return False

		popenArgs = [mayaPath, "-r", "file", "-rd", newOutputDir, "-im", newOutputFile, "-s", str(startFrame), "-e", str(endFrame)]

		if "width" in jobData:
			popenArgs += ["-x", jobData["width"]]

		if "height" in jobData:
			popenArgs += ["-y", jobData["height"]]

		if "camera" in jobData:
			popenArgs += ["-cam", jobData["camera"]]

		popenArgs.append(sceneFile)

		thread = self.startRenderThread(pOpenArgs=popenArgs, jData=jobData, prog="maya")
		return thread


	# start a Blender job
	@err_decorator
	def bldStartJob(self, sceneFile="", startFrame=0, endFrame=0, jobData={}):
		self.writeLog("starting blender job. " + self.curjob["name"], 0)

		bldOverride = self.getPConfig("dccoverrides", "blenderoverride")
		bldOverridePath = self.getPConfig("dccoverrides", "blenderpath")

		if bldOverride == "True" and bldOverridePath is not None and os.path.exists(bldOverridePath):
			blenderPath = bldOverridePath
		else:
			blenderPath = self.getBlenderPath()

			if blenderPath is None:
				self.writeLog("no Blender installation found", 3)
				self.renderingFailed()
				return "skipped"

			blenderPath = "%s" % blenderPath

		if "outputpath" in jobData:
			curOutput = jobData["outputpath"]
			if self.localmode:
				newOutput = curOutput
			else:
				newOutput = os.path.join(self.localSlavePath, "RenderOutput", self.curjob["code"], os.path.basename(os.path.dirname(curOutput)), os.path.basename(curOutput))
			try:
				os.makedirs(os.path.dirname(newOutput))
			except:
				pass
		else:
			self.writeLog("no outputpath specified", 2)
			self.renderingFailed()
			return False

		if not os.path.exists(sceneFile):
			self.writeLog("scenefile does not exist", 2)
			self.renderingFailed()
			return False

		if "savedbasepath" not in jobData:
			self.writeLog("savedBasePath is not defined", 2)
			self.renderingFailed()
			return False

		preRendScript = """
import os, bpy

bpy.ops.file.unpack_all(method='USE_LOCAL')
bpy.ops.file.find_missing_files(\'EXEC_DEFAULT\', directory=\'%s\')

usePasses = False
if bpy.context.scene.node_tree is not None and bpy.context.scene.use_nodes:
	outNodes = [x for x in bpy.context.scene.node_tree.nodes if x.type == 'OUTPUT_FILE']
	rlayerNodes = [x for x in bpy.context.scene.node_tree.nodes if x.type == 'R_LAYERS']

	for m in outNodes:
		connections = []
		for idx, i in enumerate(m.inputs):
			if len(list(i.links)) > 0:
				connections.append([i.links[0], idx])

		m.base_path = os.path.dirname("%s")

		for i, idx in connections:
			passName = i.from_socket.name

			if passName == "Image":
				passName = "beauty"
	
			if i.from_node.type == "R_LAYERS":
				if len(rlayerNodes) > 1:
					passName = "%%s_%%s" %% (i.from_node.layer, passName)

			else:
				if hasattr(i.from_node, "label") and i.from_node.label != "":
					passName = i.from_node.label

			extensions = {"PNG": ".png", "JPEG": ".jpg", "JPEG2000": "jpg", "TARGA": ".tga", "TARGA_RAW": ".tga", "OPEN_EXR_MULTILAYER": ".exr", "OPEN_EXR": ".exr", "TIFF": ".tif" }
			nodeExt = extensions[m.format.file_format]
			curSlot = m.file_slots[idx]
			if curSlot.use_node_format:
				ext = nodeExt
			else:
				ext = extensions[curSlot.format.file_format]
			
#			curSlot.path = "../%%s/%%s" %% (passName, os.path.splitext(os.path.basename("%s"))[0].replace("beauty", passName) + ext)
			usePasses = True

if usePasses:
	tmpOutput = os.path.join(os.environ["temp"], "PrismRender", "tmp.####.exr")
	bpy.context.scene.render.filepath = tmpOutput
	if not os.path.exists(os.path.dirname(tmpOutput)):
		os.makedirs(os.path.dirname(tmpOutput))

bpy.ops.wm.save_mainfile()

""" % ( os.path.dirname(sceneFile), newOutput, newOutput)

		preScriptPath = os.path.join(os.path.dirname(os.path.dirname(sceneFile)), "preRenderScript.py")

		open(preScriptPath, 'a').close()
		with open(preScriptPath, 'w') as scriptfile:
			scriptfile.write(preRendScript.replace("\\", "\\\\"))

		popenArgs = [blenderPath, "--background", sceneFile, "--render-output", newOutput, "--frame-start", str(startFrame), "--frame-end", str(endFrame), "--python", preScriptPath]

		if "width" in jobData:
			popenArgs += ["--python-expr", "import bpy; bpy.context.scene.render.resolution_x=%s" % jobData["width"]]

		if "height" in jobData:
			popenArgs += ["--python-expr", "import bpy; bpy.context.scene.render.resolution_y=%s" % jobData["height"]]

		popenArgs.append("-a")

		thread = self.startRenderThread(pOpenArgs=popenArgs, jData=jobData, prog="blender")
		return thread


	# called when a renderjob is finished. Evaluates the result.
	@err_decorator
	def finishedJob(self, jobData):
		if self.localmode:
			basePath = jobData['outputbase']
		else:
			basePath = os.path.join(self.localSlavePath, "RenderOutput", self.curjob["code"])

		syncPath = os.path.join(self.slavePath, "Output", self.curjob["code"])

		hasNewOutput = False
		for i in os.walk(basePath):
			for k in i[2]:
				fpath = os.path.join(i[0], k)
				if int(os.path.getmtime(fpath)) > self.taskStartTime:
					hasNewOutput = True

		if self.interrupted:
			self.writeLog("rendering interrupted - %s - %s" % (self.curTask, self.curjob["name"]), 2)
		elif self.taskFailed:
			self.writeLog("rendering failed - %s - %s" % (self.curTask, self.curjob["name"]), 3)
		elif not hasNewOutput:
			self.writeLog("rendering didn't produce any output - %s - %s" % (self.curTask, self.curjob["name"]), 3)
		else:
			self.writeLog("rendering finished - %s - %s" % (self.curTask, self.curjob["name"]), 1)

		if hasNewOutput and not self.localmode and "uploadoutput" in jobData and eval(jobData["uploadoutput"]):
			relPath = os.path.dirname(os.path.dirname(jobData["outputpath"].replace(jobData["savedbasepath"], "")))
			if relPath.startswith("\\") or relPath.startswith("/"):
				relPath = relPath[1:]

			for i in os.walk(basePath):
				for k in i[2]:
					if k.endswith(".exr.lock"):
						continue

					filePath = os.path.join(i[0], k)
					targetPath = filePath.replace(basePath, syncPath)

					copyFile = True

					if os.path.exists(targetPath):
						curFileDate = int(os.path.getmtime(os.path.abspath(filePath)))
						targetFileDate = int(os.path.getmtime(targetPath))

						if curFileDate <= targetFileDate:
							copyFile = False

					if copyFile:
						folderExists = True
						if not os.path.exists(os.path.dirname(targetPath)):
							try:
								os.makedirs(os.path.dirname(targetPath))
							except:
								self.writeLog("could not create upload folder", 2)
								folderExists = False

						if folderExists:
							try:
								shutil.copy2(filePath, targetPath)
							except Exception as e:
								self.writeLog("ERROR occured while copying files %s %s %s" % (e, filePath, targetPath) , 3)

			self.writeLog("uploading files", 1)


		if self.interrupted:
			self.communicateOut(["taskUpdate", self.curjob["code"], self.curTask, "ready", "", "", ""])
			self.interrupted = False
		else:
			elapsed = time.time() - self.taskStartTime
			hours = int(elapsed/3600)
			elapsed = elapsed - (hours*3600)
			minutes = int(elapsed/60)
			elapsed = elapsed - (minutes*60)
			seconds = int(elapsed)
			taskTime = "%s:%s:%s" % (format(hours, '02'), format(minutes, '02'), format(seconds, '02'))

			outputNum = -1
			if self.taskFailed or not hasNewOutput:
				status = "error"
				taskResult = "failed"
			else:
				status = "finished"
				taskResult = "completed"

				outputNum = 0
				for i in os.walk(syncPath):
					outputNum += len(i[2])

					for k in i[2]:
						if os.path.splitext(k)[1] not in [".exr", "jpg", ".png", ".bgeo", ".abc", ".tif", ".tiff", ".tga"]:
							self.writeLog("unknown fileoutput type: %s" % (k), 2)

			cmd = ["taskUpdate", self.curjob["code"], self.curTask, status, taskTime, self.taskStartTime, time.time(), outputNum]
			self.communicateOut(cmd)

			self.setState("idle")

			self.writeLog("task " + taskResult, 1)

			if self.interrupted:
				self.interrupted = False

		self.renderTasks = [x for x in self.renderTasks if not (x["code"] == self.curjob["code"] and x["task"] == self.curTask)]

		self.curjob = {"code":"", "name":""}
		self.curTask = ""
		self.curJobData = {}
		self.getIniSetting("curjob", section='slaveinfo', setval=True)


	# called by the user, if he wants to upload all renderings from the current job, before the job is finished
	@err_decorator
	def uploadCurJob(self):
		uploadedFiles = 0
		if self.curjob["code"] != "" and self.curJobData != {}:
			relPath = os.path.dirname(os.path.dirname(self.curJobData["outputpath"].replace(self.curJobData["savedbasepath"], "")))
			if relPath.startswith("\\") or relPath.startswith("/"):
				relPath = relPath[1:]
			syncPath = os.path.join(self.slavePath, "Output", self.curjob["code"], self.curJobData["projectname"], relPath)

			basePath = os.path.join(self.localSlavePath, "RenderOutput", self.curjob["code"], self.curJobData["projectname"])
			for i in os.walk(basePath):
				for k in i[2]:
					filePath = os.path.join(i[0], k)
					targetPath = filePath.replace(basePath, syncPath)
					if not os.path.exists(targetPath):
						folderExists = True
						if not os.path.exists(os.path.dirname(targetPath)):
							try:
								os.makedirs(os.path.dirname(targetPath))
							except:
								self.writeLog("could not create upload folder", 2)
								folderExists = False
						if folderExists:
							try:
								shutil.copy2(filePath, targetPath)
								uploadedFiles += 1
							except:
								self.writeLog("ERROR occured while copying files", 3)

		self.writeLog("uploaded files from current job (%s): %s" % (self.curjob["name"], uploadedFiles), 1)


	# called when the rendering failed and writes out the error
	@err_decorator
	def renderingFailed(self):
		self.stopRender()
		self.communicateOut(["taskUpdate", self.curjob["code"], self.curTask, "ready", "", "", ""])
		self.interrupted = False
		self.curjob = {"code": "", "name": ""}
		self.curTask = ""
		self.curJobData = {}
		self.getIniSetting("curjob", section='slaveinfo', setval=True)
		self.checkAssignments()



# true when this script is executed and not imported
if __name__ == "__main__":
	qapp = QApplication(sys.argv)

	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
	# set window icon
	appIcon = QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserInterfacesPandora", "pandora_slave.ico"))
	qapp.setWindowIcon(appIcon)
	qapp.setQuitOnLastWindowClosed(False)

	# check if already a Pandora slave process is running
	slaveProc = []
	for x in psutil.pids():
		try:
			if x != os.getpid() and os.path.basename(psutil.Process(x).exe()) ==  "PandoraSlave.exe":
				slaveProc.append(x)
		except:
			pass

	if len(slaveProc) > 0:
		if sys.argv[-1] == "forcestart":
			PROCNAME = 'PandoraSlave.exe'
			for pid in slaveProc:
				proc = psutil.Process(pid)
				proc.kill()
			sl = SlaveLogic()
			sys.exit(qapp.exec_())
		else:
			QMessageBox.warning(QWidget(), "Pandora RenderSlave", "Pandora RenderSlave is already running.")
			sys.exit()
	else:
		sl = SlaveLogic()
		sys.exit(qapp.exec_())