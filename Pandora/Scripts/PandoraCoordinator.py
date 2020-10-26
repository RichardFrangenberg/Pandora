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

import sys, os, io, time, shutil, socket, traceback, subprocess, json
import random
import string
from functools import wraps

if sys.version[0] == "3":
    pyLibs = "Python37"
    pVersion = 3
else:
    pyLibs = "Python27"
    pVersion = 2

pndPath = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "PythonLibs",
    pyLibs,
)
sys.path.append(pndPath)
import psutil


class PandoraCoordinator:
    def __init__(self):
        try:
            self.version = "v1.1.0.6"

            self.coordUpdateTime = 5  # seconds
            self.activeThres = 10  # time in min after a slave becomes inactive
            self.notifySlaveInterval = (
                10
            )  # time in min in which interval a connection check is send to the slaves
            self.connectionCheckInterval = (
                20
            )  # time in min in which interval a to check if a connection to the slave exists
            self.lastConnectionCheckTime = time.time()
            self.lastNotifyTime = time.time()

            pandoraConfig = os.path.join(
                os.environ["userprofile"], "Documents", "Pandora", "Pandora.json"
            )
            self.repPath = ""
            self.localMode = True
            self.restartGDriveEnabled = False
            self.coordConf = ""

            curPath = os.path.dirname(os.path.abspath(__file__))
            if not curPath.replace("\\", "/").endswith("/Scripts/PandoraCoordinator"):
                cData = {}
                cData["coordEnabled"] = ["coordinator", "enabled"]
                cData["localMode"] = ["globals", "localMode"]
                cData["globalRootpath"] = ["globals", "rootPath"]
                cData["coordRootpath"] = ["coordinator", "rootPath"]
                cData["repositoryPath"] = ["globals", "repositoryPath"]
                cData = self.getConfig(data=cData, configPath=pandoraConfig)

                if cData["coordEnabled"] is not None and cData["coordEnabled"] == False:
                    self.writeLog("Coordinator is disabled. Closing Coordinator")
                    return

                if cData["localMode"] is not None:
                    self.localMode = cData["localMode"] == True

                if self.localMode:
                    rootPath = cData["globalRootpath"]
                else:
                    rootPath = cData["coordRootpath"]

                if rootPath is None:
                    self.writeLog("Sync directory is not defined. Closing Coordinator")
                    return

                if not os.path.exists(rootPath):
                    try:
                        os.makedirs(rootPath)
                    except:
                        self.writeLog("Sync directory doesn't exist. Closing Coordinator")
                        return

                self.coordBasePath = os.path.join(rootPath, "Scripts", "PandoraCoordinator")

                if cData["repositoryPath"] is None or cData["repositoryPath"] == "":
                    self.writeLog(
                        "Repository is invalid. Fallback to default repository location."
                    )
                else:
                    repoDir = os.path.join(cData["repositoryPath"], "Coordinator")
                    if not os.path.exists(repoDir):
                        try:
                            os.makedirs(repoDir)
                        except:
                            pass

                    if os.path.exists(repoDir):
                        self.repPath = repoDir
                        self.writeLog("Set repository: %s" % self.repPath)
                    else:
                        self.writeLog(
                            "Repository doesn't exist. Fallback to default repository location."
                        )

                slScript = os.path.join(os.path.dirname(__file__), "PandoraSlave.py")
                hScript = os.path.join(os.path.dirname(__file__), "PandoraStartHouJob.py")

                tslScript = os.path.join(
                    os.path.dirname(self.coordBasePath), "PandoraSlaves", "PandoraSlave.py"
                )
                thScript = os.path.join(
                    os.path.dirname(self.coordBasePath),
                    "PandoraSlaves",
                    "PandoraStartHouJob.py",
                )

                if not os.path.exists(os.path.dirname(tslScript)):
                    try:
                        os.makedirs(os.path.dirname(tslScript))
                    except:
                        pass

            # 	if not os.path.exists(tslScript):
            # 		shutil.copy2(slScript, tslScript)
            # 	if not os.path.exists(thScript):
            # 		shutil.copy2(hScript, thScript)
            else:
                self.coordBasePath = os.path.dirname(os.path.abspath(__file__))

            self.writeLog("Coordinator path: %s" % self.coordBasePath)

            self.slPath = os.path.abspath(
                os.path.join(self.coordBasePath, os.pardir, os.pardir)
            )

            self.coordLog = os.path.join(
                self.coordBasePath, "Coordinator_Log_%s.txt" % socket.gethostname()
            )
            self.coordConf = os.path.join(self.coordBasePath, "Coordinator_Settings.json")
            self.actSlvPath = os.path.join(self.coordBasePath, "ActiveSlaves.json")
            self.coordWarningsConf = os.path.join(
                self.coordBasePath, "Coordinator_Warnings_%s.json" % socket.gethostname()
            )
            self.logCache = os.path.join(self.slPath, "Workstations", "Logs", "Coordinator", "LogCache.json")

            self.close = False
            self.tvRequests = []
            self.slaveContactTimes = {}
            self.renderingTasks = []
            self.collectTasks = {}
            self.jobDirs = []

            self.writeLog(
                "Starting Coordinator - %s - %s" % (self.version, socket.gethostname()), 1
            )

            repConf = self.getConfig("settings", "repository")

            if repConf is not None and os.path.exists(repConf):
                self.repPath = repConf
                self.writeLog("Set repository: %s" % self.repPath)

            if self.repPath == "":
                self.repPath = os.path.join(self.slPath, "JobRepository")
                self.writeLog("set repository: %s" % self.repPath)

            lmodeConf = self.getConfig("settings", "localMode")

            if lmodeConf is not None:
                self.localMode = lmodeConf == True
                self.writeLog("Set localMode: %s" % self.localMode)

            self.writeLog("Repository: %s" % self.repPath, 1)
            self.writeLog("Coordinatorbase: %s" % self.coordBasePath, 1)
            self.writeLog("localMode: %s" % self.localMode, 1)

            self.pAssetPath = os.path.join(self.repPath, "ProjectAssets")
            self.jobPath = os.path.join(self.repPath, "Jobs")

            self.prioList = os.path.join(self.repPath, "PriorityList.json")

            self.getGDrivePath()

            cmdPath = os.path.join(self.coordBasePath, "command.txt")

            while not self.close:
                if os.path.exists(cmdPath):
                    with open(cmdPath, "r") as cmdFile:
                        cmd = cmdFile.read()

                    if cmd == "exit":
                        closeCoord = time.time() - os.path.getmtime(cmdPath) < 30
                        try:
                            os.remove(cmdPath)
                        except:
                            pass

                        if closeCoord:
                            break

                self.startCoordination()
                time.sleep(self.coordUpdateTime)

            self.writeLog("Coordinator closed", 1)
            self.notifyWorkstations()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.writeLog(
                "ERROR - init - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno), 3
            )

        sys.exit()

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Coordinator:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].writeLog(erStr, 3)

        return func_wrapper

    def writeLog(self, text, level=0, writeWarning=True):
        # print text
        if not hasattr(self, "coordLog") or not os.path.exists(self.coordLog):
            try:
                logPath = self.coordLog
                if not os.path.exists(os.path.dirname(self.coordLog)):
                    os.makedirs(os.path.dirname(self.coordLog))
            except:
                logPath = os.path.join(
                    os.path.dirname(__file__),
                    "Coordinator_Log_%s.txt" % socket.gethostname(),
                )
        else:
            logPath = self.coordLog

        if hasattr(self, "coordConf"):
            debug = self.getConfig("settings", "debugMode", suppressError=True)
            if debug is None and self.coordConf != "":
                self.setConfig("settings", "debugMode", False, suppressError=True)
                debug = False
        else:
            debug = True

        if level == 0 and not debug:
            return
        elif level > 1 and writeWarning:
            self.writeWarning(text, level)

        with io.open(logPath, "a", encoding="utf-16") as log:
            log.write(
                    "[%s] %s - %s : %s\n"
                    % (level, os.getpid(), time.strftime("%d/%m/%y %X"), text)
            )

        # print "[%s] %s : %s\n" % (level, time.strftime("%d/%m/%y %X"), text)

    def writeWarning(self, text, level=2):
        if not os.path.exists(self.coordWarningsConf):
            try:
                open(self.coordWarningsConf, "a").close()
            except:
                self.writeLog("Cannot create warning config", 2, writeWarning=False)
                return None

        warningConfig = self.getConfig(
            configPath=self.coordWarningsConf, getConf=True, suppressError=True
        )
        if warningConfig is None:
            return

        warnings = []
        if "warnings" in warningConfig:
            for i in warningConfig["warnings"]:
                warnings.append(warningConfig["warnings"][i])

            warnings = [x for x in warnings if x[0] != text]

        warnings.insert(0, [text, time.time(), level])

        warningConfig = {"warnings": {}}

        for idx, val in enumerate(warnings):
            warningConfig["warnings"]["warning%s" % idx] = val

        self.setConfig(
            configPath=self.coordWarningsConf, confData=warningConfig, suppressError=True
        )

    @err_decorator
    def checkCommands(self):
        val = self.getConfig("settings", "command")
        if val != "":
            self.setConfig("settings", "command", "")

        if val is not None and val != "":
            self.writeLog("CheckCommands - execute: %s" % val, 1)
            try:
                exec(val)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR - checkCommands - %s - %s - %s"
                    % (str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )

    @err_decorator
    def getConfig(
        self,
        cat=None,
        param=None,
        data=None,
        configPath=None,
        getOptions=False,
        getItems=False,
        getConf=False,
        suppressError=False,
    ):
        try:
            if configPath is None:
                configPath = self.coordConf

            if configPath is None or configPath == "":
                return

            isCoordConf = configPath == self.coordConf

            if isCoordConf and not os.path.exists(configPath):
                self.createUserPrefs()

            if not os.path.exists(os.path.dirname(configPath)):
                return

            if len(
                [
                    x
                    for x in os.listdir(os.path.dirname(configPath))
                    if x.startswith(os.path.basename(configPath) + ".bak")
                ]
            ):
                self.restoreConfig(configPath)

            userConfig = {}

            try:
                if os.path.exists(configPath):
                    with open(configPath, "r") as f:
                        userConfig = json.load(f)
            except:
                if isCoordConf:
                    warnStr = "The coordinator preferences file seems to be corrupt.\n\nIt will be reset, which means all coordinator settings will fall back to their defaults."
                else:
                    warnStr = "Cannot read the following file:\n\n%s" % configPath

                    if not suppressError:
                        self.writeWarning(warnStr, 2)
                    # print warnStr

                if isCoordConf:
                    self.createUserPrefs()
                    with open(configPath, "r") as f:
                        userConfig = json.load(f)

            if getConf:
                return userConfig

            if getOptions:
                if cat in userConfig:
                    return userConfig[cat].values()
                else:
                    return []

            if getItems:
                if cat in userConfig:
                    return userConfig[cat]
                else:
                    return {}

            returnData = {}
            if data is None:
                rData = {"val": [cat, param]}
            else:
                rData = data

            for i in rData:
                cat = rData[i][0]
                param = rData[i][1]

                if cat in userConfig and param in userConfig[cat]:
                    returnData[i] = userConfig[cat][param]
                else:
                    returnData[i] = None

            if data is None:
                return returnData["val"]
            else:
                return returnData
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errStr = "%s ERROR - getconfig %s:\n%s\n\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.version,
                "".join(traceback.format_stack()),
                traceback.format_exc(),
            )
            # print errStr
            if not suppressError:
                raise e

    @err_decorator
    def setConfig(
        self,
        cat=None,
        param=None,
        val=None,
        data=None,
        configPath=None,
        delete=False,
        confData=None,
        suppressError=True,
    ):
        try:
            if configPath is None:
                configPath = self.coordConf

            isCoordConf = configPath == self.coordConf

            if isCoordConf and not os.path.exists(configPath):
                self.createUserPrefs()

            fcontent = os.listdir(os.path.dirname(configPath))
            if len(
                [x for x in fcontent if x.startswith(os.path.basename(configPath) + ".bak")]
            ):
                self.restoreConfig(configPath)

            if confData is None:
                userConfig = {}
                try:
                    if os.path.exists(configPath):
                        with open(configPath, "r") as f:
                            userConfig = json.load(f)
                except:
                    if isCoordConf:
                        warnStr = "The coordinator preferences file seems to be corrupt.\n\nIt will be reset, which means all coordinator settings will fall back to their defaults."
                    else:
                        warnStr = (
                            "Cannot read the following file. It will be reset now:\n\n%s"
                            % configPath
                        )

                    if not suppressError:
                        self.writeWarning(warnStr, 2)
                    # print warnStr

                    if isCoordConf:
                        self.createUserPrefs()
                        with open(configPath, "r") as f:
                            userConfig = json.load(f)

                if data is None:
                    data = [[cat, param, val]]

                for i in data:
                    cat = i[0]
                    param = i[1]
                    val = i[2]

                    if cat not in userConfig:
                        userConfig[cat] = {}

                    if delete:
                        if param is None:
                            del userConfig[cat]
                            continue

                        if param in userConfig[cat]:
                            del userConfig[cat][param]
                        continue

                    userConfig[cat][param] = val
            else:
                userConfig = confData

            with open(configPath, "w") as inifile:
                json.dump(userConfig, inifile, indent=4)

            try:
                with open(configPath, "r") as f:
                    testConfig = json.load(f)
                if confData is None:
                    for i in userConfig:
                        for k in userConfig[i]:
                            if k not in testConfig[i]:
                                raise RuntimeError
            except:
                backupPath = configPath + ".bak" + str(random.randint(1000000, 9999999))
                with open(backupPath, "w") as inifile:
                    json.dump(userConfig, inifile, indent=4)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errStr = "%s ERROR - getconfig %s:\n%s\n\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.version,
                "".join(traceback.format_stack()),
                traceback.format_exc(),
            )
            # print errStr
            if not suppressError:
                raise e

    @err_decorator
    def restoreConfig(self, configPath):
        path = os.path.dirname(configPath)
        backups = []
        for i in os.listdir(path):
            if not i.startswith(os.path.basename(configPath) + "."):
                continue

            try:
                backups.append(
                    {
                        "name": i,
                        "time": os.path.getmtime(os.path.join(path, i)),
                        "size": os.stat(os.path.join(path, i)).st_size,
                    }
                )
            except Exception:
                return False

        times = [x["time"] for x in backups]

        if len(times) == 0:
            return False

        minTime = min(times)

        validBackup = None
        for i in backups:
            if i["time"] == minTime and (
                validBackup is None or validBackup["size"] > i["size"]
            ):
                validBackup = i

        if validBackup is None:
            return False

        try:
            if os.path.exists(configPath):
                os.remove(configPath)
        except Exception:
            warnStr = (
                "Could not remove corrupt config in order to restore a backup config:\n\n%s"
                % configPath
            )
            self.writeWarning(warnStr, 2)

        validBuPath = os.path.join(path, validBackup["name"])

        try:
            shutil.copy2(validBuPath, configPath)
        except:
            warnStr = "Could not restore backup config:\n\n%s" % validBuPath
            self.writeWarning(warnStr, 2)
            return False

        for i in backups:
            buPath = os.path.join(path, i["name"])
            try:
                os.remove(buPath)
            except:
                pass

        return True

    @err_decorator
    def createUserPrefs(self):
        if os.path.exists(self.coordConf):
            try:
                os.remove(self.coordConf)
            except:
                pass

        if not os.path.exists(os.path.dirname(self.coordConf)):
            os.makedirs(os.path.dirname(self.coordConf))

        uconfig = {
            "settings": {
                "coordUpdateTime": self.coordUpdateTime,
                "command": "",
                "debugMode": False,
                "repository": "",
                "notifySlaveInterval": 10,
                "restartGDrive": False,
            }
        }

        with open(self.coordConf, "w") as inifile:
            json.dump(uconfig, inifile, indent=4)

    @err_decorator
    def startCoordination(self):
        self.writeLog("Cycle start")
        # checking slaves
        if os.path.exists(os.path.join(self.coordBasePath, "EXIT.txt")):
            return True

        self.checkCommands()

        newUTime = self.getConfig("settings", "coordUpdateTime")
        if newUTime is None:
            self.setConfig("settings", "coordUpdateTime", self.coordUpdateTime)
        elif newUTime != self.coordUpdateTime:
            self.writeLog(
                "Updating updateTime from %s to %s" % (self.coordUpdateTime, newUTime), 1
            )
            self.coordUpdateTime = newUTime

        newCInterval = self.getConfig("settings", "notifySlaveInterval")
        if newCInterval is None:
            self.setConfig("settings", "notifySlaveInterval", self.notifySlaveInterval)
        elif newCInterval != self.notifySlaveInterval:
            self.writeLog(
                "Updating notifySlaveInterval from %s to %s"
                % (self.notifySlaveInterval, newCInterval),
                1,
            )
            self.notifySlaveInterval = newCInterval

        rgdrive = self.getConfig("settings", "restartGDrive")
        if rgdrive is None:
            self.setConfig("settings", "restartGDrive", self.restartGDriveEnabled)
        elif rgdrive != self.restartGDriveEnabled:
            self.writeLog(
                "Updating restartGDrive from %s to %s"
                % (self.restartGDriveEnabled, rgdrive),
                1,
            )
            self.restartGDriveEnabled = rgdrive

        self.activeSlaves = {}
        self.availableSlaves = []

        if not os.path.exists(self.jobPath):
            os.makedirs(self.jobPath)

        self.getJobAssignments()

        if not os.path.exists(os.path.join(self.slPath, "Slaves")):
            os.makedirs(os.path.join(self.slPath, "Slaves"))

        self.checkSlaves()
        self.setConfig(configPath=self.actSlvPath, confData=self.slaveContactTimes)

        if not self.localMode:
            self.checkConnection()
        self.checkRenderingTasks()
        self.getAvailableSlaves()
        self.assignJobs()
        self.checkTvRequests()
        if not self.localMode:
            self.checkCollectTasks()
        self.notifyWorkstations()
        self.notifySlaves()

        self.writeLog("Cycle finished")

    @err_decorator
    def handleCmd(self, cmFile, origin=""):
        self.writeLog("Handle cmd file: %s" % cmFile)

        with open(cmFile, "r") as comFile:
            cmdText = comFile.read()
            command = None
            try:
                command = eval(cmdText)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR -- handleCmd evalCmd -- %s\n%s\n%s\n%s\n%s"
                    % (str(e), exc_type, exc_tb.tb_lineno, origin, cmdText),
                    3,
                )

        if command is not None and type(command) == list:
            for i in range(1):
                if command[0] == "taskUpdate":
                    if len(command) < 7:
                        self.writeLog(
                            "ERROR - taskupdate has not enough information: %s" % (command),
                            1,
                        )
                        continue

                    jobCode = command[1]
                    taskName = command[2]
                    taskStatus = command[3]
                    taskTime = command[4]
                    taskStart = command[5]
                    taskEnd = command[6]
                    if taskStatus == "finished":
                        outputFileNum = int(command[7])

                    jobSettings = os.path.join(self.jobPath, jobCode, "PandoraJob.json")

                    if not os.path.exists(jobSettings):
                        self.writeLog(
                            "ERROR - jobSettings don't exist %s (%s)" % (jobCode, origin), 3
                        )
                        continue

                    jName = self.getConfig("information", "jobName", configPath=jobSettings)
                    if jName is not None:
                        jobName = jName
                    else:
                        jobName = jobCode

                    taskData = self.getConfig("jobtasks", taskName, configPath=jobSettings)
                    if taskData is None:
                        self.writeLog(
                            "ERROR - task is not listed %s - %s (%s)"
                            % (jobName, taskName, origin),
                            3,
                        )
                        continue

                    if (
                        type(taskData) != list
                        or len(taskData) != 7
                        or (taskData[2] == "rendering" and taskData[3] != origin)
                        or taskData[2] in ["finished", "disabled"]
                    ):
                        self.writeLog(
                            "Could not set taskdata on job %s for task %s - %s (%s)"
                            % (jobName, taskName, command, origin),
                            1,
                        )
                        continue

                    if (
                        taskData[2] == "rendering"
                        and [jobCode, taskName] in self.renderingTasks
                    ):
                        self.renderingTasks.remove([jobCode, taskName])

                    taskData[2] = taskStatus
                    if taskStatus == "ready":
                        taskData[3] = "unassigned"
                    else:
                        taskData[3] = origin
                    taskData[4] = taskTime
                    taskData[5] = taskStart
                    taskData[6] = taskEnd
                    self.setConfig("jobtasks", taskName, taskData, configPath=jobSettings)

                    if (
                        taskStatus == "rendering"
                        and [jobCode, taskName] not in self.renderingTasks
                    ):
                        self.renderingTasks.append([jobCode, taskName])

                    if (
                        taskStatus == "finished"
                        and outputFileNum > 0
                        and not self.localMode
                    ):
                        if origin in self.collectTasks:
                            self.collectTasks[origin][jobCode] = outputFileNum
                        else:
                            self.collectTasks[origin] = {jobCode: outputFileNum}

                    self.writeLog(
                        "Updated Task %s in %s to %s (%s)"
                        % (taskName, jobName, str(taskData), origin),
                        1,
                    )

                elif command[0] == "setSetting":
                    settingType = command[1]
                    parentName = command[2]
                    settingName = command[3]
                    settingVal = command[4]

                    if settingType == "Job":
                        settingsPath = os.path.join(
                            self.jobPath, parentName, "PandoraJob.json"
                        )
                        section = "jobglobals"
                    elif settingType == "Slave":
                        self.sendCommand(
                            parentName, ["setSetting", settingName, settingVal]
                        )
                        self.writeLog(
                            "Set config setting %s - %s: %s (%s)"
                            % (parentName, settingName, settingVal, origin),
                            1,
                        )

                        if (
                            settingType == "Slave"
                            and settingName in ["command", "corecommand"]
                            and settingVal == "self.startTeamviewer()"
                        ):
                            if (
                                len(
                                    [
                                        x
                                        for x in self.tvRequests
                                        if x["slave"] == parentName
                                        and x["workstation"] == origin
                                    ]
                                )
                                == 0
                            ):
                                self.tvRequests.append(
                                    {
                                        "slave": parentName,
                                        "workstation": origin,
                                        "requestTime": time.time(),
                                    }
                                )

                        continue
                    elif settingType == "Coordinator":
                        settingsPath = self.coordConf
                        section = "settings"

                    if not os.path.exists(settingsPath):
                        self.writeLog(
                            "ERROR - settingsPath doesn't exist %s (%s)"
                            % (parentName, origin),
                            2,
                        )
                        continue

                    self.setConfig(
                        section, settingName, settingVal, configPath=settingsPath
                    )

                    if settingType == "Job" and settingName == "priority":
                        self.setConfig(
                            parentName, "priority", settingVal, configPath=self.prioList
                        )

                    self.writeLog(
                        "Set config setting %s - %s: %s (%s)"
                        % (parentName, settingName, settingVal, origin),
                        1,
                    )

                elif command[0] == "deleteJob":
                    if os.path.exists(self.prioList):
                        self.setConfig(command[1], delete=True, configPath=self.prioList)
                    else:
                        self.writeLog(
                            "WARNING - priolist does not exist (%s)" % (origin), 2
                        )

                    jobPath = os.path.join(self.repPath, "Jobs", command[1])
                    jobConf = os.path.join(jobPath, "PandoraJob.json")

                    projectName = ""
                    jobCode = command[1]
                    jobName = command[1]

                    if os.path.exists(jobConf):
                        cData = {}
                        cData["jobName"] = ["information", "jobName"]
                        cData["projectName"] = ["information", "projectName"]
                        cData = self.getConfig(data=cData, configPath=jobConf)

                        if cData["jobName"] is not None:
                            jobName = cData["jobName"]

                        if cData["projectName"] is not None:
                            projectName = cData["projectName"]

                    if os.path.exists(jobPath):
                        shutil.rmtree(jobPath)
                    else:
                        self.writeLog(
                            "WARNING - job %s did not exist before deletion (%s)"
                            % (jobName, origin),
                            2,
                        )

                    for m in os.listdir(os.path.join(self.slPath, "Slaves")):
                        if not m.startswith("S_"):
                            continue

                        slaveName = m[2:]

                        jobFiles = os.path.join(
                            self.slPath, "Slaves", m, "AssignedJobs", command[1]
                        )
                        jobOutput = os.path.join(
                            self.slPath, "Slaves", m, "Output", command[1]
                        )

                        for k in [jobFiles, jobOutput]:
                            if os.path.exists(k):
                                try:
                                    shutil.rmtree(k)
                                except:
                                    self.writeLog(
                                        "ERROR - cannot remove folder: %s (%s)"
                                        % (k, origin),
                                        3,
                                    )

                        self.sendCommand(slaveName, ["deleteJob", str(jobCode)])

                    for m in os.listdir(os.path.join(self.slPath, "Workstations")):
                        if not m.startswith("WS_"):
                            continue

                        logFile = os.path.join(
                            self.slPath,
                            "Workstations",
                            m,
                            "Logs",
                            "Jobs",
                            "PandoraJob.json",
                        )
                        jobOutput = os.path.join(
                            self.slPath,
                            "Workstations",
                            m,
                            "RenderOutput",
                            projectName,
                            command[1],
                        )
                        for k in [logFile, jobOutput]:
                            if os.path.exists(k):
                                try:
                                    if os.path.isfile(k):
                                        os.remove(k)
                                    else:
                                        shutil.rmtree(k)
                                except:
                                    self.writeLog(
                                        "ERROR - cannot remove file(s): %s (%s)"
                                        % (k, origin),
                                        3,
                                    )

                    self.writeLog("Deleted Job %s (%s)" % (jobName, origin), 1)

                elif command[0] == "restartTask":
                    jobCode = command[1]
                    taskNum = command[2]

                    jobConf = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.json")
                    jName = self.getConfig("information", "jobName", configPath=jobConf)
                    if jName is not None:
                        jobName = jName
                    else:
                        jobName = jobCode

                    taskData = self.getConfig(
                        "jobtasks", "task%04d" % taskNum, configPath=jobConf
                    )
                    if taskData is None:
                        self.writeLog(
                            "Job %s has no task %s (%s)" % (jobName, taskNum, origin), 2
                        )
                        continue

                    if taskData[2] in ["rendering", "assigned"]:
                        self.sendCommand(
                            taskData[3], ["cancelTask", jobCode, "task%04d" % taskNum]
                        )

                    taskData[2] = "ready"
                    taskData[3] = "unassigned"
                    taskData[4] = ""
                    taskData[5] = ""
                    taskData[6] = ""
                    self.setConfig(
                        "jobtasks", "task%04d" % taskNum, taskData, configPath=jobConf
                    )

                    self.writeLog(
                        "Restarted Task %s from Job %s (%s)" % (taskNum, jobName, origin), 1
                    )

                elif command[0] == "disableTask":
                    jobCode = command[1]
                    taskNum = command[2]
                    enable = command[3]

                    if enable:
                        action = "enable"
                    else:
                        action = "disable"

                    jobConf = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.json")
                    jName = self.getConfig("information", "jobName", configPath=jobConf)
                    if jName is not None:
                        jobName = jName
                    else:
                        jobName = jobCode

                    taskData = self.getConfig(
                        "jobtasks", "task%04d" % taskNum, configPath=jobConf
                    )
                    if taskData is None:
                        self.writeLog(
                            "Job %s has no task %s (%s)" % (jobName, taskNum, origin), 2
                        )
                        continue

                    if (
                        (taskData[2] != "disabled" and enable)
                        or (taskData[2] == "disabled" and not enable)
                        or taskData[2] in ["finished", "error"]
                    ):
                        continue

                    if enable:
                        taskData[2] = "ready"
                        taskData[3] = "unassigned"
                    else:
                        if taskData[2] in ["rendering", "assigned"]:
                            self.sendCommand(
                                taskData[3], ["cancelTask", jobCode, "task%04d" % taskNum]
                            )

                        taskData[2] = "disabled"
                        taskData[3] = "unassigned"
                        taskData[5] = ""

                    self.setConfig(
                        "jobtasks", "task%04d" % taskNum, taskData, configPath=jobConf
                    )
                    self.writeLog(
                        "%sd task %s from Job %s (%s)" % (action, taskNum, jobName, origin),
                        1,
                    )

                elif command[0] == "deleteWarning":
                    warnType = command[1]
                    slaveName = command[2]
                    warnText = command[3]
                    warnTime = command[4]

                    if warnType == "Coordinator":
                        warningConfig = self.getConfig(
                            configPath=self.coordWarningsConf, getConf=True
                        )

                        warnings = []
                        if "warnings" in warningConfig:
                            for i in warningConfig["warnings"]:
                                warnings.append(warningConfig["warnings"][i])

                            warnings = [
                                x
                                for x in warnings
                                if not (x[0] == warnText and x[1] == warnTime)
                            ]

                        warningConfig = {"warnings": {}}

                        for idx, val in enumerate(warnings):
                            warningConfig["warnings"]["warning%s" % idx] = val

                        self.setConfig(
                            configPath=self.coordWarningsConf, confData=warningConfig
                        )

                    elif warnType == "Slave":
                        self.sendCommand(slaveName, ["deleteWarning", warnText, warnTime])

                    if warnType == "Slave":
                        self.writeLog("Warning deleted: %s (%s)" % (slaveName, origin), 1)
                    elif warnType == "Coordinator":
                        self.writeLog("Coordinator warning deleted (%s)" % origin, 1)

                elif command[0] == "clearWarnings":
                    warnType = command[1]
                    slaveName = command[2]

                    if warnType == "Coordinator":
                        warnConfig = {"warnings": {}}
                        self.setConfig(
                            confData=warnConfig, configPath=self.coordWarningsConf
                        )

                    elif warnType == "Slave":
                        self.sendCommand(slaveName, ["clearWarnings"])

                    if warnType == "Slave":
                        self.writeLog("Warnings cleared: %s (%s)" % (slaveName, origin), 1)
                    elif warnType == "Coordinator":
                        self.writeLog("Coordinator warnings cleared (%s)" % origin, 1)

                elif command[0] == "clearLog":
                    logType = command[1]
                    logName = command[2]

                    if logType == "Coordinator":
                        logPath = self.coordLog
                        open(logPath, "w").close()

                    elif logType == "Slave":
                        self.sendCommand(logName, ["clearLog"])

                    self.writeLog(
                        "Cleared log for %s %s (%s)" % (logType, logName, origin), 1
                    )

                elif command[0] == "collectJob":
                    jobCode = command[1]

                    jobConf = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.json")

                    jName = self.getConfig("information", "jobName", configPath=jobConf)
                    if jName is not None:
                        jobName = jName
                    else:
                        jobName = jobCode

                    copiedNum, errors, targetPath = self.collectOutput(jobCode=jobCode)

                    collectStr = "Job %s output collected. %s files copied to %s" % (
                        jobName,
                        copiedNum,
                        targetPath,
                    )
                    if errors > 0:
                        collectStr += " %s errors occured" % errors
                        errorLvl = 3
                    else:
                        errorLvl = 1

                    self.writeLog(collectStr + " (%s)" % (origin), errorLvl)

        try:
            os.remove(cmFile)
        except:
            self.writeLog("ERROR - cannot remove file: %s (%s)" % (cmFile, origin), 3)

    @err_decorator
    def searchUncollectedRnd(self):
        uncollRnds = {}

        slaveSyncPath = os.path.join(self.slPath, "Slaves")
        for i in os.listdir(slaveSyncPath):
            slOutput = os.path.join(slaveSyncPath, i, "Output")
            if os.path.exists(slOutput):
                for n in os.listdir(slOutput):
                    if n not in uncollRnds:
                        uncollRnds[n] = 0

                    jobPath = os.path.join(slOutput, n)
                    for k in os.walk(jobPath):
                        for m in k[2]:
                            filePath = os.path.join(k[0], m)
                            relFilePath = filePath.replace(jobPath, "")
                            while relFilePath.startswith("\\") or relFilePath.startswith(
                                "/"
                            ):
                                relFilePath = relFilePath[1:]
                            targetPath = os.path.join(
                                os.path.dirname(self.slPath), "Projects", relFilePath
                            )
                            if not os.path.exists(targetPath):
                                uncollRnds[n] += 1

        collectStr = "Uncollected renderings searched:\n"
        if len([x for x in uncollRnds.values() if x > 0]) == 0:
            collectStr += "no uncollected renderings found"
            errorLvl = 1
        else:
            for i in uncollRnds:
                if uncollRnds[i] > 0:
                    collectStr += "%s: uncollected renderings: %s\n" % (i, uncollRnds[i])
            errorLvl = 1

        self.writeLog(collectStr, errorLvl)

    @err_decorator
    def getJobAssignments(self):
        self.writeLog("Check job submissions")

        if not os.path.exists(os.path.join(self.slPath, "Workstations")):
            self.writeWarning(
                "Workstations folder doesn't exist (%s)"
                % (os.path.join(self.slPath, "Workstations")),
                2,
            )
            return

        for i in os.listdir(os.path.join(self.slPath, "Workstations")):
            try:
                if not os.path.isdir(
                    os.path.join(self.slPath, "Workstations", i)
                ) or not i.startswith("WS_"):
                    continue

                cmdDir = os.path.join(self.slPath, "Workstations", i, "Commands")
                wsName = i[len("WS_") :]

                if os.path.exists(cmdDir):
                    for k in sorted(os.listdir(cmdDir)):
                        cmFile = os.path.join(cmdDir, k)

                        if k == "Pandora_update.zip":
                            shutil.move(
                                cmFile,
                                os.path.join(
                                    self.slPath,
                                    "Scripts",
                                    "PandoraSlaves",
                                    "Pandora-development.zip",
                                ),
                            )
                            continue

                        if not k.startswith("handlerOut_"):
                            continue

                        self.handleCmd(cmFile, origin=wsName)

                jobDir = os.path.join(self.slPath, "Workstations", i, "JobSubmissions")

                if not os.path.exists(jobDir):
                    # self.writeWarning("Job JobSubmission folder does not exist (%s)" % wsName, 2)
                    continue

                for k in os.listdir(jobDir):
                    if k == "ProjectAssets":
                        continue

                    jobCode = k
                    self.writeLog("Found job %s on workstation %s." % (jobCode, wsName))

                    jobConf = os.path.join(jobDir, jobCode, "PandoraJob.json")
                    if not os.path.exists(jobConf):
                        self.writeWarning(
                            "Job config does not exist for job: %s (%s)"
                            % (jobCode, wsName),
                            2,
                        )
                        continue

                    cData = {}
                    cData["jobName"] = ["information", "jobName"]
                    cData["fileCount"] = ["information", "fileCount"]
                    cData["priority"] = ["jobglobals", "priority"]
                    cData["projectAssets"] = ["information", "projectAssets"]
                    cData["projectName"] = ["information", "projectName"]
                    cData = self.getConfig(data=cData, configPath=jobConf)

                    if cData["jobName"] is not None:
                        jobName = cData["jobName"]
                    else:
                        jobName = jobCode

                    if cData["fileCount"] is not None and cData["priority"] is not None:
                        jobFileCount = cData["fileCount"]
                        jobPrio = cData["priority"]
                    else:
                        self.writeWarning(
                            "not all required information for job %s exists (%s)"
                            % (jobName, wsName),
                            2,
                        )
                        continue

                    existingFiles = 0

                    if cData["projectAssets"] is not None:
                        wspaFolder = os.path.join(
                            jobDir, "ProjectAssets", cData["projectName"]
                        )
                        paFolder = os.path.join(self.pAssetPath, cData["projectName"])
                        if not os.path.exists(paFolder):
                            os.makedirs(os.path.join(self.pAssetPath, cData["projectName"]))

                        for m in cData["projectAssets"]:
                            aPath = os.path.join(wspaFolder, m[0])
                            if not os.path.exists(aPath):
                                continue

                            taPath = os.path.join(paFolder, m[0])
                            if os.path.exists(taPath) and int(
                                os.path.getmtime(taPath)
                            ) == int(m[1]):
                                existingFiles += 1
                                continue

                            if os.path.exists(aPath) and int(
                                os.path.getmtime(aPath)
                            ) == int(m[1]):
                                try:
                                    shutil.copy2(aPath, taPath)
                                    existingFiles += 1
                                except:
                                    self.writeWarning(
                                        "Could not copy file to ProjectAssets: %s %s %s %s"
                                        % (wsName, cData["projectName"], jobName, m),
                                        2,
                                    )
                            else:
                                self.writeLog(
                                    "Project asset is missing or outdated: %s for job %s"
                                    % (m[0], jobName)
                                )

                    jobFilesDir = os.path.join(jobDir, jobCode, "JobFiles")
                    if not os.path.isdir(jobFilesDir):
                        self.writeLog(
                            "Jobfiles folder does not exist for job %s (%s)"
                            % (jobName, wsName),
                            1,
                        )
                        continue

                    if (len(os.listdir(jobFilesDir)) + existingFiles) < jobFileCount:
                        self.writeLog(
                            "Not all required files for job %s exists (%s)"
                            % (jobName, wsName)
                        )
                        continue

                    targetPath = os.path.join(self.repPath, "Jobs", jobCode)

                    while os.path.exists(targetPath):
                        newjobCode = "".join(
                            random.choice(string.lowercase) for x in range(10)
                        )
                        self.writeLog("Renamed job %s to %s" % (jobCode, newjobCode))
                        jobCode = newjobCode
                        targetPath = os.path.join(self.repPath, "Jobs", jobCode)

                    cData = []
                    cData.append(["information", "jobcode", jobCode])
                    cData.append(["information", "submitWorkstation", wsName])
                    cData = self.setConfig(configPath=jobConf, data=cData)

                    self.writeLog(
                        "Copying job %s (%s) to coordinator repository."
                        % (jobName, jobCode)
                    )
                    try:
                        shutil.move(os.path.join(jobDir, jobCode), targetPath)
                    except:
                        self.writeWarning(
                            "Jobfolder %s could not be copied to the JobRepository (%s)"
                            % (jobName, wsName),
                            3,
                        )
                        continue

                    self.setConfig(jobCode, "priority", jobPrio, configPath=self.prioList)
                    self.writeLog(
                        "Job %s was added to the JobRepository from %s" % (jobName, wsName),
                        1,
                    )

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR -- getJobAssignments -- %s\n%s\n%s"
                    % (str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )

    @err_decorator
    def checkSlaves(self):
        # checks for updated slave script and handles slaveout commands
        self.writeLog("Checking slave commands.")

        for i in os.listdir(os.path.join(self.slPath, "Slaves")):
            try:
                slavePath = os.path.join(self.slPath, "Slaves", i)
                if not (i.startswith("S_") and os.path.isdir(slavePath)):
                    self.writeWarning("WARNING -- Slaves folder is invalid %s" % i, 2)
                    continue

                slaveName = i[len("S_") :]
                slaveActivePath = os.path.join(slavePath, "slaveActive_%s" % slaveName)
                slaveComPath = os.path.join(slavePath, "Communication")

                file_mod_time = 0

                if os.path.exists(slaveActivePath):
                    file_mod_time = os.stat(slaveActivePath).st_mtime

                webapiPath = os.path.join(
                    os.path.dirname(slavePath), "webapi", "slaveActive_%s" % slaveName
                )
                if (
                    os.path.exists(webapiPath)
                    and os.stat(webapiPath).st_mtime > file_mod_time
                ):
                    file_mod_time = os.stat(webapiPath).st_mtime

                last_time = int((time.time() - file_mod_time) / 60)

                self.slaveContactTimes[slaveName] = file_mod_time
                if last_time < self.activeThres:
                    self.activeSlaves[slaveName] = file_mod_time

                slaveScriptPath = os.path.join(slavePath, "Scripts", "PandoraSlave.py")
                masterScriptPath = os.path.join(
                    self.slPath, "Scripts", "PandoraSlaves", "PandoraSlave.py"
                )
                if os.path.exists(masterScriptPath):
                    try:
                        if not os.path.exists(os.path.dirname(slaveScriptPath)):
                            os.makedirs(os.path.dirname(slaveScriptPath))

                        if os.path.exists(slaveScriptPath):
                            sFileDate = int(os.path.getmtime(slaveScriptPath))
                        else:
                            sFileDate = 0

                        mFileDate = int(os.path.getmtime(masterScriptPath))

                        if mFileDate > sFileDate:
                            shutil.copy2(masterScriptPath, slaveScriptPath)
                            self.writeLog("Updated Slave for %s" % slaveName, 1)

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        self.writeLog(
                            "ERROR -- checkSlaves mlp -- %s %s\n%s\n%s"
                            % (slaveName, str(e), exc_type, exc_tb.tb_lineno),
                            3,
                        )

                else:
                    self.writeLog("master Slave script does not exist")

                shouJobPath = os.path.join(slavePath, "Scripts", "PandoraStartHouJob.py")
                mhouJobPath = os.path.join(
                    self.slPath, "Scripts", "PandoraSlaves", "PandoraStartHouJob.py"
                )
                if os.path.exists(mhouJobPath):
                    try:
                        if not os.path.exists(os.path.dirname(shouJobPath)):
                            os.makedirs(os.path.dirname(shouJobPath))

                        if os.path.exists(shouJobPath):
                            sFileDate = int(os.path.getmtime(shouJobPath))
                        else:
                            sFileDate = 0

                        mFileDate = int(os.path.getmtime(mhouJobPath))

                        if mFileDate > sFileDate:
                            shutil.copy2(mhouJobPath, shouJobPath)
                            self.writeLog("Updated houJobScript for %s" % slaveName, 1)

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        self.writeLog(
                            "ERROR -- checkSlaves mhp -- %s\n%s\n%s"
                            % (str(e), exc_type, exc_tb.tb_lineno),
                            3,
                        )
                else:
                    self.writeLog("master houJob script does not exist")

                sZipPath = os.path.join(slavePath, "Scripts", "Pandora-development.zip")
                mZipPath = os.path.join(
                    self.slPath, "Scripts", "PandoraSlaves", "Pandora-development.zip"
                )

                if os.path.exists(mZipPath):
                    try:
                        if not os.path.exists(os.path.dirname(sZipPath)):
                            os.makedirs(os.path.dirname(sZipPath))

                        if os.path.exists(sZipPath):
                            sFileDate = int(os.path.getmtime(sZipPath))
                        else:
                            sFileDate = 0

                        mFileDate = int(os.path.getmtime(mZipPath))

                        if mFileDate > sFileDate:
                            shutil.copy2(mZipPath, sZipPath)
                            self.writeLog("Updated Pandora for %s" % slaveName, 1)

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        self.writeLog(
                            "ERROR -- checkSlaves mzp -- %s\n%s\n%s"
                            % (str(e), exc_type, exc_tb.tb_lineno),
                            3,
                        )

                    try:
                        os.remove(mZipPath)
                    except:
                        pass

                if not os.path.exists(slaveComPath):
                    try:
                        os.makedirs(slaveComPath)
                    except:
                        self.writeLog(
                            "Could not create Communication folder for %s" % slaveName, 3
                        )
                        continue

                for k in sorted(os.listdir(slaveComPath)):
                    if not k.startswith("slaveOut_"):
                        continue

                    cmFile = os.path.join(slaveComPath, k)
                    self.handleCmd(cmFile, origin=slaveName)

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR -- checkSlaves -- %s\n%s\n%s"
                    % (str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )

    @err_decorator
    def checkConnection(self):
        if not self.restartGDriveEnabled:
            return

        if len(self.activeSlaves) == 0 and (time.time() - self.lastConnectionCheckTime) > (
            self.connectionCheckInterval * 60
        ):
            self.restartGDrive()
            self.lastConnectionCheckTime = time.time()

    # restarts "backup and sync" from google
    @err_decorator
    def restartGDrive(self):
        if "psutil" not in locals():
            return

        self.writeLog("Restart gdrive")
        PROCNAME = "googledrivesync.exe"
        for proc in psutil.process_iter():
            if proc.name() == PROCNAME:
                p = psutil.Process(proc.pid)

                if not "SYSTEM" in p.username():
                    proc.kill()

        if os.path.exists(self.gdrive):
            subprocess.Popen(self.gdrive)

    # searches for the installation path of "backup and sync" from google in the registry
    @err_decorator
    def getGDrivePath(self):
        try:
            import _winreg
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\Google\Drive",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            self.gdrive = (_winreg.QueryValueEx(key, "InstallLocation"))[0]
            if not os.path.exists(self.gdrive):
                self.gdrive = ""
        except:
            self.gdrive = ""

        self.writeLog("Set gdrive path to: %s" % self.gdrive)

    @err_decorator
    def checkRenderingTasks(self):
        self.writeLog("Checking rendering tasks.")

        removed = []
        for i in self.renderingTasks:
            jobCode = i[0]
            taskName = i[1]

            confPath = os.path.join(self.jobPath, jobCode, "PandoraJob.json")

            if not os.path.exists(confPath):
                self.writeWarning("Job config does not exist: %s" % confPath, 2)
                removed.append(i)
                continue

            taskData = self.getConfig("jobtasks", taskName, configPath=confPath)
            if taskData is None:
                self.writeWarning("no jobtasks in %s" % confPath)
                continue

            if taskData[2] != "rendering":
                self.writeWarning("rendertask is not rendering: %s" % i)
                continue

            rSlave = taskData[3]
            slaveSettings = os.path.join(
                self.slPath, "Slaves", "S_%s" % rSlave, "slaveSettings_%s.json" % rSlave
            )
            if not os.path.exists(slaveSettings):
                self.writeWarning("slave settings does not exist: %s" % rSlave)
                continue

            sStatus = self.getConfig("slaveinfo", "status", configPath=slaveSettings)
            sTasks = self.getConfig("slaveinfo", "curtasks", configPath=slaveSettings)

            if sStatus != "idle" and sTasks is not None:
                for task in sTasks:
                    if task["jobcode"] == jobCode and task["taskname"] == taskName:
                        break
                else:
                    taskData[2] = "ready"
                    taskData[3] = "unassigned"
                    taskData[4] = ""
                    taskData[5] = ""
                    taskData[6] = ""
                    self.setConfig("jobtasks", taskName, taskData, configPath=confPath)

                    removed.append(i)
                    self.writeLog("Reset task %s of job %s" % (taskName, jobCode), 1)

        for i in removed:
            self.renderingTasks.remove(i)

    @err_decorator
    def getAvailableSlaves(self):
        self.writeLog("Getting available slaves.")

        jobBase = os.path.join(self.repPath, "Jobs")
        slaveAssignments = {}

        if os.path.exists(jobBase):
            for i in os.listdir(jobBase):
                try:
                    confPath = os.path.join(jobBase, i, "PandoraJob.json")

                    if not os.path.exists(confPath):
                        continue

                    jobConfig = self.getConfig(configPath=confPath, getConf=True)

                    if "jobtasks" not in jobConfig:
                        self.writeWarning(
                            "Job config does not contain jobtasks: %s" % confPath, 2
                        )
                        continue

                    for k in jobConfig["jobtasks"]:
                        taskData = jobConfig["jobtasks"][k]
                        if taskData[2] in ["assigned", "rendering"]:
                            try:
                                startTime = float(taskData[5])
                            except:
                                pass
                            else:
                                elapsedTime = (time.time() - startTime) / 60.0

                                taskTimedOut = False
                                if taskData[2] == "assigned":
                                    if elapsedTime > 15:
                                        taskTimedOut = True

                                elif taskData[2] == "rendering":
                                    if "taskTimeout" in jobConfig["jobglobals"]:
                                        timeout = jobConfig["jobglobals"]["taskTimeout"]
                                        if elapsedTime > timeout:
                                            taskTimedOut = True

                                if "jobName" in jobConfig["information"]:
                                    jName = jobConfig["information"]["jobName"]
                                else:
                                    jName = ""

                                if taskTimedOut:
                                    self.sendCommand(
                                        taskData[3], ["cancelTask", jName, i, k]
                                    )

                                    taskData[2] = "ready"
                                    taskData[3] = "unassigned"
                                    taskData[4] = ""
                                    taskData[5] = ""
                                    taskData[6] = ""
                                    self.setConfig(
                                        "jobtasks", k, taskData, configPath=confPath
                                    )

                                    self.writeLog(
                                        "Timeout of %s from Job %s (%s min)"
                                        % (k, jName, elapsedTime),
                                        1,
                                    )
                                    continue

                            slaveName = taskData[3]
                            if slaveName not in slaveAssignments:
                                slaveAssignments[slaveName] = {"concurrent": []}

                            jobCon = jobConfig["jobglobals"].get("concurrentTasks", 1)
                            slaveAssignments[slaveName]["concurrent"].append(jobCon)
                            # self.writeLog("DEBUG - unavailable slaves: %s - %s" % (taskData[3],i))
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    self.writeLog(
                        "ERROR - getAvailableSlaves - %s - %s - %s"
                        % (str(e), exc_type, exc_tb.tb_lineno),
                        3,
                    )

        # self.writeLog("DEBUG - unavailable slaves: %s" % unavailableSlaves)

        for slave in self.activeSlaves:
            try:
                slaveData = {"name": slave}
                slaveSettings = os.path.join(
                    self.slPath, "Slaves", "S_%s" % slave, "slaveSettings_%s.json" % slave
                )
                if not os.path.exists(slaveSettings):
                    self.writeWarning("slave settings does not exist: %s" % slave)
                    continue

                maxSlaveTasks = self.getConfig("settings", "maxConcurrentTasks", configPath=slaveSettings)

                if slave in slaveAssignments:
                    concList = slaveAssignments[slave]["concurrent"]
                    if len(concList) >= min(concList) or len(concList) >= maxSlaveTasks:
                        continue

                    slaveData["maxTasks"] = min([min(concList), maxSlaveTasks])
                    slaveData["curTaskNum"] = len(concList)
                else:
                    slaveData["maxTasks"] = maxSlaveTasks
                    slaveData["curTaskNum"] = 0

                self.availableSlaves.append(slaveData)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR -- getAvailableSlaves -- %s -- %s\n%s\n%s"
                    % (slave, str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )

    @err_decorator
    def assignJobs(self):
        self.writeLog("Start checking jobs")

        jobPrios = self.getConfig(configPath=self.prioList, getConf=True)
        self.jobDirs = [
            x
            for x in reversed(sorted(jobPrios, key=lambda x: jobPrios[x]["priority"]))
            if os.path.exists(os.path.join(self.repPath, "Jobs", x))
        ]

        for jobDir in self.jobDirs:
            confPath = os.path.join(self.jobPath, jobDir, "PandoraJob.json")

            if not os.path.exists(confPath):
                self.writeWarning("Job config does not exist: %s" % jobDir, 2)
                continue

            jobConfig = self.getConfig(configPath=confPath, getConf=True)
            cData = {}
            cData["jobName"] = ["information", "jobName"]
            cData["sceneName"] = ["information", "sceneName"]
            cData["fileCount"] = ["information", "fileCount"]
            cData["projectAssets"] = ["information", "projectAssets"]
            cData["jobDependecies"] = ["jobglobals", "jobDependecies"]
            cData["listSlaves"] = ["jobglobals", "listSlaves"]
            cData["projectName"] = ["information", "projectName"]
            cData["concurrentTasks"] = ["jobglobals", "concurrentTasks"]
            cData = self.getConfig(data=cData, configPath=confPath)

            if cData["jobName"] is not None:
                jobName = cData["jobName"]
            else:
                self.writeWarning("Job has no jobname option: %s" % jobDir, 2)
                continue

            if cData["sceneName"] is not None:
                sceneName = cData["sceneName"]
            else:
                self.writeWarning("Job has no sceneName option: %s" % jobName, 2)
                continue

            if cData["fileCount"] is not None:
                jobFileCount = cData["fileCount"]
                if (
                    len(os.listdir(os.path.join(self.jobPath, jobDir, "JobFiles")))
                    < jobFileCount
                    and cData["projectAssets"] is None
                ):
                    self.writeLog(
                        "Assign job - not all required files for job %s exists" % jobName, 1
                    )
                    continue
            else:
                self.writeWarning("Job has no fileCount option: %s" % jobName, 2)
                continue

            if "jobtasks" not in jobConfig:
                self.writeWarning("Job tasks are missing: %s" % jobName, 2)
                continue

            dependentSlaves = []

            if cData["jobDependecies"] is not None:
                depsFinished = [True]
                jobDeps = cData["jobDependecies"]
                for jDep in jobDeps:
                    if len(jDep) == 2:
                        depName = jDep[0]
                        depConf = os.path.join(self.jobPath, depName, "PandoraJob.json")
                        if not os.path.exists(depConf):
                            self.writeWarning(
                                "For job %s the dependent job %s is missing."
                                % (jobName, depName),
                                2,
                            )
                            depsFinished = [False, depName]
                            break

                        depConfig = self.getConfig(configPath=depConf, getConf=True)

                        if (
                            "information" in depConfig
                            and "jobName" in depConfig["information"]
                        ):
                            depJobName = depConfig["information"]["jobName"]
                        else:
                            depJobName = depName

                        if not "jobtasks" in depConfig:
                            self.writeWarning(
                                "For job %s the dependent job %s has no tasks."
                                % (jobName, depJobName),
                                2,
                            )
                            depsFinished = [False, depJobName]
                            break

                        for dTask in depConfig["jobtasks"]:
                            taskData = depConfig["jobtasks"][dTask]

                            if not (
                                type(taskData) == list
                                and len(taskData) == 7
                                and taskData[2] == "finished"
                            ):
                                depsFinished = [False, depJobName]
                                break
                            else:
                                if taskData[3] not in dependentSlaves:
                                    dependentSlaves.append(taskData[3])

                    if not depsFinished[0]:
                        break

                if not depsFinished[0]:
                    self.writeLog(
                        "For job %s the dependent job %s is not finished."
                        % (jobName, depsFinished[1]),
                        0,
                    )
                    continue

            jobSlaves = []

            if cData["listSlaves"] is not None:
                listSlaves = cData["listSlaves"]
                if listSlaves.startswith("exclude "):
                    whiteList = False
                    listSlaves = listSlaves[len("exclude "):]
                else:
                    whiteList = True

                for slave in self.availableSlaves:
                    slaveName = slave["name"]
                    if len(dependentSlaves) > 0 and slaveName not in dependentSlaves:
                        continue

                    conc = cData["concurrentTasks"] or 1
                    if slave["curTaskNum"] >= conc:
                        continue

                    if listSlaves.startswith("groups: "):
                        jGroups = listSlaves[len("groups: "):].split(", ")

                        slaveSettings = os.path.join(
                            self.slPath, "Slaves", "S_%s" % slaveName, "slaveSettings_%s.json" % slaveName
                        )
                        slaveGroups = self.getConfig(
                            "settings", "slaveGroup", configPath=slaveSettings
                        )

                        if slaveGroups is None:
                            continue

                        for k in jGroups:
                            if (k not in slaveGroups) == whiteList:
                                break
                        else:
                            jobSlaves.append(slave)
                    else:
                        if (
                            listSlaves == "All"
                            or (slaveName in listSlaves.split(", ")) == whiteList
                        ):
                            jobSlaves.append(slave)

            for i in sorted(jobConfig["jobtasks"]):
                taskData = jobConfig["jobtasks"][i]
                if len(jobSlaves) == 0:
                    break

                if not (type(taskData) == list and len(taskData) == 7):
                    continue

                if taskData[2] != "ready":
                    continue

                assignedSlave = jobSlaves[0]

                slavePath = os.path.join(self.slPath, "Slaves", "S_%s" % assignedSlave["name"])
                slaveSettings = os.path.join(
                    slavePath, "slaveSettings_%s.json" % assignedSlave["name"]
                )

                slaveJobPath = os.path.join(slavePath, "AssignedJobs", "%s" % jobDir)

                self.writeLog("Assigning job %s to slave %s." % (jobName, assignedSlave["name"]))

                if not os.path.exists(slaveJobPath):
                    self.writeLog(
                        "Copying job files for job %s to slave %s."
                        % (jobName, assignedSlave["name"])
                    )
                    shutil.copytree(os.path.join(self.jobPath, jobDir), slaveJobPath)

                if cData["projectAssets"] is not None:
                    jpAssets = cData["projectAssets"][1:]
                    pName = cData["projectName"]
                    sPAssetPath = os.path.join(slavePath, "ProjectAssets", pName)
                    if not os.path.exists(sPAssetPath):
                        os.makedirs(sPAssetPath)

                    for k in jpAssets:
                        paPath = os.path.join(self.pAssetPath, pName, k[0])
                        if not os.path.exists(paPath):
                            self.writeWarning(
                                "Required ProjectAsset does not exist: %s %s"
                                % (pName, k[0]),
                                2,
                            )
                            continue

                        sPAsset = os.path.join(sPAssetPath, k[0])
                        if os.path.exists(sPAsset) and os.path.getmtime(
                            paPath
                        ) == os.path.getmtime(sPAsset):
                            continue

                        self.writeLog(
                            "Copying project asset %s to slave %s." % (k[0], assignedSlave["name"])
                        )

                        shutil.copy2(paPath, sPAsset)

                cmd = str(["renderTask", jobDir, jobName, i])
                self.sendCommand(assignedSlave["name"], cmd)

                taskData[2] = "assigned"
                taskData[3] = assignedSlave["name"]
                taskData[5] = time.time()

                assignedSlave["curTaskNum"] += 1
                conc = cData["concurrentTasks"] or 1
                if conc < assignedSlave["maxTasks"]:
                    assignedSlave["maxTasks"] = conc

                if assignedSlave["curTaskNum"] == assignedSlave["maxTasks"]:
                    jobSlaves.remove(assignedSlave)
                    self.availableSlaves = [x for x in self.availableSlaves if x["name"] != assignedSlave["name"]]

                self.setConfig("jobtasks", i, taskData, configPath=confPath)
                self.writeLog(
                    "Assigned %s to %s in job %s" % (assignedSlave["name"], i, jobName), 1
                )

    @err_decorator
    def sendCommand(self, slave, cmd):
        cmdDir = os.path.join(self.slPath, "Slaves", "S_%s" % slave, "Communication")
        curNum = 1

        for i in os.listdir(cmdDir):
            if not i.startswith("slaveIn_"):
                continue

            num = i.split("_")[1]
            if sys.version[0] == "2":
                unum = unicode(num)
            else:
                unum = num

            if not unum.isnumeric():
                continue

            if int(num) >= curNum:
                curNum = int(num) + 1

        cmdFile = os.path.join(
            cmdDir, "slaveIn_%s_%s.txt" % (format(curNum, "04"), time.time())
        )

        self.writeLog("Sending command: %s" % cmd)

        with open(cmdFile, "w") as cFile:
            cFile.write(str(cmd))

    @err_decorator
    def checkTvRequests(self):
        handledRequests = []

        for i in self.tvRequests:
            self.writeLog("Handling teamviewer request: %s" % i)
            ssPath = os.path.join(
                self.slPath, "Slaves", "S_%s" % i["slave"], "ScreenShot_%s.jpg" % i["slave"]
            )
            if os.path.exists(ssPath) and os.path.getmtime(ssPath) > i["requestTime"]:
                targetPath = os.path.join(
                    self.slPath, "Workstations", "WS_%s" % i["workstation"], "Screenshots"
                )
                try:
                    shutil.copy2(ssPath, targetPath)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    self.writeLog(
                        "ERROR -- could not copy file %s -- %s\n%s\n%s"
                        % (i, str(e), exc_type, exc_tb.tb_lineno),
                        3,
                    )

                handledRequests.append(i)

        self.tvRequests = [x for x in self.tvRequests if x not in handledRequests]

    @err_decorator
    def checkCollectTasks(self):
        removeTasks = []
        for slave in self.collectTasks:
            for job in self.collectTasks[slave]:
                expNum = self.collectTasks[slave][job]

                outputPath = os.path.join(
                    self.slPath, "Slaves", "S_" + slave, "Output", job
                )

                if not os.path.exists(outputPath):
                    self.writeLog(
                        "Can't collect output. The Outputpath doesn't exist: %s"
                        % outputPath
                    )
                    continue

                fileCount = 0
                for i in os.walk(outputPath):
                    fileCount += len(i[2])

                if fileCount != expNum:
                    self.writeLog(
                        "Can't collect output. The fileCount doesn't match: %s from %s for %s"
                        % (fileCount, expNum, outputPath)
                    )
                    continue

                copiedNum, errors, targetPath = self.collectOutput(slave=slave, jobCode=job)

                jobConf = os.path.join(self.repPath, "Jobs", job, "PandoraJob.json")
                jName = self.getConfig("information", "jobName", configPath=jobConf)

                if jName is not None:
                    jobName = jName
                else:
                    jobName = job

                collectStr = ""
                if copiedNum != 0 or errors != 0:
                    collectStr = (
                        "Job %s output collected automatically. %s files copied to %s"
                        % (jobName, copiedNum, targetPath)
                    )

                if errors > 0:
                    collectStr += " %s errors occured" % errors
                    errorLvl = 2
                else:
                    errorLvl = 0

                removeTasks.append([slave, job])

                if collectStr != "":
                    self.writeLog(collectStr, errorLvl)

        for i in removeTasks:
            del self.collectTasks[i[0]][i[1]]

    @err_decorator
    def collectOutput(self, slave=None, jobCode=None):
        jobConf = os.path.join(self.repPath, "Jobs", jobCode, "PandoraJob.json")
        if os.path.exists(jobConf):
            jconfig = self.getConfig(configPath=jobConf, getConf=True)
            cData = {}
            cData["submitWorkstation"] = ["information", "submitWorkstation"]
            cData["projectName"] = ["information", "projectName"]
            cData = self.getConfig(data=cData, configPath=jobConf)
        else:
            self.writeWarning("Job config does not exist for job: %s" % (jobCode), 2)
            return [0, 0, ""]

        copiedNum = 0
        errors = 0
        targetPath = "None"
        if cData["submitWorkstation"] is not None:
            targetBase = os.path.join(
                self.slPath,
                "Workstations",
                "WS_" + cData["submitWorkstation"],
                "RenderOutput",
                cData["projectName"],
                jobCode,
            )
        else:
            return [0, 0, ""]

        jfolderExists = True
        if not os.path.exists(targetBase):
            try:
                os.makedirs(targetBase)
            except:
                jfolderExists = False

        if jfolderExists:
            try:
                shutil.copy2(jobConf, targetBase)
            except:
                pass

        slaveSyncPath = os.path.join(self.slPath, "Slaves")
        for i in os.listdir(slaveSyncPath):
            slaveName = i[len("S_") :]
            if slave is not None and slave != slaveName:
                continue

            jobOutput = os.path.join(slaveSyncPath, i, "Output", jobCode)
            if os.path.exists(jobOutput):
                for k in os.walk(jobOutput):
                    for m in k[2]:
                        filePath = os.path.join(k[0], m)
                        relFilePath = filePath.replace(jobOutput, "")
                        while relFilePath.startswith("\\") or relFilePath.startswith("/"):
                            relFilePath = relFilePath[1:]
                        targetPath = os.path.join(targetBase, relFilePath)

                        copyFile = True

                        if os.path.exists(targetPath):
                            curFileDate = int(os.path.getmtime(os.path.abspath(filePath)))
                            targetFileDate = int(os.path.getmtime(targetPath))

                            if curFileDate <= targetFileDate:
                                copyFile = False

                        if copyFile:
                            folderExists = True
                            if not os.path.exists(os.path.dirname(targetPath)):
                                try:
                                    os.makedirs(os.path.dirname(targetPath))
                                except:
                                    errors += 1
                                    folderExists = False
                            if folderExists:
                                try:
                                    shutil.copy2(filePath, targetPath)
                                    copiedNum += 1
                                except:
                                    errors += 1

        if "jobtasks" in jconfig["jobtasks"]:
            for k in jconfig["jobtasks"]:
                taskData = jconfig["jobtasks"][k]
                if taskData[2] != "finished":
                    break
            else:
                targetConf = os.path.join(
                    self.slPath,
                    "Workstations",
                    "WS_" + cData["submitWorkstation"],
                    "RenderOutput",
                    cData["projectName"],
                    jobCode,
                    "PandoraJob.json",
                )
                if os.path.exists(targetConf):
                    outputCount = 0
                    for i in os.walk(os.path.dirname(targetConf)):
                        outputCount += len(i[2])

                    self.setConfig(
                        "information", "outputFileCount", outputCount, configPath=targetConf
                    )

        return [copiedNum, errors, targetPath]

    @err_decorator
    def notifyWorkstations(self):
        self.writeLog("Notify workstations")

        logDir = os.path.join(self.slPath, "Workstations", "Logs")

        if not os.path.exists(logDir):
            try:
                os.makedirs(logDir)
            except:
                self.writeLog(
                    "ERROR -- could not create log folder %s -- %s\n%s\n%s" % (logDir), 3
                )
                return

        validLogs = []
        validLogs += self.copyLogs(
            [self.coordLog, self.coordConf, self.actSlvPath, self.coordWarningsConf],
            os.path.join(logDir, "Coordinator"),
        )

        filesToCopy = []
        for jobDir in self.jobDirs:
            jobConf = os.path.join(self.jobPath, jobDir, "PandoraJob.json")
            filesToCopy.append(jobConf)

        validLogs += self.copyLogs(filesToCopy, os.path.join(logDir, "Jobs"))

        filesToCopy = []
        for i in os.listdir(os.path.join(self.slPath, "Slaves")):
            if i.startswith("S_"):
                slaveName = i[len("S_") :]
                slaveLog = os.path.join(
                    self.slPath, "Slaves", i, "slaveLog_%s.txt" % slaveName
                )
                slaveSettings = os.path.join(
                    os.path.dirname(slaveLog), "slaveSettings_%s.json" % slaveName
                )
                slaveWarnings = os.path.join(
                    os.path.dirname(slaveLog), "slaveWarnings_%s.json" % slaveName
                )
                filesToCopy += [slaveLog, slaveSettings, slaveWarnings]

        validLogs += self.copyLogs(filesToCopy, os.path.join(logDir, "Slaves"))
        for log in validLogs:
            log["path"] = log["path"].replace(logDir, "")

        self.setConfig(configPath=self.logCache, confData=validLogs)

    @err_decorator
    def notifySlaves(self):
        if self.localMode:
            return

        if (time.time() - self.lastNotifyTime) < (self.notifySlaveInterval * 60):
            return

        self.writeLog("Notify slaves")

        for i in os.listdir(os.path.join(self.slPath, "Slaves")):
            if not i.startswith("S_"):
                continue

            slaveName = i[len("S_") :]
            if slaveName not in self.activeSlaves.keys():
                continue

            self.lastNotifyTime = time.time()

            self.sendCommand(slaveName, ["checkConnection"])

    @err_decorator
    def copyLogs(self, files, target):
        if not os.path.exists(target):
            try:
                os.makedirs(target)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR -- could not create folder %s -- %s\n%s\n%s"
                    % (target, str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )

        jobNames = []

        validLogs = []
        for i in files:
            # self.writeLog(i)
            if not os.path.exists(i):
                self.writeLog("Copy logs: skipping %s" % i)
                continue

            origTime = int(os.path.getmtime(i))

            if os.path.basename(i) == "PandoraJob.json":
                jobName = self.getConfig("information", "jobName", configPath=i)

                if jobName is not None:
                    origjobName = jobName

                    jNum = 1
                    while jobName in jobNames:
                        jobName = origjobName + " (%s)" % jNum
                        jNum += 1

                    jobNames.append(jobName)
                else:
                    jobName = os.path.basename(i)

                targetPath = os.path.join(target, jobName + ".json")
            else:
                targetPath = os.path.join(target, os.path.basename(i))

            validLogs.append({"path": targetPath, "mtime": origTime})

            if (
                not os.path.exists(targetPath)
                or int(os.path.getmtime(targetPath)) != origTime
            ):
                try:
                    shutil.copy2(i, targetPath)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    self.writeLog(
                        "ERROR -- could not copy file %s -- %s\n%s\n%s"
                        % (i, str(e), exc_type, exc_tb.tb_lineno),
                        2,
                    )

        baseNames = [os.path.basename(x) for x in files if os.path.exists(x)]
        baseNames.append("LogCache.json")

        for i in os.listdir(target):
            if i not in baseNames and os.path.splitext(i)[0] not in jobNames:
                lpath = os.path.join(target, i)
                os.remove(lpath)
                self.writeLog("removed log: %s" % lpath)

        return validLogs


if __name__ == "__main__":
    sco = PandoraCoordinator()
