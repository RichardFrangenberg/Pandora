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


import sys, os, shutil, time, io, multiprocessing, threading, socket, subprocess, traceback
from functools import wraps

pandoraRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPandora"))

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if sys.version[0] == "3":
    pyLibs = "Python37"
    pVersion = 3
else:
    pyLibs = "Python27"
    pVersion = 2

pyLibPath = os.path.join(pandoraRoot, "PythonLibs", pyLibs)
cpLibs = os.path.join(pandoraRoot, "PythonLibs", "CrossPlatform")

if cpLibs not in sys.path:
    sys.path.append(cpLibs)

if pyLibPath not in sys.path:
    sys.path.append(pyLibPath)

sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", pyLibs, "PySide"))
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


import qdarkstyle
import psutil
from PIL import ImageGrab


# custom messagebox, which closes after some seconds. It is used to ask wether this PC is currently used by a person.
class counterMessageBox(QMessageBox):
    def __init__(self, prerenderwaittime):
        QMessageBox.__init__(self)

        # definde the amount of seconds after which the messagebox closes
        self.seconds = prerenderwaittime

        # set up text and buttons of the messagebox
        QMessageBox.setText(
            self,
            "Do you want to use this PC now? Otherwise this PC will start rendering.\n\nRendering starts in %s seconds"
            % self.seconds,
        )
        QMessageBox.setWindowTitle(self, "Pandora RenderSlave")

        self.addButton("Yes, I want to use this PC", QMessageBox.YesRole)
        self.addButton("No, this PC can start rendering", QMessageBox.NoRole)

        # starts a timer, which updates the remaining seconds on the messagebox
        self.t = QTimer()
        self.t.timeout.connect(self.timeoutSlot)
        self.t.start(1000)  # amount of milliseconds after which the timer is executed

    # called every second. updates the remaining time and closes if the time is 0.
    def timeoutSlot(self):
        self.seconds -= 1
        QMessageBox.setText(
            self,
            "Do you want to use this PC now? Otherwise this PC will start rendering.\n\nRendering starts in %s seconds"
            % self.seconds,
        )

        if self.seconds == 0:
            self.t.stop()
            QMessageBox.close(self)


