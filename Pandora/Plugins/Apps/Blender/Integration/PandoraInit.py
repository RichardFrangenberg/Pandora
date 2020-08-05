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
# Copyright (C) 2016-2020 Richard Frangenberg
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


import sys, os, bpy

pandoraRoot = PANDORAROOT


if sys.version_info[0] != 3 and sys.version_info[1] != 7:
    print("Pandora supports Python37 only in Blender")

sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", "CrossPlatform"))
sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", "Python37"))
sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", "Python37", "PySide"))
sys.path.insert(0, os.path.join(pandoraRoot, "Scripts"))

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from bpy.app.handlers import persistent


def pandoraInit():
    import PandoraCore

    Pandora = PandoraCore.PandoraCore(app="Blender")
    return Pandora


class PandoraSubmitter(bpy.types.Operator):
    bl_idname = "object.pandora_submitter"
    bl_label = "Submitter"

    def execute(self, context):
        Pandora.openSubmitter()
        return {"FINISHED"}


class PandoraRenderHandler(bpy.types.Operator):
    bl_idname = "object.pandora_renderhandler"
    bl_label = "Render-Handler"

    def execute(self, context):
        Pandora.openRenderHandler()
        return {"FINISHED"}


class PandoraSettings(bpy.types.Operator):
    bl_idname = "object.pandora_settings"
    bl_label = "Settings"

    def execute(self, context):
        Pandora.openSettings()
        return {"FINISHED"}


if bpy.app.version < (2, 80, 0):
    Region = "TOOLS"
else:
    Region = "UI"


class PandoraPanel(bpy.types.Panel):
    bl_label = "Pandora Tools"
    bl_idname = "pandoraToolsPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = Region
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

        if bpy.app.version < (2, 80, 0):
            qssFile = os.path.join(
                pandoraRoot,
                "Plugins",
                "Apps",
                "Blender",
                "UserInterfaces",
                "BlenderStyleSheet",
                "Blender2.79.qss",
            )
        else:
            qssFile = os.path.join(
                pandoraRoot,
                "Plugins",
                "Apps",
                "Blender",
                "UserInterfaces",
                "BlenderStyleSheet",
                "Blender2.8.qss",
            )

        with (open(qssFile, "r")) as ssFile:
            ssheet = ssFile.read()

        ssheet = ssheet.replace("qss:", os.path.dirname(qssFile).replace("\\", "/") + "/")
        qapp.setStyleSheet(ssheet)
        appIcon = QIcon(
            os.path.join(
                pandoraRoot, "Scripts", "UserInterfacesPandora", "pandora_tray.png"
            )
        )
        qapp.setWindowIcon(appIcon)

        global Pandora
        Pandora = pandoraInit()
        bpy.utils.register_class(PandoraSubmitter)
        bpy.utils.register_class(PandoraRenderHandler)
        bpy.utils.register_class(PandoraSettings)
        bpy.utils.register_class(PandoraPanel)
        # 	qapp.exec_()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(
            "ERROR - PandoraInit - %s - %s - %s\n\n" % (str(e), exc_type, exc_tb.tb_lineno)
        )


def unregister():
    if bpy.app.background:
        return

    bpy.utils.unregister_class(PandoraSubmitter)
    bpy.utils.unregister_class(PandoraRenderHandler)
    bpy.utils.unregister_class(PandoraSettings)
    bpy.utils.unregister_class(PandoraPanel)
