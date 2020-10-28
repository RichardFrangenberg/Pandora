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


import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as api
import maya.OpenMayaUI as OpenMayaUI

try:
    import mtoa.aovs as maovs
except:
    pass

import os, sys
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


class Pandora_Maya_Functions(object):
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
                erStr = "%s ERROR - Pandora_Plugin_Maya %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].plugin.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self, origin):
        if os.path.basename(sys.executable) != "mayapy.exe":
            if QApplication.instance() is None:
                return False

            if not hasattr(QApplication, "topLevelWidgets"):
                return False

            for obj in QApplication.topLevelWidgets():
                if obj.objectName() == "MayaWindow":
                    mayaQtParent = obj
                    break
            else:
                return False

            try:
                topLevelShelf = mel.eval("string $m = $gShelfTopLevel")
            except:
                return False

            if cmds.shelfTabLayout(topLevelShelf, query=True, tabLabelIndex=True) == None:
                return False

            origin.timer.stop()
            origin.messageParent = mayaQtParent

        else:
            origin.timer.stop()
            origin.messageParent = QWidget()

    @err_decorator
    def getCurrentFileName(self, origin, path=True):
        if path:
            return cmds.file(q=True, sceneName=True)
        else:
            return cmds.file(q=True, sceneName=True, shortName=True)

    @err_decorator
    def saveScene(self, origin, filepath):
        cmds.file(rename=filepath)
        try:
            return cmds.file(save=True)
        except:
            return False

    @err_decorator
    def getFrameRange(self, origin):
        startframe = cmds.playbackOptions(q=True, minTime=True)
        endframe = cmds.playbackOptions(q=True, maxTime=True)

        return [startframe, endframe]

    @err_decorator
    def setRCStyle(self, origin, rcmenu):
        pass

    @err_decorator
    def onPandoraSettingsOpen(self, origin):
        pass

    @err_decorator
    def getCurrentSceneFiles(self, origin):
        curFileName = self.core.getCurrentFileName()
        curFileBase = os.path.splitext(os.path.basename(curFileName))[0]
        xgenfiles = [
            os.path.join(os.path.dirname(curFileName), x)
            for x in os.listdir(os.path.dirname(curFileName))
            if x.startswith(curFileBase) and os.path.splitext(x)[1] in [".xgen", "abc"]
        ]
        scenefiles = [curFileName] + xgenfiles
        return scenefiles

    @err_decorator
    def onSubmitterOpen(self, origin):
        origin.w_status.setVisible(False)
        origin.w_connect.setVisible(False)

    @err_decorator
    def getSceneCameras(self, origin):
        return ["Current View"] + cmds.listRelatives(
            cmds.ls(cameras=True, long=True), parent=True, fullPath=True
        )

    @err_decorator
    def getCameraName(self, origin, handle):
        if handle == "Current View":
            return handle

        nodes = cmds.ls(handle)
        if len(nodes) == 0:
            return "invalid"
        else:
            return str(nodes[0])

    @err_decorator
    def getExternalFiles(self, origin, isSubmitting=False):
        prjPath = cmds.workspace(fullName=True, query=True)
        if prjPath.endswith(":"):
            prjPath += "/"

        prjPath = os.path.join(prjPath, "untitled")
        extFiles = [
            self.core.fixPath(str(x))
            for x in cmds.file(query=True, list=True)
            if self.core.fixPath(str(x)) != self.core.fixPath(prjPath)
            and self.core.fixPath(str(x)) != self.core.getCurrentFileName()
        ]
        return extFiles

    @err_decorator
    def preSubmit(self, origin, rSettings):
        if origin.chb_resOverride.isChecked():
            rSettings["width"] = cmds.getAttr("defaultResolution.width")
            rSettings["height"] = cmds.getAttr("defaultResolution.height")
            cmds.setAttr("defaultResolution.width", origin.sp_resWidth.value())
            cmds.setAttr("defaultResolution.height", origin.sp_resHeight.value())

        rSettings["imageFolder"] = cmds.workspace(fileRuleEntry="images")
        rSettings["imageFilePrefix"] = cmds.getAttr("defaultRenderGlobals.imageFilePrefix")
        rSettings["outFormatControl"] = cmds.getAttr(
            "defaultRenderGlobals.outFormatControl"
        )
        rSettings["animation"] = cmds.getAttr("defaultRenderGlobals.animation")
        rSettings["putFrameBeforeExt"] = cmds.getAttr(
            "defaultRenderGlobals.putFrameBeforeExt"
        )
        rSettings["extpadding"] = cmds.getAttr("defaultRenderGlobals.extensionPadding")

        outputPrefix = (
            "../" + os.path.splitext(os.path.basename(rSettings["outputName"]))[0]
        )

        cmds.workspace(fileRule=["images", os.path.dirname(rSettings["outputName"])])
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string")
        cmds.setAttr("defaultRenderGlobals.outFormatControl", 0)
        cmds.setAttr("defaultRenderGlobals.animation", 1)
        cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", 1)
        cmds.setAttr("defaultRenderGlobals.extensionPadding", 4)

        curRenderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        if curRenderer == "arnold":
            driver = cmds.ls("defaultArnoldDriver")
            if not driver:
                mel.eval("RenderGlobalsWindow;")
            rSettings["ar_fileformat"] = cmds.getAttr("defaultArnoldDriver.ai_translator")
            rSettings["ar_exrPixelType"] = cmds.getAttr("defaultArnoldDriver.halfPrecision")
            rSettings["ar_exrCompression"] = cmds.getAttr(
                "defaultArnoldDriver.exrCompression"
            )

            cmds.setAttr("defaultArnoldDriver.ai_translator", "exr", type="string")
            # 	cmds.setAttr("defaultArnoldDriver.halfPrecision", 1) # 16 bit
            # 	cmds.setAttr("defaultArnoldDriver.exrCompression", 3) # ZIP compression

            aAovs = maovs.AOVInterface().getAOVNodes(names=True)
            aAovs = [x for x in aAovs if cmds.getAttr(x[1] + ".enabled")]
            if cmds.getAttr("defaultArnoldRenderOptions.aovMode") != 0 and len(aAovs) > 0:
                outputPrefix = "../" + outputPrefix

                cmds.setAttr(
                    "defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string"
                )

                # rSettings["outputName"] = os.path.join(os.path.dirname(os.path.dirname(rSettings["outputName"])), os.path.basename(rSettings["outputName"]))
                passPrefix = ".."

                drivers = ["defaultArnoldDriver"]
                for i in aAovs:
                    aDriver = cmds.connectionInfo(
                        "%s.outputs[0].driver" % i[1], sourceFromDestination=True
                    ).rsplit(".", 1)[0]
                    if aDriver in drivers:
                        continue
                    # if aDriver in drivers or aDriver == "":
                    # 	aDriver = cmds.createNode( 'aiAOVDriver', n='%s_driver' % i[0] )
                    # 	cmds.connectAttr("%s.aiTranslator" % aDriver, "%s.outputs[0].driver" % i[1], force=True)

                    passPath = os.path.join(
                        passPrefix, i[0], os.path.basename(outputPrefix)
                    ).replace("beauty", i[0])
                    drivers.append(aDriver)
                    cmds.setAttr(aDriver + ".prefix", passPath, type="string")
        elif curRenderer == "vray":
            driver = cmds.ls("vraySettings")
            if not driver:
                mel.eval("RenderGlobalsWindow;")

            rSettings["vr_imageFilePrefix"] = (
                cmds.getAttr("vraySettings.fileNamePrefix") or ""
            )
            # rSettings["vr_fileformat"] = cmds.getAttr("vraySettings.imageFormatStr")
            # rSettings["vr_sepRGBA"] = cmds.getAttr("vraySettings.relements_separateRGBA")
            rSettings["vr_animation"] = cmds.getAttr("vraySettings.animType")

            #cmds.setAttr("vraySettings.imageFormatStr", "exr", type="string")
            cmds.setAttr("vraySettings.animType", 1)

            # aovs = cmds.ls(type="VRayRenderElement")
            # aovs = [x for x in aovs if cmds.getAttr(x + ".enabled")]
            # if cmds.getAttr("vraySettings.relements_enableall") != 0 and len(aovs) > 0:
            #     try:
            #         shutil.rmtree(os.path.dirname(rSettings["outputName"]))
            #     except:
            #         pass

            #     rSettings["vr_sepFolders"] = cmds.getAttr(
            #         "vraySettings.relements_separateFolders"
            #     )
            #     rSettings["vr_sepStr"] = cmds.getAttr(
            #         "vraySettings.fileNameRenderElementSeparator"
            #     )

            #     cmds.setAttr("vraySettings.fileNamePrefix", outputPrefix, type="string")
            #     cmds.setAttr("vraySettings.relements_separateFolders", 1)
            #     cmds.setAttr("vraySettings.relements_separateRGBA", 1)
            #     cmds.setAttr(
            #         "vraySettings.fileNameRenderElementSeparator", "_", type="string"
            #     )
            # else:
            #     cmds.setAttr("vraySettings.relements_separateRGBA", 0)
            #     outputPrefix = outputPrefix[3:]
            #     cmds.setAttr("vraySettings.fileNamePrefix", outputPrefix, type="string")
        elif curRenderer == "redshift":
            driver = cmds.ls("redshiftOptions")
            if not driver:
                mel.eval("RenderGlobalsWindow;")

            rSettings["rs_fileformat"] = cmds.getAttr("redshiftOptions.imageFormat")

            cmds.setAttr("redshiftOptions.imageFormat", 1)

            outputPrefix = outputPrefix[3:]
            cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string"
            )

            aovs = cmds.ls(type="RedshiftAOV")
            aovs = [
                [cmds.getAttr(x + ".name"), x] for x in aovs if cmds.getAttr(x + ".enabled")
            ]

            if cmds.getAttr("redshiftOptions.aovGlobalEnableMode") != 0 and len(aovs) > 0:
                for i in aovs:
                    cmds.setAttr(
                        i[1] + ".filePrefix",
                        "<BeautyPath>/../<RenderPass>/%s"
                        % os.path.basename(outputPrefix).replace("beauty", i[0]),
                        type="string",
                    )
        else:
            rSettings["fileformat"] = cmds.getAttr("defaultRenderGlobals.imageFormat")
            rSettings["exrPixelType"] = cmds.getAttr("defaultRenderGlobals.exrPixelType")
            rSettings["exrCompression"] = cmds.getAttr(
                "defaultRenderGlobals.exrCompression"
            )

            if curRenderer in ["mayaSoftware", "mayaHardware", "mayaVector"]:
                rndFormat = 4  # .tif
            else:
                rndFormat = 40  # .exr
            cmds.setAttr("defaultRenderGlobals.imageFormat", rndFormat)
            cmds.setAttr("defaultRenderGlobals.exrPixelType", 1)  # 16 bit
            cmds.setAttr("defaultRenderGlobals.exrCompression", 3)  # ZIP compression

    @err_decorator
    def undoRenderSettings(self, origin, rSettings):
        if "width" in rSettings:
            cmds.setAttr("defaultResolution.width", rSettings["width"])
        if "height" in rSettings:
            cmds.setAttr("defaultResolution.height", rSettings["height"])
        if "imageFolder" in rSettings:
            cmds.workspace(fileRule=["images", rSettings["imageFolder"]])
        if "imageFilePrefix" in rSettings:
            if rSettings["imageFilePrefix"] is None:
                prefix = ""
            else:
                prefix = rSettings["imageFilePrefix"]
            cmds.setAttr("defaultRenderGlobals.imageFilePrefix", prefix, type="string")
        if "outFormatControl" in rSettings:
            cmds.setAttr(
                "defaultRenderGlobals.outFormatControl", rSettings["outFormatControl"]
            )
        if "animation" in rSettings:
            cmds.setAttr("defaultRenderGlobals.animation", rSettings["animation"])
        if "putFrameBeforeExt" in rSettings:
            cmds.setAttr(
                "defaultRenderGlobals.putFrameBeforeExt", rSettings["putFrameBeforeExt"]
            )
        if "extpadding" in rSettings:
            cmds.setAttr("defaultRenderGlobals.extensionPadding", rSettings["extpadding"])
        if "fileformat" in rSettings:
            cmds.setAttr("defaultRenderGlobals.imageFormat", rSettings["fileformat"])
        if "exrPixelType" in rSettings:
            cmds.setAttr("defaultRenderGlobals.exrPixelType", rSettings["exrPixelType"])
        if "exrCompression" in rSettings:
            cmds.setAttr("defaultRenderGlobals.exrCompression", rSettings["exrCompression"])
        if "ar_fileformat" in rSettings:
            cmds.setAttr(
                "defaultArnoldDriver.ai_translator",
                rSettings["ar_fileformat"],
                type="string",
            )
        if "ar_exrPixelType" in rSettings:
            cmds.setAttr("defaultArnoldDriver.halfPrecision", rSettings["ar_exrPixelType"])
        if "ar_exrCompression" in rSettings:
            cmds.setAttr(
                "defaultArnoldDriver.exrCompression", rSettings["ar_exrCompression"]
            )
        if "vr_fileformat" in rSettings:
            cmds.setAttr(
                "vraySettings.imageFormatStr", rSettings["vr_fileformat"], type="string"
            )
        if "startFrame" in rSettings:
            cmds.setAttr("defaultRenderGlobals.startFrame", rSettings["startFrame"])
        if "endFrame" in rSettings:
            cmds.setAttr("defaultRenderGlobals.endFrame", rSettings["endFrame"])
        if "vr_imageFilePrefix" in rSettings:
            cmds.setAttr(
                "vraySettings.fileNamePrefix",
                rSettings["vr_imageFilePrefix"],
                type="string",
            )
        if "vr_sepFolders" in rSettings:
            cmds.setAttr(
                "vraySettings.relements_separateFolders", rSettings["vr_sepFolders"]
            )
        if "vr_sepRGBA" in rSettings:
            cmds.setAttr("vraySettings.relements_separateRGBA", rSettings["vr_sepRGBA"])
        if "vr_sepStr" in rSettings:
            cmds.setAttr(
                "vraySettings.fileNameRenderElementSeparator",
                rSettings["vr_sepStr"],
                type="string",
            )
        if "rs_fileformat" in rSettings:
            cmds.setAttr("redshiftOptions.imageFormat", rSettings["rs_fileformat"])

    @err_decorator
    def preSubmitChecks(self, origin, jobData):
        pass

    @err_decorator
    def getJobConfigParams(self, origin, cData):
        for i in cData:
            if i[1] == "programVersion":
                break
        else:
            cData.append(["information", "programVersion", cmds.about(version=True)])
