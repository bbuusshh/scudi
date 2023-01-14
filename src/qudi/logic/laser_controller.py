# -*- coding: utf-8 -*
from collections import OrderedDict
import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
from time import sleep
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import RecursiveMutex
from qudi.core.module import LogicBase
from qudi.hardware.cwave.cwave_api import PiezoChannel, StatusBit, PiezoMode, ExtRampMode, StepperChannel, Log, ShutterChannel
from PySide2 import QtCore

class LaserControllerLogic(LogicBase):
    motor_pulser = Connector(interface='DigitalSwitchNI')
    ao_laser_control = Connector(interface='NIXSeriesAnalogOutput')
    
    def __init__(self):
        self._motor_pulser = self.motor_pulser()
        self._ao_laser_control = self.ao_laser_control()

    def set_thin_etalon_voltage(self,v):
        self._ao_laser_control.set_voltage(a0 = v)
    def set_motor_direction(self,sign):
        if sign > 0:
            self._ao_laser_control(a2 = 5)
        elif sign < 0 :
            self._ao_laser_control(a2=-5)
    def move_motor_pulse(self):
        self._motor_pulser(self.ni._stepper_pulse_channel)