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
# Copyright (C) 2016-2026 Richard Frangenberg and contributors
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


"""A Pandora core without user interface.

PandoraCore needs Qt and a desktop. Render nodes often have neither, so the
renderslave can run with this core instead. It provides the parts of
PandoraCore, which the slave and the render functions of the DCC plugins use:
the configuration files and the plugins.
"""

import os
import sys
import json
import importlib

import PandoraPaths


class HeadlessCore(object):
    def __init__(self):
        self.version = "v1.2.0.0"
        self.headless = True
        self.pandoraRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self.pluginPathApp = os.path.join(self.pandoraRoot, "Plugins", "Apps")
        self.pluginPathCustom = os.path.join(self.pandoraRoot, "Plugins", "Custom")
        self.pluginDirs = [self.pluginPathApp, self.pluginPathCustom]
        self.configPath = PandoraPaths.getUserConfigPath()
        self.plugins = {}

    def writeErrorLog(self, text):
        sys.stderr.write("%s\n" % text)
        sys.stderr.flush()

    # settings, which are defined through the environment, replace the user preferences
    def getEnvConfig(self):
        overrides = PandoraPaths.getEnvOverrides()
        envConfig = {"globals": {}}
        for key in ["rootPath", "repositoryPath", "localMode"]:
            if key in overrides:
                envConfig["globals"][key] = overrides[key]

        return envConfig

    def readConfig(self, configPath):
        userConfig = {}
        if os.path.exists(configPath):
            with open(configPath, "r") as f:
                userConfig = json.load(f)

        if configPath == self.configPath:
            envConfig = self.getEnvConfig()
            for cat in envConfig:
                userConfig.setdefault(cat, {}).update(envConfig[cat])

        return userConfig

    def getConfig(
        self,
        cat=None,
        param=None,
        data=None,
        configPath=None,
        getOptions=False,
        getItems=False,
        getConf=False,
        silent=False,
    ):
        if configPath is None:
            configPath = self.configPath

        if configPath is None or configPath == "":
            return

        try:
            userConfig = self.readConfig(configPath)
        except Exception as e:
            if silent:
                return "Error"

            self.writeErrorLog("Cannot read the following file: %s (%s)" % (configPath, e))
            userConfig = {}

        if getConf:
            return userConfig

        if getOptions:
            return list(userConfig.get(cat, {}).keys())

        if getItems:
            return userConfig.get(cat, {})

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

    def setConfig(
        self,
        cat=None,
        param=None,
        val=None,
        data=None,
        configPath=None,
        delete=False,
        confData=None,
        silent=False,
    ):
        if configPath is None:
            configPath = self.configPath

        try:
            if not os.path.exists(os.path.dirname(configPath)):
                os.makedirs(os.path.dirname(configPath))

            if confData is None:
                userConfig = {}
                if os.path.exists(configPath):
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
                        if param in userConfig[cat]:
                            del userConfig[cat][param]

                        continue

                    userConfig[cat][param] = val
            else:
                userConfig = confData

            # write to a temporary file first, so that other machines never read a half written config
            tmpPath = "%s.tmp%s" % (configPath, os.getpid())
            with open(tmpPath, "w") as confFile:
                json.dump(userConfig, confFile, indent=4)

            try:
                os.replace(tmpPath, configPath)
            except Exception:
                # e.g. the file is opened by another process on Windows
                with open(configPath, "w") as confFile:
                    json.dump(userConfig, confFile, indent=4)

                os.remove(tmpPath)
        except Exception as e:
            errStr = "Error - Cannot write the following file: %s (%s)" % (configPath, e)
            if silent:
                return errStr

            self.writeErrorLog(errStr)

    def getPlugin(self, pluginName):
        """Returns the plugin of a DCC or None if it is not available on this machine."""
        if pluginName in self.plugins:
            return self.plugins[pluginName]

        plugin = None
        for pluginDir in self.pluginDirs:
            scriptDir = os.path.join(pluginDir, pluginName, "Scripts")
            if not os.path.exists(
                os.path.join(scriptDir, "Pandora_%s_init_unloaded.py" % pluginName)
            ):
                continue

            if scriptDir not in sys.path:
                sys.path.append(scriptDir)

            try:
                module = importlib.import_module("Pandora_%s_init_unloaded" % pluginName)
                plugin = getattr(module, "Pandora_%s_unloaded" % pluginName)(self)
            except Exception as e:
                self.writeErrorLog("Cannot load plugin %s: %s" % (pluginName, e))
                plugin = None

            break

        self.plugins[pluginName] = plugin
        return plugin

    def updatePandora(self, *args, **kwargs):
        self.writeErrorLog("Updating Pandora is not supported without user interface.")

    def openSettings(self, *args, **kwargs):
        pass
