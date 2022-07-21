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
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex, RecursiveMutex

from qudi.util.widgets.fitting import FitConfigurationDialog, FitWidget
from qudi.util.datastorage import TextDataStorage
from qudi.util.datafitting import FitContainer, FitConfigurationsModel
from qudi.core.statusvariable import StatusVar
COUNT_DTYPE =  np.dtype([('wavelength', np.float64), ('counts', np.float64)])
WAVELENGTH_DTYPE = np.dtype([('time', np.float64), ('wavelength', np.float64)])
class WavemeterLoggerLogic(LogicBase):
    """This logic module gathers data from wavemeter and the counter logic.
    """


    sigUpdateSettings = QtCore.Signal(dict)
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
    wavelength_buffer = 5000
    zpl_bin_width = 0.2 #GHz #.00005 #
    _settings = {
        'bin_width':0.2,
        'start_value':0,
        'stop_value':1000
    }
    current_wavelength = -1
    _xmin = 420 * 1e3 # GHz
    _xmax = 425 * 1e3 # GHz
    wavelengths = np.array([], dtype = WAVELENGTH_DTYPE)
    count_data = np.array([], dtype = COUNT_DTYPE)
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
        self._thread_lock = RecursiveMutex()
        # internal min and max wavelength determined by the measured wavelength

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._counter_logic = self.counter()
        self._wavemeter = self.wavemeter()

        self.sig_query_wavemeter.connect(self.query_wavemeter, QtCore.Qt.QueuedConnection)
        # connect the signals in and out of the threaded object

        self.sigUpdateSettings.connect(self._udpate_settings)
        
        self._queryTimer = QtCore.QTimer()
        self._queryTimer.setInterval(self._logic_update_timing)
        self._queryTimer.setSingleShot(False)
        self._queryTimer.timeout.connect(
            lambda : self.sig_update_data.emit(self.wavelengths, self.count_data)
        , QtCore.Qt.QueuedConnection)     
        
        self.recalculate_histogram()
        self._counter_logic.start_measure()
        self._wavemeter.start_acquisition()
        self._acquisition_start_time = time.time()

        self._queryTimer.start()
        self.sig_query_wavemeter.emit()

        

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_scanning()

    @QtCore.Slot(dict)
    def _udpate_settings(self, settings):
        if self.module_state() != 'locked':
            self._settings.update(settings)
            self.recalculate_histogram()
            # settings['mode'] # frequency or vac or air
        return 

    def get_bins(self):
        return len(self.plot_x)

    def toggle_log(self, start):
        with self._thread_lock:
            if start:
                self.module_state.lock()
                self.sig_query_wavemeter.emit()
            else:
                self.module_state.unlock()
                self.sig_query_wavemeter.emit()
                

                

    @QtCore.Slot()
    def query_wavemeter(self):
        with self._thread_lock:
            self.current_wavelength = self._wavemeter.get_current_wavelength()
            self._time_elapsed = time.time() - self._acquisition_start_time
            if self.current_wavelength > 0:
                if self.wavelengths.shape[0] == 0:
                    self.wavelengths = np.array([(self._time_elapsed, self.current_wavelength)], dtype=WAVELENGTH_DTYPE)
                elif self._time_elapsed > self.wavelengths['time'][-1]:
                    self.wavelengths = np.append(self.wavelengths, np.array([(time.time() - self._acquisition_start_time, self.current_wavelength)], dtype=WAVELENGTH_DTYPE))
                    self.cts = self._counter_logic.get_data_trace()[0].mean()
                    self.cts_ys[np.argmin(np.abs(self.current_wavelength - self.wlth_xs))] += self.cts
                    self.samples_num[np.argmin(np.abs(self.current_wavelength - self.wlth_xs))] += 1
                    
                    self.plot_y = np.divide(self.cts_ys, self.samples_num, out = np.zeros_like(self.cts_ys), where=self.samples_num != 0)
                    self.count_data = np.zeros(self.plot_x.shape[0], dtype = COUNT_DTYPE)
                    self.count_data['wavelength'] = self.plot_x
                    self.count_data['counts'] = self.plot_y
            self.wavelengths = self.wavelengths[-self.wavelength_buffer:]
            
            if self.module_state() != 'idle':
                self.sig_query_wavemeter.emit()

    
    def recalculate_histogram(self, bins=None, xmin=None, xmax=None):
        self._settings['bin_width']
        if self.module_state() != 'locked':
                self.wlth_xs = np.arange(
                    self._settings['start_value'], 
                    self._settings['stop_value'], 
                    self._settings['bin_width']
                )
                self.cts_ys = np.zeros(len(self.wlth_xs))
                self.samples_num = np.zeros(len(self.wlth_xs))
                self.plot_x = self.wlth_xs
                self.plot_y = self.cts_ys

    def wavelength_to_freq(self, wavelength):
        if isinstance(wavelength, float):
            return 299792458.0 * 1e9 / wavelength
        wavelength = np.array(wavelength)
        aa = 299792458.0 * 1e9 * np.ones(wavelength.shape[0])
        freqs = np.divide(aa, wavelength, out=np.zeros_like(aa), where=wavelength!=0)
        return freqs