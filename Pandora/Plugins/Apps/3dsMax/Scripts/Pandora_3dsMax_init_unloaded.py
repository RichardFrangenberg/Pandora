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


from Pandora_3dsMax_Variables import Pandora_3dsMax_Variables
from Pandora_3dsMax_externalAccess_Functions import Pandora_3dsMax_externalAccess_Functions
from Pandora_3dsMax_Integration import Pandora_3dsMax_Integration


class Pandora_3dsMax_unloaded(
    Pandora_3dsMax_Variables,
    Pandora_3dsMax_externalAccess_Functions,
    Pandora_3dsMax_Integration,
):
    def __init__(self, core):
        Pandora_3dsMax_Variables.__init__(self, core, self)
        Pandora_3dsMax_externalAccess_Functions.__init__(self, core, self)
        Pandora_3dsMax_Integration.__init__(self, core, self)
