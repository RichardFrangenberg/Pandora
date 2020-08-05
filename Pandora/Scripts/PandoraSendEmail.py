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
import sys
import traceback

prismRoot = sys.argv[-4]
pyLibs = sys.argv[-3]
subject = sys.argv[-2]
message = sys.argv[-1]

try:
    pyLibPath = os.path.join(prismRoot, 'PythonLibs', pyLibs)
    if pyLibPath not in sys.path:
        sys.path.insert(0, pyLibPath)

    pyLibPath = os.path.join(prismRoot, 'PythonLibs', 'CrossPlatform')
    if pyLibPath not in sys.path:
        sys.path.insert(0, pyLibPath)

    import requests
    url = "https://prism-pipeline.com/wp-json/contact-form-7/v1/contact-forms/1042/feedback"
    form = {
        "your-name": (None, "PrismMessage"),
        "your-subject": (None, subject),
        "your-message": (None, message),
    }

    response = requests.post(url, files=form)

    if 'Thank you for your message. It has been sent.' in response.text:
        sys.stdout.write('success')
    else:
        sys.stdout.write('failed')
except:
    sys.stdout.write('failed %s' % traceback.format_exc())
