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

    def on_deactivate(self):
        """ Reverse steps of activation
        @return int: error code (0:OK, -1:error)
        """
        self._save_window_geometry(self._mw)
        self._mw.close()
        self.sigScannerTargetChanged.disconnect()
        self.sigScanSettingsChanged.disconnect()
        self.sigToggleScan.disconnect()
        # self.sigToggleOptimize.disconnect()
        return 0

    def on_activate(self):
        """ 
        """
        self._mw = PLEScanMainWindow()
        self._mw.show()
        self.scan_axis = self._scanning_logic()._scan_axis

        # Connect signals
        self.sigScannerTargetChanged.connect(
            self._scanning_logic().set_target_position, QtCore.Qt.QueuedConnection
        )
        self.sigScanSettingsChanged.connect(
            self._scanning_logic().set_scan_settings, QtCore.Qt.QueuedConnection
        )
        self.sigToggleScan.connect(self._scanning_logic().toggle_scan, QtCore.Qt.QueuedConnection)
        self._mw.actionToggle_scan.triggered.connect(self.toggle_scan, QtCore.Qt.QueuedConnection)
        self._scanning_logic().sigRepeatScan.connect(self.scan_repeated, QtCore.Qt.QueuedConnection)
        
        self._scanning_logic().sigScanStateChanged.connect(
            self.scan_state_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScannerTargetChanged.connect(
            self.scanner_target_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScanSettingsChanged.connect(
            self.scanner_settings_updated, QtCore.Qt.QueuedConnection
        )
        # self.sigToggleOptimize.connect(
        #     self._optimize_logic().toggle_optimize, QtCore.Qt.QueuedConnection
        # )
        # Initialize widget data
        # self.scanner_settings_updated()

        # self._mw.ple_widget.fit_region.sigRegionChangeFinished.connect(self.fit_region_value_changed)
        # self._mw.ple_widget.axis_type.sigStateChanged.connect(self.axis_type_changed)
        self._mw.ple_widget.target_point.sigPositionChangeFinished.connect(self.set_scanner_target_position)
        self._mw.ple_widget.fit_region.sigRegionChangeFinished.connect(self.region_value_changed)
        self.scanner_target_updated()
        self.scan_state_updated(self._scanning_logic().module_state() != 'idle')

        self._init_ranges()
        self._init_ui_connectors()
    
    def _init_ui_connectors(self):
        new_scan_range = lambda: self.sigScanSettingsChanged.emit({'range': {self.scan_axis: (self._mw.startDoubleSpinBox.value(), self._mw.stopDoubleSpinBox.value())}})
        self._mw.startDoubleSpinBox.editingFinished.connect(new_scan_range)
        self._mw.stopDoubleSpinBox.editingFinished.connect(new_scan_range)
        self._mw.frequencyDoubleSpinBox.editingFinished.connect(
            lambda: self.sigScanSettingsChanged.emit({'frequency': {self.scan_axis: self._mw.frequencyDoubleSpinBox.value()}})
        )
        self._mw.resolutionDoubleSpinBox.editingFinished.connect(
            lambda: self.sigScanSettingsChanged.emit({'resolution': {self.scan_axis: self._mw.resolutionDoubleSpinBox.value()}})
            ) 
        self._mw.actionFull_range.triggered.connect(
            self._scanning_logic().set_full_scan_ranges, QtCore.Qt.QueuedConnection
        )
        # !ValueError: all the input array dimensions for the concatenation axis must match exactly, but along dimension 1, the array at index 0 has size 50 and the array at index 1 has size 100
        # self._mw.number_of_repeats_SpinBox.editingFinished.connect()


    def _init_ranges(self):
        # self._scanning_logic().scan_ranges[self.scan_axis]
        x_range = self._scanning_logic().scan_ranges[self.scan_axis]
        y_range =  (0, self._scanning_logic()._number_of_repeats)
        self._mw.matrix_widget.set_plot_range(x_range = x_range, y_range = y_range)
        matrix_range = (x_range, y_range)
        self._mw.matrix_widget.image_widget.set_image_extent(matrix_range,
                        adjust_for_px_size=True)
        self._mw.matrix_widget.image_widget.autoRange()
        self._mw.ple_widget.fit_region.setRegion(x_range)
        self._mw.ple_widget.target_point.setValue((x_range[0] + x_range[1])/2)
        self._mw.ple_widget.plot_widget.setRange(xRange = x_range)

        self._mw.constDoubleSpinBox.setRange(*x_range)


    def toggle_scan(self):
        self.sigToggleScan.emit(self._mw.actionToggle_scan.isChecked(), [self.scan_axis], self.module_uuid)

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    @QtCore.Slot()
    def region_value_changed(self):
        region = self._mw.ple_widget.fit_region.getRegion()
        self.sigScanSettingsChanged.emit({'range': {self.scan_axis: region}})
        self._mw.startDoubleSpinBox.setValue(region[0])
        self._mw.stopDoubleSpinBox.setValue(region[1])

    @QtCore.Slot()
    def restore_scanner_settings(self):
        """ ToDo: Document
        """
        self.scanner_settings_updated({'frequency': self._scanning_logic().scan_frequency})


    @QtCore.Slot(dict)
    def scanner_settings_updated(self, settings=None):
        """
        Update scanner settings from logic and set widgets accordingly.

        @param dict settings: Settings dict containing the scanner settings to update.
                              If None (default) read the scanner setting from logic and update.
        """
        if not isinstance(settings, dict):
            settings = self._scanning_logic().scan_settings

        # if self._scanner_settings_locked:
        #     return
        # ToDo: Handle all remaining settings
        # ToDo: Implement backwards scanning functionality

        if 'resolution' in settings:
            self._mw.resolutionDoubleSpinBox.setValue(settings['resolution'][self.scan_axis])
        if 'range' in settings:
            x_range = settings['range'][self.scan_axis]
            self._mw.startDoubleSpinBox.setValue(x_range[0])
            self._mw.stopDoubleSpinBox.setValue(x_range[1])
            self._mw.constDoubleSpinBox.setRange(*x_range)
            

            y_range =  (0, self._scanning_logic()._number_of_repeats)
            self._mw.matrix_widget.set_plot_range(x_range = x_range, y_range = y_range)
            matrix_range = (x_range, y_range)
            self._mw.matrix_widget.image_widget.set_image_extent(matrix_range,
                            adjust_for_px_size=True)
            self._mw.matrix_widget.image_widget.autoRange()
            
        if 'frequency' in settings:
            self._mw.freqDoubleSpinBox.setValue(settings['frequency'][self.scan_axis])
        
        self._scanning_logic().reset_accumulated()
        # self._mw.number_of_repeats_SpinBox
        

    @QtCore.Slot(bool, tuple)
    def scan_repeated(self, start, scan_axes):
        self._mw.elapsed_lines_DisplayWidget.display(self._scanning_logic()._repeated)

# self._mw.startDoubleSpinBox.editingFinished.connect()
        # self._mw.stopDoubleSpinBox.editingFinished.connect()
        # self._mw.speedDoubleSpinBox.editingFinished.connect()
        # self._mw.resolutionDoubleSpinBox.editingFinished.connect(
        #     lambda: self.sigScanSettingsChanged.emit({'resolution': {self.scan_axis: self._mw.resolutionDoubleSpinBox.value()}})
        #     ) 
        #!ValueError: all the input array dimensions for the concatenation axis must match exactly, but along dimension 1, the array at index 0 has size 50 and the array at index 1 has size 100
        # self._mw.number_of_repeats_SpinBox.editingFinished.connect()



    @QtCore.Slot(dict)
    def set_scanner_target_position(self, target_pos=None):
        """
        Issues new target to logic and updates gui.

        @param dict target_pos:
        """
        target = self._mw.ple_widget.target_point.value()
        target_pos = {self._scanning_logic()._scan_axis: target}
        self._mw.constDoubleSpinBox.setValue(target)
        self.scanner_target_updated(pos_dict=target_pos, caller_id=None)

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
            
        self._mw.ple_widget.target_point.setValue(pos_dict[self._scanning_logic()._scan_axis])
        # self.scanner_control_dockwidget.set_target(pos_dict)

    @QtCore.Slot(bool, object, object)
    def scan_state_updated(self, is_running, scan_data=None, caller_id=None):
        scan_axes = scan_data.scan_axes if scan_data is not None else None
        if scan_data is not None:
            self._mw.actionToggle_scan.setChecked(is_running)
            self._update_scan_data(scan_data)
        return
    
    @QtCore.Slot(object)
    def _update_scan_data(self, scan_data):
        """
        @param ScanData scan_data:
        """
        axes = scan_data.scan_axes
        
        self._mw.ple_widget.set_scan_data(scan_data)
        if scan_data.accumulated_data is not None:
            self._mw.matrix_widget.set_scan_data(scan_data)


    def save_view(self):
        """Saves the current GUI state as a QbyteArray.
           The .data() function will transform it to a bytearray, 
           which can be saved as a StatusVar and read by the load_view method. 
        """
        self._save_display_view = self._mw.saveState().data() 
        

    def load_view(self):
        """Loads the saved state from the GUI and can read a QbyteArray
            or a simple byteArray aswell.
        """
        if self._save_display_view is None:
            pass
        else:
            self._mw.restoreState(self._save_display_view)

