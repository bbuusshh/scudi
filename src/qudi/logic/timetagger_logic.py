from qtpy import QtCore
import sys, os
import numpy as np
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.util.mutex import Mutex, RecursiveMutex
import yaml
from qtpy import QtCore

class TimeTaggerLogic(LogicBase):
    """ Logic module agreggating multiple hardware switches.
    """

    timetagger = Connector(interface='TT')
    queryInterval = ConfigOption('query_interval', 500)
    
    sigCounterDataChanged = QtCore.Signal(object)
    sigCorrDataChanged = QtCore.Signal(object)
    sigHistDataChanged = QtCore.Signal(object)

    sigUpdate = QtCore.Signal()
    sigNewMeasurement = QtCore.Signal()
    sigHistRefresh = QtCore.Signal(float)
    sigUpdateGuiParams=QtCore.Signal()
    def __init__(self, **kwargs):
        """ Create CwaveScannerLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()
        self.stopRequested = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._timetagger = self.timetagger()
        self._constraints = self._timetagger._constraints
        self.stopRequested = False

        self._counter_poll_timer = QtCore.QTimer()
        self._counter_poll_timer.setSingleShot(False)
        self._counter_poll_timer.timeout.connect(self.acquire_data_block, QtCore.Qt.QueuedConnection)
        self._counter_poll_timer.setInterval(50)

        self._corr_poll_timer = QtCore.QTimer()
        self._corr_poll_timer.setSingleShot(False)
        self._corr_poll_timer.timeout.connect(self.acquire_corr_block, QtCore.Qt.QueuedConnection)
        self._corr_poll_timer.setInterval(50)

        self._hist_poll_timer = QtCore.QTimer()
        self._hist_poll_timer.setSingleShot(False)
        self._hist_poll_timer.timeout.connect(self.acquire_hist_block, QtCore.Qt.QueuedConnection)
        self._hist_poll_timer.setInterval(50)

        self.counter = None
        self.trace_data = {}
        self.counter_params = self._timetagger._counter
        self.hist_params = self._timetagger._hist
        self.corr_params  = self._timetagger._corr
    
    def on_deactivate(self):
        pass
    
    def configure_counter(self, data):
        self.counter_freq, self.counter_length, self.counter_channels, self.counter_toggle, self.display_channel = data['counter']

        with self.threadlock:
            bin_width = int(1/self.counter_freq*1e12)
            n_values = int(self.counter_length*1e12/bin_width)
            self.toggled_channels = []
            self.display_channel_number = 0
            for ch in self.counter_channels:
                if self.counter_channels[ch]:
                    self.toggled_channels.append(ch)
                    if self.display_channel == f'Channel {ch}':
                        self.display_channel_number = ch

            if self.toggled_channels and self.counter_toggle:
                self.counter = self._timetagger.counter(channels = self.toggled_channels, bin_width = bin_width, n_values = n_values)
        
                self._counter_poll_timer.start()
    
    def configure_corr(self, data):
        self.corr_bin_width, self.corr_record_length, self.corr_toggled = data['corr']
        self.corr_record_length *= 1e6
        with self.threadlock:
            if self.corr_toggled:
                self.corr = self._timetagger.correlation(channel_start = self._constraints['corr']['channel_start'], 
                                                        channel_stop = self._constraints['corr']['channel_stop'], 
                                                        bin_width = int(self.corr_bin_width), 
                                                        number_of_bins = int(self.corr_record_length/self.corr_bin_width))
        
                self._corr_poll_timer.start()
    
    def configure_hist(self, data):
        self.hist_bin_width, self.hist_record_length, self.hist_channel, self.hist_toggled = data['hist']
        self.hist_record_length *= 1e6

        if self.hist_toggled:
            self.hist = self._timetagger.histogram(channel = self.hist_channel, 
                                                   trigger_channel = self._constraints['hist']['trigger_channel'], 
                                                   bin_width = int(self.hist_bin_width), 
                                                   number_of_bins = int(self.hist_record_length/self.hist_bin_width))

            self._hist_poll_timer.start()


    def acquire_data_block(self):
        """
        This method gets the available data from the hardware.

        It runs repeatedly by being connected to a QTimer timeout signal.
        """
        with self.threadlock:
            if not self.counter_toggle or not self.counter:
                self._counter_poll_timer.stop()
                return
            self.trace_data = {}
            counter_sum = None
            raw = self.counter.getDataNormalized()
            index = self.counter.getIndex()/1e12
            # raw = np.random.random(100)
            # index = np.arange(100)
            counter_sum = np.zeros_like(raw[0])
            for i, ch in enumerate(self.toggled_channels):
                self.trace_data[ch] = (index, raw[i])
                if self.display_channel_number==0:
                    counter_sum += raw[i]
                elif self.display_channel_number==ch:
                    counter_sum += raw[i]

            self.sigCounterDataChanged.emit({'trace_data':self.trace_data, 'sum': np.mean(np.nan_to_num(counter_sum))})
        return
    
    def acquire_corr_block(self):
        with self.threadlock:
            if not self.corr_toggled:
                self._corr_poll_timer.stop()
                return
            raw = self.corr.getDataNormalized()
            index = self.corr.getIndex()/1e12
            # raw = np.random.random(100)
            # index = np.arange(100)
            self.corr_data = (index, np.nan_to_num(raw))
            self.sigCorrDataChanged.emit({'corr_data':self.corr_data})
        return   
    
    def acquire_hist_block(self):
        with self.threadlock:
            if not self.hist_toggled:
                self._hist_poll_timer.stop()
                return
            raw = self.hist.getData()
            index = self.hist.getIndex()/1e12
            # raw = np.random.random(100)
            # index = np.arange(100)
            self.hist_data = (index, np.nan_to_num(raw))
            self.sigHistDataChanged.emit({'hist_data':self.hist_data})
        return
