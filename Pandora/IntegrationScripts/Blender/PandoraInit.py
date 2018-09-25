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



import sys, os, bpy
sys.path.append(os.path.join(os.getenv('LocalAppdata'), "Pandora", "PythonLibs", "Python35"))
sys.path.append(os.path.join(os.getenv('LocalAppdata'), "Pandora", "Scripts"))
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from bpy.app.handlers import persistent

def pandoraInit():
	import PandoraCore
	pandoraCore = PandoraCore.PandoraCore()
	return pandoraCore


class PandoraSubmitter(bpy.types.Operator):
	bl_idname = "object.pandora_submitter"
	bl_label = "Submitter"

	def execute(self, context):
		pandoraCore.openSubmitter()
		return {'FINISHED'}


class PandoraRenderHandler(bpy.types.Operator):
	bl_idname = "object.pandora_renderhandler"
	bl_label = "Render-Handler"

	def execute(self, context):
		pandoraCore.openRenderHandler()
		return {'FINISHED'}


class PandoraSettings(bpy.types.Operator):
	bl_idname = "object.pandora_settings"
	bl_label = "Settings"

	def execute(self, context):
		pandoraCore.openSettings()
		return {'FINISHED'}


class PandoraPanel(bpy.types.Panel):
	bl_label = "Pandora Tools"
	bl_idname = "pandoraToolsPanel"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_context = "objectmode"
	bl_category = "Pandora"

	def draw(self, context):
		layout = self.layout

		row = layout.row()
		row.operator("object.pandora_submitter")

		row = layout.row()
		row.operator("object.pandora_renderhandler")

		row = layout.row()
		row.operator("object.pandora_settings")


def register():
	if bpy.app.background:
		return

	try:
		qapp = QApplication.instance()
		if qapp == None:
			qapp = QApplication(sys.argv)
			
		with (open(os.path.join(os.getenv('LocalAppdata'), "Pandora", "Scripts", "UserInterfacesPandora", "BlenderStyleSheet", "Blender.qss"), "r")) as ssFile:
			ssheet = ssFile.read()

		ssheet = ssheet.replace("qss:", os.path.join(os.getenv('LocalAppdata'), "Pandora", "Scripts", "UserInterfacesPandora", "BlenderStyleSheet").replace("\\", "/") + "/")
		qapp.setStyleSheet(ssheet)
		appIcon = QIcon(os.path.join(os.getenv('LocalAppdata'), "Pandora", "Scripts", "UserInterfacesPandora", "pandora_tray.png"))
		qapp.setWindowIcon(appIcon)

		global pandoraCore
		pandoraCore = pandoraInit()
		bpy.utils.register_class(PandoraSubmitter)
		bpy.utils.register_class(PandoraRenderHandler)
		bpy.utils.register_class(PandoraSettings)
		bpy.utils.register_class(PandoraPanel)
		#	qapp.exec_()

	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		print ("ERROR - PandoraInit - %s - %s - %s\n\n" % (str(e), exc_type, exc_tb.tb_lineno))


def unregister():
	if bpy.app.background:
		return
	
	bpy.utils.unregister_class(PandoraSubmitter)
	bpy.utils.unregister_class(PandoraRenderHandler)
	bpy.utils.unregister_class(PandoraSettings)
	bpy.utils.unregister_class(PandoraPanel)