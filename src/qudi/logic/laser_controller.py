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

    def on_activate(self) -> None:
        return 

    def on_deactivate(self) -> None:
        self._ao_laser_control.set_activity_state(active=False)
       

    def set_thin_etalon_voltage(self,v):
        self._ao_laser_control.set_activity_state(active=True)
        self._ao_laser_control.set_setpoint(channel = 'a0', value = v)
        self._ao_laser_control.set_activity_state(active=False)

    def set_motor_direction(self,sign):
        self._ao_laser_control.set_activity_state(active=True)
        if sign > 0:
            self._ao_laser_control.set_setpoint(channel = 'a2', value = 5)
        elif sign < 0 :
            self._ao_laser_control.set_voltage(channel = 'a2', value = -5)
        self._ao_laser_control.set_activity_state(active=False)
    def move_motor_pulse(self):
        self._motor_pulser.set_state(switch="motor", state='Low') #'High' should be pulsing?
        