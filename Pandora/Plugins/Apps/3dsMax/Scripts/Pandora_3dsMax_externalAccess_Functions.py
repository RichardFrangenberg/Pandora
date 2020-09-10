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


class Pandora_3dsMax_externalAccess_Functions(object):
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
                erStr = "%s ERROR - Pandora_Plugin_3dsMax_ext %s:\n%s\n\n%s" % (
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
        pass

    @err_decorator
    def pandoraSettings_loadSettings(self, origin):
        pass

    # start a 3ds Max render job
    @err_decorator
    def startJob(self, origin, jobData={}):
        origin.writeLog("starting max job. " + jobData["jobname"], 0)

        maxOverride = self.core.getConfig("dccoverrides", "3dsMax_override")
        maxOverridePath = self.core.getConfig("dccoverrides", "3dsMax_path")

        if (
            maxOverride == True
            and maxOverridePath is not None
            and os.path.exists(maxOverridePath)
        ):
            maxPath = maxOverridePath
        else:
            maxPath = self.getInstallPath()

            maxPath = os.path.join(maxPath, "3dsmaxcmd.exe")

            if not os.path.exists(maxPath):
                origin.writeLog("no 3ds Max installation found", 3)
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
            outName = "-o=%s" % newOutput
            try:
                os.makedirs(os.path.dirname(newOutput))
            except:
                pass
        else:
            origin.writeLog("no outputPath specified", 2)
            origin.renderingFailed()
            return False

        if not os.path.exists(jobData["scenefile"]):
            origin.writeLog("scenefile does not exist", 2)
            origin.renderingFailed()
            return False

        preRendScript = """
separateAOVs = True
if matchpattern (classof renderers.current as string) pattern: \"V_Ray*\" then (
	separateAOVs = not renderers.current.output_on
)

if matchpattern (classof renderers.current as string) pattern: \"Redshift*\" then (
	separateAOVs = renderers.current.SeparateAovFiles
)

if separateAOVs then (
	rmg = maxOps.GetRenderElementMgr #Production
	for i=0 to (rmg.NumRenderElements() - 1) do(
	curElement = rmg.GetRenderElement i
	curName = curElement.elementName
	curPath = rmg.GetRenderElementFilename i
	curFile = filenamefrompath curPath
	newPath = \"%s\" + curFile 
	newPath = substituteString newPath \"ELEMENTNAME\" curName
	rmg.SetRenderElementFilename i newPath
	makeDir (getFilenamePath newPath)
)
)""" % (
            os.path.dirname(os.path.dirname(newOutput)).replace("\\", "\\\\")
            + "\\\\ELEMENTNAME\\\\"
        )

        preScriptPath = os.path.join(
            os.path.dirname(os.path.dirname(jobData["scenefile"])), "preRenderScript.ms"
        )

        open(preScriptPath, "a").close()
        with open(preScriptPath, "w") as scriptfile:
            scriptfile.write(preRendScript)

        popenArgs = [maxPath, outName, "-frames=%s-%s" % (str(jobData["taskStartframe"]), str(jobData["taskEndframe"]))]

        if "width" in jobData:
            popenArgs.append("-width=%s" % jobData["width"])

        if "height" in jobData:
            popenArgs.append("-height=%s" % jobData["height"])

        if "camera" in jobData:
            popenArgs.append("-cam=%s" % jobData["camera"])

        popenArgs += [
            "-showRFW=0",
            "-gammaCorrection=1",
            "-preRenderScript=%s" % preScriptPath,
            jobData["scenefile"],
        ]

        invalidChars = ["#", "&"]
        for i in invalidChars:
            if i in jobData["scenefile"] or i in maxPath or i in outName:
                origin.writeLog(
                    "invalid characters found in the scenepath or in the outputpath: %s"
                    % i,
                    2,
                )
                origin.renderingFailed(jobData)
                return False

        thread = origin.startRenderThread(
            pOpenArgs=popenArgs, jData=jobData, prog="max", decode=True
        )
        return thread
