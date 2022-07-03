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
        self._mw.actionToggle_scan.triggered.connect(self.toggle_scan, QtCore.Qt.QueuedConnection)
        
        self._scanning_logic().sigScanStateChanged.connect(
            self.scan_state_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScannerTargetChanged.connect(
            self.scanner_target_updated, QtCore.Qt.QueuedConnection
        )
        # self.sigToggleOptimize.connect(
        #     self._optimize_logic().toggle_optimize, QtCore.Qt.QueuedConnection
        # )
        # Initialize widget data
        # self.scanner_settings_updated()
        self.scanner_target_updated()
        self.scan_state_updated(self._scanning_logic().module_state() != 'idle')

    def toggle_scan(self):
        self.sigToggleScan.emit(self._mw.actionToggle_scan.isChecked(), ["a"], self.module_uuid)

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()


    @QtCore.Slot(dict)
    def set_scanner_target_position(self, target_pos):
        """
        Issues new target to logic and updates gui.

        @param dict target_pos:
        """
        if not self._scanner_settings_locked:
            self.sigScannerTargetChanged.emit(target_pos, self.module_uuid)
            # update gui with target, not actual logic values
            # we can not rely on the execution order of the above emit
            self.scanner_target_updated(pos_dict=target_pos, caller_id=None)
        else:
            # refresh gui with stored values
            self.scanner_target_updated(pos_dict=None, caller_id=None)

    def scanner_target_updated(self, pos_dict=None, caller_id=None):
        """
        Updates the scanner target and set widgets accordingly.

        @param dict pos_dict: The scanner position dict to update each axis position.
                              If None (default) read the scanner position from logic and update.
        @param int caller_id: The qudi module object id responsible for triggering this update
        """

        # If this update has been issued by this module, do not update display.
        # This has already been done before notifying the logic.
        if caller_id is self.module_uuid:
            return

        if not isinstance(pos_dict, dict):
            pos_dict = self._scanning_logic().scanner_target

        #! self._update_scan_markers(pos_dict)
        # self.scanner_control_dockwidget.set_target(pos_dict)

    @QtCore.Slot(bool, object, object)
    def scan_state_updated(self, is_running, scan_data=None, caller_id=None):
        scan_axes = scan_data.scan_axes if scan_data is not None else None
        # self._toggle_enable_scan_buttons(not is_running, exclude_scan=scan_axes)
        # if not self._optimizer_state['is_running']:
        #     self._toggle_enable_actions(not is_running)
        # else:
        #     self._toggle_enable_actions(not is_running, exclude_action=self._mw.action_optimize_position)
        # self._toggle_enable_scan_crosshairs(not is_running)
        # self.scanner_settings_toggle_gui_lock(is_running)

        if scan_data is not None:
            self.actionToggle_scan.setChecked(is_running)
            self._update_scan_data(scan_data)
        return
    
    @QtCore.Slot(object)
    def _update_scan_data(self, scan_data):
        """
        @param ScanData scan_data:
        """
        axes = scan_data.scan_axes
        
        self._mw.ple_widget.set_scan_data(scan_data)