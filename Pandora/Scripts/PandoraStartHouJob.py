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


import sys, os, io, time, socket, json
import hou

slavePath = eval(sys.argv[3])[1]


def writeLog(text, level=0):
    slaveLog = slavePath + "\\slaveLog_%s.txt" % socket.gethostname()
    if not os.path.exists(slaveLog):
        try:
            if not os.path.exists(os.path.dirname(slaveLog)):
                os.makedirs(os.path.dirname(slaveLog))
            open(slaveLog, "a").close()
        except:
            return None

    with io.open(slaveLog, "a", encoding="utf-16") as log:
        msgStr = "[%s] %s : %s\n" % (level, time.strftime("%d.%m.%y %X"), text)
        if sys.version[0] == "2":
            msgStr = unicode(msgStr)

        log.write(msgStr)


try:
    if not os.path.exists(sys.argv[1]):
        sys.exit("ERROR - Scene File does not exist - " + sys.argv[1])

    writeLog("load Scene")
    hou.hipFile.load(sys.argv[1], ignore_load_warnings=True)
    jobData = eval(sys.argv[2])
    localSlavePath = eval(sys.argv[3])[0]

    frameStart = jobData["taskStartframe"]
    frameEnd = jobData["taskEndframe"]

    depFiles = os.listdir(os.path.dirname(sys.argv[1]))
    for i in hou.fileReferences():
        try:
            fseq = False
            if "$F" in i[1]:
                countExp = os.path.basename(i[1]).count("`")
                startExp = os.path.basename(i[1]).find("`")
                endExp = os.path.basename(i[1]).rfind("`")
                if countExp == 2:
                    startName = os.path.basename(i[1])[:startExp]
                    endName = os.path.basename(i[1])[endExp + 1:]
                else:
                    startName = os.path.basename(i[1])[: os.path.basename(i[1]).find("$F")]
                    endName = os.path.basename(i[1])[
                        os.path.basename(i[1]).find("$F") + 3:
                    ]

                for k in depFiles:
                    if os.path.basename(k).startswith(startName) and os.path.basename(
                        k
                    ).endswith(endName):
                        fseq = True
                        break

            if (os.path.basename(i[1]) in depFiles and i[0] is not None) or fseq:
                try:
                    i[0].deleteAllKeyframes()
                    i[0].set("$HIP/" + os.path.basename(i[1]))
                except:
                    writeLog(
                        "Cannot relink file dependency, because the parameter is locked: %s - %s"
                        % (i[0], os.path.basename(i[1]))
                    )

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            writeLog(
                "ERROR - PandoraStartHouJob - repath dependencies - %s - %s - %s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )

    if "jobDependecies" in jobData:
        jobDeps = jobData["jobDependecies"]
        for jDep in jobDeps:
            if len(jDep) == 2:
                depName = jDep[0]

                if "localMode" in jobData and jobData["localMode"]:
                    depConf = os.path.join(
                        os.path.join(localSlavePath, "Jobs", depName, "PandoraJob.json")
                    )
                    if not os.path.exists(depConf):
                        sys.exit("ERROR - dependent job config does not exist %s" % depConf)
                    else:
                        with open(depConf, "r") as f:
                            depConfig = json.load(f)

                        if (
                            "information" in depConfig
                            and "outputPath" in depConfig["information"]
                            and depConfig["information"]["outputPath"] != ""
                        ):
                            depPath = os.path.dirname(
                                depConfig["information"]["outputPath"]
                            )
                        else:
                            sys.exit(
                                "ERROR - dependent job config has no outputpath setting exist %s"
                                % depConf
                            )
                else:
                    depPath = os.path.join(
                        os.path.join(localSlavePath, "RenderOutput", depName)
                    )

                if not os.path.exists(depPath):
                    sys.exit("ERROR - Dependent job does not exist - " + depName)

                for i in os.walk(depPath):
                    if len(i[2]) > 0:
                        depNode = hou.node(jDep[1])
                        if depNode is None or depNode.type().name() != "file":
                            sys.exit("ERROR - Dependent node is invalid - " + jDep[1])

                        fPath = os.path.join(i[0], i[2][0])
                        bname, ext = os.path.splitext(fPath)
                        if bname[-4:].isnumeric():
                            fPath = "%s$F4%s" % (bname[:-4], ext)

                        fPath = fPath.replace("\\", "/")

                        if depNode.isEditable():
                            depNode.parm("file").deleteAllKeyframes()
                            depNode.parm("file").set(fPath)
                        else:
                            writeLog(
                                "Cannot relink file dependency, because the parameter is locked: %s - %s"
                                % (depNode.parm("file"), fPath)
                            )

                        break
                else:
                    sys.exit("ERROR - Dependent files do not exist - " + depName)

    renderNode = hou.node(jobData["renderNode"])

    if renderNode is None:
        sys.exit("ERROR - Render Node does not exist")

    if "outputPath" in jobData:
        curOutput = jobData["outputPath"]

        if "localMode" in jobData and jobData["localMode"]:
            newOutput = curOutput
        else:
            newOutput = os.path.join(
                localSlavePath,
                "RenderOutput",
                jobData["jobcode"],
                os.path.basename(os.path.dirname(curOutput)),
                os.path.basename(curOutput),
            )
    else:
        sys.exit("ERROR - No outputpath specified")

    newOutput = newOutput.replace("\\", "/")

    if not os.path.exists(os.path.dirname(newOutput)):
        sys.exit("ERROR - Cannot create outputfolder - " + newOutput)

    if renderNode.type().name() == "ifd":
        numAovs = renderNode.parm("vm_numaux").eval()
        if numAovs > 0 and os.path.basename(os.path.dirname(newOutput)) != "beauty":
            bName = os.path.splitext(os.path.basename(newOutput))
            if bName[0].endswith(".$F4"):
                bName = "%s.beauty%s%s" % (bName[0][:-4], bName[0][-4:], bName[1])
            else:
                bName = "%s.beauty%s" % (bName[0], bName[1])
            newOutput = os.path.join(os.path.dirname(newOutput), "beauty", bName)

        for i in range(numAovs):
            passName = renderNode.parm("vm_variable_plane" + str(i + 1)).eval()
            passOutputName = os.path.join(
                os.path.dirname(os.path.dirname(newOutput)),
                passName,
                os.path.basename(newOutput).replace("beauty", passName),
            )

            try:
                os.makedirs(os.path.split(passOutputName)[0])
            except:
                pass

            renderNode.parm("vm_usefile_plane" + str(i + 1)).set(True)
            renderNode.parm("vm_filename_plane" + str(i + 1)).set(passOutputName)
            if passName != "all":
                renderNode.parm("vm_channel_plane" + str(i + 1)).set("rgb")
            else:
                renderNode.parm("vm_channel_plane" + str(i + 1)).set("")
                renderNode.parm("vm_lightexport" + str(i + 1)).set(1)

    # 	for idx, val in enumerate(range(renderNode.parm("vm_numaux").eval())):
    # 		curPath = renderNode.parm("vm_filename_plane" + str(idx+1)).unexpandedString()
    # 		fname = os.path.basename(os.path.dirname(curPath))
    # 		newPath = os.path.join(os.path.dirname(os.path.dirname(newOutput)), fname, os.path.basename(curPath))

    # 		try:
    # 			os.makedirs(os.path.dirname(newPath))
    # 		except:
    # 			pass

    # 		renderNode.parm("vm_filename_plane" + str(idx+1)).set(newPath)
    elif renderNode.type().name() == "Redshift_ROP":
        numAovs = renderNode.parm("RS_aov").eval()
        if numAovs > 0 and os.path.basename(os.path.dirname(newOutput)) != "beauty":
            bName = os.path.splitext(os.path.basename(newOutput))
            if bName[0].endswith(".$F4"):
                bName = "%s.beauty%s%s" % (bName[0][:-4], bName[0][-4:], bName[1])
            else:
                bName = "%s.beauty%s" % (bName[0], bName[1])
            newOutput = os.path.join(os.path.dirname(newOutput), "beauty", bName)

        renderNode.parm("RS_outputEnable").set(True)
        renderNode.parm("RS_outputFileNamePrefix").set(newOutput)
        renderNode.parm("RS_outputFileFormat").set(0)
        for parm in renderNode.parms():
            if "RS_aovCustomPrefix" in parm.name():
                expression = """currentAOVID = hou.evaluatingParm().name().split("_")[-1]
layerParmName = "RS_aovSuffix_"+currentAOVID
layerName = hou.pwd().parm(layerParmName).eval()
commonOutPut = hou.pwd().parm("RS_outputFileNamePrefix").eval()
outPut = commonOutPut.replace("beauty",layerName)
return outPut"""

                parm.setExpression(expression, hou.exprLanguage.Python)

    try:
        os.makedirs(os.path.dirname(newOutput))
    except:
        pass

    if "width" in jobData and "height" in jobData:
        resolution = "res=(%s, %s), " % (jobData["width"], jobData["height"])
        if renderNode.type().name() == "Redshift_ROP":
            renderNode.parm("RS_overrideCameraRes").set(True)
            renderNode.parm("RS_overrideResScale").set(7)
            renderNode.parm("RS_overrideRes1").set(int(jobData["width"]))
            renderNode.parm("RS_overrideRes2").set(int(jobData["height"]))
    else:
        resolution = ""

    hou.hipFile.save()

    writeLog("start rendering")
    writeLog("outputpath: %s" % newOutput)
    writeLog("start: %s" % frameStart)
    writeLog("end: %s" % frameEnd)
    if renderNode.type().name() == "filecache":
        renderNode.parm("trange").set(1)
        renderNode.parm("f1").deleteAllKeyframes()
        renderNode.parm("f2").deleteAllKeyframes()
        renderNode.parm("f1").set(frameStart)
        renderNode.parm("f2").set(frameEnd)
        renderNode.parm("file").set(newOutput)
        renderNode.parm("execute").pressButton()
    else:
        exec(
            "renderNode.render(frame_range=(frameStart,frameEnd), %s output_file=newOutput, verbose=True)"
            % resolution
        )


except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    writeLog(
        "ERROR - PandoraStartHouJob - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno)
    )
    sys.exit(
        "ERROR - PandoraStartHouJob - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno)
    )
