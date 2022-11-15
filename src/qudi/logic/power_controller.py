# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic class that captures and processes fluorescence spectra.
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

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex
#from logic.generic_logic import GenericLogic
from qudi.core.module import Base
from qudi.core.module import LogicBase
from qtpy import QtCore


def delay(delay_msec = 100):
    dieTime = QtCore.QTime.currentTime().addMSecs(delay_msec)
    while (QtCore.QTime.currentTime() < dieTime):
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 100)
    
class PowerControllerLogic(LogicBase):

    """This logic module gathers data from the spectrometer.
    Demo config:
    spectrumlogic:
        module.Class: 'spectrum.SpectrumLogic'
        connect:
            spectrometer: 'myspectrometer'
            savelogic: 'savelogic'
            odmrlogic: 'odmrlogic' # optional
            fitlogic: 'fitlogic'
    """
    queryInterval = 1000
    calibration_factor_1= 1
    calibration_factor_2= 2
    # declare connectors
    powermeter = Connector(interface='PM100D', optional = True)
    motor_pi3 = Connector(interface='Motordriver')
    counter = Connector(interface='TimeTaggerCounter', optional=True)
    # spectrometer = Connector(interface='SpectrometerInterface')
    # spectrometer_fine = Connector(interface='SpectrometerInterface')
    # odmrlogic = Connector(interface='ODMRLogic', optional=True)
    # fitlogic = Connector(interface='FitLogic')
    # nicard = Connector(interface='NationalInstrumentsXSeries', optional=True)
    # ello_devices = Connector(interface='ThorlabsElloDevices', optional=True)
    # cwavelaser = Connector(interface='CwaveLaser')
    calibration_resolution = 180
    # declare status variables
    _saturation_data = StatusVar('saturation_data', np.empty((2, 0)))
    _saturation_background = StatusVar('saturation_background', np.empty((2, 0)))
    _background_correction = StatusVar('background_correction', False)
    _power_calib = StatusVar('_power_calibration', np.array([]))
    fc = StatusVar('fits', None)
    plot_domain = (0, 10000)
    # Internal signals
    sig_data_updated = QtCore.Signal()
    sig_run_calibration = QtCore.Signal(int)
    sig_next_diff_loop = QtCore.Signal()
    sig_set_power = QtCore.Signal(float, int, bool)
    channels = []

    def __init__(self, **kwargs):
        """ Create SpectrometerLogic object with connectors.
          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)
        # self._power_calib = np.array([])
        self.stopRequested = False
        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._saturation_data_corrected = np.array([])
        self._calculate_corrected_spectrum()
        if self.powermeter() is not None:
            self._powermeter = self.powermeter()
        self._motor_pi3 = self.motor_pi3()
        self.channels = self._motor_pi3._active_motor_numbers
        self._counter = self.counter()
        self.power_calib = self._power_calib
        self.current_power_1 = 0
        self.current_power_2 = 0
        self.sig_data_updated.emit()
        self.sig_run_calibration.connect(self.calibrate_power_wheel)
        self.sig_set_power.connect(self.set_power, QtCore.Qt.QueuedConnection)

    #     self.queryTimer = QtCore.QTimer()
    #     self.queryTimer.setInterval(self.queryInterval)
    #     self.queryTimer.setSingleShot(True)
    #     self.queryTimer.timeout.connect(self.loop_body)#, QtCore.Qt.QueuedConnection)     
    #     self.queryTimer.start(self.queryInterval)

    # def loop_body(self):
    #     qi = self.queryInterval
    #     self.queryTimer.start(qi)
    #     if self.powermeter() is not None:
    #         self.current_power_1 = self._powermeter.get_power() * self.calibration_factor_1
    #         self.current_power_2 = self._powermeter.get_power() * self.calibration_factor_2
        
    #         self.sig_data_updated.emit()
        

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
        
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            pass
    


    @QtCore.Slot(int)
    def calibrate_power_wheel(self, motor=1):
        """ADD WARNING 
        insert powermeter into the path where it is conveneint to measure

        """
        self._motor_pi3.stopAllMovements()
        self._motor_pi3.zeroMotor(motor=motor)
        # delay(10000)
        self._motor_pi3.moveToAbsolutePosition(motor = motor, pos = 0)
        delay(5000)
        print("Zeroed")
       
        powers = []
        angles = np.linspace(0, 360, self.calibration_resolution).astype(int)
        for angle in angles:
            self._motor_pi3.moveToAbsolutePosition(motor = motor, pos = angle)
            delay(1000)
            pw = self._powermeter.get_power()
            pw = (self._powermeter.get_power() + pw)/2
            powers.append(pw)
            print(angle, pw)
            if self.stopRequested:
                print("ups")
                self._motor_pi3.stopAllMovements()
                self.stopRequested = False
                return
        delay(1000)
        self._motor_pi3.moveToAbsolutePosition(motor=motor, pos = 0)
        power_calib = np.vstack((angles, np.array(powers))).T
        self.power_calib = power_calib[np.argsort(power_calib[:,1])]
        # self._power_range = (min(self._power_calib[:,1]), max(self._power_calib[:,1]))

        # self._motor_pi3.stopAllMovements()
    
    @property
    def power_calib(self):
        return self._power_calib
    
    @power_calib.setter
    def power_calib(self, calibration):
        self._power_calib = calibration
        print("New power range")
        self._power_range = (min(calibration[:,1]), max(calibration[:,1]))
        

    @QtCore.Slot(float, int, bool)
    def set_power(self, power, motor, calibrated):
      
        if bool(calibrated) == True:
            if (power > self._power_range[1]) or (power < self._power_range[0]):
                print("Power out of calibrated range")
                return -1
            new_angle = self._power_calib[:, 0][np.argmin(np.abs(self._power_calib[:, 1] - power))]
            
            self._motor_pi3.moveToAbsolutePosition(motor = motor, pos = new_angle)
            delay(5000)
            return 
        else:
            new_angle = power
            self._motor_pi3.moveToAbsolutePosition(motor = motor, pos = new_angle)
            delay(3000)
       

    def run_saturation(self, motor = 0):
        """ Record a single saturation.
        """
        if self._counter is None:
            print("No counter")
            return
        self._motor_pi3.stopAllMovements()
        self._motor_pi3.zeroMotor(motor=motor)
        # delay(10000)
        self._motor_pi3.moveToAbsolutePosition(motor = motor, pos = 0)
        delay(5000)
        print("Zeroed")
       
        counts = []
        for angle in np.sort(self._power_calib[:, 0]):
            self._motor_pi3.moveToAbsolutePosition(motor = motor, pos = angle)
            delay(2000)
            count = self._counter.get_counter()
            counts.append(count)
            if self.stopRequested:
                print("ups")
                self._motor_pi3.stopAllMovements()
                self.stopRequested = False
                return
        delay(2000)
        self._motor_pi3.moveToAbsolutePosition(motor=motor, pos = 0)

        self._saturation_data = np.vstack(( self._power_calib[:, 1], np.array(counts))).T
        self.sig_data_updated.emit()

    def _calculate_corrected_spectrum(self):
        self._saturation_data_corrected = np.copy(self._saturation_data)
        if len(self._saturation_background) == 2 \
                and len(self._saturation_background[1, :]) == len(self._saturation_data[1, :]):
            self._saturation_data_corrected[1, :] -= self._saturation_background[1, :]
        else:
            self.log.warning('Background saturation has a different dimension then the acquired saturation. '
                             'Returning raw saturation. '
                             'Try acquiring a new background saturation.')

    @property
    def saturation_data(self):
        if self._background_correction:
            self._calculate_corrected_saturation()
            return self._saturation_data_corrected
        else:
            return self._saturation_data

    @property
    def background_correction(self):
        return self._background_correction

    @background_correction.setter
    def background_correction(self, correction=None):
        if correction is None or correction:
            self._background_correction = True
        else:
            self._background_correction = False
        self.sig_data_updated.emit()
