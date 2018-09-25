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

if psVersion == 1:
	from UserInterfacesPandora import PandoraChangeUser_ui
else:
	from UserInterfacesPandora import PandoraChangeUser_ui_ps2 as PandoraChangeUser_ui

import sys, os, traceback, time
from functools import wraps

from UserInterfacesPandora import qdarkstyle


class PandoraChangeUser(QDialog, PandoraChangeUser_ui.Ui_dlg_ChangeUser):
	def __init__(self, core):
		QDialog.__init__(self)
		self.setupUi(self)

		self.core = core
		self.core.parentWindow(self)

		self.connectEvents()

		self.setNames()

		self.validate()


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - PandoraChangeUser %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def connectEvents(self):
		self.e_name.textChanged.connect(lambda x: self.validate(x, self.e_name))
		self.buttonBox.accepted.connect(self.setUser)
		self.e_name.cursorPositionChanged.connect(self.cursorMoved)


	@err_decorator
	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()


	@err_decorator
	def setNames(self):
		if os.path.exists(self.core.configPath):
			try:	
				uname = self.core.getConfig("globals", "username")
				if uname is None:
					return
				
				self.e_name.setText(uname)

				self.validate()

			except Exception as e:
				QMessageBox.warning(self,"Warning (setNames)", "Error - Reading Pandora.ini failed\n" + str(e))
				return

		else:
			QMessageBox.warning(self,"Warning (setNames)", "Could not find Pandora.ini")
			return


	@err_decorator
	def validate(self, text = None, editfield = None):
		if text != None:
			startpos = editfield.cursorPosition()

			validText = self.core.validateStr(text)

			if not text == validText:
				startpos = self.newCursorPos
				
			editfield.setText(validText)
			editfield.setCursorPosition(startpos)

			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(len(self.e_name.text()) > 0)


	@err_decorator
	def cursorMoved(self, old, new):
		self.newCursorPos = new


	@err_decorator
	def setUser(self):
		if os.path.exists(self.core.configPath):

			try:
				self.core.setConfig("globals", "username", (self.e_name.text()))
			except Exception as e:
				QMessageBox.warning(self,"Warning (setUser)", "Error - Setting user failed\n" + str(e))
				return

		else:
			QMessageBox.warning(self,"Warning (setUser)", "Could not find Pandora.ini")
			return