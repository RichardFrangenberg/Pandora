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


import os
import sys
import traceback
import time
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

try:
    import MaxPlus
except:
    pass


class Pandora_3dsMax_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if "MaxPlus" not in globals() and sys.version[0] == "3":
            self.enabled = False
            self.core.popup("Pandora works in 3ds Max with Python 2.7 only.\nSet the environment variable ADSK_3DSMAX_PYTHON_VERSION to \"2\" to use Pandora in this version of 3ds Max")

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Pandora_Plugin_3dsMax %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].plugin.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self, origin):
        origin.timer.stop()
        if psVersion == 1:
            origin.messageParent = MaxPlus.GetQMaxWindow()
        else:
            origin.messageParent = MaxPlus.GetQMaxMainWindow()

    @err_decorator
    def executeScript(self, origin, code, returnVal=True):
        try:
            val = MaxPlus.Core.EvalMAXScript(code)
        except Exception as e:
            msg = "\nmaxscript code:\n%s" % code
            exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")

        if returnVal:
            try:
                return val.Get()
            except:
                return None

    @err_decorator
    def getCurrentFileName(self, origin, path=True):
        if path:
            return MaxPlus.FileManager.GetFileNameAndPath()
        else:
            return MaxPlus.FileManager.GetFileName()

    @err_decorator
    def saveScene(self, origin, filepath):
        return self.executeScript(origin, 'saveMaxFile "%s"' % filepath)

    @err_decorator
    def getFrameRange(self, origin):
        startframe = self.executeScript(origin, "animationrange.start.frame")
        endframe = self.executeScript(origin, "animationrange.end.frame")

        return [startframe, endframe]

    @err_decorator
    def setRCStyle(self, origin, rcmenu):
        pass

    @err_decorator
    def onPrismSettingsOpen(self, origin):
        pass

    @err_decorator
    def getCurrentSceneFiles(self, origin):
        return [self.core.getCurrentFileName()]

    @err_decorator
    def onSubmitterOpen(self, origin):
        origin.w_status.setVisible(False)
        origin.w_connect.setVisible(False)

    @err_decorator
    def getSceneCameras(self, origin):
        cams = self.executeScript(
            origin, "for i in cameras where (superclassof i) == camera collect i"
        )
        return ["Current View"] + [
            cams.GetItem(x).GetHandle() for x in range(cams.GetCount())
        ]

    @err_decorator
    def getCameraName(self, origin, handle):
        if handle == "Current View":
            return handle

        return MaxPlus.INode.GetINodeByHandle(handle).GetName()

    @err_decorator
    def getExternalFiles(self, origin, isSubmitting=False):
        extFiles = self.executeScript(
            origin,
            "mapfiles=#()\n\
fn addmap mapfile =\n\
(\n\
if (finditem mapfiles mapfile) == 0 do append mapfiles mapfile\n\
)\n\
enumeratefiles addmap\n\
for mapfile in mapfiles collect mapfile",
        )

        if extFiles is None:
            extFiles = []

        return extFiles

    @err_decorator
    def preSubmit(self, origin, rSettings):
        MaxPlus.RenderSettings.CloseDialog()

        elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
        rSettings["elementsActive"] = MaxPlus.RenderElementMgr.GetElementsActive(elementMgr)
        activePasses = MaxPlus.RenderElementMgr.GetElementsActive(elementMgr)

        separateAOVs = True
        if self.executeScript(
            origin, 'matchpattern (classof renderers.current as string) pattern: "V_Ray*"'
        ):
            separateAOVs = not self.executeScript(origin, "renderers.current.output_on")

        if self.executeScript(
            origin,
            'matchpattern (classof renderers.current as string) pattern: "Redshift*"',
        ):
            separateAOVs = self.executeScript(origin, "renderers.current.SeparateAovFiles")

        if activePasses and elementMgr.NumRenderElements() > 0 and separateAOVs:
            bName = os.path.splitext(os.path.basename(rSettings["outputName"]))
            bName = "%sbeauty.%s" % (bName[0], bName[1])
            rSettings["outputName"] = os.path.join(
                os.path.dirname(rSettings["outputName"]), "beauty", bName
            )

            for i in range(elementMgr.NumRenderElements()):
                element = elementMgr.GetRenderElement(i)
                passName = element.GetElementName()
                passOutputName = os.path.join(
                    os.path.dirname(os.path.dirname(rSettings["outputName"])),
                    passName,
                    os.path.basename(rSettings["outputName"]).replace("beauty", passName),
                )
                try:
                    os.makedirs(os.path.dirname(passOutputName))
                except:
                    pass
                self.executeScript(
                    origin,
                    '(maxOps.GetCurRenderElementMgr()).SetRenderElementFilename %s "%s"'
                    % (i, passOutputName.replace("\\", "\\\\")),
                    returnVal=False,
                )

        rSettings["savefile"] = MaxPlus.RenderSettings.GetSaveFile()
        rSettings["savefilepath"] = MaxPlus.RenderSettings.GetOutputFile()
        MaxPlus.RenderSettings.SetSaveFile(True)
        MaxPlus.RenderSettings.SetOutputFile(rSettings["outputName"])

    @err_decorator
    def undoRenderSettings(self, origin, rSettings):
        if "elementsActive" in rSettings:
            elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
            MaxPlus.RenderElementMgr.SetElementsActive(
                elementMgr, rSettings["elementsActive"]
            )
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
    def preSubmitChecks(self, origin, jobData):
        pass

    @err_decorator
    def getJobConfigParams(self, origin, cData):
        pass
