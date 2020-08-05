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


from Pandora_Blender_Variables import Pandora_Blender_Variables
from Pandora_Blender_externalAccess_Functions import (
    Pandora_Blender_externalAccess_Functions,
)
from Pandora_Blender_Functions import Pandora_Blender_Functions
from Pandora_Blender_Integration import Pandora_Blender_Integration


class Pandora_Plugin_Blender(
    Pandora_Blender_Variables,
    Pandora_Blender_externalAccess_Functions,
    Pandora_Blender_Functions,
    Pandora_Blender_Integration,
):
    def __init__(self, core):
        Pandora_Blender_Variables.__init__(self, core, self)
        Pandora_Blender_externalAccess_Functions.__init__(self, core, self)
        Pandora_Blender_Functions.__init__(self, core, self)
        Pandora_Blender_Integration.__init__(self, core, self)
