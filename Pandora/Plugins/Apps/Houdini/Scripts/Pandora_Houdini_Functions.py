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


import hou
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


class Pandora_Houdini_Functions(object):
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
                erStr = "%s ERROR - Pandora_Plugin_Houdini %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].plugin.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self, origin):
        if not hou.isUIAvailable():
            return False

        if hou.ui.mainQtWindow() is None:
            return False

        origin.timer.stop()
        origin.messageParent = hou.ui.mainQtWindow()

    @err_decorator
    def getCurrentFileName(self, origin, path=True):
        return hou.hipFile.path()

    @err_decorator
    def saveScene(self, origin, filepath):
        return hou.hipFile.save(file_name=filepath, save_to_recent_files=True)

    @err_decorator
    def getFrameRange(self, origin):
        startframe = hou.playbar.playbackRange()[0]
        endframe = hou.playbar.playbackRange()[1]

        return [startframe, endframe]

    @err_decorator
    def setRCStyle(self, origin, rcmenu):
        rcmenu.setStyleSheet(hou.qt.styleSheet())

    @err_decorator
    def onPrismSettingsOpen(self, origin):
        origin.w_startTray.setVisible(False)
        origin.scrollArea.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QScrollArea")
        )

    @err_decorator
    def onPrismRenderHandlerOpen(self, origin):
        origin.tw_taskList.verticalHeader().setFixedWidth(20)
        origin.tw_taskList.verticalHeader().setDefaultSectionSize(20)

        origin.tw_slaves.verticalHeader().setFixedWidth(20)
        origin.tw_slaves.verticalHeader().setDefaultSectionSize(20)

        origin.splitter_3.setStyleSheet(hou.qt.styleSheet().replace("QLabel", "QSplitter"))
        origin.tw_jobs.setStyleSheet(hou.qt.styleSheet().replace("QLabel", "QHeaderView"))
        origin.tw_slaves.setStyleSheet(hou.qt.styleSheet().replace("QLabel", "QHeaderView"))
        origin.tw_slaveWarnings.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QHeaderView")
        )
        origin.tw_coordWarnings.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QHeaderView")
        )

    @err_decorator
    def onSubmitterOpen(self, origin):
        origin.scrollArea.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QScrollArea")
        )

        self.node = None
        origin.l_status.setText("Not connected")
        origin.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

        origin.b_goTo.clicked.connect(lambda: self.goToNode(origin))
        origin.b_connect.clicked.connect(lambda: self.connectNode(origin))

    @err_decorator
    def goToNode(self, origin):
        try:
            self.node.name()
        except:
            return False

        self.node.setCurrent(True, clear_all_selected=True)
        hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).frameSelection()

    @err_decorator
    def connectNode(self, origin):
        if len(hou.selectedNodes()) > 0 and (
            hou.selectedNodes()[0].type().name() in ["ifd", "Redshift_ROP"]
        ):
            self.node = hou.selectedNodes()[0]

            self.node.name()
            origin.l_status.setText(self.node.name())
            origin.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")

    @err_decorator
    def getSceneCameras(self, origin):
        cams = []
        for node in hou.node("/").allSubChildren():

            if (
                node.type().name() == "cam" and node.name() != "ipr_camera"
            ) or node.type().name() == "vrcam":
                cams.append(node)

        return cams

    @err_decorator
    def getCameraName(self, origin, handle):
        return handle.name()

    @err_decorator
    def getExternalFiles(self, origin, isSubmitting=False):
        hou.setFrame(hou.playbar.playbackRange()[0])
        whitelist = [
            "$HIP/$OS-bounce.rat",
            "$HIP/$OS-fill.rat",
            "$HIP/$OS-key.rat",
            "$HIP/$OS-rim.rat",
        ]
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

            if x[0] is not None and x[0].name() in [
                "RS_outputFileNamePrefix",
                "vm_picture",
            ]:
                continue

            if x[0] is not None and x[0].name() in [
                "RS_outputFileNamePrefix",
                "vm_picture",
            ]:
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "dopoutput", "copoutput", "sopoutput"]
                and x[0].node().type().name()
                in ["rop_alembic", "rop_dop", "rop_comp", "rop_geometry"]
            ):
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "sopoutput"]
                and x[0].node().type().category().name() == "Driver"
                and x[0].node().type().name() in ["geometry", "alembic"]
            ):
                continue

            extFiles.append(hou.expandString(x[1]).replace("\\", "/"))
            extFilesSource.append(x[0])

        return extFiles

    @err_decorator
    def preSubmit(self, origin, rSettings):
        try:
            rSettings["renderNode"] = self.node.path()
        except:
            pass

    @err_decorator
    def undoRenderSettings(self, origin, rSettings):
        pass

    @err_decorator
    def preSubmitChecks(self, origin, jobData):
        renderNode = None
        try:
            if hou.node(jobData["renderNode"]).type().name() in [
                "ifd",
                "Redshift_ROP",
                "rop_dop",
                "rop_comp",
                "rop_geometry",
                "rop_alembic",
                "filecache",
                "geometry",
                "alembic",
            ]:
                renderNode = jobData["renderNode"]
        except:
            pass

        if renderNode is None:
            return "Submission canceled: Node is invalid."

    @err_decorator
    def getJobConfigParams(self, origin, cData):
        for i in cData:
            if i[1] == "programVersion":
                break
        else:
            cData.append(["information", "programVersion", hou.applicationVersionString()])
