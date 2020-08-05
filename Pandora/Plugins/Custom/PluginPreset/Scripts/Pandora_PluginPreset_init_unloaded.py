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


from Pandora_PluginPreset_Variables import Pandora_PluginPreset_Variables
from Pandora_PluginPreset_Functions import Pandora_PluginPreset_Functions


class Pandora_PluginPreset_unloaded(
    Pandora_PluginPreset_Variables, Pandora_PluginPreset_Functions
):
    def __init__(self, core):
        Pandora_PluginPreset_Variables.__init__(self, core, self)
        Pandora_PluginPreset_Functions.__init__(self, core, self)
