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


try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

import sys, os, time, traceback
from functools import wraps

for i in ["PandoraSubmitter_ui", "PandoraSubmitter_ui_ps2"]:
    try:
        del sys.modules[i]
    except:
        pass

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))

if psVersion == 1:
    import PandoraSubmitter_ui
else:
    import PandoraSubmitter_ui_ps2 as PandoraSubmitter_ui


class PandoraSubmitter(QDialog, PandoraSubmitter_ui.Ui_dlg_pandoraSubmitter):
    def __init__(self, core):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        self.setTooltips()
        self.core.callback(name="onSubmitterOpen", types=["curApp", "custom"], args=[self])
        self.connectEvents()
        self.loadSettings()

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - PandoraSubmitter %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].core.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def closeEvent(self, event):
        self.saveSettings()

    @err_decorator
    def setTooltips(self):
        self.l_projectName.setToolTip(
            "Use the same project name for all renderjobs of the project you are working on"
        )
        self.l_jobName.setToolTip(
            'Use an individial job name for each submission e.g. "Shot-020_anm_v0007"'
        )
        self.l_nodeStatus.setToolTip(
            "Shows the status of the connected render node, which will be rendered"
        )
        self.l_framerange.setToolTip(
            "Sets the first and the last frame, which should be rendered with this job (all frames between first frame and last frame will be rendered)"
        )
        self.l_camera.setToolTip(
            "Sets the camera you want to look through during rendering"
        )
        self.l_resOverride.setToolTip(
            "If checked, sets the resolution of the rendered images. If not checked the current settings from the scenefile will be used"
        )
        self.l_prio.setToolTip(
            """Sets the priority of the renderjob. Jobs with higher priority will be rendered before jobs with lower priority.
Please contact the renderfarm administrator before increasing the priority."""
        )
        self.l_framesPerTask.setToolTip(
            """Each renderjob is divided into multiple tasks. Each task contains the same number of frames to be be rendered and each task can be rendered by a different renderslave.
If you have a lot of frames, which render fast you may want to increase this value. For jobs with long rendertimes you want to decrease it."""
        )
        self.l_submitSuspended.setToolTip(
            "If checked, the renderjob will be submitted as suspended (deactivated). It can be activated manually later in the RenderHandler."
        )
        self.l_submitDependent.setToolTip(
            "If checked, all external files (e.g. Textures, References) will be submitted with this renderjob"
        )
        self.l_uploadOutput.setToolTip(
            """If checked the rendered images will be uploaded to the renderfarm server.
If set to False, the renderings can be found locally on the renderslave, which rendered the job."""
        )

    @err_decorator
    def connectEvents(self):
        self.sp_rangeStart.editingFinished.connect(self.startChanged)
        self.sp_rangeEnd.editingFinished.connect(self.endChanged)
        self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
        self.b_resPresets.clicked.connect(self.showResPresets)
        self.b_browseOutputpath.clicked.connect(self.browseOutput)
        self.b_submit.clicked.connect(self.startSubmission)

    @err_decorator
    def browseOutput(self):
        selectedPath = QFileDialog.getSaveFileName(
            self, "Select outputpath", self.e_outputpath.text(), "All files (*.*)"
        )[0]

        if selectedPath != "":
            self.e_outputpath.setText(self.core.fixPath(selectedPath))

    @err_decorator
    def startChanged(self):
        if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
            self.sp_rangeEnd.setValue(self.sp_rangeStart.value())

    @err_decorator
    def endChanged(self):
        if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
            self.sp_rangeStart.setValue(self.sp_rangeEnd.value())

    @err_decorator
    def resOverrideChanged(self, checked):
        self.sp_resWidth.setEnabled(checked)
        self.sp_resHeight.setEnabled(checked)
        self.b_resPresets.setEnabled(checked)

    @err_decorator
    def showResPresets(self):
        pmenu = QMenu()

        resolutionPresets = ["1920x1080", "1280x720", "640x360", "4000x2000", "2000x1000"]

        for i in resolutionPresets:
            pAct = QAction(i, self)
            pwidth = int(i.split("x")[0])
            pheight = int(i.split("x")[1])
            pAct.triggered.connect(lambda v=pwidth: self.sp_resWidth.setValue(v))
            pAct.triggered.connect(lambda v=pheight: self.sp_resHeight.setValue(v))
            pmenu.addAction(pAct)

        getattr(self.core.appPlugin, "setRCStyle", lambda x, y: None)(self, pmenu)
        pmenu.exec_(QCursor.pos())

    @err_decorator
    def loadSettings(self):
        # update Cams
        self.cb_cam.clear()

        camlist = self.core.appPlugin.getSceneCameras(self)

        self.cb_cam.addItems([self.core.appPlugin.getCameraName(self, i) for i in camlist])

        self.sp_rangeStart.setValue(self.core.appPlugin.getFrameRange(self)[0])
        self.sp_rangeEnd.setValue(self.core.appPlugin.getFrameRange(self)[1])

        cData = {}
        cData["projectName"] = ["lastUsedSettings", "projectName"]
        cData["startFrame"] = ["lastUsedSettings", "startFrame"]
        cData["endFrame"] = ["lastUsedSettings", "endFrame"]
        cData["camera"] = ["lastUsedSettings", "camera"]
        cData["resolutionOverride"] = ["lastUsedSettings", "resolutionOverride"]
        cData["resolutionOverrideX"] = ["lastUsedSettings", "resolutionOverrideX"]
        cData["resolutionOverrideY"] = ["lastUsedSettings", "resolutionOverrideY"]
        cData["outputPath"] = ["lastUsedSettings", "outputPath"]
        cData["priority"] = ["lastUsedSettings", "priority"]
        cData["framesPerTask"] = ["lastUsedSettings", "framesPerTask"]
        cData["taskTimeout"] = ["lastUsedSettings", "taskTimeout"]
        cData["concurrentTasks"] = ["lastUsedSettings", "concurrentTasks"]
        cData["suspended"] = ["lastUsedSettings", "suspended"]
        cData["dependentFiles"] = ["lastUsedSettings", "dependentFiles"]
        cData["localMode"] = ["globals", "localMode"]
        cData["uploadOutput"] = ["lastUsedSettings", "uploadOutput"]

        cData = self.core.getConfig(data=cData)

        if cData["projectName"] is not None:
            self.e_projectName.setText(cData["projectName"])

        if cData["startFrame"] is not None:
            try:
                self.sp_rangeStart.setValue(cData["startFrame"])
            except:
                pass

        if cData["endFrame"] is not None:
            try:
                self.sp_rangeEnd.setValue(cData["endFrame"])
            except:
                pass

        if cData["camera"] is not None:
            idx = self.cb_cam.findText(cData["camera"])
            if idx != -1:
                self.cb_cam.setCurrentIndex(idx)

        if cData["resolutionOverride"] is not None:
            try:
                self.chb_resOverride.setChecked(cData["resolutionOverride"])
            except:
                pass

        if cData["resolutionOverrideX"] is not None:
            try:
                self.sp_resWidth.setValue(cData["resolutionOverrideX"])
            except:
                pass

        if cData["resolutionOverrideY"] is not None:
            try:
                self.sp_resHeight.setValue(cData["resolutionOverrideY"])
            except:
                pass

        if cData["outputPath"] is not None:
            try:
                self.e_outputpath.setText(cData["outputPath"])
            except:
                pass

        if cData["priority"] is not None:
            try:
                self.sp_priority.setValue(cData["priority"])
            except:
                pass

        if cData["framesPerTask"] is not None:
            try:
                self.sp_framesPerTask.setValue(cData["framesPerTask"])
            except:
                pass

        if cData["taskTimeout"] is not None:
            try:
                self.sp_rjTimeout.setValue(cData["taskTimeout"])
            except:
                pass

        if cData["concurrentTasks"] is not None:
            try:
                self.sp_concurrent.setValue(cData["concurrentTasks"])
            except:
                pass

        if cData["suspended"] is not None:
            try:
                self.chb_suspended.setChecked(cData["suspended"])
            except:
                pass

        if cData["dependentFiles"] is not None:
            try:
                self.chb_dependencies.setChecked(cData["dependentFiles"])
            except:
                pass

        if cData["localMode"] is not None and cData["localMode"]:
            self.chb_uploadOutput.setChecked(False)
            self.f_osUpload.setVisible(False)
        else:
            if cData["uploadOutput"] is not None:
                try:
                    self.chb_uploadOutput.setChecked(cData["uploadOutput"])
                except:
                    pass

    @err_decorator
    def saveSettings(self):
        cData = []
        cData.append(["lastUsedSettings", "projectName", self.e_projectName.text()])
        cData.append(["lastUsedSettings", "startFrame", self.sp_rangeStart.value()])
        cData.append(["lastUsedSettings", "endFrame", self.sp_rangeEnd.value()])
        cData.append(["lastUsedSettings", "camera", self.cb_cam.currentText()])
        cData.append(
            ["lastUsedSettings", "resolutionOverride", self.chb_resOverride.isChecked()]
        )
        cData.append(["lastUsedSettings", "resolutionOverrideX", self.sp_resWidth.value()])
        cData.append(["lastUsedSettings", "resolutionOverrideY", self.sp_resHeight.value()])
        cData.append(["lastUsedSettings", "outputPath", self.e_outputpath.text()])
        cData.append(["lastUsedSettings", "priority", self.sp_priority.value()])
        cData.append(["lastUsedSettings", "framesPerTask", self.e_projectName.text()])
        cData.append(["lastUsedSettings", "taskTimeout", self.sp_rjTimeout.value()])
        cData.append(["lastUsedSettings", "concurrentTasks", self.sp_concurrent.value()])
        cData.append(["lastUsedSettings", "suspended", self.chb_suspended.isChecked()])
        cData.append(
            ["lastUsedSettings", "dependentFiles", self.chb_dependencies.isChecked()]
        )
        cData.append(
            ["lastUsedSettings", "uploadOutput", self.chb_uploadOutput.isChecked()]
        )

        self.core.setConfig(data=cData)

    @err_decorator
    def startSubmission(self):
        jobName = self.e_jobName.text()

        if (
            not os.path.isabs(self.e_outputpath.text())
            or os.path.splitext(self.e_outputpath.text())[1] == ""
        ):
            QMessageBox.warning(
                self.core.messageParent,
                "Submission canceled",
                "Submission Canceled:\n\nOutputpath is invalid.\nPlease enter a complete filename.",
            )
            return

        outputName = os.path.join(
            os.path.dirname(self.e_outputpath.text()),
            "%s%s.exr"
            % (
                os.path.splitext(os.path.basename(self.e_outputpath.text()))[0],
                self.core.appPlugin.frameString,
            ),
        )

        rSettings = {"outputName": outputName}

        self.core.appPlugin.preSubmit(self, rSettings)

        outputFolder = self.e_outputpath.text()
        if os.path.splitext(outputFolder)[1] != "":
            outputFolder = os.path.dirname(outputFolder)

        jobData = {}
        jobData["projectName"] = self.e_projectName.text()
        jobData["jobName"] = self.e_jobName.text()
        jobData["startFrame"] = self.sp_rangeStart.value()
        jobData["endFrame"] = self.sp_rangeEnd.value()
        jobData["renderCam"] = self.cb_cam.currentText()
        jobData["overrideResolution"] = self.chb_resOverride.isChecked()
        jobData["resolutionWidth"] = self.sp_resWidth.value()
        jobData["resolutionHeight"] = self.sp_resHeight.value()
        jobData["priority"] = self.sp_priority.value()
        jobData["framesPerTask"] = self.sp_framesPerTask.value()
        jobData["suspended"] = self.chb_suspended.isChecked()
        jobData["submitDependendFiles"] = self.chb_dependencies.isChecked()
        jobData["uploadOutput"] = self.chb_uploadOutput.isChecked()
        jobData["timeout"] = self.sp_rjTimeout.value()
        jobData["concurrentTasks"] = self.sp_concurrent.value()
        jobData["outputFolder"] = outputFolder
        jobData["outputPath"] = rSettings["outputName"]

        if "renderNode" in rSettings:
            jobData["renderNode"] = rSettings["renderNode"]

        self.saveSettings()

        result = self.core.submitJob(jobData)
        self.core.appPlugin.undoRenderSettings(self, rSettings)

        if isinstance(result, list) and result[0] == "Success":
            msg = QMessageBox(
                QMessageBox.Information,
                "Submit Pandora renderjob",
                'Successfully submited job "%s"' % jobData["jobName"],
                QMessageBox.Ok,
            )
            msg.addButton("Open in explorer", QMessageBox.YesRole)
            self.core.parentWindow(msg)
            action = msg.exec_()

            if action == 0:
                self.core.openFolder(os.path.dirname(result[2]))
            self.close()
        elif result.startswith("Submission canceled"):
            QMessageBox.warning(self.core.messageParent, "Submission canceled", result)

    @err_decorator
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()
