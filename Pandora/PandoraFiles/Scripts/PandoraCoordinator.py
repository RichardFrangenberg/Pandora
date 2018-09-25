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


import os

import sys, os, io, time, shutil, socket, traceback, subprocess
from functools import wraps
from ConfigParser import ConfigParser

try:
	import _winreg
	pndPath = os.path.join(os.getenv('localappdata'), "Pandora", "PythonLibs", "Renderslave")
	sys.path.append(pndPath)
	import psutil
except:
	pass


class PandoraCoordinator():

	def __init__(self):
		try:
			self.version = "v1.0.0"

			self.coordUpdateTime = 5 #seconds
			self.activeThres = 10 # time in min after a slave becomes inactive
			self.notifySlaveInterval = 10 # time in min in which interval a connection check is send to the slaves
			self.connectionCheckInterval = 20 # time in min in which interval a to check if a connection to the slave exists
			self.lastConnectionCheckTime = time.time()
			self.lastNotifyTime = time.time()

			pandoraConfig = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Config", "Pandora.ini")
			self.repPath = ""
			self.localmode = True
			self.restartGDriveEnabled = False

			if os.path.exists(pandoraConfig):
				pConfig = ConfigParser()
				pConfig.read(pandoraConfig)

				if pConfig.has_option("coordinator", "enabled") and pConfig.get("coordinator", "enabled") == "False":
					self.writeLog("coordinator is disabled. Closing Coordinator")
					return

				if pConfig.has_option("globals", "localmode"):
					lm = pConfig.get("globals", "localmode")
					self.localmode = lm == "True"

				if self.localmode:
					pathSection = "globals"
				else:
					pathSection = "coordinator"

				if not pConfig.has_option(pathSection, "rootpath"):
					self.writeLog("sync directory is not defined. Closing Coordinator")
					return

				syncDir = pConfig.get(pathSection, "rootpath")
				if not os.path.exists(syncDir):
					self.writeLog("sync directory doesn't exist. Closing Coordinator")
					return

				self.coordBasePath = os.path.join(syncDir, "PandoraFarm", "Scripts", "PandoraCoordinator")

				repoDir = pConfig.get("globals", "repositorypath")
				if repoDir is None or repoDir == "":
					self.writeLog("repository is invalid. Fallback to default repository location.")
				else:
					repoDir = os.path.join(repoDir, "Coordinator")
					if not os.path.exists(repoDir):
						try:
							os.makedirs(repoDir)
						except:
							pass

					if os.path.exists(repoDir):
						self.repPath = repoDir
						self.writeLog("set repository: %s" % self.repPath)
					else:
						self.writeLog("repository doesn't exist. Fallback to default repository location.")

				slScript = os.path.join(os.path.dirname(__file__), "PandoraSlaveLogic.py")
				hScript = os.path.join(os.path.dirname(__file__), "PandoraStartHouJob.py")

				tslScript = os.path.join(os.path.dirname(self.coordBasePath), "PandoraSlaves", "PandoraSlaveLogic.py")
				thScript = os.path.join(os.path.dirname(self.coordBasePath), "PandoraSlaves", "PandoraStartHouJob.py")

				if not os.path.exists(os.path.dirname(tslScript)):
					try:
						os.makedirs(os.path.dirname(tslScript))
					except:
						pass

				shutil.copy2(slScript, tslScript)
				shutil.copy2(hScript, thScript)
			else:
				self.coordBasePath = os.path.dirname(os.path.abspath(__file__))

			self.slPath = os.path.abspath(os.path.join(self.coordBasePath, os.pardir, os.pardir))

			self.coordLog = os.path.join(self.coordBasePath, "PandoraCoordinator_Log.txt")
			self.coordIni = os.path.join(self.coordBasePath, "PandoraCoordinator_Settings.ini")
			self.actSlvPath = os.path.join(self.coordBasePath, "ActiveSlaves.txt")
			self.coordWarningsIni = os.path.join(self.coordBasePath, "PandoraCoordinator_Warnings.ini")

			self.close = False
			self.tvRequests = []
			self.slaveContactTimes = {}
			self.renderingTasks = []
			self.collectTasks = {}
			self.jobDirs = []

			self.writeLog("starting Coordinator - %s" % self.version, 1)

			repConf = self.getIniSetting("repository")

			if repConf is not None and os.path.exists(repConf):
				self.repPath = repConf
				self.writeLog("set repository: %s" % self.repPath)

			if self.repPath == "":
				self.repPath = os.path.join(self.slPath, "JobRepository")
				self.writeLog("set repository: %s" % self.repPath)

			lmodeConf = self.getIniSetting("localmode")

			if lmodeConf is not None:
				self.localmode = lmodeConf == "True"
				self.writeLog("set localmode: %s" % self.localmode)

			self.pAssetPath = os.path.join(self.repPath, "ProjectAssets")
			self.jobPath = os.path.join(self.repPath, "Jobs")

			self.prioList = os.path.join(self.repPath, "PriorityList.txt")

			self.getGDrivePath()

			exitActive = os.path.join(self.coordBasePath, "EXIT.txt")
			exitInactive = os.path.join(self.coordBasePath, "EXIT-.txt")

			while not self.close:
				if os.path.exists(exitActive):
					try:
						os.rename(exitActive, exitInactive)
					except:
						pass
					break

				if not os.path.exists(exitInactive):
					open(exitInactive, "w").close()

				self.startCoordination()
				time.sleep(self.coordUpdateTime)

			self.writeLog("Coordinator closed", 1)
			self.notifyWorkstations()

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.writeLog("ERROR - init - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), 3)

		sys.exit()


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - PandoraCoordinator:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].writeLog(erStr, 3)

		return func_wrapper
			

	def writeLog(self, text, level=0):
	#	print text 
		if not hasattr(self, "coordLog") or not os.path.exists(self.coordLog):
			try:
				logPath = self.coordLog
				if not os.path.exists(os.path.dirname(self.coordLog)):
					os.makedirs(os.path.dirname(self.coordLog))
			except:
				logPath = os.path.join(os.path.dirname(__file__), "PandoraCoordinator_Log.txt")
		else:
			logPath = self.coordLog

		if hasattr(self, "coordIni"):
			debug = self.getIniSetting("debugMode", stype="bool")
			if debug is None:
				self.getIniSetting("debugmode", setval=True, value="False")
				debug = False
		else:
			debug = True

		if level==0 and not debug:
			return
		elif level > 1:
			self.writeWarning(text, level)

		with io.open(logPath, 'a', encoding='utf-16') as log:
			log.write(unicode("[%s] %s : %s\n" % (level, time.strftime("%d/%m/%y %X"), text)))

		#print "[%s] %s : %s\n" % (level, time.strftime("%d/%m/%y %X"), text)


	@err_decorator
	def writeWarning(self, text, level=2):
		if not os.path.exists(self.coordWarningsIni):
			try:
				open(self.coordWarningsIni, 'a').close()
			except:
				self.writeLog("cannot create warningIni", 2)
				return None

		warningConfig = ConfigParser()
		warningConfig.read(self.coordWarningsIni)

		warnings = []
		if warningConfig.has_section("warnings"):
			for i in warningConfig.options("warnings"):
				warnings.append(eval(warningConfig.get("warnings", i)))

			warnings = [x for x in warnings if x[0] != text]

		warnings.insert(0, [text, time.time(), level])

		warningConfig = ConfigParser()
		warningConfig.add_section("warnings")
		for idx, val in enumerate(warnings):
			warningConfig.set("warnings", "warning%s" % idx, val)

		with open(self.coordWarningsIni, 'w') as inifile:
			warningConfig.write(inifile)


	@err_decorator
	def checkCommands(self):
		val = self.getIniSetting("command")
		if val != "":
			self.getIniSetting("command", setval=True)

		if val is not None and val != "":
			self.writeLog("checkCommands - execute: %s" % val, 1)
			try:
				exec(val)
			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR - checkCommands - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), 3)


	@err_decorator
	def getIniSetting(self, setting, section="settings", stype="string", setval=False, value=""):
		if not os.path.exists(self.coordIni):
			self.coordConfig = ConfigParser()
			self.coordConfig.read(self.coordIni)
			self.coordConfig.add_section("settings")
			self.coordConfig.set("settings", "coordUpdateTime", str(self.coordUpdateTime))
			self.coordConfig.set("settings", "command", "")
			self.coordConfig.set("settings", "debugmode", "False")
			self.coordConfig.set("settings", "repository", "")
			self.coordConfig.set("settings", "notifySlaveInterval", "10")
			self.coordConfig.set("settings", "restartgdrive", "False")
			with open(self.coordIni, 'w') as inifile:
				self.coordConfig.write(inifile)
		else:
			self.coordConfig = ConfigParser()
			try:
				self.coordConfig.read(self.coordIni)
			except:
				self.writeWarning("unable to read coordSettings. (%s)" % setting, 2)
				return None

			if not self.coordConfig.has_section(section):
				self.coordConfig.add_section(section)

		if setval:
			self.coordConfig.set(section, setting, value)
			with open(self.coordIni, 'w') as inifile:
				self.coordConfig.write(inifile)
		else:
			if not self.coordConfig.has_option(section, setting):
				return None

			if stype == "string":
				return self.coordConfig.get(section, setting)
			elif stype == "int":
				return self.coordConfig.getint(section, setting)
			elif stype == "float":
				return self.coordConfig.getfloat(section, setting)
			elif stype == "bool":
				return self.coordConfig.getboolean(section, setting)


	@err_decorator
	def startCoordination(self):
		# checking slaves
		if os.path.exists(os.path.join(self.coordBasePath, "EXIT.txt")):
			return True

		self.checkCommands()

		newUTime = self.getIniSetting("coordUpdateTime", stype="int")
		if newUTime is None:
			self.getIniSetting("coordUpdateTime", setval=True, value=self.coordUpdateTime)
		elif newUTime != self.coordUpdateTime:
			self.writeLog("updating updateTime from %s to %s" % (self.coordUpdateTime, newUTime), 1)
			self.coordUpdateTime = newUTime

		newCInterval = self.getIniSetting("notifySlaveInterval", stype="int")
		if newCInterval is None:
			self.getIniSetting("notifySlaveInterval", setval=True, value=self.notifySlaveInterval)
		elif newCInterval != self.notifySlaveInterval:
			self.writeLog("updating notifySlaveInterval from %s to %s" % (self.notifySlaveInterval, newCInterval), 1)
			self.notifySlaveInterval = newCInterval

		rgdrive = self.getIniSetting("restartgdrive", stype="bool")
		if rgdrive is None:
			self.getIniSetting("restartgdrive", setval=True, value=self.restartGDriveEnabled)
		elif rgdrive != self.restartGDriveEnabled:
			self.writeLog("updating restartGDrive from %s to %s" % (self.restartGDriveEnabled, rgdrive), 1)
			self.restartGDriveEnabled = rgdrive

		self.activeSlaves = {}
		self.availableSlaves = []

		if not os.path.exists(self.jobPath):
			os.makedirs(self.jobPath)

		self.getJobAssignments()
		
		if not os.path.exists(os.path.join(self.slPath, "Slaves")):
			os.makedirs(os.path.join(self.slPath, "Slaves"))

		self.checkSlaves()
		with open(self.actSlvPath, "w") as actfile:
			actfile.write(str(self.slaveContactTimes))

		if self.localmode:
			self.checkConnection()
		self.checkRenderingTasks()
		self.getAvailableSlaves()
		self.assignJobs()
		self.checkTvRequests()
		if self.localmode:
			self.checkCollectTasks()
		self.notifyWorkstations()
		self.notifySlaves()

		self.writeLog("cycle finished")


	@err_decorator
	def handleCmd(self, cmFile, origin=""):
		with open(cmFile, 'r') as comFile:
			cmdText = comFile.read()
			command = None
			try:
				command = eval(cmdText)
			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR -- handleCmd evalCmd -- %s\n%s\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno, origin, cmdText), 3)

		if command is not None and type(command) == list:
			for i in range(1):
				if command[0] == "taskUpdate":
					if len(command) < 7:
						self.writeLog("ERROR - taskupdate has not enough information: %s" % (command), 1)
						continue

					jobCode = command[1]
					taskName = command[2]
					taskStatus = command[3]
					taskTime = command[4]
					taskStart = command[5]
					taskEnd = command[6]
					if taskStatus == "finished":
						outputFileNum = int(command[7])

					jobSettings = os.path.join(self.jobPath, jobCode, "PandoraJob.ini")

					if not os.path.exists(jobSettings):
						self.writeLog("ERROR - jobSettings don't exist %s (%s)" % (jobCode, origin), 3)
						continue

					jobConfig = ConfigParser()
					jobConfig.read(jobSettings)

					if jobConfig.has_option("information", "jobname"):
						jobName = jobConfig.get("information", "jobName")
					else:
						jobName = jobCode

					if not jobConfig.has_option("jobtasks", taskName):
						self.writeLog("ERROR - task is not listed %s - %s (%s)" % (jobName, taskName, origin), 3)
						continue

					taskData = eval(jobConfig.get("jobtasks", taskName))
					if type(taskData) != list or len(taskData) != 7 or (taskData[2] == "rendering" and taskData[3] != origin) or taskData[2] in ["finished", "disabled"]:
						self.writeLog("could not set taskdata on job %s for task %s - %s (%s)" % (jobName, taskName, command, origin), 1)
						continue

					if taskData[2] == "rendering" and [jobCode, taskName] in self.renderingTasks:
						self.renderingTasks.remove([jobCode, taskName])

					taskData[2] = taskStatus
					if taskStatus == "ready":
						taskData[3] = "unassigned"
					else:
						taskData[3] = origin
					taskData[4] = taskTime
					taskData[5] = taskStart
					taskData[6] = taskEnd
					jobConfig.set('jobtasks', taskName, taskData)

					if taskStatus == "rendering" and [jobCode, taskName] not in self.renderingTasks:
						self.renderingTasks.append([jobCode, taskName])

					with open(jobSettings, 'w') as jobInifile:
						jobConfig.write(jobInifile)
				
					if taskStatus == "finished" and outputFileNum > 0 and self.localmode:
						if self.collectTasks.has_key(origin):
							self.collectTasks[origin][jobCode] = outputFileNum
						else:
							self.collectTasks[origin] = {jobCode: outputFileNum}

					self.writeLog("updated Task %s in %s to %s (%s)" % (taskName, jobName, str(taskData), origin), 1)

				elif command[0] == "setSetting":
					settingType = command[1]
					parentName = command[2]
					settingName = command[3]
					settingVal = command[4]

					if settingType == "Job":
						settingsPath = os.path.join(self.jobPath, parentName, "PandoraJob.ini")
						section = "jobglobals"
					elif settingType == "Slave":
						self.sendCommand(parentName, ["setSetting", settingName, settingVal])
						self.writeLog("set config setting %s - %s: %s (%s)" % (parentName, settingName, settingVal, origin), 1)

						if settingType == "Slave" and settingName in ["command", "corecommand"] and settingVal == "self.startTeamviewer()":
							if len([x for x in self.tvRequests if x["slave"] == parentName and x["workstation"] == origin]) == 0:
								self.tvRequests.append({"slave": parentName, "workstation":origin, "requestTime": time.time()})

						continue
					elif settingType == "Coordinator":
						settingsPath = self.coordIni
						section = "settings"

					if not os.path.exists(settingsPath):
						self.writeLog("ERROR - settingsPath doesn't exist %s (%s)" % (parentName, origin), 2)
						continue

					setConfig = ConfigParser()
					setConfig.read(settingsPath)

					if not setConfig.has_section(section):
						setConfig.add_section(section)

					setConfig.set(section, settingName, settingVal)

					with open(settingsPath, 'w') as settingsFile:
						setConfig.write(settingsFile)

					if settingType == "Job" and settingName == "priority":
						if not os.path.exists(self.prioList):
							open(self.prioList, 'a').close()

						jobs = ""
						added = False
						with open(self.prioList, 'r') as priofile:
							for line in priofile.readlines():
								jobData = eval(line)
								if jobData[0] < settingVal and not added:
									jobs += str([settingVal, parentName]) + "\n"
									added = True
								if jobData[1] != parentName:
									jobs += line

							if not added:
								jobs += str([settingVal, parentName]) + "\n"

						with open(self.prioList, 'w') as priofile:
							priofile.write(jobs)

					self.writeLog("set config setting %s - %s: %s (%s)" % (parentName, settingName, settingVal, origin), 1)

				elif command[0] == "deleteJob":
					if os.path.exists(self.prioList):
						with open(self.prioList, 'r') as priofile:
							prioText = ""
							for line in priofile.readlines():
								jobName = eval(line)[1]
								if command[1] != jobName:
									prioText += line
						with open(self.prioList, 'w') as priofile:
							priofile.write(prioText)
					else:
						self.writeLog("WARNING - priolist does not exist (%s)" % (origin), 2)

					jobPath = os.path.join(self.repPath, "Jobs", command[1])
					jobIni = os.path.join(jobPath, "PandoraJob.ini")

					projectName = ""
					jobName = command[1]

					if os.path.exists(jobIni):
						jobConfig = ConfigParser()
						jobConfig.read(jobIni)

						if jobConfig.has_option("information", "jobname"):
							jobName = jobConfig.get("information", "jobName")

						if jobConfig.has_option("information", "projectname"):
							projectName = jobConfig.get("information", "projectname")

					if os.path.exists(jobPath):
						shutil.rmtree(jobPath)
					else:
						self.writeLog("WARNING - job %s did not exist before deletion (%s)" % (jobName, origin), 2)

					for m in os.listdir(os.path.join(self.slPath, "Slaves")):
						jobFiles = os.path.join(self.slPath, "Slaves", m, "AssignedJobs", command[1])
						jobOutput = os.path.join(self.slPath, "Slaves", m, "Output", command[1])

						for k in [jobFiles, jobOutput]:
							if os.path.exists(k):
								try:
									shutil.rmtree(k)
								except:
									self.writeLog("ERROR - cannot remove folder: %s (%s)" % (k, origin), 3)

					for m in os.listdir(os.path.join(self.slPath, "Workstations")):
						if not m.startswith("WS_"):
							continue

						logFile = os.path.join(self.slPath, "Workstations", m, "Logs", "Jobs", "PandoraJob.ini")
						jobOutput = os.path.join(self.slPath, "Workstations", m, "RenderOutput", projectName, command[1])
						for k in [logFile, jobOutput]:
							if os.path.exists(k):
								try:
									if os.path.isfile(k):
										os.remove(k)
									else:
										shutil.rmtree(k)
								except:
									self.writeLog("ERROR - cannot remove file(s): %s (%s)" % (k, origin), 3)

					self.writeLog("deleted Job %s (%s)" % (jobName, origin), 1)

				elif command[0] == "restartTask":
					jobCode = command[1]
					taskNum = command[2]

					jobIni = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.ini")
					jconfig = ConfigParser()
					jconfig.read(jobIni)

					if jconfig.has_option("information", "jobname"):
						jobName = jconfig.get("information", "jobName")
					else:
						jobName = jobCode

					if not jconfig.has_option("jobtasks", "task%s" % taskNum):
						self.writeLog("Job %s has no task %s (%s)" % (jobName, taskNum, origin), 2)
						continue

					taskData = eval(jconfig.get('jobtasks', "task%s" % taskNum))

					if taskData[2] in ["rendering", "assigned"]:
						self.sendCommand(taskData[3], ["cancelTask", jobCode, "task%s" % taskNum])
					
					taskData[2] = "ready"
					taskData[3] = "unassigned"
					taskData[4] = ""
					taskData[5] = ""
					taskData[6] = ""
					jconfig.set('jobtasks', "task%s" % taskNum , str(taskData))

					with open(jobIni, 'w') as inifile:
						jconfig.write(inifile)

					self.writeLog("restarted Task %s from Job %s (%s)" % (taskNum, jobName, origin), 1)

				elif command[0] == "disableTask":
					jobCode = command[1]
					taskNum = command[2]
					enable = command[3]

					if enable:
						action = "enable"
					else:
						action = "disable"

					jobIni = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.ini")
					jconfig = ConfigParser()
					jconfig.read(jobIni)

					if jconfig.has_option("information", "jobname"):
						jobName = jconfig.get("information", "jobName")
					else:
						jobName = jobCode

					if not jconfig.has_option("jobtasks", "task%s" % taskNum):
						self.writeLog("Job %s has no task %s (%s)" % (jobName, taskNum, origin), 2)
						continue

					taskData = eval(jconfig.get('jobtasks', "task%s" % taskNum))
					if (taskData[2] != "disabled" and enable) or (taskData[2] == "disabled" and not enable) or taskData[2] in ["finished", "error"]:
						continue

					if enable:
						taskData[2] = "ready"
						taskData[3] = "unassigned"
					else:
						if taskData[2] in ["rendering", "assigned"]:
							self.sendCommand(taskData[3], ["cancelTask", jobCode, "task%s" % taskNum])

						taskData[2] = "disabled"
						taskData[3] = "unassigned"
						taskData[5] = ""
					jconfig.set('jobtasks', "task%s" % taskNum , str(taskData))

					with open(jobIni, 'w') as inifile:
						jconfig.write(inifile)

					self.writeLog("%sd task %s from Job %s (%s)" % (action, taskNum, jobName, origin), 1)

				elif command[0] == "deleteWarning":
					warnType = command[1]
					slaveName = command[2]
					warnText = command[3]
					warnTime = command[4]

					if warnType == "Coordinator":
						warningConfig = ConfigParser()
						warningConfig.read(self.coordWarningsIni)

						warnings = []
						if warningConfig.has_section("warnings"):
							for i in warningConfig.options("warnings"):
								warnings.append(eval(warningConfig.get("warnings", i)))

							warnings = [x for x in warnings if not (x[0] == warnText and x[1] == warnTime)]

						warningConfig = ConfigParser()
						warningConfig.add_section("warnings")
						for idx, val in enumerate(warnings):
							warningConfig.set("warnings", "warning%s" % idx, val)

						with open(self.coordWarningsIni, 'w') as inifile:
							warningConfig.write(inifile)

					elif warnType == "Slave":
						self.sendCommand(slaveName, ["deleteWarning", warnText, warnTime])

					if warnType == "Slave":
						self.writeLog("warning deleted: %s (%s)" % (slaveName, origin), 1)
					elif warnType == "Coordinator":
						self.writeLog("coordinator warning deleted (%s)" % origin, 1)

				elif command[0] == "clearWarnings":
					warnType = command[1]
					slaveName = command[2]

					if warnType == "Coordinator":
						with open(self.coordWarningsIni, 'w') as inifile:
							inifile.write("[warnings]")

					elif warnType == "Slave":
						self.sendCommand(slaveName, ["clearWarnings"])

					if warnType == "Slave":
						self.writeLog("warnings cleared: %s (%s)" % (slaveName, origin), 1)
					elif warnType == "Coordinator":
						self.writeLog("coordinator warnings cleared (%s)" % origin, 1)

				elif command[0] == "clearLog":
					logType = command[1]
					logName = command[2]

					if logType == "Coordinator":
						logPath = self.coordLog
						open(logPath, 'w').close()

					elif logType == "Slave":
						self.sendCommand(logName, ["clearLog"])

					self.writeLog("Cleared log for %s %s (%s)" % (logType, logName, origin), 1)


				elif command[0] == "collectJob":
					jobCode = command[1]

					jobIni = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.ini")
					jconfig = ConfigParser()
					jconfig.read(jobIni)

					if jconfig.has_option("information", "jobname"):
						jobName = jconfig.get("information", "jobName")
					else:
						jobName = jobCode

					copiedNum, errors, targetPath = self.collectOutput(jobCode=jobCode)

					collectStr = "Job %s output collected. %s files copied to %s" % (jobName, copiedNum, targetPath)
					if errors > 0:
						collectStr += " %s errors occured" % errors
						errorLvl = 3
					else:
						errorLvl = 1

					self.writeLog(collectStr + " (%s)" % (origin), errorLvl)

			try:
				os.remove(cmFile)
			except:
				self.writeLog("ERROR - cannot remove file: %s (%s)" % (cmFile, origin), 3)


	@err_decorator
	def searchUncollectedRnd(self):
		uncollRnds = {}

		slaveSyncPath = os.path.join(self.slPath, "Slaves")
		for i in os.listdir(slaveSyncPath):
			slOutput = os.path.join(slaveSyncPath, i, "Output")
			if os.path.exists(slOutput):
				for n in os.listdir(slOutput):
					if not uncollRnds.has_key(n):
						uncollRnds[n] = 0

					jobPath = os.path.join(slOutput, n)
					for k in os.walk(jobPath):
						for m in k[2]:
							filePath = os.path.join(k[0], m)
							relFilePath = filePath.replace(jobPath, "")
							while relFilePath.startswith("\\") or relFilePath.startswith("/"):
								relFilePath = relFilePath[1:]
							targetPath = os.path.join(os.path.dirname(self.slPath), "Projects", relFilePath)
							if not os.path.exists(targetPath):
								uncollRnds[n] += 1

		collectStr = "Uncollected renderings searched:\n"
		if len([x for x in uncollRnds.values() if x > 0]) == 0:
			collectStr += "no uncollected renderings found"
			errorLvl = 1
		else:
			for i in uncollRnds:
				if uncollRnds[i] > 0:
					collectStr += "%s: uncollected renderings: %s\n" % (i, uncollRnds[i])
			errorLvl = 1

		self.writeLog(collectStr, errorLvl)


	@err_decorator
	def getJobAssignments(self):
		if not os.path.exists(os.path.join(self.slPath, "Workstations")):
			self.writeWarning("Workstations folder doesn't exist (%s)" % (os.path.join(self.slPath, "Workstations")), 2)
			return

		for i in os.listdir(os.path.join(self.slPath, "Workstations")):
			try:
				if not os.path.isdir(os.path.join(self.slPath, "Workstations", i)) or not i.startswith("WS_"):
					continue

				cmdDir = os.path.join(self.slPath, "Workstations", i, "Commands")
				wsName = i[len("WS_"):]

				if os.path.exists(cmdDir):
					for k in sorted(os.listdir(cmdDir)):
						if not k.startswith("handlerOut_"):
							continue

						cmFile = os.path.join(cmdDir, k)
						self.handleCmd(cmFile, origin=wsName)

				jobDir = os.path.join(self.slPath, "Workstations", i, "JobSubmissions")

				if not os.path.exists(jobDir):
					#self.writeWarning("Job JobSubmission folder does not exist (%s)" % wsName, 2)
					continue

				for k in os.listdir(jobDir):
					if k == "ProjectAssets":
						continue

					jobCode = k

					jobIni = os.path.join(jobDir, jobCode, "PandoraJob.ini")
					if not os.path.exists(jobIni):
						self.writeWarning("Job Ini does not exist for job: %s (%s)" % (jobCode, wsName), 2)
						continue

					jobConfig = ConfigParser()
					jobConfig.read(jobIni)

					if jobConfig.has_option("information", "jobname"):
						jobName = jobConfig.get("information", "jobname")
					else:
						jobName = jobCode

					if jobConfig.has_option("information", "filecount") and jobConfig.has_option("jobglobals", "priority"):
						jobFileCount = jobConfig.getint("information", "filecount")
						jobPrio = jobConfig.getint("jobglobals", "priority")
					else:
						self.writeWarning("not all required information for job %s exists (%s)" % (jobName, wsName), 2)
						continue

					existingFiles = 0

					if jobConfig.has_option("information", "projectassets"):
						passets = eval(jobConfig.get("information", "projectassets"))
						pName = jobConfig.get("information", "projectname")
						wspaFolder = os.path.join(jobDir, "ProjectAssets", pName)
						paFolder = os.path.join(self.pAssetPath, pName)
						if not os.path.exists(paFolder):
							os.makedirs(os.path.join(self.pAssetPath, pName))

						for m in passets:
							aPath = os.path.join(wspaFolder, m[0])
							if not os.path.exists(aPath):
								continue

							taPath = os.path.join(paFolder, m[0])
							if os.path.exists(taPath) and int(os.path.getmtime(taPath)) == int(m[1]):
								existingFiles += 1
								continue

							if os.path.exists(aPath) and int(os.path.getmtime(aPath)) == int(m[1]):
								try:
									shutil.copy2(aPath, taPath)
									existingFiles += 1
								except:
									self.writeWarning("Could not copy file to ProjectAssets: %s %s %s %s" % (wsName, pName, jobName, m), 2)
							else:
								self.writeLog("Project asset is missing or outdated: %s for job %s" % (m[0], jobName))

					jobFilesDir = os.path.join(jobDir, jobCode, "JobFiles")
					if not os.path.isdir(jobFilesDir):
						self.writeLog("jobfiles folder does not exist for job %s (%s)" % (jobName, wsName), 1)
						continue

					if (len(os.listdir(jobFilesDir)) + existingFiles) < jobFileCount:
						self.writeLog("not all required files for job %s exists (%s)" % (jobName, wsName))
						continue

					targetPath = os.path.join(self.repPath, "Jobs", jobCode)

					while os.path.exists(targetPath):
						newjobCode = ''.join(random.choice(string.lowercase) for x in range(10))
						self.writeLog("renamed job %s to %s" % (jobCode, newjobCode))
						jobCode = newjobCode
						targetPath = os.path.join(self.repPath, "Jobs", jobCode)

					jobConfig.set("information", "jobcode", jobCode)
					jobConfig.set("information", "submitWorkstation", wsName)
					with open(jobIni, 'w') as inifile:
						jobConfig.write(inifile)

					try:
						shutil.move(os.path.join(jobDir, jobCode) ,targetPath)
					except:
						self.writeWarning("Jobfolder %s could not be copied to the JobRepository (%s)" % (jobName, wsName), 3)
						continue

					if not os.path.exists(self.prioList):
						open(self.prioList, 'a').close()

					jobs = ""
					added = False
					with open(self.prioList, 'r') as priofile:
						for line in priofile.readlines():
							jobData = eval(line)
							if jobData[0] < jobPrio and not added:
								jobs += str([jobPrio, jobCode]) + "\n"
								added = True
							jobs += line

						if not added:
							jobs += str([jobPrio, jobCode]) + "\n"

					with open(self.prioList, 'w') as priofile:
						priofile.write(jobs)

					self.writeLog("Job %s was added to the JobRepository from %s" % (jobName, wsName), 1)

			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR -- getJobAssignments -- %s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), 3)


	@err_decorator
	def checkSlaves(self):
		# checks for updated slave script and handles slaveout commands

		for i in os.listdir(os.path.join(self.slPath, "Slaves")):
			try:
				slavePath = os.path.join(self.slPath, "Slaves", i)
				if not (i.startswith("S_") and os.path.isdir(slavePath)):
					self.writeWarning("WARNING -- Slaves folder is invalid %s" % i, 2)
					continue

				slaveName = i[len("S_"):]
				slaveActivePath = os.path.join(slavePath, "slaveActive_%s" % slaveName)
				slaveComPath = os.path.join(slavePath, "Communication")

				file_mod_time = 0

				if os.path.exists(slaveActivePath):
					file_mod_time = os.stat(slaveActivePath).st_mtime

				webapiPath = os.path.join(os.path.dirname(slavePath), "webapi", "slaveActive_%s" % slaveName)
				if os.path.exists(webapiPath) and os.stat(webapiPath).st_mtime > file_mod_time:
					file_mod_time = os.stat(webapiPath).st_mtime

				last_time = int((time.time() - file_mod_time) / 60)

				self.slaveContactTimes[slaveName] = file_mod_time
				if last_time < self.activeThres:
					self.activeSlaves[slaveName] = file_mod_time

				slaveScriptPath = os.path.join(slavePath, "Scripts", "PandoraSlaveLogic.py")
				masterScriptPath = os.path.join(self.slPath, "Scripts", "PandoraSlaves", "PandoraSlaveLogic.py")
				if os.path.exists(masterScriptPath):
					try:
						if not os.path.exists(os.path.dirname(slaveScriptPath)):
							os.makedirs(os.path.dirname(slaveScriptPath))
							
						if os.path.exists(slaveScriptPath):
							sFileDate = int(os.path.getmtime(slaveScriptPath))
						else:
							sFileDate = 0

						mFileDate = int(os.path.getmtime(masterScriptPath))

						if mFileDate > sFileDate:
							shutil.copy2(masterScriptPath, slaveScriptPath)
							self.writeLog("updated SlaveLogic for %s" % slaveName, 1)

					except Exception,e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						self.writeLog("ERROR -- checkSlaves mlp -- %s %s\n%s\n%s" % (slaveName, str(e), exc_type, exc_tb.tb_lineno), 3)

				else:
					self.writeWarning("WARNING -- master SlaveLogic script does not exist", 2)

				shouJobPath = os.path.join(slavePath, "Scripts", "PandoraStartHouJob.py")
				mhouJobPath = os.path.join(self.slPath, "Scripts", "PandoraSlaves", "PandoraStartHouJob.py")
				if os.path.exists(mhouJobPath):
					try:
						if not os.path.exists(os.path.dirname(shouJobPath)):
							os.makedirs(os.path.dirname(shouJobPath))

						if os.path.exists(shouJobPath):
							sFileDate = int(os.path.getmtime(shouJobPath))
						else:
							sFileDate = 0

						mFileDate = int(os.path.getmtime(mhouJobPath))

						if mFileDate > sFileDate:
							shutil.copy2(mhouJobPath, shouJobPath)
							self.writeLog("updated houJobScript for %s" % slaveName, 1)

					except Exception,e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						self.writeLog("ERROR -- checkSlaves mhp -- %s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), 3)
				else:
					self.writeWarning("WARNING -- master houJob script does not exist", 2)

				if not os.path.exists(slaveComPath):
					try:
						os.makedirs(slaveComPath)
					except:
						self.writeLog("could not create Communication folder for %s" % slaveName, 3)
						continue

				for k in sorted(os.listdir(slaveComPath)):
					if not k.startswith("slaveOut_"):
						continue

					cmFile = os.path.join(slaveComPath, k)
					self.handleCmd(cmFile, origin=slaveName)

			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR -- checkSlaves -- %s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), 3)


	@err_decorator
	def checkConnection(self):
		if not self.restartGDriveEnabled:
			return

		if len(self.activeSlaves) == 0 and (time.time() - self.lastConnectionCheckTime) > (self.connectionCheckInterval *60):
			self.restartGDrive()
			self.lastConnectionCheckTime = time.time()


	# restarts "backup and sync" from google
	@err_decorator
	def restartGDrive(self):
		self.writeLog("restart gdrive")
		PROCNAME = 'googledrivesync.exe'
		for proc in psutil.process_iter():
			if proc.name() == PROCNAME:
				p = psutil.Process(proc.pid)

				if not 'SYSTEM' in p.username():
					proc.kill()

		if os.path.exists(self.gdrive):
			subprocess.Popen(self.gdrive)


	# searches for the installation path of "backup and sync" from google in the registry
	@err_decorator
	def getGDrivePath(self):
		try:
			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\Google\Drive",
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			self.gdrive = (_winreg.QueryValueEx(key, "InstallLocation"))[0]
			if not os.path.exists(self.gdrive):
				self.gdrive = ""
		except:
			self.gdrive = ""

		self.writeLog("set gdrive path to: %s" % self.gdrive)


	@err_decorator
	def checkRenderingTasks(self):
		removed = []
		for i in self.renderingTasks:
			jobName = i[0]
			taskName = i[1]

			iniPath = os.path.join(self.jobPath, jobName, "PandoraJob.ini")

			if not os.path.exists(iniPath):
				self.writeWarning("Job Ini does not exist: %s" % iniPath, 2)
				removed.append(i)
				continue
				
			jobConfig = ConfigParser()
			jobConfig.read(iniPath)
			if not jobConfig.has_option("jobtasks", taskName):
				self.writeWarning("no jobtasks in %s" % iniPath)
				continue

			taskData = eval(jobConfig.get("jobtasks", taskName))

			if taskData[2] != "rendering":
				self.writeWarning("rendertask is not rendering: %s" % i)
				continue

			rSlave = taskData[3]
			slaveSettings = os.path.join(self.slPath, "Slaves", "S_%s" % rSlave, "slaveSettings_%s.ini" % rSlave)
			if not os.path.exists(slaveSettings):
				self.writeWarning("slave settings does not exist: %s" % rSlave)
				continue

			slaveConfig = ConfigParser()
			slaveConfig.read(slaveSettings)
			if slaveConfig.has_option("slaveinfo", "status") and slaveConfig.has_option("slaveinfo", "curjob"):
				curTask = slaveConfig.get("slaveinfo", "curjob").split(" ")[-1]
				if curTask.startswith("(") and curTask.endswith(")"):
					curTask = curTask[1:-1]
				else:
					curTask = ""

				if slaveConfig.get("slaveinfo", "status") != "idle" and curTask != taskName:
					taskData[2] = "ready"
					taskData[3] = "unassigned"
					taskData[4] = ""
					taskData[5] = ""
					taskData[6] = ""
					jobConfig.set("jobtasks", taskName, taskData)
					with open(iniPath, 'w') as jobInifile:
						jobConfig.write(jobInifile)

					removed.append(i)
					self.writeLog("reset task %s of job %s" % (taskName, jobName))

		for i in removed:
			self.renderingTasks.remove(i)


	@err_decorator
	def getAvailableSlaves(self):
		jobBase = os.path.join(self.repPath, "Jobs")
		unavailableSlaves = []

		if os.path.exists(jobBase):
			for i in os.listdir(jobBase):
				iniPath = os.path.join(jobBase, i, "PandoraJob.ini")

				if not os.path.exists(iniPath):
					continue

				jobConfig = ConfigParser()
				jobConfig.read(iniPath)

				for k in jobConfig.options("jobtasks"):
					taskData = eval(jobConfig.get("jobtasks", k))
					if taskData[2] in ["assigned", "rendering"]:
						try:
							startTime = float(taskData[5])
						except:
							pass
						else:
							elapsedTime = (time.time()-startTime)/60.0

							taskTimedOut = False
							if taskData[2] == "assigned":
								if elapsedTime > 15:
									taskTimedOut = True

							elif taskData[2] == "rendering":
								if jobConfig.has_option("jobglobals", "taskTimeout"):
									timeout = jobConfig.getint("jobglobals", "taskTimeout")
									if elapsedTime > timeout:
										taskTimedOut = True

							if jobConfig.has_option("information", "jobname"):
								jName = jobConfig.get("information", "jobname")
							else:
								jName = ""

							if taskTimedOut:
								self.sendCommand(taskData[3], ["cancelTask", jName, i, k])
								
								taskData[2] = "ready"
								taskData[3] = "unassigned"
								taskData[4] = ""
								taskData[5] = ""
								taskData[6] = ""
								jobConfig.set('jobtasks', k , str(taskData))

								with open(iniPath, 'w') as inifile:
									jobConfig.write(inifile)

								self.writeLog("Timeout of %s from Job %s (%s min)" % (k, jName, elapsedTime), 1)
								continue

						unavailableSlaves.append(taskData[3])
						#self.writeLog("DEBUG - unavailable slaves: %s - %s" % (taskData[3],i))
						
		#self.writeLog("DEBUG - unavailable slaves: %s" % unavailableSlaves)

		for i in self.activeSlaves:
			try:
				if i in unavailableSlaves:
					continue

				slaveSettings = os.path.join(self.slPath, "Slaves", "S_%s" % i, "slaveSettings_%s.ini" % i)
				slaveConfig = ConfigParser()
				slaveConfig.read(slaveSettings)

				if not slaveConfig.has_section("slaveinfo"):
					self.writeLog("Slavesettings from %s do not have a section \"slaveinfo\"" % i, 2)
					continue

				if not slaveConfig.has_option("slaveinfo", 'status'):
					self.writeLog("Slavesettings from %s do not have an option \"status\" in \"slaveinfo\"" % i, 2)
					continue

				slaveStatus = slaveConfig.get('slaveinfo', 'status')

				if slaveStatus == "idle":
					self.availableSlaves.append(i)
			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR -- getAvailableSlaves -- %s -- %s\n%s\n%s" % (i, str(e), exc_type, exc_tb.tb_lineno), 3)


	@err_decorator
	def assignJobs(self):
		self.jobDirs = []

		if not os.path.exists(self.prioList):
			open(self.prioList, 'a').close()

		with open(self.prioList, 'r') as priofile:
			for line in priofile.readlines():
				jobName = eval(line)[1]
				if os.path.exists(os.path.join(self.repPath, "Jobs", jobName)):
					self.jobDirs.append(jobName)

		self.writeLog("start checking jobs")

		for jobDir in self.jobDirs:
			iniPath = os.path.join(self.jobPath, jobDir, "PandoraJob.ini")

			if not os.path.exists(iniPath):
				self.writeWarning("Job Ini does not exist: %s" % jobDir, 2)
				continue
				
			jobConfig = ConfigParser()
			jobConfig.read(iniPath)

			if jobConfig.has_option("information", "jobname"):
				jobName = jobConfig.get("information", "jobname")
			else:
				self.writeWarning("Job has no jobname option: %s" % jobDir, 2)
				continue

			if jobConfig.has_option("information", "scenename"):
				sceneName = jobConfig.get("information", "scenename")
			else:
				self.writeWarning("Job has no scenename option: %s" % jobName, 2)
				continue

			if jobConfig.has_option("information", "filecount"):
				jobFileCount = jobConfig.getint("information", "filecount")
				if len(os.listdir(os.path.join(self.jobPath, jobDir, "JobFiles"))) < jobFileCount and not jobConfig.has_option("information", "projectassets"):
					self.writeLog("assign job - not all required files for job %s exists" % jobName, 1)
					continue
			else:
				self.writeWarning("Job has no filecount option: %s" % jobName, 2)
				continue

			if not jobConfig.has_section("jobtasks"):
				self.writeWarning("Job tasks are missing: %s" % jobName, 2)
				continue

			dependentSlaves = []

			if jobConfig.has_option("jobglobals", "jobdependecies"):
				depsFinished = [True]
				jobDeps = eval(jobConfig.get("jobglobals", "jobdependecies"))
				for jDep in jobDeps:
					if len(jDep) == 2:
						depName = jDep[0]
						depIni = os.path.join(self.jobPath, depName, "PandoraJob.ini")
						if not os.path.exists(depIni):
							self.writeWarning("For job %s the dependent job %s is missing." % (jobName, depName), 2)
							depsFinished = [False, depName]
							break

						depConfig = ConfigParser()
						depConfig.read(depIni)

						if depConfig.has_option("information", "jobname"):
							depJobName = depConfig.get("information", "jobname")
						else:
							depJobName = depName

						if not depConfig.has_section("jobtasks"):
							self.writeWarning("For job %s the dependent job %s has no tasks." % (jobName, depJobName), 2)
							depsFinished = [False, depJobName]
							break

						for dTask in depConfig.options("jobtasks"):
							taskData = eval(depConfig.get("jobtasks", dTask))
					
							if not (type(taskData) == list and len(taskData) == 7 and taskData[2] == "finished"):
								depsFinished = [False, depJobName]
								break
							else:
								if taskData[3] not in dependentSlaves:
									dependentSlaves.append(taskData[3])


					if not depsFinished[0]:
						break

				if not depsFinished[0]:
					self.writeLog("For job %s the dependent job %s is not finished." % (jobName, depsFinished[1]), 0)
					continue


			jobSlaves = []

			if jobConfig.has_option("jobglobals", "listslaves"):
				listSlaves = jobConfig.get("jobglobals", "listslaves")
				if listSlaves.startswith("exclude "):
					whiteList = False
					listSlaves = listSlaves[len("exclude "):]
				else:
					whiteList = True
				
				for i in self.availableSlaves:
					if len(dependentSlaves) > 0 and i not in dependentSlaves:
						continue

					if listSlaves.startswith("groups: "):
						jGroups = listSlaves[len("groups: "):].split(", ")

						slaveSettings = os.path.join(self.slPath, "Slaves", "S_%s" % i, "slaveSettings_%s.ini" % i)
						slaveConfig = ConfigParser()
						slaveConfig.read(slaveSettings)

						if not slaveConfig.has_option('settings', 'slavegroup') or slaveConfig.get('settings', 'slavegroup') is None:
							continue

						slaveGroups = eval(slaveConfig.get('settings', 'slavegroup'))

						for k in jGroups:
							if (k not in slaveGroups) == whiteList:
								break
						else:
							jobSlaves.append(i)
					else:
						if listSlaves == "All" or (i in listSlaves.split(", ")) == whiteList:
							jobSlaves.append(i)
							
			for i in jobConfig.options("jobtasks"):

				taskData = eval(jobConfig.get("jobtasks", i))
				if taskData[2] == "assigned" and taskData[3] in self.availableSlaves:
					self.availableSlaves.remove(taskData[3])
					if taskData[3] in jobSlaves:
						jobSlaves.remove(taskData[3])

				if len(jobSlaves) == 0:
					break

				if not (type(taskData) == list and len(taskData) == 7):
					continue

				if taskData[2] != "ready":
					continue

				assignedSlave = jobSlaves[0]

				slavePath = os.path.join(self.slPath, "Slaves", "S_%s" % assignedSlave)
				slaveSettings = os.path.join(slavePath, "slaveSettings_%s.ini" % assignedSlave)
				
				slaveJobPath = os.path.join(slavePath, "AssignedJobs", "%s" % jobDir)

				if not os.path.exists(slaveJobPath):
					shutil.copytree(os.path.join(self.jobPath, jobDir), slaveJobPath)

				if jobConfig.has_option("information", "projectassets"):
					jpAssets = eval(jobConfig.get("information", "projectassets"))[1:]
					pName = jobConfig.get("information", "projectname")
					sPAssetPath = os.path.join(slavePath, "ProjectAssets", pName)
					if not os.path.exists(sPAssetPath):
						os.makedirs(sPAssetPath)

					for k in jpAssets:
						paPath = os.path.join(self.pAssetPath, pName, k[0])
						if not os.path.exists(paPath):
							self.writeWarning("Required ProjectAsset does not exist: %s %s" % (pName, k[0]), 2)
							continue

						sPAsset = os.path.join(sPAssetPath, k[0])
						if os.path.exists(sPAsset) and os.path.getmtime(paPath) == os.path.getmtime(sPAsset):
							continue

						shutil.copy2(paPath, sPAsset)

				cmd = str(["renderTask", jobDir, jobName, i])
				self.sendCommand(assignedSlave, cmd)

				taskData[2] = "assigned"
				taskData[3] = assignedSlave
				taskData[5] = time.time()
				jobSlaves.remove(assignedSlave)
				self.availableSlaves.remove(assignedSlave)

				jobConfig.set("jobtasks", i, taskData)
				with open(iniPath, 'w') as jobInifile:
					jobConfig.write(jobInifile)

				self.writeLog("assigned %s to %s in job %s" % (assignedSlave, i, jobName), 1)


	@err_decorator
	def sendCommand(self, slave, cmd):
		cmdDir = os.path.join(self.slPath, "Slaves", "S_%s" % slave, "Communication")
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
	def checkTvRequests(self):
		handledRequests = []

		for i in self.tvRequests:
			self.writeLog("handling teamviewer request: %s" % i)
			ssPath = os.path.join(self.slPath, "Slaves", "S_%s" % i["slave"], "ScreenShot_%s.jpg" % i["slave"])
			if os.path.exists(ssPath) and os.path.getmtime(ssPath) > i["requestTime"]:
				targetPath = os.path.join(self.slPath, "Workstations", "WS_%s" % i["workstation"],  "Screenshots")
				try:
					shutil.copy2(ssPath, targetPath)
				except Exception,e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					self.writeLog("ERROR -- could not copy file %s -- %s\n%s\n%s" % (i, str(e), exc_type, exc_tb.tb_lineno), 3)

				handledRequests.append(i)

		self.tvRequests = [x for x in self.tvRequests if x not in handledRequests]


	@err_decorator
	def checkCollectTasks(self):
		removeTasks = []
		for slave in self.collectTasks:
			for job in self.collectTasks[slave]:
				expNum = self.collectTasks[slave][job]

				outputPath = os.path.join(self.slPath, "Slaves", "S_" + slave, "Output", job)

				if not os.path.exists(outputPath):
					self.writeLog("Can't collect output. The Outputpath doesn't exist: %s" % outputPath)
					continue

				fileCount = 0
				for i in os.walk(outputPath):
					fileCount += len(i[2])

				if fileCount != expNum:
					self.writeLog("Can't collect output. The filecount doesn't match: %s from %s for %s" % (fileCount, expNum, outputPath))
					continue

				copiedNum, errors, targetPath = self.collectOutput(slave=slave, jobCode=job)

				jobIni = os.path.join(self.repPath, "Jobs", job, "PandoraJob.ini")
				jconfig = ConfigParser()
				jconfig.read(jobIni)

				if jconfig.has_option("information", "jobname"):
					jobName = jconfig.get("information", "jobName")
				else:
					jobName = job

				collectStr = ""
				if copiedNum != 0 or errors != 0:
					collectStr = "Job %s output collected automatically. %s files copied to %s" % (jobName, copiedNum, targetPath)
					
				if errors > 0:
					collectStr += " %s errors occured" % errors
					errorLvl = 2
				else:
					errorLvl = 0
					
				removeTasks.append([slave, job])

				if collectStr != "":
					self.writeLog(collectStr, errorLvl)

		for i in removeTasks:
			del self.collectTasks[i[0]][i[1]]


	@err_decorator
	def collectOutput(self, slave=None, jobCode=None):
		jobIni = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.ini")
		jconfig = ConfigParser()
		if os.path.exists(jobIni):
			jconfig.read(jobIni)
		else:
			self.writeWarning("Job Ini does not exist for job: %s" % (jobCode), 2)
			return [0,0, ""]

		copiedNum = 0
		errors = 0
		targetPath = "None"
		if jconfig.has_option("information", "submitWorkstation"):
			wsName = jconfig.get("information", "submitWorkstation")
			targetBase = os.path.join(self.slPath, "Workstations", "WS_" + wsName, "RenderOutput", jconfig.get("information", "projectname"), jobCode)
		else:
			return [0,0, ""]

		jfolderExists = True
		if not os.path.exists(targetBase):
			try:
				os.makedirs(targetBase)
			except:
				jfolderExists = False

		if jfolderExists:
			try:
				shutil.copy2(jobIni, targetBase)
			except:
				pass

		slaveSyncPath = os.path.join(self.slPath, "Slaves")
		for i in os.listdir(slaveSyncPath):
			slaveName = i[len("S_"):]
			if slave is not None and slave != slaveName:
				continue

			jobOutput = os.path.join(slaveSyncPath, i, "Output", jobCode)
			if os.path.exists(jobOutput):
				for k in os.walk(jobOutput):
					for m in k[2]:
						filePath = os.path.join(k[0], m)
						relFilePath = filePath.replace(jobOutput, "")
						while relFilePath.startswith("\\") or relFilePath.startswith("/"):
							relFilePath = relFilePath[1:]
						targetPath = os.path.join(targetBase, relFilePath)

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
									errors += 1
									folderExists = False
							if folderExists:
								try:
									shutil.copy2(filePath, targetPath)
									copiedNum += 1
								except:
									errors +=1

		if jconfig.has_section("jobtasks"):
			for k in jconfig.options("jobtasks"):
				taskData = eval(jconfig.get("jobtasks", k))
				if taskData[2] != "finished":
					break
			else:
				targetIni = os.path.join(self.slPath, "Workstations", "WS_" + wsName, "RenderOutput", jconfig.get("information", "projectname"), jobCode, "PandoraJob.ini")
				tconfig = ConfigParser()
				if os.path.exists(targetIni):
					tconfig.read(targetIni)

					if not tconfig.has_section("information"):
						tconfig.add_section("information")

					outputCount = 0
					for i in os.walk(os.path.dirname(targetIni)):
						outputCount += len(i[2])

					tconfig.set("information", "outputfilecount", outputCount)

					with open(targetIni, 'w') as jobInifile:
						tconfig.write(jobInifile)

		return [copiedNum, errors, targetPath]


	@err_decorator
	def notifyWorkstations(self):
		logDir = os.path.join(self.slPath, "Workstations", "Logs")

		if not os.path.exists(logDir):
			try:
				os.makedirs(logDir)
			except:
				self.writeLog("ERROR -- could not create log folder %s -- %s\n%s\n%s" % (logDir), 3)
				return

		self.copyLogs([self.coordLog, self.coordIni, self.actSlvPath, self.coordWarningsIni], os.path.join(logDir, "PandoraCoordinator"))

		filesToCopy = []
		for jobDir in self.jobDirs:
			jobIni = os.path.join(self.jobPath, jobDir, "PandoraJob.ini")
			filesToCopy.append(jobIni)

		self.copyLogs(filesToCopy, os.path.join(logDir, "Jobs"))

		filesToCopy = []
		for i in os.listdir(os.path.join(self.slPath, "Slaves")):
			if i.startswith("S_"):
				slaveName = i[len("S_"):]
				slaveLog = os.path.join(self.slPath, "Slaves", i, "slaveLog_%s.txt" % slaveName)
				slaveSettings = os.path.join(os.path.dirname(slaveLog), "slaveSettings_%s.ini" % slaveName)
				slaveWarnings = os.path.join(os.path.dirname(slaveLog), "slaveWarnings_%s.ini" % slaveName)
				filesToCopy += [slaveLog, slaveSettings, slaveWarnings]

		self.copyLogs(filesToCopy, os.path.join(logDir, "Slaves"))


	@err_decorator
	def notifySlaves(self):
		if self.localmode:
			return

		if (time.time() - self.lastNotifyTime) < (self.notifySlaveInterval*60):
			return

		for i in os.listdir(os.path.join(self.slPath, "Slaves")):
			if not i.startswith("S_"):
				continue

			slaveName = i[len("S_"):]
			if slaveName not in self.activeSlaves.keys():
				continue

			self.lastNotifyTime = time.time()
		
			self.sendCommand(slaveName, ["checkConnection"])


	@err_decorator
	def copyLogs(self, files, target):
		if not os.path.exists(target):
			try:
				os.makedirs(target)
			except Exception,e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				self.writeLog("ERROR -- could not create folder %s -- %s\n%s\n%s" % (target, str(e), exc_type, exc_tb.tb_lineno), 3)

		jobNames = []

		for i in files:
			if not os.path.exists(i):
				#self.writeLog("copy logs: skipping %s" % i)
				continue

			origTime = int(os.path.getmtime(i))

			if os.path.basename(i) == "PandoraJob.ini":
				jConfig = ConfigParser()
				jConfig.read(i)

				if jConfig.has_option("information", "jobname"):
					jobName = jConfig.get("information", "jobname")

					origjobName = jobName

					jNum = 1
					while jobName in jobNames:
						jobName = origjobName + " (%s)" % jNum
						jNum += 1

					jobNames.append(jobName)
				else:
					jobName = os.path.basename(i)

				targetPath = os.path.join(target, jobName + ".ini")
			else:
				targetPath = os.path.join(target, os.path.basename(i))

			if not os.path.exists(targetPath) or int(os.path.getmtime(targetPath)) != origTime:
				try:
					shutil.copy2(i, targetPath)
				except Exception,e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					self.writeLog("ERROR -- could not copy file %s -- %s\n%s\n%s" % (i, str(e), exc_type, exc_tb.tb_lineno), 3)

		baseNames = [os.path.basename(x) for x in files if os.path.exists(x)]
		for i in os.listdir(target):
			if i not in baseNames and os.path.splitext(i)[0] not in jobNames:
				os.remove(os.path.join(target,i))



if __name__ == "__main__":
	sco = PandoraCoordinator()