# main class for handling rendering
class SlaveLogic(QDialog):
    def __init__(self, core):
        QDialog.__init__(self)
        self.core = core
        self.slaveLogicVersion = "v1.1.0.6"

        # define some initial variables
        self.slaveState = "idle"  # slave render status
        self.debugMode = (
            False
        )  # if slave is in debug mode, more information will be printed to the log file
        self.updateTime = (
            10
        )  # interval in seconds after which the slave checks for new render jobs or commands
        self.useRestPeriod = (
            False
        )  # restperiod defines a time in which the slave does not render
        self.startRP = 9  # start time of rest period
        self.endRP = 18  # end time of rest period
        self.maxCPU = (
            30
        )  # the CPU usage has to be lower than this value before the rendering starts. This prevents the slave from starting a render, when the PC is currently rendering locally.
        self.prerenderwaittime = 0
        self.maxTasks = 2  # maximum concurrent tasks rendering at the same time

        self.cursorCheckPos = None  # cursor position  to check if the PC is currently used
        self.parentWidget = QWidget()  # used as a parent for UIs

        self.userAsked = (
            False
        )  # defines wether the user was already asked if it is ok to start rendering
        self.interrupted = False  # holds wether the current rendering was interrupted
        self.assignedTasks = []  # stores new job assigments from the coordinator
        self.curTasks = []  # list of currently rendering tasks
        self.waitingForFiles = False
        #       self.lastConnectionTime = time.time()
        #       self.connectionTimeout = 15

        cData = {}
        cData["localMode"] = ["globals", "localMode"]
        cData["repositoryPath"] = ["globals", "repositoryPath"]
        cData["rootPath"] = ["globals", "rootPath"]
        cData["slavePath"] = ["slave", "slavePath"]
        cData = self.core.getConfig(data=cData)

        if cData["localMode"] is not None:
            self.localMode = cData["localMode"]
        else:
            self.localMode = True

        if cData["repositoryPath"] is None:
            QMessageBox.warning(self, "Warning", "Pandora repository path is not defined.")
            sys.exit()
            return

        repoDir = os.path.join(cData["repositoryPath"], "Slave")
        if not os.path.exists(repoDir):
            try:
                os.makedirs(repoDir)
            except:
                pass

        if not os.path.exists(repoDir):
            try:
                os.makedirs(repoDir)
            except:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Pandora repository path doesn't exist.\n\n%s" % repoDir,
                )
                sys.exit()
                return

        self.localSlavePath = repoDir

        if self.localMode:
            if cData["rootPath"] is None:
                QMessageBox.warning(self, "Warning", "Pandora root path is not defined.")
                sys.exit()
                return

            if not os.path.exists(cData["rootPath"]):
                try:
                    os.makedirs(cData["rootPath"])
                except:
                    QMessageBox.warning(self, "Warning", "Pandora root path doesn't exist.")
                    sys.exit()
                    return

            self.slavePath = os.path.join(
                cData["rootPath"], "Slaves", "S_" + socket.gethostname()
            )
        else:
            if cData["slavePath"] is None:
                QMessageBox.warning(
                    self, "Warning", "No slave root folder specified in the Pandora config"
                )
                sys.exit()
                return
            else:
                self.slavePath = cData["slavePath"]

        self.slaveConf = os.path.join(
            self.slavePath, "slaveSettings_%s.json" % socket.gethostname()
        )  # path for the file with the RenderSlave settings
        self.slaveLog = os.path.join(
            self.slavePath, "slaveLog_%s.txt" % socket.gethostname()
        )  # path for the RenderSlave Log file
        self.slaveWarningsConf = os.path.join(
            self.slavePath, "slaveWarnings_%s.json" % socket.gethostname()
        )
        self.slaveComPath = os.path.join(
            self.slavePath, "Communication"
        )  # path where the in- and out-commands are stored

        # create the communication folder if it doesn't exist already
        if not os.path.exists(self.slaveComPath):
            try:
                os.makedirs(self.slaveComPath)
            except:
                self.writeLog(
                    "could not create Communication folder for %s" % socket.gethostname(), 2
                )

        if not os.path.exists(self.slaveWarningsConf):
            warningConfig = {"warnings": {}}

            self.setConfig(configPath=self.slaveWarningsConf, confData=warningConfig)

        # save the default slave settings to the settings file if they don't exist already
        self.createSettings(complement=True)
        self.setSlaveInfo()
        #   self.getGDrivePath()

        slaveEnabled = self.getConfSetting("enabled")
        if slaveEnabled is None:
            self.getConfSetting("enabled", setval=True, value=True)
            slaveEnabled = True
        elif slaveEnabled and self.slaveState == "disabled":
            self.setState("idle")
        elif not slaveEnabled:
            self.setState("disabled")

        self.createTrayIcon()
        self.trayIcon.show()

        showslavewindow = self.getConfSetting("showSlaveWindow")

        # display a messagebox, which informs the user, that this PC is a RenderSlave
        if showslavewindow:
            self.msgStart = QMessageBox(
                QMessageBox.Information,
                "Pandora RenderSlave",
                "<b>Please don't shut down this PC, when you leave.</b>",
                QMessageBox.Ok,
            )
            self.msgStart.setInformativeText(
                "This PC is part of a renderfarm and will start rendering, when nobody is working on it."
            )
            self.msgStart.buttons()[0].setHidden(True)
            self.msgStart.setWindowIcon(self.slaveIcon)
            self.msgStart.show()

        self.writeLog("Slave started - %s" % self.slaveLogicVersion, 1)

        self.logicTimer = QTimer()
        self.logicTimer.setSingleShot(True)
        self.logicTimer.timeout.connect(self.checkAssignments)

        self.checkAssignments()

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Pandora RenderSlave %s:\n%s\n\n%s\n%s - %s" % (
                    time.strftime("%d.%m.%y %X"),
                    args[0].slaveLogicVersion,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                    args,
                    kwargs,
                )
                args[0].writeLog(erStr, 3)
                if func == args[0].checkAssignments:
                    args[0].logicTimer.start(args[0].updateTime * 1000)

        return func_wrapper

    # creates the tray icon, which gives the user some options to control the slave
    @err_decorator
    def createTrayIcon(self):
        self.trayIconMenu = QMenu(self.parentWidget)
        self.wAction = QWidgetAction(self.parentWidget)
        self.statusLabel = QLabel("Status:\n\n\n")
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.wAction.setDefaultWidget(self.statusLabel)
        self.trayIconMenu.addAction(self.wAction)
        self.trayIconMenu.addSeparator()
        self.activateAction = QAction("Activate now", self.parentWidget)
        self.activateAction.triggered.connect(self.activateSlave)
        self.trayIconMenu.addAction(self.activateAction)
        self.pauseMenu = QMenu("Pause", self.parentWidget)
        self.pause1Action = QAction("15 min.", self.parentWidget)
        self.pause1Action.triggered.connect(lambda: self.pauseSlave(15))
        self.pauseMenu.addAction(self.pause1Action)
        self.pause2Action = QAction("1h", self.parentWidget)
        self.pause2Action.triggered.connect(lambda: self.pauseSlave(60))
        self.pauseMenu.addAction(self.pause2Action)
        self.pause3Action = QAction("3h", self.parentWidget)
        self.pause3Action.triggered.connect(lambda: self.pauseSlave(180))
        self.pauseMenu.addAction(self.pause3Action)
        self.pause4Action = QAction("6h", self.parentWidget)
        self.pause4Action.triggered.connect(lambda: self.pauseSlave(360))
        self.pauseMenu.addAction(self.pause4Action)
        self.trayIconMenu.addMenu(self.pauseMenu)
        self.enableAction = QAction(
            "Enabled",
            self.parentWidget,
            checkable=True,
            checked=self.slaveState != "disabled",
        )
        self.enableAction.triggered[bool].connect(self.setSlave)
        self.trayIconMenu.addAction(self.enableAction)
        self.restartAction = QAction(
            "Restart ", self.parentWidget, triggered=self.restartLogic
        )
        self.trayIconMenu.addAction(self.restartAction)
        self.trayIconMenu.addSeparator()
        self.folderAction = QAction(
            "Open Slave Repository",
            self.parentWidget,
            triggered=lambda: self.openFolder(self.localSlavePath),
        )
        self.trayIconMenu.addAction(self.folderAction)
        self.folderAction = QAction(
            "Open Slave Root",
            self.parentWidget,
            triggered=lambda: self.openFolder(self.slavePath),
        )
        self.trayIconMenu.addAction(self.folderAction)
        self.folderAction = QAction(
            "Show Log", self.parentWidget, triggered=lambda: self.openFolder(self.slaveLog)
        )
        self.trayIconMenu.addAction(self.folderAction)
        self.trayIconMenu.addSeparator()
        self.settingsAction = QAction(
            "Pandora Settings...", self.parentWidget, triggered=self.core.openSettings
        )
        self.trayIconMenu.addAction(self.settingsAction)
        self.trayIconMenu.addSeparator()
        self.exitAction = QAction("Exit", self.parentWidget, triggered=self.exitLogic)
        self.trayIconMenu.addAction(self.exitAction)

        self.trayIcon = QSystemTrayIcon()
        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.trayIcon.setToolTip(" Pandora RenderSlave")

        self.trayIcon.activated.connect(self.trayActivated)

        self.slaveIcon = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
        self.slaveIcon = QIcon(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "UserInterfacesPandora",
                "pandora_slave.ico",
            )
        )

        self.trayIcon.setIcon(self.slaveIcon)
        self.setWindowIcon(self.slaveIcon)

    # called when the user open the tray icon option. updates and displays the current slave status
    @err_decorator
    def trayActivated(self, reason):
        if reason == QSystemTrayIcon.Context:
            statusText = "Status:\n%s" % self.slaveState
            if self.slaveState == "paused":
                pauseMin = QDateTime.currentDateTime().secsTo(self.pauseEnd) // 60
                hourPause = pauseMin // 60
                pauseMin = pauseMin - hourPause * 60
                if hourPause > 0:
                    statusText += " (%sh %smin.)" % (hourPause, pauseMin)
                else:
                    statusText += " (%s min.)" % pauseMin

            self.enableAction.setChecked(self.slaveState != "disabled")

            statusText += "\n"
            self.statusLabel.setText(statusText)

    # called from the tray icon. Forces the slave to emmediatly check for renderjobs/commands
    @err_decorator
    def activateSlave(self):
        self.setState("idle")
        self.enableAction.setChecked(True)
        self.checkAssignments()

    # called from the tray icon. Enables/Disables the slave
    @err_decorator
    def setSlave(self, enabled):
        if enabled:
            self.setState("idle")
            self.getConfSetting("enabled", setval=True, value=True)
        else:
            self.stopRender()
            self.getConfSetting("enabled", setval=True, value=False)
            self.setState("disabled")
            self.writeLog("slave disabled", 1)

        self.checkAssignments()

    # called from the tray icon or methods. Pauses the slave
    @err_decorator
    def pauseSlave(self, duration, stop=True):
        if stop:
            self.stopRender()

        self.setState("paused")

        self.pauseEnd = QDateTime.currentDateTime().addSecs(duration * 60)

        self.enableAction.setChecked(True)
        # self.logicTimer.start(duration*60*1000)
        self.writeLog("slave paused for %s minutes" % duration, 1)

    # restarts or closes the slave
    @err_decorator
    def restartLogic(self, restart=True):
        self.stopRender()
        if hasattr(self, "msgStart") and self.msgStart.isVisible():
            self.msgStart.close()

        if restart:
            self.setState("restarting")
            self.writeLog("slave restarting", 1)
            pwExe = os.path.join(pandoraRoot, pyLibs, "Pandora Slave.exe")
            cmd = 'start "" "%s" "%s" %s' % (pwExe, os.path.abspath(__file__), "forcestart")
            self.writeLog(cmd)
            os.system(cmd)
        else:
            self.setState("shut down")

        QApplication.quit()
        sys.exit()

    # closes the slave
    @err_decorator
    def exitLogic(self):
        self.writeLog("exit slave", 1)
        self.restartLogic(restart=False)

    # used to ignore the event, when the user tries to close a messagebox with the "X"
    @err_decorator
    def ignoreEvent(self, event):
        self.writeLog("ignore event", 1)
        event.ignore()

    # writes text to a log file. A higher level means more importance.
    @err_decorator
    def writeLog(self, text, level=0, writeWarning=True):
        try:
            if not os.path.exists(self.slaveLog):
                try:
                    if not os.path.exists(os.path.dirname(self.slaveLog)):
                        os.makedirs(os.path.dirname(self.slaveLog))
                    open(self.slaveLog, "a").close()
                except:
                    return None

            if level == 0 and not self.debugMode:
                return

            elif level > 1 and writeWarning:
                self.writeWarning(text, level)

            #   print text

            with io.open(self.slaveLog, "a", encoding="utf-16") as log:
                log.write(
                    "[%s] %s : %s\n" % (level, time.strftime("%d.%m.%y %X"), text)
                )
        except:
            pass

    # writes warning to a file. A higher level means more importance.
    def writeWarning(self, text, level=1):
        if not os.path.exists(self.slaveWarningsConf):
            try:
                if not os.path.exists(os.path.dirname(self.slaveWarningsConf)):
                    os.makedirs(os.path.dirname(self.slaveWarningsConf))
                confData = {}
                result = self.setConfig(
                    configPath=self.slaveWarningsConf, confData=confData
                )
                if result:
                    self.writeLog("writeWarning %s" % result, 2, writeWarning=False)
            except:
                self.writeLog("cannot create warningConfig", 2, writeWarning=False)
                self.writeLog(text, level)
                return None

        warningConfig = self.core.getConfig(
            configPath=self.slaveWarningsConf, getConf=True, silent=True
        )
        warnings = []

        if warningConfig == "Error":
            self.writeLog("cannot read warningConfig", 2, writeWarning=False)
        else:
            if "warnings" in warningConfig:
                for i in warningConfig["warnings"]:
                    warnings.append(warningConfig["warnings"][i])

                warnings = [x for x in warnings if x[0] != text]

        warnings.insert(0, [text, time.time(), level])

        warningConfig = {"warnings": {}}
        for idx, val in enumerate(warnings):
            warningConfig["warnings"]["warning%s" % idx] = val

        result = self.setConfig(configPath=self.slaveWarningsConf, confData=warningConfig)
        if result:
            self.writeLog("writeWarning %s" % result, 2, writeWarning=False)

    # writes slave infos to file
    @err_decorator
    def setSlaveInfo(self):
        self.getConfSetting(
            "status", section="slaveinfo", setval=True, value=self.slaveState
        )

        self.getConfSetting("curtasks", section="slaveinfo", setval=True, value=self.getCurTasksData())
        self.getConfSetting(
            "cpucount", section="slaveinfo", setval=True, value=multiprocessing.cpu_count()
        )
        self.getConfSetting(
            "slaveScriptVersion",
            section="slaveinfo",
            setval=True,
            value=self.slaveLogicVersion,
        )

        process = os.popen("wmic memorychip get capacity")
        result = process.read()
        process.close()
        totalMem = 0
        for m in result.split("  \r\n")[1:-1]:
            totalMem += int(m)

        self.getConfSetting(
            "ram", section="slaveinfo", setval=True, value=(totalMem // (1024 ** 3))
        )

    # reads a slave setting from file and returns the value
    @err_decorator
    def getConfSetting(
        self, setting, section="settings", stype="string", setval=False, value=""
    ):
        if not os.path.exists(self.slaveConf):
            self.writeLog("create config", 1)
            self.createSettings()

        if setval:
            self.setConfig(section, setting, value, configPath=self.slaveConf)

            if setting == "debugMode":
                self.debugMode = value

            if setting == "cursorCheck" and value == False:
                self.cursorCheckPos = None
                if self.slaveState == "userActive":
                    self.setState("idle")
        else:
            val = self.core.getConfig(
                section, setting, configPath=self.slaveConf, silent=True
            )
            if val == "Error":
                self.writeLog(
                    "Failed to read config setting: %s %s" % (setting, section), 2
                )
                return

            return val

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
        silent=True,
    ):
        result = self.core.setConfig(
            cat=cat,
            param=param,
            val=val,
            data=data,
            configPath=configPath,
            delete=delete,
            confData=confData,
            silent=silent,
        )

        if type(result) == str and result.startswith("Error"):
            self.writeLog(result + " (Retry in 10 seconds)", 2)
            time.sleep(10)
            self.setConfig(
                cat=cat,
                param=param,
                val=val,
                data=data,
                configPath=configPath,
                delete=delete,
                confData=confData,
                silent=silent,
            )

    # shutdown this PC
    @err_decorator
    def shutdownPC(self, restart):
        self.stopRender()
        self.writeLog("restarting PC", 1)
        self.setState("restarting")

        cmd = "shutdown -t 0 -f"

        if restart:
            cmd = "shutdown -t 0 -r -f"

        os.system(cmd)

    # clears the log file
    @err_decorator
    def clearLog(self):
        try:
            open(self.slaveLog, "w").close()
            self.writeLog("SlaveLog cleared", 1)
        except:
            self.writeLog("ERROR - Could not clear log: %s" % self.slaveLog, 3)

    # starts teamviewer portable
    @err_decorator
    def startTeamviewer(self):
        self.writeLog("starting Teamviewer", 1)
        tvPath = os.path.join(pandoraRoot, "Tools", "TeamViewerPortable", "TeamViewer.exe")
        if not os.path.exists(tvPath):
            self.writeLog("WARNING - teamviewer.exe not found.", 2)
            return

        subprocess.Popen(tvPath)
        time.sleep(5)

        self.writeScreenshot()

    # makes a screenshot and save it. Usefull to get the teamviewer password
    @err_decorator
    def writeScreenshot(self):
        filename = "ScreenShot_%s.jpg" % socket.gethostname()
        img = ImageGrab.grab()
        saveas = os.path.join(self.slavePath, filename)
        img.save(saveas)

    # writes out a command to the coordinator
    @err_decorator
    def communicateOut(self, cmd):
        curNum = 1

        for i in os.listdir(self.slaveComPath):
            if not i.startswith("slaveOut_"):
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
            self.slaveComPath, "slaveOut_%s_%s.txt" % (format(curNum, "04"), time.time())
        )

        open(cmdFile, "a").close()
        with open(cmdFile, "w") as cFile:
            cFile.write(str(cmd))

        self.writeLog("communicate out: %s" % cmd, 0)

    # opens a specified folder in the windows explorer
    @err_decorator
    def openFolder(self, path):
        if os.path.exists(path):
            if os.path.isdir(path):
                subprocess.call(["explorer", path.replace("/", "\\")])
            else:
                subprocess.call(["start", "", "%s" % path.replace("/", "\\")], shell=True)

    # removes a file
    @err_decorator
    def remove(self, filepath):
        try:
            os.remove(filepath)
        except:
            self.writeLog("ERROR - cannot remove file: " % filepath, 3)

    # writes the slave settings to file
    @err_decorator
    def createSettings(self, complement=False):
        sConfig = {
            "settings": {
                "updateTime": 10,
                "restPeriod": [False, 9, 18],
                "maxCPU": 30,
                "command": "",
                "cursorCheck": False,
                "slaveGroup": [],
                "enabled": True,
                "debugMode": False,
                "connectionTimeout": 15,
                "preRenderWaitTime": 0,
                "showSlaveWindow": False,
                "showInterruptWindow": False,
                "maxConcurrentTasks": 2,
            },
            "slaveinfo": {},
        }

        if complement:
            curConfig = self.core.getConfig(
                configPath=self.slaveConf, getConf=True, silent=True
            )
            if curConfig == "Error":
                self.writeLog("Failed to read config: %s" % self.slaveConf, 2)
                curConfig = {}

            for i in sConfig:
                if i not in curConfig:
                    curConfig[i] = {}

            for i in sConfig["settings"]:
                if i not in curConfig["settings"]:
                    curConfig["settings"][i] = sConfig["settings"][i]
                    self.writeLog(
                        "complement config: %s %s" % (i, sConfig["settings"][i]), 1
                    )

            sConfig = curConfig

        self.setConfig(configPath=self.slaveConf, confData=sConfig)

    # sets the slavestate and writes it to file
    @err_decorator
    def setState(self, state):
        if self.slaveState != state:
            self.slaveState = state
            self.getConfSetting(
                "status", section="slaveinfo", setval=True, value=self.slaveState
            )

    # checks if the slave can start rendering
    @err_decorator
    def checkAssignments(self):
        self.writeLog("start checking assignments")
        self.writeActive()

        debug = self.getConfSetting("debugMode")
        if debug is None:
            self.getConfSetting("debugMode", setval=True, value=False)
            self.debugMode = False
        else:
            self.debugMode = debug

        slaveEnabled = self.getConfSetting("enabled")
        if slaveEnabled is None:
            self.getConfSetting("enabled", setval=True, value=True)
            slaveEnabled = True
        elif slaveEnabled and self.slaveState == "disabled":
            self.setState("idle")
        elif not slaveEnabled:
            self.setState("disabled")

        if not (os.path.exists(self.slavePath)):
            self.writeWarning("paths don't exist", 3)
            self.logicTimer.start(self.updateTime * 1000)
            return False

        newUTime = self.getConfSetting("updateTime")
        if newUTime is None:
            self.getConfSetting("updateTime", setval=True, value=self.updateTime)
        elif newUTime != self.updateTime:
            self.writeLog(
                "updating updateTime from %s to %s" % (self.updateTime, newUTime), 1
            )
            self.updateTime = newUTime

        self.checkCmds()
        self.checkCommandSetting()

        #       timeout = self.getConfSetting("connectionTimeout", stype="int")
        #       if timeout is None:
        #           self.getConfSetting("connectionTimeout", setval=True, value=self.connectionTimeout)
        #       else:
        #           self.connectionTimeout = timeout
        #
        #       if (time.time() - self.lastConnectionTime) > (60 * self.connectionTimeout):
        #           self.restartGDrive()
        #           self.lastConnectionTime = time.time()

        if self.slaveState != "rendering":
            self.checkForUpdates()

        if self.slaveState == "userActive":
            cresult = self.checkCursor()
            if cresult > 0:
                self.logicTimer.start(cresult * 1000)
                return False

        if self.checkRest():
            if self.slaveState == "idle":
                self.setState("rest")
        elif self.slaveState == "rest":
            self.setState("idle")

        if self.slaveState == "paused" and QDateTime.currentDateTime() > self.pauseEnd:
            self.writeLog("Pause ended. Changed slavestate to idle.")
            self.setState("idle")

        if slaveEnabled and len(self.assignedTasks) > 0:
            for task in self.assignedTasks:
                rcheck = self.preRenderCheck()
                if not rcheck[0]:
                    self.writeLog("preRenderCheck not passed")
                    if rcheck[1] > 0:
                        self.logicTimer.start(rcheck[1] * 1000)
                    return

                self.startRenderJob(task)

        if self.cursorCheckPos is None:
            if not self.waitingForFiles:
                for i in self.assignedTasks:
                    for task in self.curTasks:
                        if not (i["name"] == task["jobname"] and i["task"] == task["taskname"]):
                            self.writeLog(
                                "giving back assignment of %s from job %s"
                                % (i["task"], i["name"])
                            )
                            self.communicateOut(
                                ["taskUpdate", i["code"], i["task"], "ready", "", "", ""]
                            )
                self.assignedTasks = []

        if self.slaveState != "idle":
            self.logicTimer.start(self.updateTime * 1000)
            return

        if self.waitingForFiles:
            #           self.writeLog("DEBUG - waiting for files")
            self.logicTimer.start(30 * 1000)
            return

        self.writeLog("no task assigned")
        if hasattr(self, "msg") and self.msg.isVisible():
            self.msg.closeEvent = self.msg.origCloseEvent
            self.msg.close()

        self.userAsked = False

        self.logicTimer.start(self.updateTime * 1000)

    # tells the server that this slave is currently running
    @err_decorator
    def writeActive(self):
        slaveActive = (
            self.slavePath + "\\slaveActive_%s" % socket.gethostname()
        )  # path for the RenderSlave active file. The modifing date is used to tell wether the slave is running

        if (
            os.path.exists(slaveActive)
            and float(os.stat(slaveActive).st_size / 1024.0) > 10
        ):
            open(slaveActive, "w").close()

        with open(slaveActive, "a") as actFile:
            actFile.write(" ")

    # open a questionbox, which asks the user if this PC should start rendering.
    @err_decorator
    def openActiveQuestion(self):
        if hasattr(self, "questionMsg") and self.questionMsg.isVisible():
            self.writeLog("Question window is already open")
            return 0

        if self.getConfSetting("preRenderWaitTime") is None:
            self.getConfSetting(
                "preRenderWaitTime", setval=True, value=self.prerenderwaittime
            )
        else:
            self.prerenderwaittime = self.getConfSetting("preRenderWaitTime")

        if self.prerenderwaittime <= 0:
            return 1

        self.writeLog("open Question window")

        self.questionMsg = counterMessageBox(self.prerenderwaittime)
        self.questionMsg.setWindowIcon(self.slaveIcon)
        self.questionMsg.setWindowFlags(
            self.questionMsg.windowFlags() | Qt.WindowStaysOnTopHint
        )
        result = self.questionMsg.exec_()

        if result == 0:
            self.writeLog("User pressed active button - slave paused for 60 min", 1)
            if hasattr(self, "msg") and self.msg.isVisible():
                self.msg.closeEvent = self.msg.origCloseEvent
                self.msg.close()

            for task in self.curTasks:
                self.communicateOut(
                    ["taskUpdate", task["jobcode"], task["taskname"], "ready", "", "", ""]
                )
            self.pauseSlave(60)

        return result

    # evaluates the command parameter in the settings file
    @err_decorator
    def checkCommandSetting(self):
        val = self.getConfSetting("command")
        self.getConfSetting("command", setval=True)
        if val is not None and val != "":
            self.writeLog("checkCommands - execute: %s" % val, 1)
            try:
                exec(val)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR - checkCommandSetting - %s - %s - %s - %s"
                    % (val, str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )

    # evaluates command files in the communication folder
    @err_decorator
    def checkCmds(self):
        if not os.path.exists(self.slaveComPath):
            self.writeWarning("Communication path does not exist", 2)
            self.logicTimer.start(self.updateTime * 1000)
            return False

        for i in sorted(os.listdir(self.slaveComPath)):
            if not i.startswith("slaveIn_"):
                continue

            cmFile = os.path.join(self.slaveComPath, i)
            with open(cmFile, "r") as comFile:
                cmdText = comFile.read()

            command = None
            try:
                command = eval(cmdText)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR - checkCmds - %s - %s - %s"
                    % (str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )

            self.handleCmd(command, cmFile)

            #           self.lastConnectionTime = time.time()

            self.remove(cmFile)

    # handles different types of commands
    @err_decorator
    def handleCmd(self, command, cmFile):
        self.writeLog("handle cmd: %s" % command)

        if command is not None and type(command) == list:
            if command[0] == "clearLog":
                self.clearLog()

            elif command[0] == "setSetting":
                settingName = command[1]
                settingVal = command[2]

                section = "settings"

                if not os.path.exists(self.slaveConf):
                    self.writeLog("ERROR - handle cmd - slaveConfig doesn't exist.", 2)
                    return

                self.getConfSetting(settingName, setval=True, value=settingVal)

                self.writeLog("set config setting - %s: %s" % (settingName, settingVal), 1)

            elif command[0] == "renderTask":
                if time.time() - os.path.getmtime(cmFile) < 60 * 15:
                    self.assignedTasks.append(
                        {"code": command[1], "name": command[2], "task": command[3]}
                    )
                else:
                    self.communicateOut(
                        ["taskUpdate", command[1], command[3], "ready", "", "", ""]
                    )
                    self.writeLog(
                        "render job expired - %s: %s" % (command[1], command[2]), 1
                    )

            elif command[0] == "cancelTask":
                cJobCode = command[1]
                cTaskNum = command[2]

                self.assignedTasks = [
                    x
                    for x in self.assignedTasks
                    if not (x["code"] == cJobCode and x["task"] == cTaskNum)
                ]

                for task in self.curTasks:
                    if task["jobcode"] == cJobCode and task["taskname"] == cTaskNum:
                        self.writeLog(
                            "cancel task command recieved: %s - %s" % (cJobCode, cTaskNum), 1
                        )
                        self.stopRender(tasks=[task])

            elif command[0] == "deleteWarning":
                warnText = command[1]
                warnTime = command[2]

                if not os.path.exists(self.slaveWarningsConf):
                    self.writeLog(
                        "ERROR - handle cmd - slave warningfile doesn't exist.", 2
                    )
                    return None

                warningConfig = self.core.getConfig(
                    configPath=self.slaveWarningsConf, getConf=True, silent=True
                )
                if warningConfig == "Error":
                    self.writeLog("Failed to read config: %s" % self.slaveWarningsConf, 2)
                    warningConfig = {}

                warnings = []
                if "warnings" in warningConfig:
                    for i in warningConfig["warnings"]:
                        warnings.append(warningConfig["warnings"][i])

                    warnPrev = len(warnings)
                    warnings = [
                        x for x in warnings if not (x[0] == warnText and x[1] == warnTime)
                    ]

                    if warnPrev != len(warnings):
                        self.writeLog("warning deleted", 1)

                warningConfig = {"warnings": {}}
                for idx, val in enumerate(warnings):
                    warningConfig["warnings"]["warning%s" % idx] = val

                self.setConfig(configPath=self.slaveWarningsConf, confData=warningConfig)
            elif command[0] == "clearWarnings":
                if not os.path.exists(self.slaveWarningsConf):
                    self.writeLog(
                        "ERROR - handle cmd - slave warningfile doesn't exist.", 2
                    )
                    return None

                warnData = {"warnings": {}}
                self.setConfig(configPath=self.slaveWarningsConf, confData=warnData)
            elif command[0] == "deleteJob":
                jobCode = command[1]
                jobName = command[1]

                jobPath = os.path.join(self.localSlavePath, "Jobs", jobCode)
                jobConf = os.path.join(jobPath, "PandoraJob.json")

                if os.path.exists(jobConf):
                    cData = {}
                    cData["jobName"] = ["information", "jobName"]
                    cData = self.core.getConfig(data=cData, configPath=jobConf, silent=True)
                    if cData == "Error":
                        self.writeLog("Failed to read config: %s" % jobConf, 2)
                    else:
                        if cData["jobName"] is not None:
                            jobName = cData["jobName"]

                if os.path.exists(jobPath):
                    shutil.rmtree(jobPath)
                    self.writeLog("deleted local job %s" % (jobName), 1)
                else:
                    self.writeLog("job %s did not exist before deletion" % (jobName), 0)

            elif command[0] == "checkConnection":
                pass
            elif command[0] == "exitSlave":
                self.remove(cmFile)
                self.exitLogic()
            else:
                self.writeLog("unknown command: %s" % command, 1)

    # checks wether this PC is allowed to start rendering
    @err_decorator
    def preRenderCheck(self):
        # enabled/paused
        if self.slaveState == "disabled":
            self.writeLog("slave is disabled", 1)
            return [False, 0]
        elif self.slaveState == "paused":
            if QDateTime.currentDateTime() < self.pauseEnd:
                return [False, self.updateTime]

        # still rendering
        if self.slaveState == "rendering":
            concurrent = []
            for task in self.curTasks:
                concurrent.append(task.get("concurrentTasks", 1))

            self.maxTasks = self.getConfSetting("maxConcurrentTasks")
            if not self.maxTasks:
                self.getConfSetting("maxConcurrentTasks", setval=True, value=self.maxTasks)
                self.maxTasks = self.getConfSetting("maxConcurrentTasks")
            self.writeLog(self.maxTasks, 2)

            if len(concurrent) >= min(concurrent) or len(concurrent) >= self.maxTasks:
                self.writeLog("maximum concurrent tasks reached")
                return [False, self.updateTime]

        # restperiod
        if self.checkRest():
            self.setState("rest")
            self.writeLog("slave in rest period")
            return [False, self.updateTime]

        # max CPU usage
        if self.getConfSetting("maxCPU") is None:
            self.getConfSetting("maxCPU", setval=True, value=self.maxCPU)
        else:
            self.maxCPU = self.getConfSetting("maxCPU")

        response = psutil.cpu_percent(interval=1)
        try:
            if response > self.maxCPU:
                self.writeLog("processor usage is over %s%%" % self.maxCPU, 1)
                return [False, self.updateTime]
        except:
            self.writeLog("unable to measure processor usage. %s" % response, 2)

        # cursor check
        cresult = self.checkCursor()
        if cresult > 0:
            return [False, cresult]

        return [True]

    # checks if the rest period is active
    @err_decorator
    def checkRest(self):
        restData = self.getConfSetting("restPeriod")
        if restData is None:
            self.getConfSetting(
                "restPeriod",
                setval=True,
                value=[self.useRestPeriod, self.startRP, self.endRP],
            )
        else:
            try:
                self.useRestPeriod = restData[0]
                self.startRP = restData[1]
                self.endRP = restData[2]
            except:
                self.writeLog("unable to read rest period: %s" % restData, 2)

        restActive = self.useRestPeriod and int(time.strftime("%H")) in range(
            self.startRP, self.endRP
        )
        return restActive

    # checks if the pc is beeing used by comparing the cursor position over time
    @err_decorator
    def checkCursor(self):
        if self.getConfSetting("cursorCheck"):
            self.writeLog("startCursorCheck")
            if self.cursorCheckPos is None:
                self.cursorCheckPos = QCursor.pos()
                return 15

            self.userMovedMouse = not (
                self.cursorCheckPos.x() == QCursor.pos().x()
                and self.cursorCheckPos.y() == QCursor.pos().y()
            )
            if self.userMovedMouse:
                level = 1
                self.writeLog(
                    "cursorCheck positions: [%s, %s] - [%s, %s]"
                    % (
                        self.cursorCheckPos.x(),
                        self.cursorCheckPos.y(),
                        QCursor.pos().x(),
                        QCursor.pos().y(),
                    ),
                    0,
                )
            else:
                level = 0

            self.cursorCheckPos = None

            self.writeLog("endcursorCheck - User active: %s" % self.userMovedMouse, level)
            if self.userMovedMouse:
                self.setState("userActive")
                return self.updateTime
            else:
                self.setState("idle")
        elif self.slaveState == "userActive":
            self.setState("idle")

        return 0

    # starts a render job
    @err_decorator
    def startRenderJob(self, command):
        jobCode = command["code"]
        jobName = command["name"]
        taskName = command["task"]

        if self.interrupted:
            self.interrupted = False

        localPath = os.path.join(self.localSlavePath, "Jobs", jobCode, "JobFiles")
        jobPath = os.path.join(self.slavePath, "AssignedJobs", jobCode, "JobFiles")

        jobConf = os.path.join(os.path.dirname(jobPath), "PandoraJob.json")
        if not os.path.exists(jobConf):
            self.writeLog("Warning - JobConfig does not exist %s" % jobCode, 2)
            return

        jobConfig = self.core.getConfig(configPath=jobConf, getConf=True, silent=True)
        if jobConfig == "Error":
            self.writeLog("Warning - Failed to read config: %s" % jobConf, 2)
            return

        jobData = {}
        if "jobglobals" in jobConfig:
            for k in jobConfig["jobglobals"]:
                jobData[k] = jobConfig["jobglobals"][k]

        if "information" in jobConfig:
            for k in jobConfig["information"]:
                jobData[k] = jobConfig["information"][k]

        if taskName in jobConfig["jobtasks"]:
            tData = jobConfig["jobtasks"][taskName]
        else:
            self.writeLog("could not find assigned task", 2)
            return

        if "jobName" in jobData:
            jobName = jobData["jobName"]
        else:
            self.writeLog("Warning - No jobName in %s config" % jobCode, 2)
            return True

        if "sceneName" in jobData:
            sceneName = jobData["sceneName"]
        else:
            self.writeLog("Warning - No sceneName in %s config" % jobName, 2)
            return True

        if "program" not in jobData:
            self.writeLog("Warning - No program is defined in %s config" % jobName, 2)
            return True

        if "projectName" not in jobData:
            self.writeLog("Warning - No Projectname is defined in %s config" % jobName, 2)
            return True

        if "outputFolder" not in jobData:
            self.writeLog("Warning - No OutputFolder is defined in %s config" % jobName, 2)
            return True

        if "jobDependecies" in jobData:
            depsFinished = [True]
            for jDep in jobData["jobDependecies"]:
                if len(jDep) == 2:
                    depName = jDep[0]
                    if self.localMode:
                        depConf = os.path.join(
                            os.path.join(
                                self.localSlavePath, "Jobs", depName, "PandoraJob.json"
                            )
                        )
                        if not os.path.exists(depConf):
                            self.writeLog(
                                "Warning - dependent JobConfig does not exist %s" % depConf,
                                2,
                            )
                            return

                        depOutPath = self.core.getConfig(
                            "information", "outputPath", configPath=depConf, silent=True
                        )
                        if depOutPath == "Error":
                            self.writeLog(
                                "Warning - Failed to read config: %s" % depConf, 2
                            )
                            return

                        if depOutPath is not None and depOutPath != "":
                            depPath = os.path.dirname(depOutPath)
                        else:
                            return
                    else:
                        depPath = os.path.join(
                            os.path.join(self.localSlavePath, "RenderOutput", depName)
                        )

                    if not os.path.exists(depPath):
                        self.writeLog(
                            "Warning - For job %s the dependent job %s is missing."
                            % (jobName, depName),
                            2,
                        )
                        return True

        sceneFile = os.path.join(localPath, sceneName)
        self.waitingForFiles = False

        if "fileCount" in jobData:
            expNum = int(jobData["fileCount"])

            if "projectAssets" in jobData:
                passets = jobData["projectAssets"][1:]
                pName = jobData["projectName"]
                paFolder = os.path.join(self.slavePath, "ProjectAssets", pName)

                epAssets = []
                for m in passets:
                    aPath = os.path.join(paFolder, m[0])

                    if not os.path.exists(aPath) or int(os.path.getmtime(aPath)) != int(
                        m[1]
                    ):
                        self.writeLog("Project asset missing or outdated: %s" % (aPath))
                        continue

                    epAssets.append(aPath)

                expNum -= len(epAssets)

            if os.path.exists(jobPath):
                curNum = len(os.listdir(jobPath))
            else:
                curNum = 0

            if curNum < expNum:
                self.writeLog(
                    "Not all required files are already available. %s %s from %s"
                    % (sceneName, curNum, expNum),
                    1,
                )
                self.waitingForFiles = True
                return

        taskData = {
            "jobcode": jobCode,
            "jobname": jobName,
            "taskname": taskName,
            "scenefile": sceneFile,
            "taskStartframe": tData[0],
            "taskEndframe": tData[1],
        }
        taskData.update(jobData)
        self.curTasks.append(taskData)

        if not self.userAsked:
            result = self.openActiveQuestion()
            if result == 0:
                return True

        showinterruptwindow = self.getConfSetting("showInterruptWindow")
        if self.getConfSetting("showInterruptWindow") is None:
            self.getConfSetting("showInterruptWindow", setval=True, value=False)
        else:
            showinterruptwindow = self.getConfSetting("showInterruptWindow")

        if showinterruptwindow and not (hasattr(self, "msg") and self.msg.isVisible()):
            self.msg = QMessageBox(
                QMessageBox.Information,
                "Pandora RenderSlave",
                "Press OK to interrupt the current rendering.",
            )
            bugButton = self.msg.addButton("bug", QMessageBox.RejectRole)
            self.msg.addButton("OK", QMessageBox.AcceptRole)
            self.msg.accepted.connect(lambda: self.stopRender(msgPressed=True))
            self.msg.setModal(True)
            self.msg.setWindowIcon(self.slaveIcon)
            self.msg.origCloseEvent = self.msg.closeEvent
            self.msg.closeEvent = self.ignoreEvent
            self.msg.setWindowFlags(self.msg.windowFlags() | Qt.WindowStaysOnTopHint)
            bugButton.setVisible(False)
            self.msg.show()

        if not os.path.exists(localPath):
            shutil.copytree(
                os.path.join(self.slavePath, "AssignedJobs", jobCode),
                os.path.dirname(localPath),
            )

        if "projectAssets" in taskData:
            for k in epAssets:
                local_asset = os.path.join(localPath, os.path.basename(k))
                if os.path.exists(local_asset) and os.path.getmtime(k) == os.path.getmtime(
                    local_asset
                ):
                    continue

                try:
                    shutil.copy2(k, localPath)
                    self.writeLog("copy asset to slave repository: %s" % k)
                except:
                    self.writeLog(
                        "Could not copy file to Job folder: %s %s %s"
                        % (taskData["projectName"], k, jobName),
                        2,
                    )

        if self.localMode:
            basePath = taskData["outputFolder"]
        else:
            basePath = os.path.join(
                self.localSlavePath, "RenderOutput", taskData["jobcode"]
            )

        fileNum = 0
        for i in os.walk(basePath):
            for k in i[2]:
                fileNum += 1

        taskData["existingOutputFileNum"] = fileNum
        self.taskStartTime = time.time()

        self.setState("rendering")
        self.getConfSetting(
            "curtasks",
            section="slaveinfo",
            setval=True,
            value=self.getCurTasksData(),
        )

        self.communicateOut(
            ["taskUpdate", jobCode, taskName, self.slaveState, "", self.taskStartTime, ""]
        )

        self.assignedTasks = [
            x
            for x in self.assignedTasks
            if not (x["code"] == jobCode and x["task"] == taskName)
        ]

        self.userAsked = True
        self.taskFailed = False

        self.writeLog("starting %s from job %s" % (taskName, jobName), 1)

        dccPlugin = self.core.getPlugin(taskData["program"])

        if dccPlugin is not None:
            result = dccPlugin.startJob(self, jobData=taskData)
        else:
            self.writeLog("unknown scene type: %s" % os.path.splitext(sceneName)[1], 2)
            self.renderingFailed(task=taskData)
            self.setState("idle")

        return True

    @err_decorator
    def getCurTasksData(self):
        curTasksData = []
        for task in self.curTasks:
            data = {
                "jobname": task["jobname"],
                "jobcode": task["jobcode"],
                "taskname": task["taskname"],
            }
            curTasksData.append(data)

        return curTasksData

    # stops any renderjob if there is one active
    @err_decorator
    def stopRender(self, tasks=None, msgPressed=False):
        self.userAsked = False
        self.interrupted = True
        self.cursorCheckPos = None

        if not tasks:
            tasks = self.curTasks

        for task in tasks:
            try:
                proc = psutil.Process(task["renderProc"].pid)
                for child in proc.children():
                    child.kill()
                proc.kill()
            except:
                self.interrupted = False

        if hasattr(self, "msg") and self.msg.isVisible():
            self.msg.closeEvent = self.msg.origCloseEvent
            self.msg.close()

        if hasattr(self, "questionMsg") and self.questionMsg.isVisible():
            self.questionMsg.close()

        if self.slaveState == "rendering":
            self.setState("idle")

        self.writeLog("stopRender - msgPressed = %s" % msgPressed, 1)

        if msgPressed:
            self.pauseSlave(60, stop=False)

    # check for newer script versions
    @err_decorator
    def checkForUpdates(self):
        # logic update
        latestFile = (
            self.slavePath + "\\Scripts\\%s\\PandoraSlave.py" % socket.gethostname()
        )
        if not os.path.exists(latestFile):
            latestFile = os.path.join(
                os.path.dirname(os.path.dirname(latestFile)), os.path.basename(latestFile)
            )

        if os.path.exists(latestFile):
            curFileDate = int(os.path.getmtime(os.path.abspath(__file__)))
            latestFileDate = int(os.path.getmtime(latestFile))

            if curFileDate < latestFileDate:
                self.writeLog("restart for updating", 1)
                shutil.copy2(latestFile, os.path.abspath(__file__))
                self.restartLogic()
            elif curFileDate > latestFileDate:
                self.writeWarning("local PandoraSlave.py is newer than the global", 2)

        # startHouJob update
        latestFile = (
            self.slavePath + "\\Scripts\\%s\\PandoraStartHouJob.py" % socket.gethostname()
        )
        if not os.path.exists(latestFile):
            latestFile = os.path.join(
                os.path.dirname(os.path.dirname(latestFile)), os.path.basename(latestFile)
            )

        curFile = os.path.dirname(os.path.abspath(__file__)) + "\\PandoraStartHouJob.py"
        if os.path.exists(curFile):
            curFileDate = int(os.path.getmtime(curFile))
        else:
            curFileDate = 0

        if os.path.exists(latestFile):
            latestFileDate = int(os.path.getmtime(latestFile))

            if curFileDate < latestFileDate:
                self.writeLog("updating 'PandoraStartHouJob.py'", 1)
                try:
                    shutil.copy2(latestFile, curFile)
                except:
                    pass

            elif curFileDate > latestFileDate:
                self.writeWarning("local PandoraStartHouJob.py is newer than the global", 2)

        # zip Pandora update
        latestFile = (
            self.slavePath + "\\Scripts\\%s\\Pandora-development.zip" % socket.gethostname()
        )
        if not os.path.exists(latestFile):
            latestFile = os.path.join(
                os.path.dirname(os.path.dirname(latestFile)), os.path.basename(latestFile)
            )

        if os.path.exists(latestFile):
            targetdir = os.path.join(
                os.environ["temp"], "PandoraSlaveUpdate", "Pandora_update.zip"
            )

            if not os.path.exists(os.path.dirname(targetdir)):
                try:
                    os.makedirs(os.path.dirname(targetdir))
                except:
                    self.writeLog("could not create PandoraUpdate folder", 2)
                    return

            shutil.move(latestFile, targetdir)

            self.writeLog("restart for Pandora update", 1)
            self.stopRender()
            self.core.updatePandora(filepath=targetdir, silent=True, startSlave=True)

    # start the thread for the rendering process
    @err_decorator
    def startRenderThread(self, pOpenArgs, jData, prog, decode=False):
        def runInThread(popenArgs, jobData, prog, decode):
            try:
                self.writeLog("call " + prog, 1)
                self.writeLog(popenArgs, 0)
                jobData["renderProc"] = subprocess.Popen(
                    popenArgs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True
                )

                def readStdout(jobData, prog, decode):
                    try:
                        for line in iter(jobData["renderProc"].stdout.readline, ""):
                            if decode:
                                line = line.replace("\x00", "")

                            if line in ["", "\n"]:
                                continue

                            if "Error" in line or "ERROR" in line or "error" in line:
                                logLevel = 2
                            else:
                                logLevel = 1

                                # reduce blender logdata
                                if (
                                    prog == "blender"
                                    and line.startswith("Fra:")
                                    and " | Time:" in line in line
                                ):
                                    continue

                            self.writeLog(line.strip(), logLevel)

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        self.writeLog(
                            "ERROR - readStdout - %s - %s - %s"
                            % (str(e), exc_type, exc_tb.tb_lineno),
                            3,
                        )

                def readStderr(jobData, prog, decode):
                    try:
                        for line in iter(jobData["renderProc"].stderr.readline, ""):
                            if decode:
                                line = line.replace("\x00", "")

                            line = line.strip()

                            if line == "" or (
                                prog == "maya"
                                and line.startswith('Starting "')
                                and line.endswith('mayabatch.exe"')
                            ):
                                continue

                            line = "stderr - " + line

                            if prog == "max":
                                self.writeLog(line, 2)
                            elif prog == "maya":
                                if (
                                    " (kInvalidParameter): No element at given index"
                                    in line
                                ):
                                    self.writeLog(line, 1)
                                else:
                                    self.writeLog(line, 2)
                            elif prog == "houdini":
                                if "Unable to load HFS OpenCL platform." in line:
                                    self.writeLog(line, 1)
                                else:
                                    self.writeLog(line, 2)
                            elif prog == "blender":
                                if (
                                    (
                                        "AL lib: (EE) UpdateDeviceParams: Failed to set 44100hz, got 48000hz instead"
                                        in line
                                    )
                                    or ("Could not open" in line)
                                    or ("Unable to open" in line)
                                    or (
                                        "Warning: edge " in line
                                        and "appears twice, correcting" in line
                                    )
                                ):
                                    self.writeLog(line, 1)
                                else:
                                    self.writeLog(line, 2)
                            else:
                                self.writeLog(line, 3)
                                self.taskFailed = True

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        self.writeLog(
                            "ERROR - readStderr - %s - %s - %s"
                            % (str(e), exc_type, exc_tb.tb_lineno),
                            3,
                        )

                rothread = threading.Thread(target=readStdout, args=(jobData, prog, decode))
                rothread.start()
                rethread = threading.Thread(target=readStderr, args=(jobData, prog, decode))
                rethread.start()

                jobData["renderProc"].wait()
                #   self.writeLog(jobData["renderProc"].communicate()[0].decode('utf-16'))
                self.finishedJob(jobData)
                return

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.writeLog(
                    "ERROR - runInThread - %s - %s - %s"
                    % (str(e), exc_type, exc_tb.tb_lineno),
                    3,
                )
                self.renderingFailed(task=jobData)

        thread = threading.Thread(target=runInThread, args=(pOpenArgs, jData, prog, decode))
        thread.start()

        self.writeLog("thread started", 0)

    # called when a renderjob is finished. Evaluates the result.
    @err_decorator
    def finishedJob(self, task):
        if self.localMode:
            basePath = task["outputFolder"]
        else:
            basePath = os.path.join(
                self.localSlavePath, "RenderOutput", task["jobcode"]
            )

        syncPath = os.path.join(self.slavePath, "Output", task["jobcode"])

        hasNewOutput = False
        fileNum = 0
        for i in os.walk(basePath):
            for k in i[2]:
                fpath = os.path.join(i[0], k)
                if int(os.path.getmtime(fpath)) > self.taskStartTime:
                    hasNewOutput = True
                fileNum += 1

        if fileNum > task["existingOutputFileNum"]:
            hasNewOutput = True

        if self.interrupted:
            self.writeLog(
                "rendering interrupted - %s - %s" % (task["taskname"], task["jobname"]), 2
            )
        elif self.taskFailed:
            self.writeLog(
                "rendering failed - %s - %s" % (task["taskname"], task["jobname"]), 3
            )
        elif not hasNewOutput:
            self.writeLog(
                "rendering didn't produce any output - %s - %s"
                % (task["taskname"], task["jobname"]),
                3,
            )
        else:
            self.writeLog(
                "rendering finished - %s - %s" % (task["taskname"], task["jobname"]), 1
            )

        if (
            hasNewOutput
            and not self.localMode
            and "uploadOutput" in task
            and task["uploadOutput"]
        ):
            for i in os.walk(basePath):
                for k in i[2]:
                    if k.endswith(".exr.lock"):
                        continue

                    filePath = os.path.join(i[0], k)
                    targetPath = filePath.replace(basePath, syncPath)

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
                                self.writeLog("could not create upload folder", 2)
                                folderExists = False

                        if folderExists:
                            try:
                                shutil.copy2(filePath, targetPath)
                            except Exception as e:
                                self.writeLog(
                                    "ERROR occured while copying files %s %s %s"
                                    % (e, filePath, targetPath),
                                    3,
                                )

            self.writeLog("uploading files", 1)

        if self.interrupted:
            self.communicateOut(
                ["taskUpdate", task["jobcode"], task["taskname"], "ready", "", "", ""]
            )
            self.interrupted = False
        else:
            elapsed = time.time() - self.taskStartTime
            hours = int(elapsed / 3600)
            elapsed = elapsed - (hours * 3600)
            minutes = int(elapsed / 60)
            elapsed = elapsed - (minutes * 60)
            seconds = int(elapsed)
            taskTime = "%s:%s:%s" % (
                format(hours, "02"),
                format(minutes, "02"),
                format(seconds, "02"),
            )

            outputNum = -1
            if self.taskFailed or not hasNewOutput:
                status = "error"
                taskResult = "failed"
            else:
                status = "finished"
                taskResult = "completed"

                outputNum = 0
                for i in os.walk(syncPath):
                    outputNum += len(i[2])

                    for k in i[2]:
                        if os.path.splitext(k)[1] not in [
                            ".exr",
                            "jpg",
                            ".png",
                            ".bgeo",
                            ".abc",
                            ".tif",
                            ".tiff",
                            ".tga",
                        ]:
                            self.writeLog("unknown fileoutput type: %s" % (k), 2)

            cmd = [
                "taskUpdate",
                task["jobcode"],
                task["taskname"],
                status,
                taskTime,
                self.taskStartTime,
                time.time(),
                outputNum,
            ]
            self.communicateOut(cmd)

            self.setState("idle")

            self.writeLog("task " + taskResult, 1)

            if self.interrupted:
                self.interrupted = False

        if self.prerenderwaittime == 0 and hasattr(self, "msg") and self.msg.isVisible():
            self.msg.closeEvent = self.msg.origCloseEvent
            self.msg.close()

        self.curTasks = [x for x in self.curTasks if not (x["jobcode"] == task["jobcode"] and x["taskname"] == task["taskname"])]
        self.getConfSetting("curtasks", section="slaveinfo", setval=True, value=self.getCurTasksData())

    # called by the user, if he wants to upload all renderings from the current job, before the job is finished
    @err_decorator
    def uploadCurJob(self):
        for task in self.curTasks:
            uploadedFiles = 0
            syncPath = os.path.join(self.slavePath, "Output", task["jobcode"])

            basePath = os.path.join(
                self.localSlavePath,
                "RenderOutput",
                task["jobcode"],
                task["projectName"],
            )
            for i in os.walk(basePath):
                for k in i[2]:
                    filePath = os.path.join(i[0], k)
                    targetPath = filePath.replace(basePath, syncPath)
                    if not os.path.exists(targetPath):
                        folderExists = True
                        if not os.path.exists(os.path.dirname(targetPath)):
                            try:
                                os.makedirs(os.path.dirname(targetPath))
                            except:
                                self.writeLog("could not create upload folder", 2)
                                folderExists = False
                        if folderExists:
                            try:
                                shutil.copy2(filePath, targetPath)
                                uploadedFiles += 1
                            except:
                                self.writeLog("ERROR occured while copying files", 3)

            self.writeLog(
                "uploaded files from current job (%s): %s"
                % (task["jobname"], uploadedFiles),
                1,
            )

    # called when the rendering failed and writes out the error
    @err_decorator
    def renderingFailed(self, task):
        self.stopRender()
        self.communicateOut(
            ["taskUpdate", task["jobcode"], task["taskname"], "ready", "", "", ""]
        )
        self.interrupted = False
        self.curTasks = [x for x in self.curTasks if not (x["jobcode"] == task["jobcode"] and x["taskname"] == task["taskname"])]
        self.getConfSetting("curtasks", section="slaveinfo", setval=True, value=self.getCurTasksData())
        self.checkAssignments()


# true when this script is executed and not imported
if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

    # set window icon
    appIcon = QIcon(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "UserInterfacesPandora",
            "pandora_slave.ico",
        )
    )
    qapp.setWindowIcon(appIcon)
    qapp.setQuitOnLastWindowClosed(False)

    # check if already a Pandora slave process is running
    slaveProc = []
    for x in psutil.pids():
        try:
            if (
                x != os.getpid()
                and os.path.basename(psutil.Process(x).exe()) == "Pandora Slave.exe"
            ):
                slaveProc.append(x)
        except:
            pass

    if len(slaveProc) > 0:
        if sys.argv[-1] == "forcestart":
            for pid in slaveProc:
                proc = psutil.Process(pid)
                proc.kill()
        else:
            QMessageBox.warning(
                QWidget(), "Pandora RenderSlave", "Pandora RenderSlave is already running."
            )
            sys.exit()

    import PandoraCore

    pc = PandoraCore.PandoraCore()
    pc.startRenderSlave()
    sys.exit(qapp.exec_())
