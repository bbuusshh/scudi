# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module to operate the voltage (laser) scanner.
Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.
Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
import os
import numpy as np
import copy as cp
from typing import Union, Tuple
from functools import partial
from PySide2 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

import qudi.util.uic as uic
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.interface.scanning_probe_interface import ScanData
from qudi.core.module import GuiBase
from qudi.logic.scanning_optimize_logic import OptimizerScanSequence

from qudi.gui.ple.ple_ui_window import PLEScanMainWindow


class PLEScanGui(GuiBase):
    """
    """
    
    # declare connectors
    _scanning_logic = Connector(name='scannerlogic', interface='PLEScannerLogic')


    # status vars
    _window_state = StatusVar(name='window_state', default=None)
    _window_geometry = StatusVar(name='window_geometry', default=None)

    # signals
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScanSettingsChanged = QtCore.Signal(dict)
    sigToggleScan = QtCore.Signal(bool, tuple, object)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigToggleOptimize = QtCore.Signal(bool)
    sigSaveScan = QtCore.Signal(object, object)
    sigSaveFinished = QtCore.Signal()
    sigShowSaveDialog = QtCore.Signal(bool)
# def save_view(self):
#         """Saves the current GUI state as a QbyteArray.
#            The .data() function will transform it to a bytearray, 
#            which can be saved as a StatusVar and read by the load_view method. 
#         """
#         self._save_display_view = self._mw.saveState().data() 
        

#     def load_view(self):
#         """Loads the saved state from the GUI and can read a QbyteArray
#             or a simple byteArray aswell.
#         """
#         if self._save_display_view is None:
#             pass
#         else:
#             self._mw.restoreState(self._save_display_view)
    def on_deactivate(self):
        """ Reverse steps of activation
        @return int: error code (0:OK, -1:error)
        """
        self._save_window_geometry(self._mw)
        self._mw.close()
        self.sigScannerTargetChanged.disconnect()
        self.sigScanSettingsChanged.disconnect()
        self.sigToggleScan.disconnect()
        self.sigToggleOptimize.disconnect()
        return 0

    def on_activate(self):
        """ 
        """
        self._mw = PLEScanMainWindow()
        self._mw.show()

        # Connect signals
        self.sigScannerTargetChanged.connect(
            self._scanning_logic().set_target_position, QtCore.Qt.QueuedConnection
        )
        self.sigScanSettingsChanged.connect(
            self._scanning_logic().set_scan_settings, QtCore.Qt.QueuedConnection
        )
        self.sigToggleScan.connect(self._scanning_logic().toggle_scan, QtCore.Qt.QueuedConnection)
        # self.sigToggleOptimize.connect(
        #     self._optimize_logic().toggle_optimize, QtCore.Qt.QueuedConnection
        # )

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def run_stop(self, is_checked):
        """ Manages what happens if scan is started/stopped """
        self._mw.action_run_stop.setEnabled(False)
        if is_checked:
            pass

    def scan_started(self):
        self._mw.action_run_stop.setEnabled(True)

    def scan_stopped(self):
        self._mw.action_run_stop.setEnabled(True)
        self._mw.action_run_stop.setChecked(False)
