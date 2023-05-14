
import ctypes
import numpy as np
import nidaqmx as ni
from nidaqmx._lib import lib_importer  # Due to NIDAQmx C-API bug needed to bypass property getter
from nidaqmx.stream_readers import AnalogMultiChannelReader, CounterReader
from nidaqmx.stream_writers import AnalogMultiChannelWriter

from qudi.core.configoption import ConfigOption
from qudi.core.module import Base
from qudi.core.connector import Connector
from qudi.util.helpers import natural_sort
from qudi.interface.finite_sampling_io_interface import FiniteSamplingIOInterface, FiniteSamplingIOConstraints
from qudi.util.enums import SamplingOutputMode
from qudi.util.mutex import RecursiveMutex
import time
import warnings


class NI_DeviceHandle(Base):
    _device_name = ConfigOption(name='device_name', missing='error')

    _scanner_ready = False
    # Hardcoded data type
    __data_type = np.float64

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NIDAQmx device handle
        self._device_handle = None
        # Task handles for NIDAQmx tasks
        self._di_task_handles = list()
        self._do_task_handles = list()
        return


    def on_activate(self):
        """ Activate module.
        """
        dev_names = ni.system.System().devices.device_names
        if self._device_name.lower() not in set(dev.lower() for dev in dev_names):
            raise ValueError(
                f'Device name "{self._device_name}" not found in list of connected devices: '
                f'{dev_names}\nActivation of NIXSeriesFiniteSamplingIO failed!'
            )
        for dev in dev_names:
            if dev.lower() == self._device_name.lower():
                self._device_name = dev
                break
        self._device_handle = ni.system.Device(self._device_name)

        

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        # self.terminate_all_tasks()
        # Free memory if possible while module is inactive
        self.__frame_buffer = np.empty(0, dtype=self.__data_type)
        return