# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module for controlling scans of the
fourth analog output channel.  It was originally written for
scanning laser frequency, but it can be used to control any parameter
in the experiment that is voltage controlled.  The hardware
range is typically -10 to +10 V.
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

from PySide2 import QtCore
import copy as cp

from qudi.core.module import LogicBase
from qudi.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar

class LaserScannerLogic(LogicBase):

    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """

    sig_data_updated = QtCore.Signal()

    # declare connectors
    confocalscanner1 = Connector(interface='ConfocalScannerInterface')
    savelogic = Connector(interface='SaveLogic')
    wavemeter = Connector(interface='HighFinesseWavemeterClient')
    dye_controller = Connector(interface='DyeControllerClient')
    # stepmotor = Connector(interface = 'Motordriver', missing='warn')

    scan_range = StatusVar('scan_range', [0, 30000])
    number_of_repeats = StatusVar(default=10)
    resolution = StatusVar('resolution', 5000)
    _scan_speed = StatusVar('scan_speed', 15000)
    _static_v = StatusVar('goto_voltage', 0)

    sigChangeVoltage = QtCore.Signal(float)
    sigVoltageChanged = QtCore.Signal(float)
    sigScanNextLine = QtCore.Signal()
    sigUpdatePlots = QtCore.Signal()
    sigScanFinished = QtCore.Signal()
    sigScanStarted = QtCore.Signal()
    sigRunEtaScan = QtCore.Signal()
    sig_start_scan = QtCore.Signal()

    is_wlm = False

    def __init__(self, **kwargs):
        """ Create VoltageScanningLogic object with connectors.
          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()
        self.stopRequested = False
        self.eta_calib = None
        self.fit_x = []
        self.fit_y = []
        self.plot_x = []
        self.plot_y = []
        self.plot_x_stitched = []
        self.plot_y_stitched=[]
        self.plot_y_2 = []
        self.plot_y2 = []
        self.etas = []
        self.is_running_eta_scan = False
        self.large_scan_matrix = dict()
        # self.ple_matrix = np.zeros((10 * self.resolution, self.number_of_repeats))

    def add_scan_data(self):
        if np.all(self.scan_matrix_stitched == 0):
            self._initialize_stitched_matrix()
        idx_stop = np.argmin(np.abs(self.stitched_scan_length - self.wavelength_start))
        idx_start = np.argmin(np.abs(self.stitched_scan_length - self.wavelength_stop))
        # self.scan_length = np.linspace(self.wavelength_start, self.wavelength_stop, self.resolution)
        number_samples = np.abs(idx_stop - idx_start)
        self.numb_samples = number_samples
        print(number_samples)
        if (number_samples > 2*self.scan_matrix.shape[1]) or (number_samples < 0.5*self.scan_matrix.shape[1]):
            print("MODE HOPPING")
            return
        rng = default_rng()
        if (number_samples) >= self.scan_matrix.shape[1]:
            print('LARGER THAN EXPECTED')
            #oversample a bit 
            numbers = rng.choice(self.scan_matrix.shape[1]-1, size=number_samples - self.scan_matrix.shape[1], replace=False)
            new_idxs = np.sort(np.append(np.arange(self.scan_matrix.shape[1]), numbers))
        elif (number_samples) < self.scan_matrix.shape[1]:
            print('SMALLER THAN EXPECTED')
            #shuffle and undersample indices excluding the start and the end
            numbers = rng.choice(np.arange(1, self.scan_matrix.shape[1]-1), size= number_samples - 2, replace=False)
            new_idxs = np.sort(np.append(np.array([0, self.scan_matrix.shape[1]-1]), numbers))

        if self.scan_matrix_stitched[:, idx_start:idx_stop].shape != self.scan_matrix[:,new_idxs].shape:
            print("SMTH AGAIN IS WRONG WIT THE SHAPES OF THE SCAN MATRICES")
            return

        if np.any(self.scan_matrix_stitched_mask):
            self.scan_matrix_stitched[:, idx_start:idx_stop] = self.scan_matrix_stitched[:, idx_start:idx_stop] + self.scan_matrix[:,new_idxs]
            self.scan_matrix_stitched_mask[:, idx_start:idx_stop] = ~self.scan_matrix_stitched_mask[:, idx_start:idx_stop]
            # self.scan_matrix_stitched_mask = self.scan_matrix_stitched != 0
            self.scan_matrix_stitched[~self.scan_matrix_stitched_mask] = self.scan_matrix_stitched[~self.scan_matrix_stitched_mask]/2 # divide by two all zeros and doubled values
        else:
            self.scan_matrix_stitched[:, idx_start:idx_stop] = self.scan_matrix_stitched[:, idx_start:idx_stop] + self.scan_matrix[:,new_idxs]
            # self.scan_matrix_stitched_mask[:, idx_start:idx_stop] = ~self.scan_matrix_stitched_mask[:, idx_start:idx_stop]
        self.scan_matrix_stitched_mask[:, idx_start:idx_stop] = np.ones(self.scan_matrix_stitched_mask[:, idx_start:idx_stop].shape).astype(bool)
        #TODO average overlapping spectra
        

        return self.scan_matrix[:,new_idxs]
    def run_eta_scan(self):
        delay(1000)
        if len(self.etas) > 0:
            eta, self.etas = self.etas[-1], self.etas[:-1]
            self._dye_controller.set_thin_etalon_voltage(eta)
            self.sig_start_scan.emit()
        else:
            self.is_running_eta_scan =False
            self.sigScanFinished.emit()
            print("SCANNED ALL")

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._scanning_device = self.confocalscanner1()
        self._save_logic = self.savelogic()
        self._wavemeter = self.wavemeter()
        self._dye_controller = self.dye_controller()
        # self._motor = self.stepmotor()

        self.saturation_scan=False

        # Reads in the maximal scanning range. The unit of that scan range is
        # micrometer!
        self.a_range = self._scanning_device.get_position_range()[3]

        # Initialise the current position of all four scanner channels.
        self.current_position = self._scanning_device.get_scanner_position()

        # initialise the range for scanning
        self.set_scan_range(self.scan_range)

        # Keep track of the current static voltage even while a scan may cause the real-time
        # voltage to change.
        self.goto_voltage(self._static_v)

        # Sets connections between signals and functions
        self.sigChangeVoltage.connect(self._change_voltage, QtCore.Qt.QueuedConnection)
        self.sigScanNextLine.connect(self._do_next_line, QtCore.Qt.QueuedConnection)
        self.sigRunEtaScan.connect(self.run_eta_scan, QtCore.Qt.QueuedConnection)
        self.sig_start_scan.connect(self.start_scanning, QtCore.Qt.QueuedConnection)
        # Initialization of internal counter for scanning
        self._scan_counter_up = 0
        self._scan_counter_down = 0
        # Keep track of scan direction
        self.upwards_scan = True

        # calculated number of points in a scan, depends on speed and max step size
        self._num_of_steps = 50  # initialising.  This is calculated for a given ramp.

        #############################

        # TODO: allow configuration with respect to measurement duration
        self.acquire_time = 20  # seconds

        # default values for clock frequency and slowness
        # slowness: steps during retrace line
        self.set_resolution(self.resolution)
        self._goto_speed = 10  # 0.01  # volt / second
        self.set_scan_speed(self._scan_speed)
        self._smoothing_steps = 10  # steps to accelerate between 0 and scan_speed
        self._max_step = 0.01  # volt

        ##############################

        # Initialie data matrix
        self._initialise_data_matrix(100)
        self.stitched_scan_length = np.linspace(0, 10, int(self.resolution ))
        self.scan_matrix_stitched = np.zeros((self.number_of_repeats, self.resolution))
        

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.stopRequested = True

    @QtCore.Slot(int)
    def move_motor(self, direction):
        self._dye_controller.set_motor_direction(direction)
        self._dye_controller.move_motor_pulse()

    @QtCore.Slot(float)
    def goto_eta_voltage(self, volts=None):
        if volts == None:
            return 
        self._dye_controller.set_thin_etalon_voltage(volts)

    @QtCore.Slot(float)
    def goto_voltage(self, volts=None):
        """Forwarding the desired output voltage to the scanning device.
        @param float volts: desired voltage (volts)
        @return int: error code (0:OK, -1:error)
        """
        # print(tag, x, y, z)
        # Changes the respective value
        if volts is not None:
            self._static_v = volts

        # Checks if the scanner is still running
        if (self.module_state() == 'locked'
                or self._scanning_device.module_state() == 'locked'):
            self.log.error('Cannot goto, because scanner is locked!')
            return -1
        else:
            self.sigChangeVoltage.emit(volts)
            return 0

    def _change_voltage(self, new_voltage):
        """ Threaded method to change the hardware voltage for a goto.
        @return int: error code (0:OK, -1:error)
        """
        ramp_scan = self._generate_ramp(self.get_current_voltage(), new_voltage, self._goto_speed)
        self._initialise_scanner()
        ignored_counts = self._scan_line(ramp_scan)
        self._close_scanner()
        self.sigVoltageChanged.emit(new_voltage)
        return 0

    def _goto_during_scan(self, voltage=None):

        if voltage is None:
            return -1

        goto_ramp = self._generate_ramp(self.get_current_voltage(), voltage, self._goto_speed)
        ignored_counts = self._scan_line(goto_ramp)

        return 0

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock
        @param int clock_frequency: desired frequency of the clock
        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = float(clock_frequency)
        # checks if scanner is still running
        if self.module_state() == 'locked':
            return -1
        else:
            return 0

    def run_eta_calibration(self):
        eta_calib = np.array([0, 0])
        for eta_v in np.linspace(-10, 0, 40):
            self._dye_controller.set_thin_etalon_voltage(eta_v)
            delay(500)
            eta_calib = np.vstack((eta_calib, np.array([eta_v, self._wavemeter.get_current_wavelength()])))
            print(self._wavemeter.get_current_wavelength())
        self.eta_calib = eta_calib[1:]
        self.etas = np.sort(self.eta_calib, axis=0)[:,0]
        # self.lam_min, self.lam_max = self._initialize_stitched_matrix()
        r1 = (np.roll(self.eta_calib[:, 1], 1) - self.eta_calib[:, 1])
        r2 = (np.roll(self.eta_calib[:, 1], 2) - self.eta_calib[:, 1])
        r3 = (np.roll(self.eta_calib[:, 1], 3) - self.eta_calib[:, 1])
        ri = [np.roll(self.eta_calib[:, 1], i) - self.eta_calib[:, 1] for i in np.arange(1,4)]
        self.most_stable_v = self.eta_calib[:, 0][(ri[0]>0)*(ri[1]>0)*(ri[2]>0)][0]
        self.etas = np.append(self.most_stable_v, self.etas)
        self._dye_controller.set_thin_etalon_voltage(self.most_stable_v)
        # self.sig_start_scan.emit()
        return self.eta_calib

    def run_motor_calibration(self):
        return 0

    def set_resolution(self, resolution):
        """ Calculate clock rate from scan speed and desired number of pixels """
        self.resolution = resolution
        scan_range = abs(self.scan_range[1] - self.scan_range[0])
        duration = scan_range / self._scan_speed
        new_clock = resolution / duration
        return self.set_clock_frequency(new_clock)

    def set_scan_range(self, scan_range):
        """ Set the scan rnage """
        # r_max = np.clip(scan_range[1], self.a_range[0], self.a_range[1])
        # r_min = np.clip(scan_range[0], self.a_range[0], r_max)
        # self.scan_range = [r_min, r_max]
        self.scan_range = scan_range

    def set_voltage(self, volts):
        """ Set the channel idle voltage """
        self._static_v = np.clip(volts, self.a_range[0], self.a_range[1])
        self.goto_voltage(self._static_v)

    def set_scan_speed(self, scan_speed):
        """ Set scan speed in volt per second """
        self._scan_speed = np.clip(scan_speed, 1e-9, 2e6)
        self._goto_speed = self._scan_speed

    def set_scan_lines(self, scan_lines):
        self.number_of_repeats = int(np.clip(scan_lines, 1, 1e6))

    def _initialise_data_matrix(self, scan_length):
        """ Initializing the ODMR matrix plot. """

        # self.scan_matrix_stitched = np.zeros((self.number_of_repeats, scan_length))

        self.scan_matrix = np.zeros((self.number_of_repeats, scan_length))
        self.scan_matrix2 = np.zeros((self.number_of_repeats, scan_length))
        self.plot_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length)
        self.plot_y = np.zeros(scan_length)
        self.plot_y_2 = np.zeros(scan_length)
        self.plot_y2 = np.zeros(scan_length)
        self.fit_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length)
        self.fit_y = np.zeros(scan_length)
        # if self.eta_calib is not None:
        #     # self.stitched_scan_length = np.linspace(lam_min, lam_max, int(self.resolution * (delta_nu / 10)))
        #     self.scan_matrix_stitched = np.zeros((self.number_of_repeats, len(self.stitched_scan_length)))


    def _initialize_stitched_matrix(self):
        lam_min, lam_max = np.min(self.eta_calib[:,1]), np.max(self.eta_calib[:,1])
        freq_max = wavelength_to_freq([lam_min])[0]
        freq_min = wavelength_to_freq([lam_max])[0]

        lam_scan_min, lam_scan_max = self.wavelength_stop, self.wavelength_start
        freq_scan_max = wavelength_to_freq([lam_scan_min])[0]
        freq_scan_min = wavelength_to_freq([lam_scan_max])[0]


        delta_nu = (freq_max - freq_min)* (1e-9) #GHz
        delta_nu_scan = (freq_scan_max - freq_scan_min)* (1e-9) #GHz
        print("DELTA NU, ", delta_nu )
        print("DELTA NUs scan, ", delta_nu_scan )
        # lam_min = freq_to_wavelength([wavelength_to_freq([lam_min])[0] - 10*1e9])[0]
        # delta_nu = abs(wavelength_to_freq([lam_max])[0] - wavelength_to_freq([lam_min])[0])
        self.stitched_scan_length = np.linspace(lam_min, lam_max, int(self.resolution * (delta_nu / delta_nu_scan)))
        self.scan_matrix_stitched = np.zeros((self.number_of_repeats, len(self.stitched_scan_length)))
        self.scan_matrix_stitched_mask = np.zeros((self.number_of_repeats, len(self.stitched_scan_length))).astype(bool)
        return lam_min, lam_max

    def get_current_voltage(self):
        """returns current voltage of hardware device(atm NIDAQ 4th output)"""
        return self._scanning_device.get_scanner_position()[3]

    def _initialise_scanner(self):
        """Initialise the clock and locks for a scan"""
        self.module_state.lock()
        self._scanning_device.module_state.lock()

        returnvalue = self._scanning_device.set_up_scanner_clock(
            clock_frequency=self._clock_frequency)
        if returnvalue < 0:
            self._scanning_device.module_state.unlock()
            self.module_state.unlock()
            self.set_position('scanner')
            return -1

        returnvalue = self._scanning_device.set_up_scanner()
        if returnvalue < 0:
            self._scanning_device.module_state.unlock()
            self.module_state.unlock()
            self.set_position('scanner')
            return -1

        return 0
    @QtCore.Slot()
    def start_scanning(self, v_min=None, v_max=None):
        """Setting up the scanner device and starts the scanning procedure
        @return int: error code (0:OK, -1:error)
        """
        self.wavelength_start = self._wavemeter.get_current_wavelength()
        self.wavelength_stop = 0
        self.current_position = self._scanning_device.get_scanner_position()
        print(self.current_position)

        if v_min is not None:
            self.scan_range[0] = v_min
        else:
            v_min = self.scan_range[0]
        if v_max is not None:
            self.scan_range[1] = v_max
        else:
            v_max = self.scan_range[1]

        self._scan_counter_up = 0
        self._scan_counter_down = 0
        self.upwards_scan = True

        # TODO: Generate Ramps
        self._upwards_ramp = self._generate_ramp(v_min, v_max, self._scan_speed)
        self._downwards_ramp = self._generate_ramp(v_max, v_min, self._scan_speed)

        self._initialise_data_matrix(len(self._upwards_ramp[3]))

        # Lock and set up scanner
        returnvalue = self._initialise_scanner()
        if returnvalue < 0:
            # TODO: error message
            return -1

        self.sigScanNextLine.emit()
        self.sigScanStarted.emit()
        return 0

    def stop_scanning(self):
        """Stops the scan
        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
        return 0

    def _close_scanner(self):
        """Close the scanner and unlock"""
        with self.threadlock:
            self.kill_scanner()
            self.stopRequested = False
            if self.module_state.can('unlock'):
                self.module_state.unlock()

    def _do_next_line(self):
        """ If stopRequested then finish the scan, otherwise perform next repeat of the scan line
        """
        # stops scanning
        if self.stopRequested or self._scan_counter_down >= self.number_of_repeats:
            if self._scan_counter_down >= self.number_of_repeats:
                wlm_range = (wavelength_to_freq(np.array([self.wavelength_start])) - wavelength_to_freq(np.array([self.wavelength_stop])))/1e9
                if wlm_range < 20:
                    self.add_scan_data()
                else:
                    print("MODE HOPPING")
                print(self.wavelength_start, self.wavelength_stop)
                print(wlm_range, ' GHz')

            print(self.current_position)
            if self.is_running_eta_scan:
                self._close_scanner()
                self.sigUpdatePlots.emit()
                
                self.sigRunEtaScan.emit()
            else:
                self._goto_during_scan(self._static_v)
                self._close_scanner()
                self.sigScanFinished.emit()
            
            return

        if self._scan_counter_up == 0:
            # move from current voltage to start of scan range.
            self._goto_during_scan(self.scan_range[0])

        if self.upwards_scan:
            delay(300)
            self.wavelength_start = self._wavemeter.get_current_wavelength()#)/2(self.wavelength_start + 
            if self.saturation_scan:
                self._motor.moveRelative(pos = 2)
            counts = self._scan_line(self._upwards_ramp, pixel_clock=True)
            self.scan_matrix[self._scan_counter_up] = counts
            self.plot_y += counts
            self._scan_counter_up += 1
            self.upwards_scan = False
            self.plot_y_2 = counts
        else:
            delay(300)
            self.wavelength_stop = self._wavemeter.get_current_wavelength()
            counts = self._scan_line(self._downwards_ramp)
            self.scan_matrix2[self._scan_counter_down] = counts
            self.plot_y2 += counts
            self._scan_counter_down += 1
            self.upwards_scan = True
        
        self.sigUpdatePlots.emit()
        self.sigScanNextLine.emit()

    def _generate_ramp(self, voltage1, voltage2, speed):
        """Generate a ramp vrom voltage1 to voltage2 that
        satisfies the speed, step, smoothing_steps parameters.  Smoothing_steps=0 means that the
        ramp is just linear.
        @param float voltage1: voltage at start of ramp.
        @param float voltage2: voltage at end of ramp.
        """

        # It is much easier to calculate the smoothed ramp for just one direction (upwards),
        # and then to reverse it if a downwards ramp is required.

        v_min = min(voltage1, voltage2)
        v_max = max(voltage1, voltage2)

        if v_min == v_max:
            ramp = np.array([v_min, v_max])
        else:
            # These values help simplify some of the mathematical expressions
            linear_v_step = speed / self._clock_frequency
            smoothing_range = self._smoothing_steps + 1

            # Sanity check in case the range is too short

            # The voltage range covered while accelerating in the smoothing steps
            v_range_of_accel = sum(
                n * linear_v_step / smoothing_range for n in range(0, smoothing_range)
                )

            # Obtain voltage bounds for the linear part of the ramp
            v_min_linear = v_min + v_range_of_accel
            v_max_linear = v_max - v_range_of_accel

            if v_min_linear > v_max_linear:
                # self.log.warning(
                #     'Voltage ramp too short to apply the '
                #     'configured smoothing_steps. A simple linear ramp '
                #     'was created instead.')
                num_of_linear_steps = np.rint((v_max - v_min) / linear_v_step)
                ramp = np.linspace(v_min, v_max, int(num_of_linear_steps))

            else:

                num_of_linear_steps = np.rint((v_max_linear - v_min_linear) / linear_v_step)

                # Calculate voltage step values for smooth acceleration part of ramp
                smooth_curve = np.array(
                    [sum(
                        n * linear_v_step / smoothing_range for n in range(1, N)
                        ) for N in range(1, smoothing_range)
                    ])

                accel_part = v_min + smooth_curve
                decel_part = v_max - smooth_curve[::-1]

                linear_part = np.linspace(v_min_linear, v_max_linear, int(num_of_linear_steps))

                ramp = np.hstack((accel_part, linear_part, decel_part))

        # Reverse if downwards ramp is required
        if voltage2 < voltage1:
            ramp = ramp[::-1]

        # Put the voltage ramp into a scan line for the hardware (4-dimension)
        spatial_pos = self._scanning_device.get_scanner_position()

        scan_line = np.vstack((
            np.ones((len(ramp), )) * spatial_pos[0],
            np.ones((len(ramp), )) * spatial_pos[1],
            np.ones((len(ramp), )) * spatial_pos[2],
            ramp
            ))

        return scan_line

    def _scan_line(self, line_to_scan=None, pixel_clock = False):
        """do a single voltage scan from voltage1 to voltage2
        """
        if line_to_scan is None:
            self.log.error('Voltage scanning logic needs a line to scan!')
            return -1
        try:
            # scan of a single line
            if pixel_clock:
                counts_on_scan_line = self._scanning_device.scan_line(line_to_scan, pixel_clock = True)
            else:
                counts_on_scan_line = self._scanning_device.scan_line(line_to_scan)
            return counts_on_scan_line.transpose()[0]

        except Exception as e:
            self.log.error('The scan went wrong, killing the scanner.')
            self.stop_scanning()
            self.sigScanNextLine.emit()
            raise e

    def kill_scanner(self):
        """Closing the scanner device.
        @return int: error code (0:OK, -1:error)
        """
        try:
            self._scanning_device.close_scanner()
            self._scanning_device.close_scanner_clock()
        except Exception as e:
            self.log.exception('Could not even close the scanner, giving up.')
            raise e
        try:
            if self._scanning_device.module_state.can('unlock'):
                self._scanning_device.module_state.unlock()
        except:
            self.log.exception('Could not unlock scanning device.')
        return 0

    def save_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Save the counter trace data and writes it to a file.
        @return int: error code (0:OK, -1:error)
        """
        tag = str(self.wavelength_start)
        if tag is None:
            tag = ''

        self._saving_stop_time = time.time()

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath2 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath3 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        timestamp = datetime.datetime.now()

        if len(tag) > 0:
            filelabel = tag + '_volt_data'
            filelabel2 = tag + '_volt_data_raw_trace'
            filelabel3 = tag + '_volt_data_raw_retrace'
        else:
            filelabel = 'volt_data'
            filelabel2 = 'volt_data_raw_trace'
            filelabel3 = 'volt_data_raw_retrace'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data['frequency (Hz)'] = self.plot_x
        data['trace count data (counts/s)'] = self.plot_y
        # data['trace count data (counts/s)'] = self.plot_y_2
        data['retrace count data (counts/s)'] = self.plot_y2

        data2 = OrderedDict()
        data2['count data (counts/s)'] = self.scan_matrix[:self._scan_counter_up, :]

        data3 = OrderedDict()
        data3['count data (counts/s)'] = self.scan_matrix2[:self._scan_counter_down, :]

        parameters = OrderedDict()
        parameters['Number of frequency sweeps (#)'] = self._scan_counter_up
        parameters['Start Voltage (V)'] = self.scan_range[0]
        parameters['Stop Voltage (V)'] = self.scan_range[1]
        parameters['Scan speed [V/s]'] = self._scan_speed
        parameters['Clock Frequency (Hz)'] = self._clock_frequency

        fig = self.draw_figure(
            self.scan_matrix,
            self.plot_x,
            self.plot_y,
            self.fit_x,
            self.fit_y,
            cbar_range=colorscale_range,
            percentile_range=percentile_range)

        fig2 = self.draw_figure(
            self.scan_matrix2,
            self.plot_x,
            self.plot_y2,
            self.fit_x,
            self.fit_y,
            cbar_range=colorscale_range,
            percentile_range=percentile_range)

        self._save_logic.save_data(
            data,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )

        self._save_logic.save_data(
            data2,
            filepath=filepath2,
            parameters=parameters,
            filelabel=filelabel2,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp,
            plotfig=fig
        )

        self._save_logic.save_data(
            data3,
            filepath=filepath3,
            parameters=parameters,
            filelabel=filelabel3,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp,
            plotfig=fig2
        )

        self.log.info('Laser Scan saved to:\n{0}'.format(filepath))
        return 0

    def draw_figure(self, matrix_data, freq_data, count_data, fit_freq_vals, fit_count_vals, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.
        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.
        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.
        @return: fig fig: a matplotlib figure object to be saved to file.
        """

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = np.array([np.min(matrix_data), np.max(matrix_data)])
        else:
            cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(
            matrix_data,
            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
            origin='lower',
            vmin=cbar_range[0],
            vmax=cbar_range[1],
            extent=[
                np.min(freq_data),
                np.max(freq_data),
                0,
                self.number_of_repeats
                ],
            aspect='auto',
            interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which='both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig