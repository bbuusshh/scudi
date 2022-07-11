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

#TODO carefull disconnection
from email.policy import default
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
from qudi.util.widgets.fitting import FitConfigurationDialog
from .fit_dockwidget import PleFitDockWidget
from qudi.gui.ple.ple_ui_window import PLEScanMainWindow
from qudi.util.widgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox

class PLEScanGui(GuiBase):
    """
    """
    
    # declare connectors
    _scanning_logic = Connector(name='scannerlogic', interface='PLEScannerLogic')
    _microwave_logic = Connector(name='microwave', interface= 'OdmrLogic', optional=True)

    # status vars
    _window_state = StatusVar(name='window_state', default=None)
    _window_geometry = StatusVar(name='window_geometry', default=None)

    # signals
    sigScannerTargetChanged = QtCore.Signal(dict)#, object)
    sigScanSettingsChanged = QtCore.Signal(dict)
    sigToggleScan = QtCore.Signal(bool, tuple, object)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigToggleOptimize = QtCore.Signal(bool)
    sigSaveScan = QtCore.Signal(object, object)
    sigSaveFinished = QtCore.Signal()
    sigShowSaveDialog = QtCore.Signal(bool)

    sigDoFit = QtCore.Signal(str, str)

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
        self._scanning_logic = self._scanning_logic()
        self.scan_axis = self._scanning_logic._scan_axis
        self.axis = self._scanning_logic.scanner_axes[self.scan_axis]
        channel = self._scanning_logic.scanner_channels[self._scanning_logic._channel]


        self._mw = PLEScanMainWindow(self.axis, channel)
        self._mw.show()
        
        # Connect signals
        self.sigScannerTargetChanged.connect(
            self._scanning_logic.set_target_position, QtCore.Qt.QueuedConnection
        )
        self.sigScanSettingsChanged.connect(
            self._scanning_logic.set_scan_settings, QtCore.Qt.QueuedConnection
        )
        self.sigToggleScan.connect(self._scanning_logic.toggle_scan, QtCore.Qt.QueuedConnection)
        self._mw.actionToggle_scan.triggered.connect(self.toggle_scan, QtCore.Qt.QueuedConnection)
        self._scanning_logic.sigRepeatScan.connect(self.scan_repeated, QtCore.Qt.QueuedConnection)
        
        self._scanning_logic.sigScanStateChanged.connect(
            self.scan_state_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic.sigScannerTargetChanged.connect(
            self.scanner_target_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic.sigScanSettingsChanged.connect(
            self.scanner_settings_updated, QtCore.Qt.QueuedConnection
        )
        # self.sigToggleOptimize.connect(
        #     self._optimize_logic().toggle_optimize, QtCore.Qt.QueuedConnection
        # )

        self._mw.ple_widget.target_point.sigPositionChanged.connect(self.sliders_values_are_changing)
        self._mw.ple_widget.selected_region.sigRegionChanged.connect(self.sliders_values_are_changing)

        self._mw.ple_widget.target_point.sigPositionChangeFinished.connect(self.set_scanner_target_position)
        self._mw.ple_widget.selected_region.sigRegionChangeFinished.connect(self.region_value_changed) 


        # x_range = settings['range'][self.scan_axis]
        # dec_places = decimal_places = np.abs(int(f'{x_range[0]:e}'.split('e')[-1])) + 3
        self._mw.startDoubleSpinBox.setSuffix(self.axis.unit)
        self._mw.stopDoubleSpinBox.setSuffix(self.axis.unit)
        self._mw.constDoubleSpinBox.setSuffix(self.axis.unit)

        #create microwave control window if microwave is set
        if self._microwave_logic() is not None:
            self._microwave_logic = self._microwave_logic()
            self._mw.add_dock_widget('microwave')
            self._init_microwave()
        
        
        self.scanner_target_updated()
        self.scan_state_updated(self._scanning_logic.module_state() != 'idle')

        self.restore_scanner_settings()
        self._init_ui_connectors()

        self.setup_fit_widget()
        self.__connect_fit_control_signals()

    def _init_microwave(self):
        
        mw_constraints = self._microwave_logic.microwave_constraints
        self._mw.microwave_widget.set_constraints(mw_constraints)
        self._mw.microwave_widget.sig_microwave_params_updated.connect(
            self._microwave_logic.set_cw_parameters
            )
        self._mw.microwave_widget.sig_microwave_enabled.connect(
            self._microwave_logic.toggle_cw_output
        )
        self._microwave_logic.sigCwParametersUpdated.connect(
            self._mw.microwave_widget.update_params
        )
        self._microwave_logic.sigCwStateUpdated.connect(
            self._mw.microwave_widget.enable_microwave
        )

    def setup_fit_widget(self):
        self._fit_dockwidget = PleFitDockWidget(parent=self._mw, fit_container=self._scanning_logic._fit_container)
        self._fit_config_dialog = FitConfigurationDialog(parent=self._mw,
                                                         fit_config_model=self._scanning_logic._fit_config_model)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._fit_dockwidget)
        self.sigDoFit.connect(self._scanning_logic.do_fit, QtCore.Qt.QueuedConnection)
        self._scanning_logic.sigFitUpdated.connect(self._update_fit_result, QtCore.Qt.QueuedConnection)

    def __connect_fit_control_signals(self):
        self._fit_dockwidget.fit_widget.sigDoFit.connect(self._fit_clicked)
        
    def __disconnect_fit_control_signals(self):
        self._fit_dockwidget.fit_widget.sigDoFit.disconnect()


    def _fit_clicked(self, fit_config):
        channel = 'fluorescence'#self._scan_control_dockwidget.selected_channel
        # range_index = #self._scan_control_dockwidget.selected_range
        self.sigDoFit.emit(fit_config, channel)

    def _update_fit_result(self, fit_cfg_result, channel):
        current_channel = channel#self._scan_control_dockwidget.selected_channel
        # current_range_index = self._scan_control_dockwidget.selected_range
        print(fit_cfg_result)
        if current_channel == channel:# and current_range_index == range_index:
            if fit_cfg_result is None:
                self._fit_dockwidget.fit_widget.update_fit_result('No Fit', None)
                self._mw.ple_widget.set_fit_data(None, None)
            else:
                self._fit_dockwidget.fit_widget.update_fit_result(*fit_cfg_result)
                self._mw.ple_widget.set_fit_data(*fit_cfg_result[1].high_res_best_fit)



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
            self._scanning_logic.set_full_scan_ranges, QtCore.Qt.QueuedConnection
        )
        # !ValueError: all the input array dimensions for the concatenation axis must match exactly, but along dimension 1, the array at index 0 has size 50 and the array at index 1 has size 100
        self._mw.number_of_repeats_SpinBox.editingFinished.connect(
            lambda: self._scanning_logic.update_number_of_repeats(self._mw.number_of_repeats_SpinBox.value())
        )

        self._mw.constDoubleSpinBox.editingFinished.connect(
            lambda: self.set_scanner_target_position
        )

        



    def toggle_scan(self):
        self._mw.elapsed_lines_DisplayWidget.display(self._scanning_logic._repeated)
        self.sigToggleScan.emit(self._mw.actionToggle_scan.isChecked(), [self.scan_axis], self.module_uuid)

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    @QtCore.Slot()
    def region_value_changed(self):
        region = self._mw.ple_widget.selected_region.getRegion()
        self.sigScanSettingsChanged.emit({'range': {self.scan_axis: region}})
        self._mw.startDoubleSpinBox.setValue(region[0])
        self._mw.stopDoubleSpinBox.setValue(region[1])

    @QtCore.Slot()
    def sliders_values_are_changing(self):
        region = self._mw.ple_widget.selected_region.getRegion()
        self._mw.startDoubleSpinBox.setValue(region[0])
        self._mw.stopDoubleSpinBox.setValue(region[1])

        value = self._mw.ple_widget.target_point.value()
        self._mw.constDoubleSpinBox.setValue(value)


    @QtCore.Slot()
    def restore_scanner_settings(self):
        """ ToDo: Document
        """
        self.scanner_settings_updated({'frequency': self._scanning_logic.scan_frequency,
        'resolution': self._scanning_logic.scan_resolution,
        'range': self._scanning_logic.scan_ranges})


    @QtCore.Slot(dict)
    def scanner_settings_updated(self, settings=None):
        """
        Update scanner settings from logic and set widgets accordingly.

        @param dict settings: Settings dict containing the scanner settings to update.
                              If None (default) read the scanner setting from logic and update.
        """
        if not isinstance(settings, dict):
            settings = self._scanning_logic.scan_settings

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
            
            # self._mw.startDoubleSpinBox.update_value()


            y_range =  (0, self._scanning_logic._number_of_repeats)
            self._mw.matrix_widget.set_plot_range(x_range = x_range, y_range = y_range)
            matrix_range = (x_range, y_range)
            self._mw.matrix_widget.image_widget.set_image_extent(matrix_range,
                            adjust_for_px_size=True)
            self._mw.matrix_widget.image_widget.autoRange()
            
            self._mw.ple_widget.selected_region.setRegion(x_range)
            self._mw.ple_widget.target_point.setValue((x_range[0] + x_range[1])/2)
            self._mw.ple_widget.plot_widget.setRange(xRange = x_range)

        if 'frequency' in settings:
            self._mw.frequencyDoubleSpinBox.setValue(settings['frequency'][self.scan_axis])
        
        self._scanning_logic.reset_accumulated()
        self._mw.number_of_repeats_SpinBox.setValue(self._scanning_logic._number_of_repeats)
        
        

    @QtCore.Slot(bool, tuple)
    def scan_repeated(self, start, scan_axes):
        self._mw.elapsed_lines_DisplayWidget.display(self._scanning_logic.display_repeated)

    @QtCore.Slot(dict)
    def set_scanner_target_position(self, target_pos=None):
        """
        Issues new target to logic and updates gui.

        @param dict target_pos:
        """
        target = self._mw.ple_widget.target_point.value()
        target_pos = {self._scanning_logic._scan_axis: target}
        self.sigScannerTargetChanged.emit(target_pos)
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
            pos_dict = self._scanning_logic.scanner_target
            
        self._mw.ple_widget.target_point.setValue(pos_dict[self._scanning_logic._scan_axis])
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
    
        if scan_data.accumulated_data is not None:
            self._mw.ple_widget.set_scan_data(scan_data)
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

