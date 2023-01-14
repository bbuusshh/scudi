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
    cwavelaser = Connector(interface='CWave')
    
    def __init__(self):
        self.ni = ni_card.NationalInstruments()
    def set_thin_etalon_voltage(self,v):
        self.ni.scanner_set_position(a2 = v)
    def set_motor_direction(self,sign):
        if sign > 0:
            self.ni.scanner_set_position(a2 = 5)
        elif sign < 0 :
            self.ni.scanner_set_position(a1=-5)
    def move_motor_pulse(self):
        self.ni.pulse_digital_channel(self.ni._stepper_pulse_channel)