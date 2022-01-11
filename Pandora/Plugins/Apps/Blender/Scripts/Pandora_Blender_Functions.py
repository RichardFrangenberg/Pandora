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


import bpy
import os, sys, threading, platform
import traceback, time, shutil
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


class Pandora_Blender_Functions(object):
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
                erStr = "%s ERROR - Pandora_Plugin_Blender %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].plugin.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self, origin):
        try:
            bpy.data.filepath
        except:
            return False

        origin.timer.stop()

    @err_decorator
    def getCurrentFileName(self, origin, path=True):
        currentFileName = bpy.data.filepath

        if not path:
            currentFileName = os.path.basename(currentFileName)

        return currentFileName

    @err_decorator
    def getOverrideContext(self, origin=None, context=None):
        ctx = {}

        for window in bpy.context.window_manager.windows:
            ctx["window"] = window
            screen = window.screen
            ctx["screen"] = screen

            if context:
                for area in screen.areas:
                    if area.type == context:
                        ctx["area"] = area
                        for region in area.regions:
                            if region.type == "WINDOW":
                                ctx["region"] = region
                                return ctx

            for area in screen.areas:
                if area.type == "VIEW_3D":
                    ctx["area"] = area
                    return ctx

            for area in screen.areas:
                if area.type == "IMAGE_EDITOR":
                    ctx["area"] = area
                    return ctx

        return ctx

    @err_decorator
    def saveScene(self, origin, filepath):
        return bpy.ops.wm.save_as_mainfile(self.getOverrideContext(origin), filepath=filepath)

    @err_decorator
    def getFrameRange(self, origin):
        startframe = bpy.context.scene.frame_start
        endframe = bpy.context.scene.frame_end

        return [startframe, endframe]

    @err_decorator
    def setRCStyle(self, origin, rcmenu):
        pass

    @err_decorator
    def onPandoraSettingsOpen(self, origin):
        origin.resize(origin.width(), origin.height() + 60)

    @err_decorator
    def onSubmitterOpen(self, origin):
        origin.resize(origin.width(), origin.height() + 60)
        origin.w_status.setVisible(False)
        origin.w_connect.setVisible(False)

    @err_decorator
    def getSceneCameras(self, origin):
        return [x.name for x in bpy.context.scene.objects if x.type == "CAMERA"]

    @err_decorator
    def getCameraName(self, origin, handle):
        return handle

    @err_decorator
    def getExternalFiles(self, origin, isSubmitting=False):
        if isSubmitting:
            try:
                bpy.ops.file.pack_all()
            except Exception as e:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Pandora",
                    "Could not pack external files into current scenefile:\n\n%s" % str(e),
                )

        return []

    @err_decorator
    def preSubmit(self, origin, rSettings):
        if origin.chb_resOverride.isChecked():
            rSettings["width"] = bpy.context.scene.render.resolution_x
            rSettings["height"] = bpy.context.scene.render.resolution_y
            bpy.context.scene.render.resolution_x = origin.sp_resWidth.value()
            bpy.context.scene.render.resolution_y = origin.sp_resHeight.value()

        jobFrames = [origin.sp_rangeStart.value(), origin.sp_rangeEnd.value()]

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
        if origin.cb_cam.currentText() in bpy.context.scene.objects:
            bpy.context.scene.camera = bpy.context.scene.objects[
                origin.cb_cam.currentText()
            ]

        usePasses = False
        if bpy.context.scene.node_tree is not None and bpy.context.scene.use_nodes:
            outNodes = [
                x for x in bpy.context.scene.node_tree.nodes if x.type == "OUTPUT_FILE"
            ]
            rlayerNodes = [
                x for x in bpy.context.scene.node_tree.nodes if x.type == "R_LAYERS"
            ]

            bName = os.path.splitext(os.path.basename(rSettings["outputName"]))
            if bName[0].endswith(self.plugin.frameString):
                bName = "%s.beauty%s%s" % (bName[0][:-5], bName[0][-5:], bName[1])
            else:
                bName = "%s.beauty%s" % (bName[0], bName[1])
            rSettings["outputName"] = os.path.join(
                os.path.dirname(rSettings["outputName"]), "beauty", bName
            )

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

                    extensions = {
                        "PNG": ".png",
                        "JPEG": ".jpg",
                        "JPEG2000": "jpg",
                        "TARGA": ".tga",
                        "TARGA_RAW": ".tga",
                        "OPEN_EXR_MULTILAYER": ".exr",
                        "OPEN_EXR": ".exr",
                        "TIFF": ".tif",
                    }
                    nodeExt = extensions[m.format.file_format]
                    curSlot = m.file_slots[idx]
                    if curSlot.use_node_format:
                        ext = nodeExt
                    else:
                        ext = extensions[curSlot.format.file_format]

                    curSlot.path = "../%s/%s" % (
                        passName,
                        os.path.splitext(os.path.basename(rSettings["outputName"]))[
                            0
                        ].replace("beauty", passName)
                        + ext,
                    )
                    newOutputPath = os.path.abspath(
                        os.path.join(
                            rSettings["outputName"],
                            "../..",
                            passName,
                            os.path.splitext(os.path.basename(rSettings["outputName"]))[
                                0
                            ].replace("beauty", passName)
                            + ext,
                        )
                    )
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
    def undoRenderSettings(self, origin, rSettings):
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

    @err_decorator
    def preSubmitChecks(self, origin, jobData):
        pass

    @err_decorator
    def copyScene(self, origin, jobPath, submitDependendFiles):
        if not submitDependendFiles:
            return False

        jobFilePath = os.path.join(jobPath, self.getCurrentFileName(origin, path=False))
        bpy.ops.wm.save_as_mainfile(filepath=jobFilePath, copy=True, relative_remap=False)
        bpy.ops.wm.revert_mainfile()
        return True

    @err_decorator
    def getJobConfigParams(self, origin, cData):
        pass
