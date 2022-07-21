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

    sigUpdateSettings = QtCore.Signal(dict)

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
        self.wavemeterloggerlogic = self.wavemeterloggerlogic()
        self._mw.actionStop_resume_scan.triggered.connect(self.stop_resume_clicked)
        # self._mw.actionSave_histogram.triggered.connect(self.save_clicked)
        self._mw.actionStart_scan.triggered.connect(self.start_clicked)
        self._mw.actionAuto_range.triggered.connect(self.set_auto_range)

        # defining the parameters to edit
        self._mw.binSpinBox.setValue(self.wavemeterloggerlogic.get_bins())
        # self._mw.binSpinBox.editingFinished.connect(self.recalculate_histogram)

        # self._mw.minDoubleSpinBox.setValue(self.wavemeterloggerlogic.get_min_wavelength())
        # self._mw.minDoubleSpinBox.editingFinished.connect(self.recalculate_histogram)

        # self._mw.maxDoubleSpinBox.setValue(self.wavemeterloggerlogic.get_max_wavelength())
        # self._mw.maxDoubleSpinBox.editingFinished.connect(self.recalculate_histogram)


        self._mw.show()

        # self.wavemeterloggerlogic.sig_new_data_point.connect(self.add_data_point)

        self.wavemeterloggerlogic.sig_update_data.connect(self._update_data, QtCore.Qt.QueuedConnection)
        # self.wavemeterloggerlogic.sig_new_wavelength.connect(self._update_live_wavelength)

        # Connect signals
        # self._mw.actionFit_settings.triggered.connect(self._fsd.show)
        # self._mw.do_fit_PushButton.clicked.connect(self.doFit)
        # self.sigDoFit.connect(self.wavemeterloggerlogic.do_fit)
        # self.sigFitChanged.connect(self.wavemeterloggerlogic.fc.set_current_fit)
        # self.wavemeterloggerlogic.sig_fit_updated.connect(self.updateFit)

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

    def _update_live_wavelength(self, wavelength, intern_xmin, intern_xmax):
        self._mw.wavelengthLabel.setText('{0:,.6f} nm '.format(wavelength))
        self._mw.autoMinLabel.setText('Minimum: {0:3.6f} (nm)   '.format(intern_xmin))
        self._mw.autoMaxLabel.setText('Maximum: {0:3.6f} (nm)   '.format(intern_xmax))

    @QtCore.Slot(object)
    def _update_data(self, wavelengths, count_data):
        """
        @param ScanData scan_data:
        """
        if wavelengths.shape[0] > 0:
            self._mw.wavelengthLabel.setText(f"{wavelengths['wavelength'][-1]} nm")
            self._mw.wavelength_widget.set_data(wavelengths)
            self._mw.countlog_widget.set_data(count_data)


    def stop_resume_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        # If running, then we stop the measurement and enable inputs again
        if self.wavemeterloggerlogic.module_state() != 'idle':
            self._mw.actionStop_resume_scan.setText('Resume')
            self.wavemeterloggerlogic.toggle_log(False)
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.actionStart_scan.setEnabled(True)
            self._mw.binSpinBox.setEnabled(True)
        # Otherwise, we start a measurement and disable some inputs.
        else:
            self._mw.actionStop_resume_scan.setText('Stop')
            self.wavemeterloggerlogic.toggle_log(True)
            self._mw.actionStart_scan.setEnabled(False)
            self._mw.binSpinBox.setEnabled(False)

    def start_clicked(self):
        """ Handling resume of the scanning without resetting the data.
        """
        if self.wavemeterloggerlogic.module_state() == 'idle':
            # self._scatterplot.clear()
            # self.wavemeterloggerlogic.start_scanning()
            self.wavemeterloggerlogic.toggle_log(True)
            # Enable the stop button once a scan starts.
            self._mw.actionStop_resume_scan.setText('Stop')
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.actionStart_scan.setEnabled(False)
            self._mw.binSpinBox.setEnabled(False)
            # self.recalculate_histogram()
        else:
            self.log.error('Cannot scan, since a scan is already running.')


    def recalculate_histogram(self):
        self.wavemeterloggerlogic.recalculate_histogram(
            bins=self._mw.binSpinBox.value(),
            xmin=self._mw.minDoubleSpinBox.value(),
            xmax=self._mw.maxDoubleSpinBox.value()
        )

    def set_auto_range(self):
        self._mw.minDoubleSpinBox.setValue(self.wavemeterloggerlogic.intern_xmin)
        self._mw.maxDoubleSpinBox.setValue(self.wavemeterloggerlogic.intern_xmax)
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
