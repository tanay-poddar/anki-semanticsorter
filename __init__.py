# Copyright 2026 Tanay Poddar (tanayp@ucf.edu)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 

import traceback
from aqt import mw
from aqt.qt import QAction, qconnect

from .constants import MENU_NAME
from .ui import get_inputs_and_run_sort, debug_log

try:
    action = QAction(MENU_NAME, mw)
    qconnect(action.triggered, get_inputs_and_run_sort)
    mw.form.menuTools.addAction(action)
except Exception:
    debug_log("Failed to create menu item:\n" + traceback.format_exc())
