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

import sys, os, time, traceback, shutil, string, random, socket
from functools import wraps

for i in ["PandoraSubmitter_ui", "PandoraSubmitter_ui_ps2"]:
	try:
		del sys.modules[i]
	except:
		pass

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))

if psVersion == 1:
	import PandoraSubmitter_ui
else:
	import PandoraSubmitter_ui_ps2 as PandoraSubmitter_ui

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2


try:
	import MaxPlus
except:
	pass

try:
	import hou
except:
	pass

try:
	import maya.cmds as cmds
	import maya.mel as mel
	import mtoa.aovs as maovs
except:
	pass

try:
	import bpy
except:
	pass


class PandoraSubmitter(QDialog, PandoraSubmitter_ui.Ui_dlg_pandoraSubmitter):
	def __init__(self, core):
		QDialog.__init__(self)
		self.setupUi(self)

		self.core = core
		self.core.parentWindow(self)

		self.setTooltips()
		self.setAppMethods()
		self.startup()
		self.connectEvents()
		self.loadSettings()


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - PandoraSubmitter %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper

	@err_decorator
	def closeEvent(self, event):
		self.saveSettings()


	@err_decorator
	def setTooltips(self):
		self.l_projectName.setToolTip("Use the same project name for all renderjobs of the project you are working on")
		self.l_jobName.setToolTip("Use an individial job name for each submission e.g. \"Shot-020_anm_v0007\"")
		self.l_nodeStatus.setToolTip("Shows the status of the connected render node, which will be rendered")
		self.l_framerange.setToolTip("Sets the first and the last frame, which should be rendered with this job (all frames between first frame and last frame will be rendered)")
		self.l_camera.setToolTip("Sets the camera you want to look through during rendering")
		self.l_resOverride.setToolTip("If checked, sets the resolution of the rendered images. If not checked the current settings from the scenefile will be used")
		self.l_prio.setToolTip("""Sets the priority of the renderjob. Jobs with higher priority will be rendered before jobs with lower priority.
Please contact the renderfarm administrator before increasing the priority.""")
		self.l_framesPerTask.setToolTip("""Each renderjob is divided into multiple tasks. Each task contains the same number of frames to be be rendered and each task can be rendered by a different renderslave.
If you have a lot of frames, which render fast you may want to increase this value. For jobs with long rendertimes you want to decrease it.""")
		self.l_submitSuspended.setToolTip("If checked, the renderjob will be submitted as suspended (deactivated). It can be activated manually later in the RenderHandler.")
		self.l_submitDependent.setToolTip("If checked, all external files (e.g. Textures, References) will be submitted with this renderjob")
		self.l_uploadOutput.setToolTip("""If checked the rendered images will be uploaded to the renderfarm server.
If set to False, the renderings can be found locally on the renderslave, which rendered the job.""")



	@err_decorator
	def setAppMethods(self):
		self.setRcStyle = lambda x: None

		if self.core.app == 1:
			self.startup = self.maxStartup
			self.getCams = self.maxGetCams
			self.getCamName = self.maxGetCamName
			self.getExternalFiles = self.maxGetExternalFiles
			self.preSubmit = self.maxPreSubmit
			self.undoRenderSettings = self.maxUndoRenderSettings
			self.frameStr = "."

		elif self.core.app == 2:
			self.startup = self.houStartup
			self.getCams = self.houGetCams
			self.getCamName = self.houGetCamName
			self.setRcStyle = self.houSetRcStyle
			self.getExternalFiles = self.houGetExternalFiles
			self.preSubmit = lambda x: None
			self.undoRenderSettings = lambda x: None
			self.frameStr = ".$F4"

		elif self.core.app == 3:
			self.startup = self.mayaStartup
			self.getCams = self.mayaGetCams
			self.getCamName = self.mayaGetCamName
			self.getExternalFiles = self.mayaGetExternalFiles
			self.preSubmit = self.mayaPreSubmit
			self.undoRenderSettings = self.mayaUndoRenderSettings
			self.frameStr = ""

		elif self.core.app == 6:
			self.startup = self.bldStartup
			self.getCams = self.bldGetCams
			self.startup = self.bldStartup
			self.getCamName = self.bldGetCamName
			self.preSubmit = self.bldPreSubmit
			self.undoRenderSettings = self.bldUndoRenderSettings
			self.frameStr = ".####"


	@err_decorator
	def connectEvents(self):
		self.b_goTo.clicked.connect(self.goToNode)
		self.b_connect.clicked.connect(self.connectNode)
		self.sp_rangeStart.editingFinished.connect(self.startChanged)
		self.sp_rangeEnd.editingFinished.connect(self.endChanged)
		self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
		self.b_resPresets.clicked.connect(self.showResPresets)
		self.b_browseOutputpath.clicked.connect(self.browseOutput)
		self.b_submit.clicked.connect(self.startSubmission)


	@err_decorator
	def browseOutput(self):
		selectedPath = QFileDialog.getSaveFileName(self, "Select outputpath", self.e_outputpath.text(), "All files (*.*)")[0]

		if selectedPath != "":
			self.e_outputpath.setText(self.core.fixPath(selectedPath))

	@err_decorator
	def startChanged(self):
		if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
			self.sp_rangeEnd.setValue(self.sp_rangeStart.value())


	@err_decorator
	def endChanged(self):
		if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
			self.sp_rangeStart.setValue(self.sp_rangeEnd.value())


	@err_decorator
	def resOverrideChanged(self, checked):
		self.sp_resWidth.setEnabled(checked)
		self.sp_resHeight.setEnabled(checked)
		self.b_resPresets.setEnabled(checked)


	@err_decorator
	def showResPresets(self):
		pmenu = QMenu()

		resolutionPresets = ["1920x1080", "1280x720", "640x360", "4000x2000", "2000x1000"]

		for i in resolutionPresets:
			pAct = QAction(i, self)
			pwidth = int(i.split("x")[0])
			pheight = int(i.split("x")[1])
			pAct.triggered.connect(lambda v=pwidth: self.sp_resWidth.setValue(v))
			pAct.triggered.connect(lambda v=pheight: self.sp_resHeight.setValue(v))
			pmenu.addAction(pAct)

		self.setRcStyle(pmenu)
		pmenu.exec_(QCursor.pos())


	@err_decorator
	def loadSettings(self):
		#update Cams
		self.cb_cam.clear()
		
		camlist = self.getCams()

		self.cb_cam.addItems([self.getCamName(i) for i in camlist])

		self.sp_rangeStart.setValue(self.core.getFrameRange()[0])
		self.sp_rangeEnd.setValue(self.core.getFrameRange()[1])

		prjName = self.core.getConfig("lastusedsettings", "projectname")
		if prjName is not None:
			self.e_projectName.setText(prjName)
		sFrame = self.core.getConfig("lastusedsettings", "startframe")
		if sFrame is not None:
			try:
				self.sp_rangeStart.setValue(int(sFrame))
			except:
				pass
		lFrame = self.core.getConfig("lastusedsettings", "endframe")
		if lFrame is not None:
			try:
				self.sp_rangeEnd.setValue(int(lFrame))
			except:
				pass
		cam = self.core.getConfig("lastusedsettings", "camera")
		if cam is not None:
			idx = self.cb_cam.findText(cam)
			if idx != -1:
				self.cb_cam.setCurrentIndex(idx)
		ro = self.core.getConfig("lastusedsettings", "resolutionoverride")
		if ro is not None:
			try:
				self.chb_resOverride.setChecked(eval(ro))
			except:
				pass
		rox = self.core.getConfig("lastusedsettings", "resolutionoverridex")
		if rox is not None:
			try:
				self.sp_resWidth.setValue(eval(rox))
			except:
				pass
		roy = self.core.getConfig("lastusedsettings", "resolutionoverridey")
		if roy is not None:
			try:
				self.sp_resHeight.setValue(eval(roy))
			except:
				pass
	#	outputOR = self.core.getConfig("lastusedsettings", "outputoverride")
	#	if outputOR is not None:
	#		try:
	#			self.gb_outputpath.setChecked(eval(outputOR))
	#		except:
	#			pass
		outPath = self.core.getConfig("lastusedsettings", "outputpath")
		if outPath is not None:
			try:
				self.e_outputpath.setText(outPath)
			except:
				pass
		prio = self.core.getConfig("lastusedsettings", "priority")
		if prio is not None:
			try:
				self.sp_priority.setValue(eval(prio))
			except:
				pass
		fpt = self.core.getConfig("lastusedsettings", "framespertask")
		if fpt is not None:
			try:
				self.sp_framesPerTask.setValue(eval(fpt))
			except:
				pass
		timout = self.core.getConfig("lastusedsettings", "tasktimeout")
		if timout is not None:
			try:
				self.sp_rjTimeout.setValue(eval(timout))
			except:
				pass
		suspended = self.core.getConfig("lastusedsettings", "suspended")
		if suspended is not None:
			try:
				self.chb_suspended.setChecked(eval(suspended))
			except:
				pass
		deps = self.core.getConfig("lastusedsettings", "dependentfiles")
		if deps is not None:
			try:
				self.chb_dependencies.setChecked(eval(deps))
			except:
				pass

		lm = self.core.getConfig("globals", "localmode")
		if lm is not None and eval(lm):
			self.chb_uploadOutput.setChecked(False)
			self.f_osUpload.setVisible(False)
		else:
			upload = self.core.getConfig("lastusedsettings", "uploadoutput")
			if upload is not None:
				try:
					self.chb_uploadOutput.setChecked(eval(upload))
				except:
					pass


	@err_decorator
	def saveSettings(self):
		self.core.setConfig("lastusedsettings", "projectname", self.e_projectName.text())
		self.core.setConfig("lastusedsettings", "startframe", str(self.sp_rangeStart.value()))
		self.core.setConfig("lastusedsettings", "endframe", str(self.sp_rangeEnd.value()))
		self.core.setConfig("lastusedsettings", "camera", self.cb_cam.currentText())
		self.core.setConfig("lastusedsettings", "resolutionoverride", str(self.chb_resOverride.isChecked()))
		self.core.setConfig("lastusedsettings", "resolutionoverridex", str(self.sp_resWidth.value()))
		self.core.setConfig("lastusedsettings", "resolutionoverridey", str(self.sp_resHeight.value()))
	#	self.core.setConfig("lastusedsettings", "outputoverride", str(self.gb_outputpath.isChecked()))
		self.core.setConfig("lastusedsettings", "outputpath", self.e_outputpath.text())
		self.core.setConfig("lastusedsettings", "priority", str(self.sp_priority.value()))
		self.core.setConfig("lastusedsettings", "framespertask", str(self.sp_framesPerTask.value()))
		self.core.setConfig("lastusedsettings", "tasktimeout", str(self.sp_rjTimeout.value()))
		self.core.setConfig("lastusedsettings", "suspended", str(self.chb_suspended.isChecked()))
		self.core.setConfig("lastusedsettings", "dependentfiles", str(self.chb_dependencies.isChecked()))
		self.core.setConfig("lastusedsettings", "uploadoutput", str(self.chb_uploadOutput.isChecked()))


	@err_decorator
	def startSubmission(self):
		jobName = self.e_jobName.text()
	#	outputName = "default"
	#	if self.gb_outputpath.isChecked():
	#		try:
		if not os.path.isabs(self.e_outputpath.text()) or os.path.splitext(self.e_outputpath.text())[1] == "":
			QMessageBox.warning(self.core.messageParent, "Submission canceled", "Submission Canceled:\n\nOutputpath is invalid.\nPlease enter a complete filename.")
			return
		
		outputName = os.path.join(os.path.dirname(self.e_outputpath.text()), "%s%s.exr" % (os.path.splitext(os.path.basename(self.e_outputpath.text()))[0], self.frameStr))
	#		except:
	#			pass
			
		rSettings = {"outputName": outputName}

		self.preSubmit(rSettings)

		result = self.submitJob(rSettings["outputName"])

		self.undoRenderSettings(rSettings)

		if result == "Success":
			self.close()
		elif result.startswith("Submission canceled"):
			QMessageBox.warning(self.core.messageParent, "Submission canceled", result)


	@err_decorator
	def submitJob(self, outputName):
		osFolder = None

		lmode = self.core.getConfig("globals", "localmode")
		if lmode == "True":
			localmode = True
		else:
			localmode = False

		if localmode:
			rootPath = self.core.getConfig("globals", "rootpath")
			if rootPath is not None:
				osFolder = os.path.join(rootPath, "PandoraFarm", "Workstations", "WS_" + socket.gethostname())
		else:
			osFolder = self.core.getConfig('submissions', "submissionpath")

		if osFolder is None:
			return "Submission canceled: No Pandora submission folder is configured."

		if osFolder == "":
			return "Submission canceled: No Pandora submission folder is configured."

		if not os.path.exists(osFolder):
			try:
				os.makedirs(osFolder)
			except:
				return "Submission canceled: Pandora submission folder could not be created."

		fileName = self.core.getCurrentFileName()
		if not os.path.exists(fileName):
			return "Submission canceled: Please save the scene first."

		if self.core.app == 2:
			renderNode = None
			try:
				if self.node.type().name() in ["ifd", "Redshift_ROP"]:
					renderNode = self.node.path()
			except:
				pass

			if renderNode is None:
				return "Submission canceled: Node is invalid."

		projectName = self.e_projectName.text()
		jobName = self.e_jobName.text()
		startFrame = self.sp_rangeStart.value()
		endFrame = self.sp_rangeEnd.value()
		renderCam = self.cb_cam.currentText()
		overrideResolution = self.chb_resOverride.isChecked()
		resolutionWidth = self.sp_resWidth.value()
		resolutionHeight = self.sp_resHeight.value()
		priority = self.sp_priority.value()
		framesPerTask = self.sp_framesPerTask.value()
		subspended = self.chb_suspended.isChecked()
		submitDependendFiles = self.chb_dependencies.isChecked()
		uploadOutput = self.chb_uploadOutput.isChecked()
		useProjectAssets = True
		listSlaves = "All"
		userName = self.core.getConfig("submissions", "username")
		if userName is None:
			userName = ""
		programName = self.core.programName
	#	if self.gb_outputpath.isChecked():
		outputbase = self.e_outputpath.text()
		if os.path.splitext(outputbase)[1] != "":
			outputbase = os.path.dirname(outputbase)
	#	else:
	#		outputpath = "default"

		self.saveSettings()

		if projectName == "":
			return "Submission canceled: Projectname is invalid."

		if jobName == "":
			return "Submission canceled: Jobname is invalid."

		if renderCam == "":
			return "Submission canceled: Camera is invalid."

		assignPath = os.path.join(osFolder, "JobSubmissions")

		jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
		jobPath = os.path.join(assignPath, jobCode , "JobFiles")
		while os.path.exists(jobPath):
			jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
			jobPath = os.path.join(assignPath, jobCode , "JobFiles")

		jobIni = os.path.join(os.path.dirname(jobPath), "PandoraJob.ini")

		if os.path.exists(jobPath):
			return "Submission canceled: Job already exists"

		self.core.saveScene()

		os.makedirs(jobPath)

		if useProjectAssets:
			assetPath = os.path.join(assignPath, "ProjectAssets", projectName)
			if not os.path.exists(assetPath):
				os.makedirs(assetPath)
		else:
			assetPath = jobPath

		jobFiles = [[os.path.basename(fileName), os.path.getmtime(fileName)]]

		if submitDependendFiles:
			if self.core.app == 6:
				bpy.ops.file.pack_all()
			else:
				extFiles = self.getExternalFiles()			

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
							self.core.parentWindow(msg)
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
						self.core.parentWindow(msg)
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
				if self.core.app == 6 and submitDependendFiles:
					jobFilePath = os.path.join(jobPath, self.core.getCurrentFileName(path=False))
					bpy.ops.wm.save_as_mainfile(filepath=jobFilePath, copy=True)
					bpy.ops.wm.revert_mainfile()
				else:
					shutil.copy2(fileName, jobPath)
				break
			except Exception as e:
				msg = QMessageBox(QMessageBox.Warning, "Pandora job submission", "An error occurred while copying the scenefile.\n\n%s" % e, QMessageBox.Cancel)
				msg.addButton("Retry", QMessageBox.YesRole)
				msg.addButton("Skip", QMessageBox.YesRole)
				self.core.parentWindow(msg)
				action = msg.exec_()

				if action == 1:
					break
				elif action != 0:
					return "Submission canceled: Could not copy the scenefile"

		if not useProjectAssets and len(jobFiles) != len(os.listdir(jobPath)):
			return "Submission canceled: The filecount in the jobsubmission folder is not correct. %s of %s" % (len(os.listdir(jobPath)), len(jobFiles))

		if not os.path.exists(jobIni):
			open(jobIni, 'a').close()

		config = ConfigParser()
		config.read(jobIni)

		config.add_section('jobglobals')
		config.set('jobglobals', 'priority', str(priority))
		config.set('jobglobals', 'uploadOutput', str(uploadOutput))
		config.set('jobglobals', 'listslaves', listSlaves)
		config.set('jobglobals', 'taskTimeout', str(self.sp_rjTimeout.value()))

		config.add_section('information')
		config.set('information', 'jobname', jobName)
		config.set('information', 'scenename', os.path.basename(fileName))
		config.set('information', 'projectname', projectName)
		config.set('information', 'username', userName)
		config.set('information', 'submitdate', time.strftime("%d.%m.%y, %X", time.localtime()))
		config.set('information', 'framerange', "%s-%s" % (startFrame, endFrame))
		config.set('information', 'outputpath', outputName)
		config.set('information', 'filecount', str(len(jobFiles)))
		config.set('information', 'savedbasepath', outputbase)
		config.set('information', 'outputbase', outputbase)
		config.set('information', 'program', programName)

		if self.core.app == 2:
			config.set('information', 'programversion', hou.applicationVersionString())
			config.set('jobglobals', 'rendernode ', renderNode)
		elif self.core.app == 3:
			config.set('information', 'programversion', cmds.about(version=True))

		if renderCam not in ["", "Current View"]:
			config.set('information', 'camera', renderCam)
		if useProjectAssets:
			config.set('information', 'projectassets', str(jobFiles))

		if overrideResolution:
			config.set('jobglobals', "width", str(resolutionWidth))
			config.set('jobglobals', "height", str(resolutionHeight))

		config.add_section('jobtasks')

		curFrame = startFrame
		tasksNum = 0
		if subspended:
			initState = "disabled"
		else:
			initState = "ready"

		while curFrame <= endFrame:
			taskStart = curFrame
			taskEnd = curFrame + framesPerTask - 1
			if taskEnd > endFrame:
				taskEnd = endFrame
			config.set('jobtasks', 'task'+ str(tasksNum), str([taskStart, taskEnd, initState, "unassigned", "", "", ""]))
			curFrame += framesPerTask
			tasksNum += 1
		with open(jobIni, 'w') as inifile:
			config.write(inifile)
		

		msg = QMessageBox(QMessageBox.Information, "Submit Pandora renderjob", "Successfully submited job \"%s\"" % jobName, QMessageBox.Ok)
		msg.addButton("Open in explorer", QMessageBox.YesRole)
		self.core.parentWindow(msg)
		action = msg.exec_()

		if action == 0:
			self.core.openFolder(os.path.dirname(jobPath))

		return "Success"


	@err_decorator
	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()


	@err_decorator
	def maxStartup(self):
		self.w_status.setVisible(False)
		self.w_connect.setVisible(False)


	@err_decorator
	def maxGetCams(self):
		cams = self.core.executeMaxScript("for i in cameras where (superclassof i) == camera collect i")
		return ["Current View"] + [cams.GetItem(x).GetHandle() for x in range(cams.GetCount())]


	@err_decorator
	def maxGetCamName(self, handle):
		if handle == "Current View":
			return handle

		return MaxPlus.INode.GetINodeByHandle(handle).GetName()


	@err_decorator
	def maxGetExternalFiles(self):
		return self.core.executeMaxScript("mapfiles=#()\n\
fn addmap mapfile =\n\
(\n\
if (finditem mapfiles mapfile) == 0 do append mapfiles mapfile\n\
)\n\
enumeratefiles addmap\n\
for mapfile in mapfiles collect mapfile")


	@err_decorator
	def maxPreSubmit(self, rSettings):
		MaxPlus.RenderSettings.CloseDialog()

		elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
		rSettings["elementsActive"] = MaxPlus.RenderElementMgr.GetElementsActive(elementMgr)
		activePasses = MaxPlus.RenderElementMgr.GetElementsActive(elementMgr)

		if activePasses and elementMgr.NumRenderElements() > 0:
			bName = os.path.splitext(os.path.basename(rSettings["outputName"]))
			bName = "%sbeauty.%s" % (bName[0], bName[1])
			rSettings["outputName"] = os.path.join(os.path.dirname(rSettings["outputName"]), "beauty", bName)

			for i in range(elementMgr.NumRenderElements()):
				element = elementMgr.GetRenderElement(i)
				passName = element.GetElementName()
				passOutputName = os.path.join(os.path.dirname(os.path.dirname(rSettings["outputName"])), passName, os.path.basename(rSettings["outputName"]).replace("beauty", passName))
				try:
					os.makedirs(os.path.dirname(passOutputName))
				except:
					pass
				self.core.executeMaxScript("(maxOps.GetCurRenderElementMgr()).SetRenderElementFilename %s \"%s\"" % (i, passOutputName.replace("\\","\\\\")), returnVal=False)

		rSettings["savefile"] = MaxPlus.RenderSettings.GetSaveFile()
		rSettings["savefilepath"] = MaxPlus.RenderSettings.GetOutputFile()
		MaxPlus.RenderSettings.SetSaveFile(True)
		MaxPlus.RenderSettings.SetOutputFile(rSettings["outputName"])


	@err_decorator
	def maxUndoRenderSettings(self, rSettings):
		if "elementsActive" in rSettings:
			elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
			MaxPlus.RenderElementMgr.SetElementsActive(elementMgr, rSettings["elementsActive"])
		if "width" in rSettings:
			MaxPlus.RenderSettings.SetWidth(rSettings["width"])
		if "height" in rSettings:
			MaxPlus.RenderSettings.SetHeight(rSettings["height"])
		if "timetype" in rSettings:
			MaxPlus.RenderSettings.SetTimeType(rSettings["timetype"])
		if "start" in rSettings:
			MaxPlus.RenderSettings.SetStart(rSettings["start"])
		if "end" in rSettings:
			MaxPlus.RenderSettings.SetEnd(rSettings["end"])
		if "savefile" in rSettings:
			MaxPlus.RenderSettings.SetSaveFile(rSettings["savefile"])
		if "savefilepath" in rSettings:
			MaxPlus.RenderSettings.SetOutputFile(rSettings["savefilepath"])


	@err_decorator
	def houStartup(self):
		self.scrollArea.setStyleSheet(hou.qt.styleSheet().replace("QLabel", "QScrollArea"))

		self.node = None
		self.l_status.setText("Not connected")
		self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")


	@err_decorator
	def houSetRcStyle(self, rcMenu):
		rcMenu.setStyleSheet(hou.qt.styleSheet())


	@err_decorator
	def goToNode(self):
		try:
			self.node.name()
		except:
			return False

		self.node.setCurrent(True, clear_all_selected=True)
		hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).frameSelection()


	@err_decorator
	def connectNode(self):
		if len(hou.selectedNodes()) > 0 and (hou.selectedNodes()[0].type().name() == "ifd" or hou.selectedNodes()[0].type().name() == "Redshift_ROP"):
			self.node = hou.selectedNodes()[0]

			self.node.name()
			self.l_status.setText(self.node.name())
			self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")


	@err_decorator
	def houGetCams(self):
		cams = []
		for node in hou.node("/").allSubChildren():

			if (node.type().name() == "cam" and node.name() != "ipr_camera") or node.type().name() == "vrcam":
				cams.append(node)

		return cams


	@err_decorator
	def houGetCamName(self, handle):
		return handle.name()


	@err_decorator
	def houGetExternalFiles(self):
		hou.setFrame(hou.playbar.playbackRange()[0])
		whitelist = ['$HIP/$OS-bounce.rat', '$HIP/$OS-fill.rat', '$HIP/$OS-key.rat', '$HIP/$OS-rim.rat']
		houdeps = hou.fileReferences()
		extFiles = []
		extFilesSource = []
		for x in houdeps:
			if "/Redshift/Plugins/Houdini/" in x[1]:
				continue

			if x[0] is None:
				continue

			if x[1] in whitelist:
				continue

			if not os.path.isabs(hou.expandString(x[1])):
				continue

			if os.path.splitext(hou.expandString(x[1]))[1] == "":
				continue

			if x[0] is not None and x[0].name() in ["RS_outputFileNamePrefix", "vm_picture"]:
				continue

			if x[0] is not None and x[0].name() in ["filename", "dopoutput", "copoutput", "sopoutput"] and x[0].node().type().name() in ["rop_alembic", "rop_dop", "rop_comp", "rop_geometry"]:
				continue

			extFiles.append(hou.expandString(x[1]).replace("\\", "/"))
			extFilesSource.append(x[0])

		#return [extFiles, extFilesSource]
		return extFiles


	@err_decorator
	def mayaStartup(self):
		self.w_status.setVisible(False)
		self.w_connect.setVisible(False)


	@err_decorator
	def mayaGetCams(self):
		return ["Current View"] + cmds.listRelatives(cmds.ls(cameras=True, long =True), parent=True, fullPath=True)


	@err_decorator
	def mayaGetCamName(self, node):
		if node == "Current View":
			return node

		nodes = cmds.ls(node)
		if len(nodes) == 0:
			return "invalid"
		else:
			return str(nodes[0])


	@err_decorator
	def mayaGetExternalFiles(self):
		extFiles = [self.core.fixPath(str(x)) for x in self.core.executeMayaPython("cmds.file(query=True, list=True)") if self.core.fixPath(str(x)) != self.core.getCurrentFileName()]
		return extFiles


	@err_decorator
	def mayaPreSubmit(self, rSettings):
		if self.chb_resOverride.isChecked():
			rSettings["width"] = cmds.getAttr("defaultResolution.width")
			rSettings["height"] = cmds.getAttr("defaultResolution.height")
			cmds.setAttr("defaultResolution.width", self.sp_resWidth.value())
			cmds.setAttr("defaultResolution.height", self.sp_resHeight.value())

		rSettings["imageFolder"] = cmds.workspace( fileRuleEntry = 'images')
		rSettings["imageFilePrefix"] = cmds.getAttr("defaultRenderGlobals.imageFilePrefix")
		rSettings["outFormatControl"] = cmds.getAttr("defaultRenderGlobals.outFormatControl")
		rSettings["animation"] = cmds.getAttr("defaultRenderGlobals.animation")
		rSettings["putFrameBeforeExt"] = cmds.getAttr("defaultRenderGlobals.putFrameBeforeExt")
		rSettings["extpadding"] = cmds.getAttr("defaultRenderGlobals.extensionPadding")

		outputPrefix = "../" + os.path.splitext(os.path.basename(rSettings["outputName"]))[0]

		cmds.workspace( fileRule = ['images', os.path.dirname(rSettings["outputName"])])
		cmds.setAttr("defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string")
		cmds.setAttr("defaultRenderGlobals.outFormatControl", 0)
		cmds.setAttr("defaultRenderGlobals.animation", 1)
		cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", 1)
		cmds.setAttr("defaultRenderGlobals.extensionPadding", 4)
		
		curRenderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
		if curRenderer == "arnold":
			driver = cmds.ls('defaultArnoldDriver')
			if not driver:
				mel.eval('RenderGlobalsWindow;') 
			rSettings["ar_fileformat"] = cmds.getAttr("defaultArnoldDriver.ai_translator")
			rSettings["ar_exrPixelType"] = cmds.getAttr("defaultArnoldDriver.halfPrecision")
			rSettings["ar_exrCompression"] = cmds.getAttr("defaultArnoldDriver.exrCompression")

			cmds.setAttr("defaultArnoldDriver.ai_translator", "exr", type="string")
			cmds.setAttr("defaultArnoldDriver.halfPrecision", 1) # 16 bit
			cmds.setAttr("defaultArnoldDriver.exrCompression", 3) # ZIP compression

			aAovs = maovs.AOVInterface().getAOVNodes(names=True)
			aAovs = [x for x in aAovs if cmds.getAttr(x[1] + '.enabled')]
			if cmds.getAttr("defaultArnoldRenderOptions.aovMode") != 0 and len(aAovs) > 0:
				outputPrefix = "../" + outputPrefix + ".beauty"
				cmds.setAttr("defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string")
				bName = os.path.splitext(os.path.basename(rSettings["outputName"]))
				bName = "%s.beauty%s" % (bName[0], bName[1])
				rSettings["outputName"] = os.path.join(os.path.dirname(rSettings["outputName"]), bName)

				drivers = ["defaultArnoldDriver"]
				for i in aAovs:
					aDriver = cmds.connectionInfo("%s.outputs[0].driver" % i[1], sourceFromDestination=True).rsplit(".",1)[0]
					if aDriver in drivers or aDriver == "":
						aDriver = cmds.createNode( 'aiAOVDriver', n='%s_driver' % i[0] )
						cmds.connectAttr("%s.aiTranslator" % aDriver, "%s.outputs[0].driver" % i[1], force=True)

					drivers.append(aDriver)
					cmds.setAttr(aDriver + ".prefix" , os.path.join("..", i[0], os.path.basename(outputPrefix)).replace("beauty", i[0]), type="string")
		elif curRenderer == "vray":
			driver = cmds.ls('vraySettings')
			if not driver:
				mel.eval('RenderGlobalsWindow;')

			rSettings["vr_imageFilePrefix"] = cmds.getAttr("vraySettings.fileNamePrefix")
			rSettings["vr_fileformat"] = cmds.getAttr("vraySettings.imageFormatStr")
			rSettings["vr_sepRGBA"] = cmds.getAttr("vraySettings.relements_separateRGBA")
			rSettings["vr_animation"] = cmds.getAttr("vraySettings.animType")

			cmds.setAttr("vraySettings.imageFormatStr", "exr", type="string")
			cmds.setAttr("vraySettings.animType", 1)

			aovs = cmds.ls(type='VRayRenderElement')
			aovs = [x for x in aovs if cmds.getAttr(x + '.enabled')]

			outputPrefix = outputPrefix[3:]

			if cmds.getAttr("vraySettings.relements_enableall") != 0 and len(aovs) > 0:
				if os.path.exists(os.path.dirname(rSettings["outputName"])) and len(os.listdir(os.path.dirname(rSettings["outputName"]))) == 0:
					try:
						shutil.rmtree(os.path.dirname(rSettings["outputName"]))
					except:
						pass

				rSettings["vr_sepFolders"] = cmds.getAttr("vraySettings.relements_separateFolders")
				rSettings["vr_sepStr"] = cmds.getAttr("vraySettings.fileNameRenderElementSeparator")

				cmds.setAttr("vraySettings.fileNamePrefix", outputPrefix, type="string")
				cmds.setAttr("vraySettings.relements_separateFolders", 1)
				cmds.setAttr("vraySettings.relements_separateRGBA", 1)
				cmds.setAttr("vraySettings.fileNameRenderElementSeparator", ".", type="string")
			else:
				cmds.setAttr("vraySettings.relements_separateRGBA", 0)
				cmds.setAttr("vraySettings.fileNamePrefix", outputPrefix, type="string")
		elif curRenderer == "redshift":
			driver = cmds.ls('redshiftOptions')
			if not driver:
				mel.eval('RenderGlobalsWindow;')

			rSettings["rs_fileformat"] = cmds.getAttr("redshiftOptions.imageFormat")

			cmds.setAttr("redshiftOptions.imageFormat", 1)

			outputPrefix = outputPrefix[3:]

			aovs = cmds.ls(type='RedshiftAOV')
			aovs = [[cmds.getAttr(x + ".name"), x] for x in aovs if cmds.getAttr(x + '.enabled')]

			if cmds.getAttr("redshiftOptions.aovGlobalEnableMode") != 0 and len(aovs) > 0:
				outputPrefix += ".beauty"
				bName = os.path.splitext(os.path.basename(rSettings["outputName"]))
				bName = "%s.beauty%s" % (bName[0], bName[1])
				rSettings["outputName"] = os.path.join(os.path.dirname(rSettings["outputName"]), "beauty", bName)
				for i in aovs:
					cmds.setAttr(i[1] + ".filePrefix", "<BeautyPath>/../<RenderPass>/%s" % os.path.basename(outputPrefix).replace("beauty", i[0]), type="string")
		
			cmds.setAttr("defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string")

		else:
			rSettings["fileformat"] = cmds.getAttr("defaultRenderGlobals.imageFormat")
			rSettings["exrPixelType"] = cmds.getAttr("defaultRenderGlobals.exrPixelType")
			rSettings["exrCompression"] = cmds.getAttr("defaultRenderGlobals.exrCompression")

			if curRenderer in ["mayaSoftware", "mayaHardware", "mayaVector"]:
				rndFormat = 4 # .tif
			else:
				rndFormat = 40 # .exr
			cmds.setAttr("defaultRenderGlobals.imageFormat", rndFormat)
			cmds.setAttr("defaultRenderGlobals.exrPixelType", 1) # 16 bit
			cmds.setAttr("defaultRenderGlobals.exrCompression", 3) # ZIP compression


	@err_decorator
	def mayaUndoRenderSettings(self, rSettings):
		if "width" in rSettings:
			cmds.setAttr("defaultResolution.width", rSettings["width"])
		if "height" in rSettings:
			cmds.setAttr("defaultResolution.height", rSettings["height"])
		if "imageFolder" in rSettings:
			cmds.workspace( fileRule = ['images', rSettings["imageFolder"]])
		if "imageFilePrefix" in rSettings:
			if rSettings["imageFilePrefix"] is None:
				prefix = ""
			else:
				prefix = rSettings["imageFilePrefix"]
			cmds.setAttr("defaultRenderGlobals.imageFilePrefix", prefix, type="string")
		if "outFormatControl" in rSettings:
			cmds.setAttr("defaultRenderGlobals.outFormatControl", rSettings["outFormatControl"])
		if "animation" in rSettings:
			cmds.setAttr("defaultRenderGlobals.animation", rSettings["animation"])
		if "putFrameBeforeExt" in rSettings:
			cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", rSettings["putFrameBeforeExt"])
		if "extpadding" in rSettings:
			cmds.setAttr("defaultRenderGlobals.extensionPadding", rSettings["extpadding"])
		if "fileformat" in rSettings:
			cmds.setAttr("defaultRenderGlobals.imageFormat", rSettings["fileformat"])
		if "exrPixelType" in rSettings:
			cmds.setAttr("defaultRenderGlobals.exrPixelType", rSettings["exrPixelType"])
		if "exrCompression" in rSettings:
			cmds.setAttr("defaultRenderGlobals.exrCompression", rSettings["exrCompression"])
		if "ar_fileformat" in rSettings:
			cmds.setAttr("defaultArnoldDriver.ai_translator", rSettings["ar_fileformat"], type="string")
		if "ar_exrPixelType" in rSettings:
			cmds.setAttr("defaultArnoldDriver.halfPrecision", rSettings["ar_exrPixelType"])
		if "ar_exrCompression" in rSettings:
			cmds.setAttr("defaultArnoldDriver.exrCompression", rSettings["ar_exrCompression"])
		if "vr_fileformat" in rSettings:
			cmds.setAttr("vraySettings.imageFormatStr", rSettings["vr_fileformat"], type="string")
		if "startFrame" in rSettings:
			cmds.setAttr("defaultRenderGlobals.startFrame", rSettings["startFrame"])
		if "endFrame" in rSettings:
			cmds.setAttr("defaultRenderGlobals.endFrame", rSettings["endFrame"])
		if "vr_imageFilePrefix" in rSettings:
			cmds.setAttr("vraySettings.fileNamePrefix", rSettings["vr_imageFilePrefix"], type="string")
		if "vr_sepFolders" in rSettings:
			cmds.setAttr("vraySettings.relements_separateFolders", rSettings["vr_sepFolders"])
		if "vr_sepRGBA" in rSettings:
			cmds.setAttr("vraySettings.relements_separateRGBA", rSettings["vr_sepRGBA"])
		if "vr_sepStr" in rSettings:
			cmds.setAttr("vraySettings.fileNameRenderElementSeparator", rSettings["vr_sepStr"], type="string")
		if "rs_fileformat" in rSettings:
			cmds.setAttr("redshiftOptions.imageFormat", rSettings["rs_fileformat"])


	@err_decorator
	def bldStartup(self):
		self.resize(self.width(), self.height()+60 )
		self.w_status.setVisible(False)
		self.w_connect.setVisible(False)


	@err_decorator
	def bldGetCams(self):
		return [ x.name for x in bpy.context.scene.objects if x.type == "CAMERA"]


	@err_decorator
	def bldGetCamName(self, node):
		return node


	@err_decorator
	def bldPreSubmit(self, rSettings):
		if self.chb_resOverride.isChecked():
			rSettings["width"] = bpy.context.scene.render.resolution_x
			rSettings["height"] = bpy.context.scene.render.resolution_y
			bpy.context.scene.render.resolution_x = self.sp_resWidth.value()
			bpy.context.scene.render.resolution_y = self.sp_resHeight.value()

		jobFrames = [self.sp_rangeStart.value(), self.sp_rangeEnd.value()]

		rSettings["start"] = bpy.context.scene.frame_start
		rSettings["end"] = bpy.context.scene.frame_end
		rSettings["fileformat"] = bpy.context.scene.render.image_settings.file_format
		rSettings["overwrite"] = bpy.context.scene.render.use_overwrite
		rSettings["fileextension"] = bpy.context.scene.render.use_file_extension
		rSettings["resolutionpercent"] = bpy.context.scene.render.resolution_percentage
		rSettings["origOutputName"] = rSettings["outputName"]
		bpy.context.scene["PrismIsRendering"] = True
		bpy.context.scene.render.filepath = rSettings["outputName"]
		bpy.context.scene.render.image_settings.file_format = "OPEN_EXR"
		bpy.context.scene.render.image_settings.color_depth = "16"
		bpy.context.scene.frame_start = jobFrames[0]
		bpy.context.scene.frame_end = jobFrames[1]
		bpy.context.scene.render.use_overwrite = True
		bpy.context.scene.render.use_file_extension = False
		bpy.context.scene.render.resolution_percentage = 100
		if self.cb_cam.currentText() in bpy.context.scene.objects:
			bpy.context.scene.camera = bpy.context.scene.objects[self.cb_cam.currentText()]

		usePasses = False
		if bpy.context.scene.node_tree is not None and bpy.context.scene.use_nodes:
			outNodes = [x for x in bpy.context.scene.node_tree.nodes if x.type == 'OUTPUT_FILE']
			rlayerNodes = [x for x in bpy.context.scene.node_tree.nodes if x.type == 'R_LAYERS']

			bName = os.path.splitext(os.path.basename(rSettings["outputName"]))
			if bName[0].endswith(self.frameStr):
				bName = "%s.beauty%s%s" % (bName[0][:-5],bName[0][-5:] , bName[1])
			else:
				bName = "%s.beauty%s" % (bName[0], bName[1])
			rSettings["outputName"] = os.path.join(os.path.dirname(rSettings["outputName"]), "beauty", bName)

			for m in outNodes:
				connections = []
				for idx, i in enumerate(m.inputs):
					if len(list(i.links)) > 0:
						connections.append([i.links[0], idx])

				m.base_path = os.path.dirname(rSettings["outputName"])

				for i, idx in connections:
					passName = i.from_socket.name

					if passName == "Image":
						passName = "beauty"
			
					if i.from_node.type == "R_LAYERS":
						if len(rlayerNodes) > 1:
							passName = "%s_%s" % (i.from_node.layer, passName)

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
					
					curSlot.path = "../%s/%s" % (passName, os.path.splitext(os.path.basename(rSettings["outputName"]))[0].replace("beauty", passName) + ext)
					newOutputPath = os.path.abspath(os.path.join(rSettings["outputName"], "../..", passName, os.path.splitext(os.path.basename(rSettings["outputName"]))[0].replace("beauty", passName) + ext))
					if passName == "beauty":
						rSettings["outputName"] = newOutputPath
					usePasses = True

		if usePasses:
			import platform
			if platform.system() == "Windows":
				tmpOutput = os.path.join(os.environ["temp"], "PrismRender", "tmp.####.exr")
				bpy.context.scene.render.filepath = tmpOutput
				if not os.path.exists(os.path.dirname(tmpOutput)):
					os.makedirs(os.path.dirname(tmpOutput))


	@err_decorator
	def bldUndoRenderSettings(self, rSettings):
		if "width" in rSettings:
			bpy.context.scene.render.resolution_x = rSettings["width"]
		if "height" in rSettings:
			bpy.context.scene.render.resolution_y = rSettings["height"]
		if "start" in rSettings:
			bpy.context.scene.frame_start = rSettings["start"]
		if "end" in rSettings:
			bpy.context.scene.frame_end = rSettings["end"]
		if "fileformat" in rSettings:
			bpy.context.scene.render.image_settings.file_format = rSettings["fileformat"]
		if "overwrite" in rSettings:
			bpy.context.scene.render.use_overwrite = rSettings["overwrite"]
		if "fileextension" in rSettings:
			bpy.context.scene.render.use_file_extension = rSettings["fileextension"]
		if "resolutionpercent" in rSettings:
			bpy.context.scene.render.resolution_percentage = rSettings["resolutionpercent"]