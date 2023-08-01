import numpy as np
import time

from PySide2 import QtCore
from PySide2.QtGui import QGuiApplication

from qudi.interface.scanning_probe_interface import ScanningProbeInterface, ScanConstraints, \
    ScannerAxis, ScannerChannel, ScanData
from qudi.core.configoption import ConfigOption
from qudi.core.connector import Connector
from qudi.util.mutex import RecursiveMutex, Mutex
from qudi.util.enums import SamplingOutputMode
from qudi.util.helpers import in_range

class DLProTTPLEScanner(ScanningProbeInterface):
    _timetagger = Connector(name='tt', interface = "TT")
    _triggered_ao = Connector(name='triggered_ao', interface='TriggeredAnalogOutputInterface')

    _channel_mapping = ConfigOption(name='channel_mapping', missing='error')

    _sum_channels = ConfigOption(name='sum_channels', default=[], missing='nothing')
    _position_ranges = ConfigOption(name='position_ranges', missing='error')
    _frequency_ranges = ConfigOption(name='frequency_ranges', missing='error')
    _resolution_ranges = ConfigOption(name='resolution_ranges', missing='error')
    _input_channel_units = ConfigOption(name='input_channel_units', missing='error')
    _scan_units = ConfigOption(name='scan_units', missing='error')
    _backwards_line_resolution = ConfigOption(name='backwards_line_resolution', default=50)
    __max_move_velocity = ConfigOption(name='maximum_move_velocity', default=400e-6)
    _ao_trigger_channel = ConfigOption(name="ao_trigger_channel", missing='error')
    _threaded = True  # Interfuse is by default not threaded.

    sigNextDataChunk = QtCore.Signal()
    sigChangeTemperatureRegime = QtCore.Signal(bool)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._current_scan_frequency = -1
        self._current_scan_ranges = [tuple(), tuple()]
        self._current_scan_axes = tuple()
        self._current_scan_resolution = tuple()

        self._scan_data = None
        self.raw_data_container = None

        self._constraints = None
        
        self._target_pos = dict()
        self._stored_target_pos = dict()
        self._start_scan_after_cursor = False
        self._abort_cursor_move = False

        self.__ao_write_timer = None
        self._min_step_interval = 1e-3
        self._scanner_distance_atol = 1e-9

        self._thread_lock_cursor = Mutex()
        self._thread_lock_data = Mutex()

    def on_activate(self):
        # Sanity checks for ni_ao and ni finite sampling io
        # TODO check that config values within fsio range?
        assert set(self._position_ranges) == set(self._frequency_ranges) == set(self._resolution_ranges), \
            f'Channels in position ranges, frequency ranges and resolution ranges do not coincide'

        assert set(self._input_channel_units).union(self._position_ranges) == set(self._channel_mapping), \
            f'Not all specified channels are mapped to an ni card physical channel'


        mapped_channels = set([val.lower() for val in self._channel_mapping.values()])

        self._sum_channels = [ch.lower() for ch in self._sum_channels]
        if len(self._sum_channels) > 1:
            self._input_channel_units["sum"] = list(self._input_channel_units.values())[1]

        # Constraints
        axes = list()
        for axis in self._position_ranges:
            axes.append(ScannerAxis(name=axis,
                                    unit=self._scan_units,
                                    value_range=self._position_ranges[axis],
                                    step_range=(0, abs(np.diff(self._position_ranges[axis]))),
                                    resolution_range=self._resolution_ranges[axis],
                                    frequency_range=self._frequency_ranges[axis])
                        )
        channels = list()
        for channel, unit in self._input_channel_units.items():
            channels.append(ScannerChannel(name=channel,
                                           unit=unit,
                                           dtype=np.float64))

        self._constraints = ScanConstraints(axes=axes,
                                            channels=channels,
                                            backscan_configurable=False,  # TODO incorporate in scanning_probe toolchain
                                            has_position_feedback=False,  # TODO incorporate in scanning_probe toolchain
                                            square_px_only=False)  # TODO incorporate in scanning_probe toolchain
