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


import os, sys
import traceback, time, platform
from functools import wraps

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1


if sys.version[0] == "3":
    import winreg as _winreg

    pVersion = 3
else:
    import _winreg

    pVersion = 2


class Pandora_Blender_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Pandora_Plugin_Blender_ext %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].plugin.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def pandoraSettings_loadUI(self, origin, tab):
        pass

    @err_decorator
    def pandoraSettings_saveSettings(self, origin):
        saveData = []

        return saveData

    @err_decorator
    def pandoraSettings_loadSettings(self, origin):
        loadData = {}
        loadFunctions = {}

        return loadData, loadFunctions

    # start a Blender job
    @err_decorator
    def startJob(self, origin, jobData={}):
        origin.writeLog("starting blender job. " + jobData["jobname"], 0)

        bldOverride = self.core.getConfig("dccoverrides", "Blender_override")
        bldOverridePath = self.core.getConfig("dccoverrides", "Blender_path")

        if (
            bldOverride == True
            and bldOverridePath is not None
            and os.path.exists(bldOverridePath)
        ):
            blenderPath = bldOverridePath
        else:
            blenderPath = self.getInstallPath()

            if not os.path.exists(blenderPath):
                origin.writeLog("no Blender installation found", 3)
                origin.renderingFailed(jobData)
                return "skipped"

        if "outputPath" in jobData:
            curOutput = jobData["outputPath"]
            if origin.localMode:
                newOutput = curOutput
            else:
                newOutput = os.path.join(
                    origin.localSlavePath,
                    "RenderOutput",
                    jobData["jobcode"],
                    os.path.basename(os.path.dirname(curOutput)),
                    os.path.basename(curOutput),
                )
            try:
                os.makedirs(os.path.dirname(newOutput))
            except:
                pass
        else:
            origin.writeLog("no outputpath specified", 2)
            origin.renderingFailed(jobData)
            return False

        if not os.path.exists(jobData["scenefile"]):
            origin.writeLog("scenefile does not exist", 2)
            origin.renderingFailed(jobData)
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

""" % (
            os.path.dirname(jobData["scenefile"]),
            newOutput,
            newOutput,
        )

        preScriptPath = os.path.join(
            os.path.dirname(os.path.dirname(jobData["scenefile"])), "preRenderScript.py"
        )

        open(preScriptPath, "a").close()
        with open(preScriptPath, "w") as scriptfile:
            scriptfile.write(preRendScript.replace("\\", "\\\\"))

        popenArgs = [
            blenderPath,
            "--background",
            jobData["scenefile"],
            "--render-output",
            newOutput,
            "--frame-start",
            str(jobData["taskStartframe"]),
            "--frame-end",
            str(jobData["taskEndframe"]),
            "--python",
            preScriptPath,
        ]

        if "width" in jobData:
            popenArgs += [
                "--python-expr",
                "import bpy; bpy.context.scene.render.resolution_x=%s" % jobData["width"],
            ]

        if "height" in jobData:
            popenArgs += [
                "--python-expr",
                "import bpy; bpy.context.scene.render.resolution_y=%s" % jobData["height"],
            ]

        popenArgs.append("-a")

        thread = origin.startRenderThread(
            pOpenArgs=popenArgs, jData=jobData, prog="blender"
        )
        return thread
