# -*- coding: utf-8 -*-
#
####################################################
#
# Pandora - Renderfarm
#
# www.prism-pipeline.com
#
# contact: prismpipeline@gmail.com
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
import sys, os, time, subprocess, shutil, socket
sys.path.append(os.path.join(os.getenv("localappdata"), "Pandora", "PythonLibs", "Renderslave"))
import psutil
from ConfigParser import ConfigParser

from UserInterfacesPandora import qdarkstyle

class PandoraTray():

	def __init__(self):
		self.parentWidget = QWidget()

		try:
			pIcon = QIcon(os.path.dirname(os.path.abspath(__file__)) + "\\UserInterfacesPandora\\pandora_tray.ico")
			self.parentWidget.setWindowIcon(pIcon)

			self.configPath = os.path.join(os.getenv("localappdata"), "Pandora", "Config", "Pandora.ini")

			if not os.path.exists(self.configPath):
				self.createDefaultConfig()

			coreProc = []
			for x in psutil.pids():
				try:
					if x != os.getpid() and os.path.basename(psutil.Process(x).exe()) == "PandoraTray.exe":
						coreProc.append(x)
				except:
					pass

			if len(coreProc) > 0:
				QMessageBox.warning(self.parentWidget, "PandoraTray", "PandoraTray is already running.")
				qapp.quit()
				sys.exit()
				return

		#	if os.path.exists(os.path.join(os.getenv("localappdata"), "Prism")):
		#		print "Prism is installed. Closing Pandora-Tray."
		#		qapp.quit()
		#		sys.exit()
		#		return

		#	sEnabled = self.getPandoraConfigData("submissions", "enabled")
		#	if sEnabled == "False":
		#		print "Pandora submissions are disabled. Closing Pandora-Tray."
		#		qapp.quit()
		#		sys.exit()
		#		return

			self.createTrayIcon()
			self.trayIcon.show()

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			QMessageBox.critical(self.parentWidget,"Unknown Error", "initTray - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno))


	def createTrayIcon(self):
		try:
			self.trayIconMenu = QMenu(self.parentWidget)
			self.handlerAction = QAction("Render Handler", self.parentWidget, triggered=self.startRenderHandler)
			self.collectAction = QAction("Collect renderings", self.parentWidget, triggered=self.collectRenderings)
			self.trayIconMenu.addAction(self.handlerAction)
			self.trayIconMenu.addAction(self.collectAction)
			self.trayIconMenu.addSeparator()

			self.slaveAction = QAction("Start Slave", self.parentWidget, triggered=self.startRenderSlave)
			self.trayIconMenu.addAction(self.slaveAction)

			self.slaveStopAction = QAction("Stop Slave", self.parentWidget, triggered=self.stopRenderSlave)
			self.trayIconMenu.addAction(self.slaveStopAction)
			self.trayIconMenu.addSeparator()

			self.coordAction = QAction("Start Coordinator", self.parentWidget, triggered=self.startCoordinator)
			self.trayIconMenu.addAction(self.coordAction)

			self.coordStopAction = QAction("Stop Coordinator", self.parentWidget, triggered=self.stopCoordinator)
			self.trayIconMenu.addAction(self.coordStopAction)
			self.trayIconMenu.addSeparator()

			self.settingsAction = QAction("Pandora Settings...", self.parentWidget, triggered=self.openSettings)
			self.trayIconMenu.addAction(self.settingsAction)
			self.trayIconMenu.addSeparator()
			self.exitAction = QAction("Exit", self.parentWidget , triggered=self.exitTray)
			self.trayIconMenu.addAction(self.exitAction)

			self.trayIcon = QSystemTrayIcon()
			self.trayIcon.setContextMenu(self.trayIconMenu)
			self.trayIcon.setToolTip("Pandora Tools")

			self.icon = QIcon(os.path.dirname(os.path.abspath(__file__)) + "\\UserInterfacesPandora\\pandora_tray.ico")

			self.trayIcon.setIcon(self.icon)

			self.trayIcon.activated.connect(self.iconActivated)
			self.trayIconMenu.aboutToShow.connect(self.aboutToShow)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			QMessageBox.critical(self.parentWidget,"Unknown Error", "createTray - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno))


	def iconActivated(self, reason):
		try:
			if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
				self.startRenderHandler()

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			QMessageBox.critical(self.parentWidget,"Unknown Error", "iconActivated - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno))


	def aboutToShow(self):
		try:
			wEnabled = self.getPandoraConfigData("submissions", "enabled")
			lmode = self.getPandoraConfigData("globals", "localmode", silent=True)
			if wEnabled == "True":
				self.handlerAction.setVisible(True)
				if lmode == "True":
					self.collectAction.setVisible(False)
				else:
					self.collectAction.setVisible(True)
			else:
				self.handlerAction.setVisible(False)
				self.collectAction.setVisible(False)

			sEnabled = self.getPandoraConfigData("slave", "enabled")
			if sEnabled == "True":
			#	slaveProc = []
			#	for x in psutil.pids():
			#		try:
			#			if os.path.basename(psutil.Process(x).exe()) == "PandoraSlave.exe":
			#				slaveProc.append(x)
			#		except:
			#			pass
			#	slaveRunning = len(slaveProc) > 0

				self.slaveAction.setVisible(True)
				self.slaveStopAction.setVisible(True)
			else:
				self.slaveAction.setVisible(False)
				self.slaveStopAction.setVisible(False)

			cEnabled = self.getPandoraConfigData("coordinator", "enabled")
			if cEnabled == "True":
			#	coordProc = []
			#	for x in psutil.pids():
			#		try:
			#			if os.path.basename(psutil.Process(x).exe()) == "PandoraCoordinator.exe":
			#				coordProc.append(x)
			#		except:
			#			pass
			#	coordRunning = len(coordProc) > 0

				self.coordAction.setVisible(True)
				self.coordStopAction.setVisible(True)
			else:
				self.coordAction.setVisible(False)
				self.coordStopAction.setVisible(False)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			QMessageBox.critical(self.parentWidget,"Unknown Error", "iconAboutToShow - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno))



	def startRenderHandler(self):
		try:
			PROCNAME = 'PandoraRenderHandler.exe'
			for proc in psutil.process_iter():
				if proc.name() == PROCNAME:
					p = psutil.Process(proc.pid)

					if not 'SYSTEM' in p.username():
						proc.kill()
		
			handlerPath = os.path.dirname(__file__) + "\\PandoraRenderHandler.py"
			if not os.path.exists(handlerPath):
				self.trayIcon.showMessage("Script missing", "PandoraRenderHandler.py does not exist.", icon = QSystemTrayIcon.Warning)
				return None

			command = '\"%s\\Pandora\\Tools\\PandoraRenderHandler.lnk\"' % os.environ["localappdata"]
			self.handlerProc = subprocess.Popen(command, shell=True)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.trayIcon.showMessage("Unknown Error", "startRenderHandler - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)


	def collectRenderings(self):
		try:
			lmode = self.getPandoraConfigData("globals", "localmode", silent=True)
			if lmode == "True":
				rootPath = self.getPandoraConfigData("globals", "rootpath", silent=True)
				psPath = os.path.join(rootPath, "PandoraFarm", "Workstations", "WS_" + socket.gethostname())
			else:
				psPath = self.getPandoraConfigData("submissions", "submissionpath", silent=True)

			if psPath is None or not os.path.exists(psPath):
				self.trayIcon.showMessage("Directory missing", "Pandora submission directory doesn't exist.", icon = QSystemTrayIcon.Warning)
				return None

			outputDir = os.path.join(psPath, "RenderOutput")

			if not os.path.exists(outputDir):
				self.trayIcon.showMessage("Directory missing", "Pandora renderoutput directory doesn't exist.", icon = QSystemTrayIcon.Warning)
				return None

			result = {}
			for i in os.walk(outputDir):
				for prj in i[1]:
					for k in os.walk(os.path.join(i[0], prj)):
						for job in k[1]:
							jobDir = os.path.join(k[0], job)
							inipath = os.path.join(k[0], job, job + ".ini")
							if not os.path.exists(inipath):
								self.trayIcon.showMessage("Config missing", "Job config doesn't exist. (%s)" % job, icon = QSystemTrayIcon.Warning)
								continue

							outputCount = 0
							for i in os.walk(jobDir):
								outputCount += len(i[2])

							jConfig = ConfigParser()
							jConfig.read(inipath)

							if not jConfig.has_option("information", "outputpath"):
								self.trayIcon.showMessage("information missing", "No outputpath is defined in job config. (%s)" % job, icon = QSystemTrayIcon.Warning)
								continue

							targetBase = os.path.dirname(os.path.dirname(jConfig.get("information", "outputpath")))

							waitmsg = QMessageBox(QMessageBox.NoIcon, "Pandora - Collect Renderings", "Collecting renderings - %s - please wait.." % job, QMessageBox.Cancel)
							waitmsg.setWindowIcon(self.parentWidget.windowIcon())
							waitmsg.buttons()[0].setHidden(True)
							waitmsg.show()
							QCoreApplication.processEvents()

							copiedNum = 0
							errors = 0

							for o in os.walk(jobDir):
								for m in o[2]:
									if m == (job + ".ini"):
										continue

									filePath = os.path.join(o[0], m)
									relFilePath = filePath.replace(jobDir, "")
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

							result["%s - %s" % (prj, job)] = [copiedNum, errors]

							if jConfig.has_option("information", "outputfilecount"):
								completeCount = jConfig.getint("information", "outputfilecount")

								if outputCount == completeCount:
									try:
										shutil.rmtree(jobDir)
									except:
										pass

							if "waitmsg" in locals() and waitmsg.isVisible():
								waitmsg.close()

						break
				break

			resStr = ""

			for i in result:
				if result[i][0] == 0 and result[i][1] == 0:
					continue

				resStr += "%s:\n" % i
				if result[i][0] > 0:
					resStr += "%s files copied\n" % result[i][0]

				if result[i][1] > 0:
					resStr += "%s errors\n" % result[i][1]

				resStr += "\n"

			if resStr == "":
				resStr = "No renderings to copy"

			QMessageBox.information(self.parentWidget, "Collect renderings", resStr)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.trayIcon.showMessage("Unknown Error", "collectRenderings - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)


	def startRenderSlave(self):
		try:
			slavePath = os.path.join(os.getenv("localappdata"), "Pandora", "Scripts", "PandoraSlaveLogic.py")
			if not os.path.exists(slavePath):
				self.trayIcon.showMessage("Script missing", "PandoraSlaveLogic.py does not exist.", icon = QSystemTrayIcon.Warning)
				return None

			command = '\"%s\\Pandora\\Tools\\PandoraSlave.lnk\"' % os.environ["localappdata"]
			subprocess.Popen(command, shell=True)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.trayIcon.showMessage("Unknown Error", "startPandoraSlave - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)


	def stopRenderSlave(self):
		try:
			lmode = self.getPandoraConfigData("globals", "localmode", silent=True)
			if lmode == "True":
				rootPath = self.getPandoraConfigData("globals", "rootpath", silent=True)
				slavepath = os.path.join(rootPath, "PandoraFarm", "Slaves", "S_" + socket.gethostname())
			else:
				slavepath = self.getPandoraConfigData("slave", "slavepath")

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

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.trayIcon.showMessage("Unknown Error", "stopPandoraSlave - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)


	def startCoordinator(self):
		try:
			coordProc = []
			for x in psutil.pids():
				try:
					if os.path.basename(psutil.Process(x).exe()) == "PandoraCoordinator.exe":
						coordProc.append(x)
				except:
					pass
			if len(coordProc) > 0:
				self.trayIcon.showMessage("PandoraCoordinator", "PandoraCoordinator is already running.", icon = QSystemTrayIcon.Information)
				return

			coordPath = os.path.join(os.getenv("localappdata"), "Pandora", "Scripts", "PandoraCoordinator.py")
			if not os.path.exists(coordPath):
				self.trayIcon.showMessage("Script missing", "PandoraCoordinator.py does not exist.", icon = QSystemTrayIcon.Warning)
				return None

			command = '\"%s\\Pandora\\Tools\\PandoraCoordinator.lnk\"' % os.environ["localappdata"]
			subprocess.Popen(command, shell=True)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.trayIcon.showMessage("Unknown Error", "startPandoraCoordinator - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)


	def stopCoordinator(self):
		try:
			lmode = self.getPandoraConfigData("globals", "localmode", silent=True)
			if lmode == "True":
				coordRoot = self.getPandoraConfigData("globals", "rootpath", silent=True)
			else:
				coordRoot = self.getPandoraConfigData("coordinator", "rootpath", silent=True)
			
			if coordRoot is None:
				return

			if not os.path.exists(coordRoot):
				try:
					os.makedirs(coordRoot)
				except:
					return

			coordBasePath = os.path.join(coordRoot, "PandoraFarm", "Scripts", "PandoraCoordinator")

			exitFile = os.path.join(coordBasePath, "EXIT-.txt")
			activeExitFile = os.path.join(coordBasePath, "EXIT.txt")

			if os.path.exists(exitFile):
				os.rename(exitFile, activeExitFile)
			else:
				open(activeExitFile, "w").close()

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.trayIcon.showMessage("Unknown Error", "stopPandoraCoordinator - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)


	def openSettings(self):
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
			self.trayIcon.showMessage("Unknown Error", "openSettings - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), icon = QSystemTrayIcon.Critical)


	def getPandoraConfigData(self, section, option, silent=False):
		try:
			if not os.path.exists(self.configPath):
				self.createDefaultConfig()

			pConfig = ConfigParser()
			pConfig.read(self.configPath)

			if not pConfig.has_option(section, option):
				if not silent:
					self.trayIcon.showMessage("Information missing", "The option %s does not exist in the Pandora config." % option, icon = QSystemTrayIcon.Warning)
				return None

			return pConfig.get(section, option)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			QMessageBox.critical(self.parentWidget,"Unknown Error", "getPandoraConfigData - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno))


	def createDefaultConfig(self):
		import PandoraCore
		pc = PandoraCore.PandoraCore()
		

	def exitTray(self):
		qapp.quit()	


if __name__ == "__main__":
	qapp = QApplication(sys.argv)
	qapp.setQuitOnLastWindowClosed(False)
	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

	if not QSystemTrayIcon.isSystemTrayAvailable():
		QMessageBox.critical(None, "PandoraTray", "Could not launch PandoraTray.")
		sys.exit(1)

	sl = PandoraTray()
	sys.exit(qapp.exec_())