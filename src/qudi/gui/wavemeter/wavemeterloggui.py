# -*- coding: utf-8 -*-

"""
This file contains a gui to see wavemeter data during laser scanning.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import datetime
import wave
import numpy as np
import os
import pyqtgraph as pg
import pyqtgraph.exporters

from qudi.core.connector import Connector
from qudi.util import units
from qudi.core.module import GuiBase
from qudi.util.colordefs import QudiPalettePale as palette
from qudi.util.widgets.fitting import FitConfigurationDialog
from PySide2 import QtCore, QtWidgets, QtGui
from qudi.util.uic import loadUi
from qudi.gui.wavemeter.wavelogger_mw import WavemeterMainWindow


class WavemeterLogGui(GuiBase):
    """
    This GUI is for PLE measurements, reading out a wavemeter
    """
    # declare connectors
    wavemeterloggerlogic = Connector(interface='WavemeterLoggerLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()
    sigFitChanged = QtCore.Signal(str)
    sigDoFit = QtCore.Signal(str, str)


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        # setting up the window
        self._mw = WavemeterMainWindow()
        self._mw.show()
        self.wavelog_logic = self.wavemeterloggerlogic()
        self._mw.actionStop_resume_scan.triggered.connect(self.stop_resume_clicked)
        # self._mw.actionSave_histogram.triggered.connect(self.save_clicked)
        self._mw.actionStart_scan.triggered.connect(self.start_clicked)
        self._mw.actionAuto_range.triggered.connect(self.set_auto_range)

        # defining the parameters to edit
        self._mw.binDoubleSpinBox.setValue(self.wavelog_logic._settings['bin_width'])
        self._mw.minDoubleSpinBox.setValue(self.wavelog_logic._settings['start_value'])
        self._mw.maxDoubleSpinBox.setValue(self.wavelog_logic._settings['stop_value'])
        self._mw.countlog_widget.selected_region.setRegion((self.wavelog_logic._settings['start_value'], self.wavelog_logic._settings['stop_value']))
        self._mw.binDoubleSpinBox.editingFinished.connect(
            lambda : self.wavelog_logic.sigUpdateSettings.emit({'bin_width': self._mw.binDoubleSpinBox.value()})
            )
        self._mw.minDoubleSpinBox.editingFinished.connect(
            lambda : self.wavelog_logic.sigUpdateSettings.emit({'start_value': self._mw.minDoubleSpinBox.value()})
            )
        self._mw.maxDoubleSpinBox.editingFinished.connect(
            lambda : self.wavelog_logic.sigUpdateSettings.emit({'stop_value': self._mw.maxDoubleSpinBox.value()})
            )
        self._mw.countlog_widget.selected_region.sigRegionChanged.connect(self.sliders_values_are_changing)
        # self.selected_region.setRegion(self._scan_data.scan_range[0])
        self._mw.show()

        # self.wavelog_logic.sig_new_data_point.connect(self.add_data_point)

        self.wavelog_logic.sig_update_data.connect(self._update_data, QtCore.Qt.QueuedConnection)
        # self.wavelog_logic.sig_new_wavelength.connect(self._update_live_wavelength)

        # Connect signals
        # self._mw.actionFit_settings.triggered.connect(self._fsd.show)
        # self._mw.do_fit_PushButton.clicked.connect(self.doFit)
        # self.sigDoFit.connect(self.wavelog_logic.do_fit)
        # self.sigFitChanged.connect(self.wavelog_logic.fc.set_current_fit)
        # self.wavelog_logic.sig_fit_updated.connect(self.updateFit)

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.close()

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    @QtCore.Slot()
    def sliders_values_are_changing(self):
        region = self._mw.countlog_widget.selected_region.getRegion()
        self._mw.minDoubleSpinBox.setValue(region[0])
        self._mw.maxDoubleSpinBox.setValue(region[1])
        self.wavelog_logic.sigUpdateSettings.emit({
                        'start_value': self._mw.minDoubleSpinBox.value(),
                        'stop_value': self._mw.maxDoubleSpinBox.value()
                        })
    @QtCore.Slot(object)
    def _update_data(self, wavelengths, count_data):
        """
        @param ScanData scan_data:
        """
        if wavelengths.shape[0] > 0:
            wavelength = np.round(wavelengths['wavelength'][-1], 6)
            frequency = np.round(self.wavelog_logic.wavelength_to_freq(wavelengths['wavelength'][-1]) * 1e-12, 6)
            # self._mw.wavelengthLabel.setText(f"{wavelength} nm")
            self._mw.frequencyLabel.setText(f"{wavelength/1e12} THz")
            self._mw.wavelength_widget.set_data(wavelengths)
            self._mw.countlog_widget.set_data(count_data)




    def stop_resume_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        # If running, then we stop the measurement and enable inputs again
        if self.wavelog_logic.module_state() != 'idle':
            self._mw.actionStop_resume_scan.setText('Resume')
            self.wavelog_logic.toggle_log(False)
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.actionStart_scan.setEnabled(True)
            self._mw.binDoubleSpinBox.setEnabled(True)
        # Otherwise, we start a measurement and disable some inputs.
        else:
            self._mw.actionStop_resume_scan.setText('Stop')
            self.wavelog_logic.toggle_log(True)
            self._mw.actionStart_scan.setEnabled(False)
            self._mw.binDoubleSpinBox.setEnabled(False)
        self._mw.countlog_widget.selected_region.show()

    def start_clicked(self):
        """ Handling resume of the scanning without resetting the data.
        """
        if self.wavelog_logic.module_state() == 'idle':
            # self._scatterplot.clear()
            # self.wavelog_logic.start_scanning()
            self.wavelog_logic.toggle_log(True)
            self._mw.countlog_widget.selected_region.hide()
            # Enable the stop button once a scan starts.
            self._mw.actionStop_resume_scan.setText('Stop')
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.actionStart_scan.setEnabled(False)
            self._mw.binDoubleSpinBox.setEnabled(False)
            # self.recalculate_histogram()
        else:
            self.log.error('Cannot scan, since a scan is already running.')


    def recalculate_histogram(self):
        self.wavelog_logic.recalculate_histogram(
            bins=self._mw.binDoubleSpinBox.value(),
            xmin=self._mw.minDoubleSpinBox.value(),
            xmax=self._mw.maxDoubleSpinBox.value()
        )

    def set_auto_range(self):
        self._mw.minDoubleSpinBox.setValue(self.wavelog_logic._xmin)
        self._mw.maxDoubleSpinBox.setValue(self.wavelog_logic._xmax)
        self.recalculate_histogram()

    ## Handle view resizing
    def _update_plot_views(self):
        ## view has resized; update auxiliary views to match
        self._right_axis.setGeometry(self._plot_item.vb.sceneBoundingRect())
        self._top_axis.setGeometry(self._plot_item.vb.sceneBoundingRect())

        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self._right_axis.linkedViewChanged(self._plot_item.vb, self._right_axis.XAxis)
        self._top_axis.linkedViewChanged(self._plot_item.vb, self._top_axis.YAxis)
