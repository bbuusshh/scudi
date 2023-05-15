
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
        # self._device_handle = None
        # Task handles for NIDAQmx tasks
        self._di_task_handles = list()

        self._ai_task_handle = None
        self._clk_task_handle = None
        self._ao_task_handle = None
        self._tasks_started_successfully = False
        # nidaqmx stream reader instances to help with data acquisition
        self._di_readers = list()
        self._ai_reader = None
        self._ao_writer = None

        # Internal settings
        self.__output_mode = None
        self.__sample_rate = -1.0

        # Internal settings
        self.__frame_size = -1
        self.__frame_buffer = -1

        # unread samples buffer
        self.__unread_samples_buffer = None
        self._number_of_pending_samples = 0

        # List of all available counters and terminals for this device
        self.__all_counters = tuple()
        self.__all_digital_terminals = tuple()
        self.__all_analog_in_terminals = tuple()
        self.__all_analog_out_terminals = tuple()

        # currently active channels
        self.__active_channels = dict(di_channels=frozenset(), ai_channels=frozenset(), ao_channels=frozenset())

        # Stored hardware constraints
        self._constraints = None
        self._thread_lock = RecursiveMutex()
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
        """
        Starts up the NI-card and performs sanity checks.
        """
        self._input_channel_units = {self._extract_terminal(key): value
                                     for key, value in self._input_channel_units.items()}
        self._output_channel_units = {self._extract_terminal(key): value
                                      for key, value in self._output_channel_units.items()}

        # Check if device is connected and set device to use
        self._tt = self._timetagger()
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
        
        if self._device_handle():
            print("Hi")
            self._device_handle = self._device_handle()
        else:
            self._device_handle = ni.system.Device(self._device_name)


        self.__all_counters = tuple(
            self._extract_terminal(ctr) for ctr in self._device_handle.co_physical_chans.channel_names if
            'ctr' in ctr.lower())
        self.__all_digital_terminals = tuple(
            self._extract_terminal(term) for term in self._device_handle.terminals if 'pfi' in term.lower())
        self.__all_analog_in_terminals = tuple(
            self._extract_terminal(term) for term in self._device_handle.ai_physical_chans.channel_names)
        self.__all_analog_out_terminals = tuple(
            self._extract_terminal(term) for term in self._device_handle.ao_physical_chans.channel_names)

        # Get digital input terminals from _input_channel_units of the Time Tagger
        # The input channels are assumed to be time tagger exclusively
        digital_sources = tuple(src for src in self._input_channel_units if 'tt' in src) #!FIX check maybe regex out tt

        analog_sources = tuple(src for src in self._input_channel_units if 'ai' in src)

        # Get analog input channels from _input_channel_units
        if analog_sources:
            source_set = set(analog_sources)
            invalid_sources = source_set.difference(set(self.__all_analog_in_terminals))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(self.__all_analog_in_terminals)))
            analog_sources = natural_sort(source_set.difference(invalid_sources))

        # Get analog output channels from _output_channel_units
        analog_outputs = tuple(src for src in self._output_channel_units if 'ao' in src)

        if analog_outputs:
            source_set = set(analog_outputs)
            invalid_sources = source_set.difference(set(self.__all_analog_out_terminals))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(self.__all_analog_in_terminals)))
            analog_outputs = natural_sort(source_set.difference(invalid_sources))

        # Check if all input channels fit in the device
        #!TODO FIX with the TimeTagger can be more inputs

        if len(analog_sources) > 16:
            raise ValueError(
                'Too many analog channels specified. Maximum number of analog channels is 16.'
            )

        # If there are any invalid inputs or outputs specified, raise an error
        defined_channel_set = set.union(set(self._input_channel_units), set(self._output_channel_units))
        detected_channel_set = set.union(set(analog_sources),
                                         set(digital_sources),
                                         set(analog_outputs))
        invalid_channels = set.difference(defined_channel_set, detected_channel_set)
        if invalid_channels:
            raise ValueError(
                f'The channels "{", ".join(invalid_channels)}", specified in the config, were not recognized.'
            )
        

        self._sum_channels = [ch.lower() for ch in self._sum_channels]
        if len(self._sum_channels) > 1:
            self._input_channel_units["sum"] = self._input_channel_units[self._sum_channels[0]]

        # Check Physical clock output if specified
        if self._physical_sample_clock_output is not None:
            self._physical_sample_clock_output = self._extract_terminal(self._physical_sample_clock_output)
            assert self._physical_sample_clock_output in self.__all_digital_terminals, \
                f'Physical sample clock terminal specified in config is invalid'

        # Get correct sampling frequency limits based on config specified channels
        if analog_sources and len(analog_sources) > 1:  # Probably "Slowest" case
            sample_rate_limits = (
                max(self._device_handle.ai_min_rate, self._device_handle.ao_min_rate),
                min(self._device_handle.ai_max_multi_chan_rate, self._device_handle.ao_max_rate)
            )
        elif analog_sources and len(analog_sources) == 1:  # Potentially faster than ai multi channel
            sample_rate_limits = (
                max(self._device_handle.ai_min_rate, self._device_handle.ao_min_rate),
                min(self._device_handle.ai_max_single_chan_rate, self._device_handle.ao_max_rate)
            )
        else:  # Only ao and di, therefore probably the fastest possible
            sample_rate_limits = (
                self._device_handle.ao_min_rate,
                min(self._device_handle.ao_max_rate, self._device_handle.ci_max_timebase)
            )

        output_voltage_ranges = {self._extract_terminal(key): value
                                 for key, value in self._output_voltage_ranges.items()}

        input_limits = dict()

        if digital_sources:
            input_limits.update({key: [0, int(1e8)]
                                 for key in digital_sources})  # TODO Real HW constraint?
        if len(self._sum_channels) > 1:
            input_limits["sum"] = [0, int(1e8)]
            
        if analog_sources:
            adc_voltage_ranges = {self._extract_terminal(key): value
                                  for key, value in self._adc_voltage_ranges.items()}

            input_limits.update(adc_voltage_ranges)

        # Create constraints
        self._constraints = FiniteSamplingIOConstraints(
            supported_output_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP),
            input_channel_units=self._input_channel_units,
            output_channel_units=self._output_channel_units,
            frame_size_limits=self._frame_size_limits,
            sample_rate_limits=sample_rate_limits,
            output_channel_limits=output_voltage_ranges,
            input_channel_limits=input_limits
        )

        assert self._constraints.output_mode_supported(self._default_output_mode), \
            f'Config output "{self._default_output_mode}" mode not supported'

        self.__output_mode = self._default_output_mode
        self.__frame_size = 0
        return
        

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        # self.terminate_all_tasks()
        # Free memory if possible while module is inactive
        self.__frame_buffer = np.empty(0, dtype=self.__data_type)
        return
    
    
    # =============================================================================================
    def _init_sample_clock(self):
        """
        Configures a counter to provide the sample clock for all
        channels. # TODO external sample clock?

        @return int: error code (0: OK, -1: Error)
        """
        # # Return if sample clock is externally supplied
        # if self._external_sample_clock_source is not None:
        #     return 0

        if self._clk_task_handle is not None:
            self.log.error('Sample clock task is already running. Unable to set up a new clock '
                           'before you close the previous one.')
            return -1

        # Try to find an available counter
        for src in self.__all_counters:
            # Check if task by that name already exists
            task_name = 'SampleClock_{0:d}'.format(id(self))
            try:
                task = ni.Task(task_name)
            except ni.DaqError:
                self.log.exception('Could not create task with name "{0}".'.format(task_name))
                return -1

            # Try to configure the task
            try:
                task.co_channels.add_co_pulse_chan_freq(
                    '/{0}/{1}'.format(self._device_name, src),
                    freq=self.sample_rate,
                    idle_state=ni.constants.Level.LOW)
                task.timing.cfg_implicit_timing(
                    sample_mode=ni.constants.AcquisitionType.FINITE,
                    samps_per_chan=self.frame_size + 1)
            except ni.DaqError:
                self.log.exception('Error while configuring sample clock task.')
                try:
                    task.close()
                    del task
                except NameError:
                    pass
                return -1

            # Try to reserve resources for the task
            try:
                task.control(ni.constants.TaskMode.TASK_RESERVE)
            except ni.DaqError:
                # Try to clean up task handle
                try:
                    task.close()
                except ni.DaqError:
                    pass
                try:
                    del task
                except NameError:
                    pass

                # Return if no counter could be reserved
                if src == self.__all_counters[-1]:
                    self.log.exception('Error while setting up clock. Probably because no free '
                                       'counter resource could be reserved.')
                    return -1
                continue
            break
        self._clk_task_handle = task

        if self._physical_sample_clock_output is not None:
            clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
            ni.system.System().connect_terms(source_terminal=clock_channel,
                                             destination_terminal='/{0}/{1}'.format(
                                                 self._device_name, self._physical_sample_clock_output))
        return 0
    
    def _init_analog_in_task(self):
        """
        Set up task for analog voltage measurement.

        @return int: error code (0:OK, -1:error)
        """
        analog_channels = self.__active_channels['ai_channels']
        if not analog_channels:
            return 0
        if self._ai_task_handle:
            self.log.error(
                'Analog input task has already been generated. Unable to set up analog in task.')
            self.terminate_all_tasks()
            return -1
        if self._clk_task_handle is None:
            self.log.error(
                'No sample clock task has been generated and no external clock source specified. '
                'Unable to create analog voltage measurement tasks.')
            self.terminate_all_tasks()
            return -1

        clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
        sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up analog input task
        task_name = 'AnalogIn_{0:d}'.format(id(self))
        try:
            ai_task = ni.Task(task_name)
        except ni.DaqError:
            self.log.exception('Unable to create analog-in task with name "{0}".'.format(task_name))
            self.terminate_all_tasks()
            return -1

        try:
            for ai_channel in analog_channels:
                ai_ch_str = '/{0}/{1}'.format(self._device_name, ai_channel)
                ai_task.ai_channels.add_ai_voltage_chan(ai_ch_str,
                                                        min_val=min(self.constraints.input_channel_limits[ai_channel]),
                                                        max_val=max(self.constraints.input_channel_limits[ai_channel])
                                                        )
            ai_task.timing.cfg_samp_clk_timing(sample_freq,
                                               source=clock_channel,
                                               active_edge=ni.constants.Edge.RISING,
                                               sample_mode=ni.constants.AcquisitionType.FINITE,
                                               samps_per_chan=self.frame_size)
        except ni.DaqError:
            self.log.exception(
                'Something went wrong while configuring the analog-in task.')
            try:
                del ai_task
            except NameError:
                pass
            self.terminate_all_tasks()
            return -1

        try:
            ai_task.control(ni.constants.TaskMode.TASK_RESERVE)
        except ni.DaqError:
            try:
                ai_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ai_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')

            self.log.exception('Unable to reserve resources for analog-in task.')
            self.terminate_all_tasks()
            return -1

        try:
            self._ai_reader = AnalogMultiChannelReader(ai_task.in_stream)
            self._ai_reader.verify_array_shape = False
        except ni.DaqError:
            try:
                ai_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ai_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')
            self.log.exception('Something went wrong while setting up the analog input reader.')
            self.terminate_all_tasks()
            return -1

        self._ai_task_handle = ai_task
        return 0

    def _init_analog_out_task(self):
        analog_channels = self.__active_channels['ao_channels']
        if not analog_channels:
            self.log.error('No output channels defined. Can initialize output task')
            return -1

        clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
        sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up analog input task
        task_name = 'AnalogOut_{0:d}'.format(id(self))

        try:
            ao_task = ni.Task(task_name)
        except ni.DaqError:
            self.log.exception('Unable to create analog-in task with name "{0}".'.format(task_name))
            self.terminate_all_tasks()
            return -1

        try:
            for ao_channel in analog_channels:
                ao_ch_str = '/{0}/{1}'.format(self._device_name, ao_channel)
                ao_task.ao_channels.add_ao_voltage_chan(ao_ch_str,
                                                        min_val=min(self.constraints.output_channel_limits[ao_channel]),
                                                        max_val=max(self.constraints.output_channel_limits[ao_channel])
                                                        )
            ao_task.timing.cfg_samp_clk_timing(sample_freq,
                                               source=clock_channel,
                                               active_edge=ni.constants.Edge.RISING,
                                               sample_mode=ni.constants.AcquisitionType.FINITE,
                                               samps_per_chan=self.frame_size)
        except ni.DaqError:
            self.log.exception(
                'Something went wrong while configuring the analog-in task.')
            try:
                del ao_task
            except NameError:
                pass
            self.terminate_all_tasks()
            return -1

        try:
            ao_task.control(ni.constants.TaskMode.TASK_RESERVE)
        except ni.DaqError:
            try:
                ao_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ao_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')

            self.log.exception('Unable to reserve resources for analog-out task.')
            self.terminate_all_tasks()
            return -1

        try:
            self._ao_writer = AnalogMultiChannelWriter(ao_task.in_stream)
            self._ao_writer.verify_array_shape = False
        except ni.DaqError:
            try:
                ao_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ao_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')
            self.log.exception('Something went wrong while setting up the analog input reader.')
            self.terminate_all_tasks()
            return -1

        self._ao_task_handle = ao_task
        return 0
    
    
    def reset_hardware(self):
        """
        Resets the NI hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._device_handle.reset_device()
            self.log.info('Reset device {0}.'.format(self._device_name))
        except ni.DaqError:
            self.log.exception('Could not reset NI device {0}'.format(self._device_name))
            return -1
        return 0
    
    
    def terminate_all_tasks(self):
        err = 0

        self._di_readers = list()
        self._ai_reader = None

        while len(self._di_task_handles) > 0:
            try:
                if not self._di_task_handles[-1].is_task_done():
                    self._di_task_handles[-1].stop()
                self._di_task_handles[-1].close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate digital counter task.')
                err = -1
            finally:
                del self._di_task_handles[-1]
        self._di_task_handles = list()

        if self._ai_task_handle is not None:
            try:
                if not self._ai_task_handle.is_task_done():
                    self._ai_task_handle.stop()
                self._ai_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate analog input task.')
                err = -1
        self._ai_task_handle = None

        if self._ao_task_handle is not None:
            try:
                if not self._ao_task_handle.is_task_done():
                    self._ao_task_handle.stop()
                self._ao_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate analog input task.')
                err = -1
            self._ao_task_handle = None

        if self._clk_task_handle is not None:
            if self._physical_sample_clock_output is not None:
                clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
                ni.system.System().disconnect_terms(source_terminal=clock_channel,
                                                    destination_terminal='/{0}/{1}'.format(
                                                        self._device_name, self._physical_sample_clock_output))
            try:
                if not self._clk_task_handle.is_task_done():
                    self._clk_task_handle.stop()
                self._clk_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate clock task.')
                err = -1

        self._clk_task_handle = None
        #self._tasks_started_successfully = False
        return err
    
    
    @staticmethod
    def _extract_terminal(term_str):
        """
        Helper function to extract the bare terminal name from a string and strip it of the device
        name and dashes.
        Will return the terminal name in lower case.

        @param str term_str: The str to extract the terminal name from
        @return str: The terminal name in lower case
        """
        term = term_str.strip('/').lower()
        if 'dev' in term:
            term = term.split('/', 1)[-1]
        return term

    def _extract_ai_di_from_input_channels(self, input_channels):
        """
        Takes an iterable with output channels and returns the split up ai and di channels

        @return tuple(di_channels), tuple(ai_channels))
        """
        input_channels = tuple(self._extract_terminal(src) for src in input_channels)

        di_channels = tuple(channel for channel in input_channels if ('pfi' in channel) or ("tt" in channel))
        ai_channels = tuple(channel for channel in input_channels if 'ai' in channel)

        assert (di_channels or ai_channels), f'No channels could be extracted from {*input_channels,}'

        return tuple(di_channels), tuple(ai_channels)


class NiInitError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)