#
        self._target_pos = self.get_position()  # get voltages/pos from ni_ao
        self._toggle_ao_setpoint_channels(False)  # And free ao resources after that
        self._t_last_move = time.perf_counter()
        self.__t_last_follow = None
        self.sigChangeTemperatureRegime.connect(self._change_temperature_regime, QtCore.Qt.QueuedConnection)
        self.sigNextDataChunk.connect(self._fetch_data_chunk, QtCore.Qt.QueuedConnection)

    def _toggle_ao_setpoint_channels(self, enable: bool) -> None:
        triggered_ao = self._triggered_ao()
        for channel in triggered_ao.constraints.setpoint_channels:
            triggered_ao.set_activity_state(channel, enable)

    @property
    def _ao_setpoint_channels_active(self) -> bool:
        mapped_channels = set(self._channel_mapping.values())
        return all(
            state for ch, state in self._triggered_ao().activity_states.items() if ch in mapped_channels
        )

    def on_deactivate(self):
        """
        Deactivate the module
        """
        self._abort_cursor_movement()
        self._triggered_ao.stop_scan()

    def get_constraints(self):
        """ Get hardware constraints/limitations.

        @return dict: scanner constraints
        """
        return self._constraints


    def get_max_move_velocity(self):
        """Gets the maximum move velocity of the scanner that was set in the config.
        
        @return float: max velocity of te scanner
        """
        max_velocity = self.__max_move_velocity.copy()
        return max_velocity


    def reset(self):
        """ Hard reset of the hardware.
        """
        pass

    def configure_scan(self, scan_settings):
        """ Configure the hardware with all parameters needed for a 1D or 2D scan.

        @param dict scan_settings: scan_settings dictionary holding all the parameters 'axes', 'resolution', 'ranges'
        #  TODO update docstring in interface

        @return (bool, ScanSettings): Failure indicator (fail=True),
                                      altered ScanSettings instance (same as "settings")
        """

        if self.is_scan_running:
            self.log.error('Unable to configure scan parameters while scan is running. '
                           'Stop scanning and try again.')
            return True, self.scan_settings

        axes = scan_settings.get('axes', self._current_scan_axes)
        ranges = tuple(
            (min(r), max(r)) for r in scan_settings.get('range', self._current_scan_ranges)
        )
        resolution = scan_settings.get('resolution', self._current_scan_resolution)
        lines_to_scan = scan_settings.get('lines_to_scan', 1)
        frequency = float(scan_settings.get('frequency', self._current_scan_frequency))
        if self._backwards_line_resolution is None:
            self._backwards_line_resolution = int(resolution[0])
        else:
            self._backwards_line_resolution = int(scan_settings.get('backward_resolution', self._backwards_line_resolution)) 

        if not set(axes).issubset(self._position_ranges):
            self.log.error('Unknown axes names encountered. Valid axes are: {0}'
                           ''.format(set(self._position_ranges)))
            return True, self.scan_settings

        if len(axes) != len(ranges) or len(axes) != len(resolution):
            self.log.error('"axes", "range" and "resolution" must have same length.')
            return True, self.scan_settings
        for i, ax in enumerate(axes):
            for axis_constr in self._constraints.axes.values():
                if ax == axis_constr.name:
                    break
            if ranges[i][0] < axis_constr.min_value or ranges[i][1] > axis_constr.max_value:
                self.log.error('Scan range out of bounds for axis "{0}". Maximum possible range'
                               ' is: {1}'.format(ax, axis_constr.value_range))
                return True, self.scan_settings
            if resolution[i] < axis_constr.min_resolution or resolution[i] > axis_constr.max_resolution:
                self.log.error('Scan resolution out of bounds for axis "{0}". Maximum possible '
                               'range is: {1}'.format(ax, axis_constr.resolution_range))
                return True, self.scan_settings
            if self._backwards_line_resolution < axis_constr.min_resolution or self._backwards_line_resolution > axis_constr.max_resolution:
                self.log.error('Backward scan resolution out of bounds for axis "{0}". Maximum possible '
                               'range is: {1}'.format(ax, axis_constr.resolution_range))
                return True, self.scan_settings
            if i == 0:
                if frequency < axis_constr.min_frequency or frequency > axis_constr.max_frequency:
                    self.log.error('Scan frequency out of bounds for fast axis "{0}". Maximum '
                                   'possible range is: {1}'
                                   ''.format(ax, axis_constr.frequency_range))
                    return True, self.scan_settings
        
        with self._thread_lock_data:
            try:
                self._scan_data = ScanData(
                    channels=tuple(self._constraints.channels.values()),
                    scan_axes=tuple(self._constraints.axes[ax] for ax in axes),
                    scan_range=ranges,
                    scan_resolution=tuple(resolution),
                    scan_frequency=frequency,
                    position_feedback_axes=None
                )
                self.raw_data_container = RawDataContainer(self._scan_data.channels,
                                                            resolution[
                                                                1] if self._scan_data.scan_dimension == 2 else 1,
                                                            resolution[0],
                                                            self._backwards_line_resolution)
                # self.log.debug(f"New scanData created: {self._scan_data.data}")

            except:
                self.log.exception("")
                return True, self.scan_settings

            channels_tt = [int(ch[2:]) for ch in self.__active_channels['di_channels'] if "tt" in ch]
            clock_tt = int(self._tt_ni_clock_input[2:])
            #Workaround for the old time tagger version at the praktikum

            voltage_start = ranges[0]
            voltage_stop = ranges[1]
            sweep_duration = int(resolution[0]) / frequency # in sec

            #configure the scanner
            self._triggered_ao.set_scan_parameters(
                voltage_start = voltage_start,
                voltage_stop = voltage_stop,
                sweep_duration = sweep_duration
            )

            #configure the time tagger
            self._time_differences_tasks = [self._tt.time_differences(
                            click_channel = channel, 
                            start_channel = self._ao_trigger_channel,
                            next_channel = self._ao_trigger_channel,
                            binwidth=frequency,
                            n_bins=int(resolution[0]),
                            n_histograms=lines_to_scan) for channel in channels_tt]
            #configure the time tagger
            self._histogram_tasks = [self._tt.histogram(
                            channel = channel, 
                            trigger_channel = self._ao_trigger_channel,
                            bin_width=frequency,
                            number_of_bins=int(resolution[0]),
                           ) for channel in channels_tt]

            self._current_scan_resolution = tuple(resolution)
            self._current_scan_ranges = ranges
            self._current_scan_axes = tuple(axes)
            self._current_scan_frequency = frequency
            self._current_lines_to_scan = lines_to_scan

            return False, self.scan_settings

    def move_absolute(self, position, velocity=None, blocking=False):
        """ Move the scanning probe to an absolute position as fast as possible or with a defined
        velocity.

        Log error and return current target position if something fails or a scan is in progress.
        """

        # assert not self.is_running, 'Cannot move the scanner while, scan is running'
        if self.is_scan_running:
            self.log.error('Cannot move the scanner while, scan is running')
            return self.get_target()

        if not set(position).issubset(self.get_constraints().axes):
            self.log.error('Invalid axes name in position')
            return self.get_target()

        try:
            self._prepare_movement(position, velocity=velocity)

            self.__start_ao_write_timer()
            if blocking:
                self.__wait_on_move_done()

            self._t_last_move = time.perf_counter()

            return self.get_target()
        except:
            self.log.exception("Couldn't move: ")

    def __wait_on_move_done(self):
        try:
            t_start = time.perf_counter()
            while self.is_move_running:
                self.log.debug(f"Waiting for move done: {self.is_move_running}, {1e3*(time.perf_counter()-t_start)} ms")
                QGuiApplication.processEvents()
                time.sleep(self._min_step_interval)

            #self.log.debug(f"Move_abs finished after waiting {1e3*(time.perf_counter()-t_start)} ms ")
        except:
            self.log.exception("")

    def move_relative(self, distance, velocity=None, blocking=False):
        """ Move the scanning probe by a relative distance from the current target position as fast
        as possible or with a defined velocity.

        Log error and return current target position if something fails or a 1D/2D scan is in
        progress.
        """
        current_position = self.get_position()
        end_pos = {ax: current_position[ax] + distance[ax] for ax in distance}
        self.move_absolute(end_pos, velocity=velocity, blocking=blocking)

        return end_pos

    def get_target(self):
        """ Get the current target position of the scanner hardware
        (i.e. the "theoretical" position).

        @return dict: current target position per axis.
        """
        if self.is_scan_running:
            return self._stored_target_pos
        else:
            return self._target_pos

    def get_position(self):
        """ Get a snapshot of the actual scanner position (i.e. from position feedback sensors).
        For the same target this value can fluctuate according to the scanners positioning accuracy.

        For scanning devices that do not have position feedback sensors, simply return the target
        position (see also: ScanningProbeInterface.get_target).

        @return dict: current position per axis.
        """
        with self._thread_lock_cursor:
            if not self._ao_setpoint_channels_active:
                self._toggle_ao_setpoint_channels(True)

            pos = self._voltage_dict_to_position_dict(self._ni_ao().setpoints)
            return pos

    def start_scan(self):
        try:

            #self.log.debug(f"Start scan in thread {self.thread()}, QT.QThread {QtCore.QThread.currentThread()}... ")

            if self.thread() is not QtCore.QThread.currentThread():
                QtCore.QMetaObject.invokeMethod(self, '_start_scan',
                                                QtCore.Qt.BlockingQueuedConnection)
            else:
                self._start_scan()

        except:
            self.log.exception("")
            return -1

        return 0

    @QtCore.Slot()
    def _start_scan(self):
        """

        @return (bool): Failure indicator (fail=True)
        """
        try:
            if self._scan_data is None:
                # todo: raising would be better, but from this delegated thread exceptions get lost
                self.log.error('Scan Data is None. Scan settings need to be configured before starting')

            if self.is_scan_running:
                self.log.error('Cannot start a scan while scanning probe is already running')

            with self._thread_lock_data:
                self._scan_data.new_scan()
                #self.log.debug(f"New scan data: {self._scan_data.data}, position {self._scan_data._position_data}")
                self._stored_target_pos = self.get_target().copy()
                self._scan_data.scanner_target_at_start = self._stored_target_pos

            # todo: scanning_probe_logic exits when scanner not locked right away
            # should rather ignore/wait until real hw timed scanning starts
            self.module_state.lock()

            first_scan_position = {ax: pos[0] for ax, pos
                                   in zip(self.scan_settings['axes'], self.scan_settings['range'])}
            self._move_to_and_start_scan(first_scan_position)

        except Exception:
            self.module_state.unlock()
            self.log.exception("Starting scan failed: ")


    def stop_scan(self):
        """
        @return bool: Failure indicator (fail=True)
        # todo: return values as error codes are deprecated
        """

        #self.log.debug("Stopping scan")
        if self.thread() is not QtCore.QThread.currentThread():
            QtCore.QMetaObject.invokeMethod(self, '_stop_scan',
                                            QtCore.Qt.BlockingQueuedConnection)
        else:
            self._stop_scan()

        return 0

    @QtCore.Slot()
    def _stop_scan(self):

        # self.log.debug("Stopping scan...")
        self._start_scan_after_cursor = False  # Ensure Scan HW is not started after movement
        if self._ao_setpoint_channels_active:
            self._abort_cursor_movement()
            # self.log.debug("Move aborted")

        if self._ni_finite_sampling_io().is_running:
            self._ni_finite_sampling_io().stop_buffered_frame()
            # self.log.debug("Frame stopped")

        self.module_state.unlock()
        # self.log.debug("Module unlocked")

        self.move_absolute(self._stored_target_pos)
        self._stored_target_pos = dict()

    def get_scan_data(self):
        """

        @return (ScanData): ScanData instance used in the scan
        #  TODO change interface
        """

        if self._scan_data is None:
            raise RuntimeError('ScanData is not yet configured, please call "configure_scan" first')
        try:
            with self._thread_lock_data:
                return self._scan_data.copy()
        except:
            self.log.exception("")

    def emergency_stop(self):
        """

        @return:
        """
        # TODO: Implement. Yet not used in logic till yet? Maybe sth like this:
        # self._ni_finite_sampling_io().terminate_all_tasks()
        # self._ni_ao().set_activity_state(False)
        pass

    @property
    def is_scan_running(self):
        """
        Read-only flag indicating the module state.

        @return bool: scanning probe is running (True) or not (False)
        """
        # module state used to indicate hw timed scan running
        #self.log.debug(f"Module in state: {self.module_state()}")
        #assert self.module_state() in ('locked', 'idle')  # TODO what about other module states?
        if self.module_state() == 'locked':
            return True
        else:
            return False

    @property
    def is_move_running(self):
        with self._thread_lock_cursor:
            running = self.__t_last_follow is not None
            return running

    @property
    def scan_settings(self):

        settings = {'axes': tuple(self._current_scan_axes),
                    'range': tuple(self._current_scan_ranges),
                    'resolution': tuple(self._current_scan_resolution),
                    'frequency': self._current_scan_frequency}
        return settings

    def _check_scan_end_reached(self):
        # not thread safe, call from thread_lock protected code only
        #FIx this shit
        
        return self.raw_data_container.is_full and self._ni_finite_sampling_io()._scanner_ready

    def _fetch_data_chunk(self):
        try:
            data_td = {}
            data_hist = {}
            for num, di_channel in enumerate(self.__active_channels['di_channels']):
                data_td[di_channel] = self._time_differences_tasks[num].getData()
                data_hist[di_channel] = self._histogram_tasks[num].getData()
                

            reverse_routing = {val.lower(): key for key, val in self._channel_mapping.items()}

            new_data = {reverse_routing[key]: samples for key, samples in data_hist.items()}
            if len(self._sum_channels) > 1:
                new_data["sum"] = np.sum([samples for key, samples in data_hist.items() if key in self._sum_channels], axis=0)
            # self.log.debug(f'new data: {new_data}')

            with self._thread_lock_data:
                self.raw_data_container.fill_container(new_data)
                self._scan_data.data = self.raw_data_container.forwards_data()
                # if self._backwards_line_resolution == len(self.raw_data_container.backwards_data()):
                self._scan_data.retrace_data = self.raw_data_container.backwards_data()
                if self._check_scan_end_reached():

                    # if self._scan_data.accumulated is None:
                    #     self._scan_data.accumulated = self._scan_data.data
                    # else:
                    #     self._scan_data.accumulated = {channel : 
                    #             np.vstack((self._scan_data.accumulated[channel], data_i)) \
                    #             for channel, data_i in self._scan_data.data.items() if len(data_i) > 0}
                        
                    # if self._scan_data.retrace_accumulated is None:
                    #     self._scan_data.retrace_accumulated = self._scan_data.retrace_data
                    # else:
                    #     self._scan_data.retrace_accumulated = {channel : 
                    #             np.vstack((self._scan_data.retrace_accumulated[channel], data_i)) \
                    #                 for channel, data_i in self._scan_data.retrace_data.items() if len(data_i) > 0}
                    self.stop_scan()
                elif not self.is_scan_running:
                    return
                else:
                    self.sigNextDataChunk.emit()

        except:
            self.log.exception("")
            self.stop_scan()

    def _position_to_voltage(self, axis, positions):
        """
        @param str axis: scanner axis name for which the position is to be converted to voltages
        @param np.array/single value position(s): Position (value(s)) to convert to voltage(s) of corresponding
        ni_channel derived from axis string

        @return np.array/single value: Position(s) converted to voltage(s) (value(s)) [single value & 1D np.array depending on input]
                      for corresponding ni_channel (keys)
        """

        channel = self._channel_mapping[axis]
        voltage_range = self._triggered_ao.constraints.output_channel_limits[channel]
        position_range = self.get_constraints().axes[axis].value_range

        slope = np.diff(voltage_range) / np.diff(position_range)
        intercept = voltage_range[1] - position_range[1] * slope

        converted = np.clip(positions * slope + intercept, min(voltage_range), max(voltage_range))

        try:
            # In case of single value, use just this value
            voltage_data = converted.item()
        except ValueError:
            voltage_data = converted

        return voltage_data

    def _pos_dict_to_vec(self, position):

        pos_list = [el[1] for el in sorted(position.items())]
        return np.asarray(pos_list)

    def _pos_vec_to_dict(self, position_vec):

        if isinstance(position_vec, dict):
            raise ValueError(f"Position can't be provided as dict.")

        axes = sorted(self.get_constraints().axes.keys())
        return {axes[idx]: pos for idx, pos in enumerate(position_vec)}

    def _voltage_dict_to_position_dict(self, voltages):
        """
        @param dict voltages: Voltages (value(s)) to convert to position(s) of corresponding scanner axis (keys)

        @return dict: Voltage(s) converted to position(s) (value(s)) [single value & 1D np.array depending on input] for
                      for corresponding axis (keys)
        """

        reverse_routing = {val.lower(): key for key, val in self._channel_mapping.items()}

        # TODO check voltages given correctly checking?
        positions_data = dict()
        for channel in voltages:
            try:
                axis = reverse_routing[channel]
                voltage_range = self._triggered_ao.constraints.output_channel_limits[channel]
                position_range = self.get_constraints().axes[axis].value_range

                slope = np.diff(position_range) / np.diff(voltage_range)
                intercept = position_range[1] - voltage_range[1] * slope

                converted = voltages[channel] * slope + intercept
                # round position values to 100 pm. Avoids float precision errors
                converted = np.around(converted, 10)
            except KeyError:
                # if one of the AO channels is not used for confocal
                continue

            try:
                # In case of single value, use just this value
                positions_data[axis] = converted.item()
            except ValueError:
                positions_data[axis] = converted

        return positions_data


    def _update_position_ranges(self, new_position_ranges):
        self._position_ranges = new_position_ranges
        # Constraints
        axes = list()
        for axis in self._position_ranges:
            axes.append(ScannerAxis(name=axis,
                                    unit=self._scan_units,
                                    value_range=self._position_ranges[axis],
                                    step_range=(0, abs(np.diff(self._position_ranges[axis]))),
                                    resolution_range=self._resolution_ranges[axis],
                                    frequency_range=self._frequency_ranges[axis])
                        )
        channels = list()
        for channel, unit in self._input_channel_units.items():
            channels.append(ScannerChannel(name=channel,
                                           unit=unit,
                                           dtype=np.float64))

        self._constraints = ScanConstraints(axes=axes,
                                            channels=channels,
                                            backscan_configurable=False,  # TODO incorporate in scanning_probe toolchain
                                            has_position_feedback=False,  # TODO incorporate in scanning_probe toolchain
                                            square_px_only=False)  # TODO incorporate in scanning_probe toolchain
        self._scan_data = None

