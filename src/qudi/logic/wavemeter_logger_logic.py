# -*- coding: utf-8 -*-

"""
This file contains the logic responsible for coordinating laser scanning.

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

from itertools import count
from PySide2 import QtCore
from collections import OrderedDict
import numpy as np
import time
import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt

from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import Base
from qudi.util.mutex import Mutex

from qudi.util.widgets.fitting import FitConfigurationDialog, FitWidget
from qudi.util.datastorage import TextDataStorage
from qudi.util.datafitting import FitContainer, FitConfigurationsModel
from qudi.core.statusvariable import StatusVar


class WavemeterLoggerLogic(Base):
    """This logic module gathers data from wavemeter and the counter logic.
    """

    sig_data_updated = QtCore.Signal()
    sig_new_data_point = QtCore.Signal(list)

    sigFitUpdated = QtCore.Signal(object, str)
    # declare connectors
    wavemeter = Connector(interface='WavemeterInterface')
    counter = Connector(interface='FastCounterInterface')
    _fit_config = StatusVar(name='fit_config', default=None)
    _fit_region = StatusVar(name='fit_region', default=[0, 1])

    _default_fit_configs = (
        {'name'             : 'Lorentzian',
         'model'            : 'Lorentzian',
         'estimator'        : 'Peak',
         'custom_parameters': None},

        {'name'             : 'Gaussian',
         'model'            : 'Gaussian',
         'estimator'        : 'Peak',
         'custom_parameters': None}
         
    )
    wavelength_buffer = 2000
    zpl_bin_width = .00005
    skip_rate = 3
    current_wavelength = -1
    wavelengths = np.array([], dtype = [('time', np.uint16), ('wavelength', np.uint32)])
    count_data = np.array([], dtype = [('wavelength', np.uint16), ('counts', np.uint32)])
    plot_x = []
    plot_y = []
    # config opts
    _logic_update_timing = ConfigOption('logic_query_timing', 200.0, missing='warn')
    # _logic_update_timing = ConfigOption('logic_update_timing', 100.0, missing='warn')
    sig_query_wavemeter = QtCore.Signal()
    sig_update_data = QtCore.Signal(object,object)
    
    def __init__(self, config, **kwargs):
        """ Create WavemeterLoggerLogic object with connectors.

          @param dict config: module configuration
          @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        self._acquisition_start_time = 0
        self._bins = 200
        self._data_index = 0

        self._recent_wavelength_window = [0, 0]
        self.counts_with_wavelength = []

        self._xmin = 636
        self._xmax = 638
        # internal min and max wavelength determined by the measured wavelength
        self.intern_xmax = -1.0
        self.intern_xmin = 1.0e10
        self.current_wavelength = 0

        self._acquisition_running = False
        self._histogram_busy = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._wavelength_data = []

        self.stopRequested = False
        self._counter_logic = self.counter()
        self._wavemeter = self.wavemeter()
        # create a new x axis from xmin to xmax with bins points
        self.histogram_axis = np.arange(
            self._xmin,
            self._xmax,
            (self._xmax - self._xmin) / self._bins
        )
        self.histogram = np.zeros(self.histogram_axis.shape)
        self.envelope_histogram = np.zeros(self.histogram_axis.shape)
        self.sig_query_wavemeter.connect(self.query_wavemeter, QtCore.Qt.QueuedConnection)
        # connect the signals in and out of the threaded object
        self.last_point_time = time.time()

        self.recalculate_histogram()
        
        self._queryTimer = QtCore.QTimer()
        self._queryTimer.setInterval(self._logic_update_timing)
        self._queryTimer.setSingleShot(False)
        self._queryTimer.timeout.connect(
            lambda : self.sig_update_data.emit(self.wavelengths, self.count_data)
        , QtCore.Qt.QueuedConnection)     
        
        self._queryTimer.start()
        
        self.sig_query_wavemeter.emit()
        self._counter_logic.start_measure()
        self._wavemeter.start_acquisition()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_scanning()

    @QtCore.Slot()
    def query_wavemeter(self):
        self.current_wavelength = self._wavemeter.get_current_wavelength()
        if self.current_wavelength > 0:
            if self.wavelengths.shape[0] == 0 :
                self.wavelengths = np.append(self.wavelengths, np.array([time.time() - self._acquisition_start_time, self.current_wavelength]))
            else:
                self.wavelengths = np.append(self.wavelengths, np.array([time.time() - self._acquisition_start_time, self.current_wavelength]), axis=0)
                
            self.cts = self._counter_logic.get_data_trace()[0].mean()
            self.cts_ys[np.argmin(np.abs(self.current_wavelength - self.wlth_xs))] += self.cts
            self.samples_num[np.argmin(np.abs(self.current_wavelength - self.wlth_xs))] += 1
            
            self.plot_y = np.divide(self.cts_ys, self.samples_num, out = np.zeros_like(self.cts_ys), where=self.samples_num != 0)
            self.count_data['wavelength'] = self.plot_x
            self.count_data['counts'] = self.plot_y
        self.sig_query_wavemeter.emit()
    
    def recalculate_histogram(self, bins=None, xmin=None, xmax=None):
        if (bins is None) or (xmin is None) or (xmax is None):
            xx = np.arange(self._xmin, self._xmax, self.zpl_bin_width)
            self.wlth_xs = xx
            self.cts_ys = np.zeros(len(xx))
            self.samples_num = np.zeros(len(xx))
            self.plot_x = xx
            self.plot_y = self.cts_ys
        else:
            self.zpl_bin_width = bins
            self.intern_xmin = xmin
            self.intern_xmin = xmax
            xx = np.arange(xmin, xmax, bins)
            self.wlth_xs = xx
            self.cts_ys = np.zeros(len(xx))
            self.samples_num = np.zeros(len(xx))
            self.plot_x = xx
            self.plot_y = self.cts_ys

    def wavelength_to_freq(wavelength):
        if isinstance(wavelength, float):
            return 299792458.0 * 1e9 / wavelength
        wavelength = np.array(wavelength)
        aa = 299792458.0 * 1e9 * np.ones(wavelength.shape[0])
        freqs = np.divide(aa, wavelength, out=np.zeros_like(aa), where=wavelength!=0)
        return freqs