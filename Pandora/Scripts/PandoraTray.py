# -*- coding: utf-8 -*-
#
####################################################
#
# Pandora - Renderfarm
#
# www.prism-pipeline.com
#
# contact: prismpipeline@gmail.com
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


import sys, os, subprocess, shutil, socket

if sys.version[0] == "3":
    pyLibs = "Python37"
    pVersion = 3
else:
    pyLibs = "Python27"
    pVersion = 2

pandoraRoot = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(pandoraRoot, "PythonLibs", pyLibs))
sys.path.insert(0, os.path.join(pandoraRoot, "PythonLibs", pyLibs, "PySide"))

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

import psutil

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from UserInterfacesPandora import qdarkstyle


class PandoraTray:
    def __init__(self, core, silent=False):
        self.core = core

        try:
            pIcon = QIcon(
                os.path.dirname(os.path.abspath(__file__))
                + "\\UserInterfacesPandora\\pandora_tray.ico"
            )
            self.core.messageParent.setWindowIcon(pIcon)

            #   coreProc = []
            #   for x in psutil.pids():
            #       try:
            #           if x != os.getpid() and os.path.basename(psutil.Process(x).exe()) == "Pandora Tray.exe":
            #               coreProc.append(x)
            #       except:
            #           pass

            #   if len(coreProc) > 0:
            #       if silent:
            #           for pid in coreProc:
            #               proc = psutil.Process(pid)
            #               proc.kill()
            #       else:
            #           QMessageBox.warning(self.core.messageParent, "PandoraTray", "Pandora Tray is already running.")
            #           QApplication.quit()
            #           sys.exit()
            #           return

            self.createTrayIcon()
            self.trayIcon.show()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "initTray - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def createTrayIcon(self):
        try:
            self.trayIconMenu = QMenu(self.core.messageParent)
            self.handlerAction = QAction(
                "Render Handler", self.core.messageParent, triggered=self.startRenderHandler
            )
            self.collectAction = QAction(
                "Collect renderings",
                self.core.messageParent,
                triggered=self.collectRenderings,
            )
            self.trayIconMenu.addAction(self.handlerAction)
            self.trayIconMenu.addAction(self.collectAction)
            self.trayIconMenu.addSeparator()

            self.slaveAction = QAction(
                "Start Slave",
                self.core.messageParent,
                triggered=lambda: self.core.startRenderSlave(newProc=True),
            )
            self.trayIconMenu.addAction(self.slaveAction)

            self.slaveStopAction = QAction(
                "Stop Slave", self.core.messageParent, triggered=self.core.stopRenderSlave
            )
            self.trayIconMenu.addAction(self.slaveStopAction)
            self.trayIconMenu.addSeparator()

            self.coordAction = QAction(
                "Start Coordinator",
                self.core.messageParent,
                triggered=self.core.startCoordinator,
            )
            self.trayIconMenu.addAction(self.coordAction)

            self.coordStopAction = QAction(
                "Stop Coordinator",
                self.core.messageParent,
                triggered=self.core.stopCoordinator,
            )
            self.trayIconMenu.addAction(self.coordStopAction)
            self.trayIconMenu.addSeparator()

            self.settingsAction = QAction(
                "Pandora Settings...", self.core.messageParent, triggered=self.openSettings
            )
            self.trayIconMenu.addAction(self.settingsAction)
            self.trayIconMenu.addSeparator()
            self.exitAction = QAction(
                "Exit", self.core.messageParent, triggered=self.exitTray
            )
            self.trayIconMenu.addAction(self.exitAction)

            self.trayIcon = QSystemTrayIcon()
            self.trayIcon.setContextMenu(self.trayIconMenu)
            self.trayIcon.setToolTip("Pandora Tools")

            self.icon = QIcon(
                os.path.dirname(os.path.abspath(__file__))
                + "\\UserInterfacesPandora\\pandora_tray.ico"
            )

            self.trayIcon.setIcon(self.icon)

            self.trayIcon.activated.connect(self.iconActivated)
            self.trayIconMenu.aboutToShow.connect(self.aboutToShow)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "createTray - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def iconActivated(self, reason):
        try:
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
                self.startRenderHandler()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "iconActivated - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def aboutToShow(self):
        try:
            cData = {}
            cData["localMode"] = ["globals", "localMode"]
            cData["slave"] = ["slave", "enabled"]
            cData["coordinator"] = ["coordinator", "enabled"]
            cData = self.core.getConfig(data=cData)

            if self.core.getSubmissionEnabled():
                self.handlerAction.setVisible(True)
                if cData["localMode"] == True:
                    self.collectAction.setVisible(False)
                else:
                    self.collectAction.setVisible(True)
            else:
                self.handlerAction.setVisible(False)
                self.collectAction.setVisible(False)

            if cData["slave"] == True:
                #   slaveProc = []
                #   for x in psutil.pids():
                #       try:
                #           if os.path.basename(psutil.Process(x).exe()) == "Pandora Slave.exe":
                #               slaveProc.append(x)
                #       except:
                #           pass
                #   slaveRunning = len(slaveProc) > 0

                self.slaveAction.setVisible(True)
                self.slaveStopAction.setVisible(True)
            else:
                self.slaveAction.setVisible(False)
                self.slaveStopAction.setVisible(False)

            if cData["coordinator"] == True:
                #   coordProc = []
                #   for x in psutil.pids():
                #       try:
                #           if os.path.basename(psutil.Process(x).exe()) == "Pandora Coordinator.exe":
                #               coordProc.append(x)
                #       except:
                #           pass
                #   coordRunning = len(coordProc) > 0

                self.coordAction.setVisible(True)
                self.coordStopAction.setVisible(True)
            else:
                self.coordAction.setVisible(False)
                self.coordStopAction.setVisible(False)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "iconAboutToShow - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def startRenderHandler(self):
        handlerIcon = QIcon(
            os.path.dirname(os.path.abspath(__file__))
            + "\\UserInterfacesPandora\\rh_tray.ico"
        )
        QApplication.setWindowIcon(handlerIcon)
        self.core.openRenderHandler()
        return

        # the following code starts the RenderHandler in a new process, but is a lot slower
        try:
            handlerPath = os.path.join(pandoraRoot, "Scripts", "PandoraRenderHandler.py")
            pythonPath = os.path.join(pandoraRoot, pyLibs, "Pandora Render Handler.exe")
            for i in [handlerPath, pythonPath]:
                if not os.path.exists(i):
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Script missing",
                        "%s does not exist." % os.path.basename(i),
                    )
                    return None

            command = ["%s" % pythonPath, "%s" % handlerPath]
            self.handlerProc = subprocess.Popen(command)

            PROCNAME = "Pandora Render Handler.exe"
            for proc in psutil.process_iter():
                if proc.name() == PROCNAME:
                    if proc.pid == self.handlerProc.pid:
                        continue

                    p = psutil.Process(proc.pid)
                    if not "SYSTEM" in p.username():
                        proc.kill()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "startRenderHandler - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def collectRenderings(self):
        try:
            cData = {}
            cData["localMode"] = ["globals", "localMode"]
            cData["rootPath"] = ["globals", "rootPath"]
            cData["submissionPath"] = ["submissions", "submissionPath"]
            cData = self.core.getConfig(data=cData)

            if cData["localMode"] == True:
                psPath = os.path.join(
                    cData["rootPath"], "Workstations", "WS_" + socket.gethostname()
                )
            else:
                psPath = cData["submissionPath"]

            if psPath is None or not os.path.exists(psPath):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Directory missing",
                    "Pandora submission directory doesn't exist.",
                )
                return None

            outputDir = os.path.join(psPath, "RenderOutput")

            if not os.path.exists(outputDir):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Directory missing",
                    "Pandora renderoutput directory doesn't exist.",
                )
                return None

            result = {}
            for i in os.walk(outputDir):
                for prj in i[1]:
                    for k in os.walk(os.path.join(i[0], prj)):
                        for job in k[1]:
                            jobDir = os.path.join(k[0], job)
                            confPath = os.path.join(k[0], job, "PandoraJob.json")
                            if not os.path.exists(confPath):
                                QMessageBox.warning(
                                    self.core.messageParent,
                                    "Config missing",
                                    "Job config doesn't exist. (%s)" % job,
                                )
                                continue

                            outputCount = 0
                            for i in os.walk(jobDir):
                                outputCount += len(i[2])

                            outPath = self.core.getConfig(
                                "information", "outputPath", configPath=confPath
                            )

                            if outPath is None:
                                QMessageBox.warning(
                                    self.core.messageParent,
                                    "information missing",
                                    "No outputpath is defined in job config. (%s)" % job,
                                )
                                continue

                            targetBase = os.path.dirname(os.path.dirname(outPath))

                            waitmsg = QMessageBox(
                                QMessageBox.NoIcon,
                                "Pandora - Collect Renderings",
                                "Collecting renderings - %s - please wait.." % job,
                                QMessageBox.Cancel,
                            )
                            waitmsg.setWindowIcon(self.core.messageParent.windowIcon())
                            waitmsg.buttons()[0].setHidden(True)
                            waitmsg.show()
                            QCoreApplication.processEvents()

                            copiedNum = 0
                            errors = 0

                            for o in os.walk(jobDir):
                                for m in o[2]:
                                    if m == "PandoraJob.json":
                                        continue

                                    filePath = os.path.join(o[0], m)
                                    relFilePath = filePath.replace(jobDir, "")
                                    while relFilePath.startswith(
                                        "\\"
                                    ) or relFilePath.startswith("/"):
                                        relFilePath = relFilePath[1:]
                                    targetPath = os.path.join(targetBase, relFilePath)

                                    copyFile = True

                                    if os.path.exists(targetPath):
                                        curFileDate = int(
                                            os.path.getmtime(os.path.abspath(filePath))
                                        )
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

                            result["%s - %s" % (prj, job)] = [copiedNum, errors]

                            completeCount = self.core.getConfig(
                                "information", "outputFileCount", configPath=confPath
                            )

                            if completeCount is not None:
                                if outputCount == completeCount:
                                    try:
                                        shutil.rmtree(jobDir)
                                    except:
                                        pass

                            if "waitmsg" in locals() and waitmsg.isVisible():
                                waitmsg.close()

                        break
                break

            resStr = ""

            for i in result:
                if result[i][0] == 0 and result[i][1] == 0:
                    continue

                resStr += "%s:\n" % i
                if result[i][0] > 0:
                    resStr += "%s files copied\n" % result[i][0]

                if result[i][1] > 0:
                    resStr += "%s errors\n" % result[i][1]

                resStr += "\n"

            if resStr == "":
                resStr = "No renderings to copy"

            QMessageBox.information(self.core.messageParent, "Collect renderings", resStr)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "collectRenderings - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def openSettings(self):
        handlerIcon = QIcon(
            os.path.join(
                pandoraRoot, "Scripts", "UserInterfacesPandora", "pandora_tray.ico"
            )
        )
        QApplication.setWindowIcon(handlerIcon)
        self.core.openSettings()
        return

        # the following code starts the Settings in a new process, but is a lot slower
        try:
            settingsPath = os.path.join(pandoraRoot, "Scripts", "PandoraSettings.py")
            pythonPath = os.path.join(pandoraRoot, pyLibs, "Pandora Settings.exe")
            for i in [settingsPath, pythonPath]:
                if not os.path.exists(i):
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Script missing",
                        "%s does not exist." % os.path.basename(i),
                    )
                    return None

            command = ["%s" % pythonPath, "%s" % settingsPath]

            self.settingsProc = subprocess.Popen(command)

            PROCNAME = "Pandora Settings.exe"
            for proc in psutil.process_iter():
                if proc.name() == PROCNAME:
                    if proc.pid == self.settingsProc.pid:
                        continue

                    p = psutil.Process(proc.pid)
                    if not "SYSTEM" in p.username():
                        proc.kill()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "openSettings - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def exitTray(self):
        QApplication.quit()


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "PandoraTray", "Could not launch PandoraTray.")
        sys.exit(1)

    isSilent = sys.argv[-1] == "silent"

    import PandoraCore

    pc = PandoraCore.PandoraCore()
    pc.startTray(silent=isSilent)
    sys.exit(qapp.exec_())
