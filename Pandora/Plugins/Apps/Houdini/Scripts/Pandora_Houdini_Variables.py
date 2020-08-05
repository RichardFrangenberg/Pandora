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


class Pandora_Houdini_Variables(object):
    def __init__(self, core, plugin):
        self.version = "v1.0.3.0"
        self.pluginName = "Houdini"
        self.pluginType = "App"
        self.appShortName = "Hou"
        self.appType = "3d"
        self.hasQtParent = True
        self.sceneFormats = [".hip", ".hipnc", ".hiplc"]
        self.appSpecificFormats = self.sceneFormats + [".bgeo"]
        self.appColor = [242, 103, 34]
        self.platforms = ["Windows"]
        self.executableName = "hython.exe"
        self.frameString = ".$F4"