class RawDataContainer:

    def __init__(self, channel_keys, number_of_scan_lines, forward_line_resolution, backwards_line_resolution):
        self.forward_line_resolution = forward_line_resolution
        self.number_of_scan_lines = number_of_scan_lines
        self.forward_line_resolution = forward_line_resolution
        self.backwards_line_resolution = backwards_line_resolution
        self.frame_aquired = False
        self.frame_size = number_of_scan_lines * (forward_line_resolution + backwards_line_resolution)
        self._raw = {key: np.full(self.frame_size, np.nan) for key in channel_keys}

    def fill_container(self, samples_dict):
        # get index of first nan from one element of dict
        #Checking if the whole frame coming at once from the time tagger or these are chuncks from the NI counter
        if self.number_of_non_nan_values == self.frame_size:
            first_nan_idx = 0
        else:
            first_nan_idx = self.number_of_non_nan_values

        for key, samples in samples_dict.items():
            self._raw[key][first_nan_idx:first_nan_idx + len(samples)] = samples

    def forwards_data(self):
        reshaped_2d_dict = dict.fromkeys(self._raw)
        for key in self._raw:
            if self.number_of_scan_lines > 1:
                reshaped_arr = self._raw[key].reshape(self.number_of_scan_lines,
                                                      self.forward_line_resolution + self.backwards_line_resolution)
                reshaped_2d_dict[key] = reshaped_arr[:, :self.forward_line_resolution].T
            elif self.number_of_scan_lines == 1:
                reshaped_2d_dict[key] = self._raw[key][:self.forward_line_resolution]
        return reshaped_2d_dict

    def backwards_data(self):
        reshaped_2d_dict = dict.fromkeys(self._raw)
        for key in self._raw:
            if self.number_of_scan_lines > 1:
                reshaped_arr = self._raw[key].reshape(self.number_of_scan_lines,
                                                      self.forward_line_resolution + self.backwards_line_resolution)
                reshaped_2d_dict[key] = reshaped_arr[:, self.forward_line_resolution:].T
            elif self.number_of_scan_lines == 1:
                reshaped_2d_dict[key] = self._raw[key][self.forward_line_resolution:]

        return reshaped_2d_dict

    @property
    def number_of_non_nan_values(self):
        """
        returns number of not NaN samples
        """
        return np.sum(~np.isnan(next(iter(self._raw.values()))))

    @property
    def is_full(self):
        return self.number_of_non_nan_values == self.frame_size
    

