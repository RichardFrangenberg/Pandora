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



import os, sys, shutil
from win32com.shell import shellcon
import win32com.shell.shell as shell
import win32con, win32event, win32process
from PySide.QtCore import *
from PySide.QtGui import *

def removePandoraFiles(pandoraPath):
	try:
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

		smTray = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Pandora", "PandoraTray.lnk")
		smHandler = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Pandora", "PandoraRenderHandler.lnk")
		smSettings = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Pandora", "PandoraSettings.lnk")
		smSlave = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Pandora", "PandoraSlave.lnk")
		smCoordinator = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Pandora", "PandoraCoordinator.lnk")
		suTray = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "PandoraTray.lnk")

		for i in [smTray, smHandler, smSettings, smSlave, smCoordinator, suTray]:
			if os.path.exists(i):
				try:
					os.remove(i)
				except:
					pass

		smFolder = os.path.dirname(smTray)
		try:
			shutil.rmtree(smFolder)
		except:
			pass

		if os.path.exists(pandoraPath):
			print "remove old files.."
			
			while True:
				try:
					shutil.rmtree(pandoraPath)
					break
				except WindowsError:
					msg = QMessageBox(QMessageBox.Warning, "Remove old files", "Could not remove Pandora files.\n\nMake sure all dependent programms like Max, Maya, Houdini, Blender, TrayIcon and eventually the windows explorer are closed.", QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					action = msg.exec_()

					if action != 0:
						print "Canceled Pandora files removal"
						return False

		return True

	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		QMessageBox.warning(QWidget(), "Pandora Uninstallation", "Error occurred during Pandora files removal:\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))
		return False


def removeMaxFiles(installPath):
	try:
		initPy = os.path.join(installPath, "python", "initPandora.py")
		initMs = os.path.join(installPath, "initPandora.ms")
		menuMs = os.path.join(installPath, "PandoraMenu.ms")
		macroMcr = os.path.join(os.path.dirname(os.path.dirname(installPath)), "usermacros", "PandoraMacros.mcr")

		for i in [initPy, initMs, menuMs, macroMcr]:
			if os.path.exists(i):
				try:
					os.remove(i)
				except:
					pass

		uninstallStr = """
if menuMan.findMenu "Pandora" != undefined then
(
	menuMan.unRegisterMenu (menuMan.findMenu "Pandora")
)

curPath = getThisScriptFilename()
deleteFile curPath
"""

		uninstallPath = os.path.join(installPath, "uninstallPandora.ms")

		if os.path.exists(uninstallPath):
			try:
				os.remove(uninstallPath)
			except:
				pass

		with open(uninstallPath, "w") as uninstallFile:
			uninstallFile.write(uninstallStr)

		print "3ds Max integration removed successfully"
		return True

	except Exception as e:
		print "Error occurred during 3ds Max integration removal: " + str(e)
		return False


def removeMayaFiles(installPath):
	try:
		initPy = os.path.join(installPath, "scripts", "PandoraInit.py")
		initPyc = os.path.join(installPath, "scripts", "PandoraInit.pyc")
		shelfpath = os.path.join(installPath, "prefs", "shelves", "shelf_Pandora.mel")

		for i in [initPy, initPyc, shelfpath]:
			if os.path.exists(i):
				try:
					os.remove(i)
				except:
					pass

		userSetup = os.path.join(installPath, "scripts", "userSetup.py")

		if os.path.exists(userSetup):
			with open(userSetup, "r") as usFile:
				text = usFile.read()

			if "#>>>PandoraStart" in text and "#<<<PandoraEnd" in text:
				text = text[:text.find("#>>>PandoraStart")] + text[text.find("#<<<PandoraEnd")+len("#<<<PandoraEnd"):]

				otherChars = [x for x in text if x != " "]
				if len(otherChars) == 0:
					try:
						os.remove(userSetup)
					except:
						pass
				else:
					with open(userSetup, "w") as usFile:
						usFile.write(text)

		print "Maya integration removed successfully"
		return True

	except Exception as e:
		print "Error occurred during Maya integration removal: " + str(e)
		return False


def removeHoudiniFiles(installPath):
	try:
		initPy = os.path.join(installPath, "houdini", "python2.7libs", "PandoraInit.py")

		for i in [initPy]:
			if os.path.exists(i):
				try:
					os.remove(i)
				except:
					pass

		prc = os.path.join(installPath, "houdini", "python2.7libs", "pythonrc.py")

		for i in [prc]:
			if os.path.exists(i):
				with open(i, "r") as usFile:
					text = usFile.read()

				if "#>>>PandoraStart" in text and "#<<<PandoraEnd" in text:
					text = text[:text.find("#>>>PandoraStart")] + text[text.find("#<<<PandoraEnd")+len("#<<<PandoraEnd"):]

					otherChars = [x for x in text if x != " "]
					if len(otherChars) == 0:
						try:
							os.remove(i)
						except:
							pass
					else:
						with open(i, "w") as usFile:
							usFile.write(text)

		print "Houdini integration removed successfully"
		return True

	except Exception as e:
		print "Error occurred during Houdini integration removal: " + str(e)
		return False


def removeBlenderFiles(installPath):
	try:
		initPy = os.path.join(installPath, "scripts", "startup", "PandoraInit.py")

		for i in [initPy]:
			if os.path.exists(i):
				try:
					os.remove(i)
				except:
					pass

		print "Blender integration removed successfully"
		return True

	except Exception as e:
		print "Error occurred during Blender integration removal: " + str(e)
		return False


def uninstallPandora(user=""):
	msg = QMessageBox(QMessageBox.Question, "Pandora Render Manager", "Are you sure you want to uninstall Pandora?\n\nThis will delete all Pandora files and Pandora integrations from your PC. Your renderings and scenefiles will remain unaffected.", QMessageBox.Cancel)
	msg.addButton("Continue", QMessageBox.YesRole)
	msg.setFocus()
	action = msg.exec_()

	if action != 0:
		return False

	pandoraPath = os.path.join(os.path.dirname(os.environ["Userprofile"]), user, "AppData", "Local", "Pandora")

	locFile = os.path.join(pandoraPath, "installLocations.txt")

	print "uninstalling..."

	result = {}

	if os.path.exists(locFile):
		with open(locFile, 'r') as locationfile:
			lines = locationfile.readlines()
			for line in lines:
				line = line.replace("\n", "")
				if "3dsMax" in line:
					result["3ds Max integration"] = removeMaxFiles(line)
				elif "maya" in line:
					result["Maya integration"] = removeMayaFiles(line)
				elif "Houdini" in line:
					result["Houdini integration"] = removeHoudiniFiles(line)
				elif "Blender" in line:
					result["Blender integration"] = removeBlenderFiles(line)
				elif "nuke" in line:
					result["Nuke integration"] = removeNukeFiles(line)

	result["Pandora Files"] = removePandoraFiles(pandoraPath)

	return result


def force_elevated():
	try:
		if sys.argv[-1] != 'asadmin':
			script = os.path.abspath(sys.argv[0])
			params = ' '.join(["\"%s\"" % script] + sys.argv[1:] + ['asadmin'])
			procInfo = shell.ShellExecuteEx(nShow=win32con.SW_SHOWNORMAL,
								 fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
								 lpVerb='runas',
								 lpFile=sys.executable,
								 lpParameters=params)

			procHandle = procInfo['hProcess']    
			obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
			rc = win32process.GetExitCodeProcess(procHandle)

		#	sys.exit()
	except Exception as ex:
		print ex