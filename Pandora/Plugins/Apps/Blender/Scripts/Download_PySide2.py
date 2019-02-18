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
# Copyright (C) 2016-2019 Richard Frangenberg
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



import os, sys, platform, subprocess, shutil, traceback, time, io, errno, stat
from functools import wraps

pandoraRoot = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir, os.pardir))

sys.path.insert(0, os.path.join(pandoraRoot, "Scripts"))
sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", "Python27", "PySide"))

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1


def err_decorator(func):
	@wraps(func)
	def func_wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			erStr = ("%s ERROR - Pandora PySide2 Setup %s:\n\n%s" % (time.strftime("%d/%m/%y %X"), ''.join(traceback.format_stack()), traceback.format_exc()))
			print erStr
			QMessageBox.warning(QWidget(), "Pandora", erStr)

	return func_wrapper


@err_decorator
def openSetupDialog():
	qapp = QApplication.instance()
	if qapp == None:
		qapp = QApplication(sys.argv)

	if sys.argv[1] == "Python35":
		qssFile = os.path.join(pandoraRoot, "Plugins", "Apps", "Blender", "UserInterfaces", "BlenderStyleSheet", "Blender2.79.qss")
	else:
		qssFile = os.path.join(pandoraRoot, "Plugins", "Apps", "Blender", "UserInterfaces", "BlenderStyleSheet", "Blender2.8.qss")

	with (open(qssFile, "r")) as ssFile:
		ssheet = ssFile.read()

	ssheet = ssheet.replace("qss:", os.path.dirname(qssFile).replace("\\", "/") + "/")
	qapp.setStyleSheet(ssheet)
	appIcon = QIcon(os.path.join(pandoraRoot, "Scripts", "UserInterfacesPandora", "pandora_tray.png"))
	qapp.setWindowIcon(appIcon)

	msg = QMessageBox()
	msg.setWindowTitle("Pandora")
	msg.setText("Pandora requires the PySide2 library for Python %s.%s in order to display its user interfaces.\n\nYou can download it now automatically or you can download it manually from the Pandora website." % (sys.argv[-1][-2], sys.argv[-1][-1]))
	msg.addButton("Download", QMessageBox.YesRole)
	msg.addButton("Open website", QMessageBox.YesRole)
	msg.addButton("Cancel", QMessageBox.YesRole)

	action = msg.exec_()

	if action == 0:
		downloadPySide2()
	elif action == 1:
		openWebsite()


@err_decorator
def downloadPySide2():
		if sys.argv[1] == "Python35":
			libFolder = "Python35"
			libStr = "Python 3.5"
		elif sys.argv[1] == "Python37":
			libFolder = "Python37"
			libStr = "Python 3.7"
		else:
			return

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
	page = requests.get('https://prism-pipeline.com/downloads/', verify=False)
	#page = requests.get('https://prism-pipeline.com/downloads/')
	cStr = page.content
	vCode = 'PySide2_%s_URL: ['
	dbLinknStr = cStr[cStr.find(vCode)+len(vCode): cStr.find(']', cStr.find(vCode))]
	sys.stdout.write(dbLinknStr)
except Exception as e:
	sys.stdout.write('failed %%s' %% e)
""" % (pandoraRoot, pandoraRoot, libFolder)

		if platform.system() == "Windows":
			pythonPath = os.path.join(pandoraRoot, "Python27", "pythonw.exe")
		else:
			pythonPath = "python"

		result = subprocess.Popen([pythonPath, "-c", pStr], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdOutData, stderrdata = result.communicate()

		if "failed" in str(stdOutData) or len(str(stdOutData).split(".")) < 3:
			QMessageBox.information(QWidget(), "Pandora", "Unable to connect to www.prism-pipeline.com. Could not download PySide2.", QMessageBox.Ok)
			return

		stdOutData = stdOutData.decode("utf-8")

		url = str(stdOutData)

		dlMsg = "Downloading PySide2 (~50-90mb) - please wait.."

		waitmsg = QMessageBox(QMessageBox.NoIcon, "Pandora", dlMsg, QMessageBox.Cancel)
		waitmsg.buttons()[0].setHidden(True)
		waitmsg.show()
		QCoreApplication.processEvents()

		import urllib

		u = urllib.urlopen(url)
		length = u.info().getheaders("Content-Length")[0]

		if length:
			length = int(length)
			blocksize = max(4096, length//100)
		else:
			blocksize = 1000000 # just made something up

		data = io.BytesIO()
		size = 0
		while True:
			buf1 = u.read(blocksize)
			if not buf1:
				break
			data.write(buf1)
			size += len(buf1)
			size += 1
			if length:
				waitmsg.setText( dlMsg + ' {}%\r done'.format(int((size/float(length))*100)))
				QCoreApplication.processEvents()

		u.close()

		if platform.system() == "Windows":
			targetdir = os.path.join(os.environ["temp"], "Pandora_PySide2")
		else:
			targetdir = "/tmp/Pandora_PySide2"

		filepath = os.path.join(targetdir, "Pandora_PySide2.zip")

		if os.path.exists(os.path.dirname(filepath)):
			shutil.rmtree(os.path.dirname(filepath), ignore_errors=False, onerror=handleRemoveReadonly)

		if not os.path.exists(os.path.dirname(filepath)):
			os.makedirs(os.path.dirname(filepath))

		with open(filepath, "wb") as f :
			f.write(data.getvalue())

		import zipfile

		waitmsg = QMessageBox(QMessageBox.NoIcon, "Pandora", "Installing - please wait..", QMessageBox.Cancel)
		waitmsg.buttons()[0].setHidden(True)
		waitmsg.show()
		QCoreApplication.processEvents()

		with zipfile.ZipFile(filepath,"r") as zip_ref:
			zip_ref.extractall(targetdir)

		libRoot = os.path.join(targetdir, libFolder)

		if not os.path.exists(libRoot):
			QMessageBox.critical(QWidget(), "Pandora", "Expected folder doesn't exist.\n(%s)" % libRoot, QMessageBox.Ok)
			return

		for i in os.walk(libRoot):
			dirs = i[1]
			break

		libTarget = os.path.join(pandoraRoot, "PythonLibs", libFolder)

		for i in dirs:
			rootLib = os.path.join(libRoot, i)
			installedLib = os.path.join(libTarget, i)
			if os.path.exists(installedLib):
				shutil.rmtree(installedLib, ignore_errors=False, onerror=handleRemoveReadonly)

			shutil.copytree(rootLib, installedLib)

		if "waitmsg" in locals() and waitmsg.isVisible():
			waitmsg.close()

		QMessageBox.information(QWidget(), "Pandora", "Successfully set up PySide2 for Pandora (%s)." % libStr, QMessageBox.Ok)


@err_decorator
def handleRemoveReadonly(func, path, exc):
	excvalue = exc[1]
	if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
		os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
		func(path)
	else:
		raise


@err_decorator
def openWebsite():
	url = "https://prism-pipeline.com/downloads/"
		
	import webbrowser
	webbrowser.open(url)


if __name__ == "__main__":
	openSetupDialog()