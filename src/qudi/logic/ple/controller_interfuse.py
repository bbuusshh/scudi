# -*- coding: utf-8 -*-
"""
This file contains a qudi logic module template

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

from ast import Raise
from email.policy import default
from qudi.core.connector import Connector
from qudi.core.module import LogicBase
from qudi.core.configoption import ConfigOption
from PySide2 import QtCore
import numpy as np
from qudi.core.statusvariable import StatusVar
from qudi.util.delay import delay
import time

class ControllerInterfuseLogic(LogicBase):
    sigGuiParamsUpdated = QtCore.Signal(object,  QtCore.Qt.QueuedConnection)
    sigTimingPlotUpdated = QtCore.Signal(object,  QtCore.Qt.QueuedConnection)
    _switch_name = ConfigOption(name='switcher_name', default=None)
    _switchlogic = Connector(name='switchlogic', interface="SwitchLogic", optional=True)
    _power_controller = Connector(name='power_controller', interface="PowerControllerLogic", optional=True)
    _power_channel = ConfigOption(name='power_channel', default=0)
    _laser_controller = Connector(name='laser_controller', interface="LaserControllerLogic", optional=True)


    default_params = {
        "power": 0
          
        }
    parameters = StatusVar(name="parameters", default=default_params)
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
    
    def on_activate(self):
        self._power_controller = self._power_controller()
        # self.switch = self._switchlogic()
        if self._power_controller:
            self.parameters['power'] = self._power_controller._current_positions[self._power_channel]
            self._power_controller.sig_set_power.connect(self.update_power, QtCore.Qt.QueuedConnection)

        if self._laser_controller:
            self.parameters['eta_voltage'] = self._laser_controller.etalon_voltage
            self.parameters["motor_direction"] = self._laser_controller.motor_direction
            # self._power_controller.sig_set_power.connect(self.update_power, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        pass
    
    @QtCore.Slot(dict)
    def params_updated(self, params):
       
        if params == self.parameters:
            # "nothing_new"
            return 

        self._power_controller.sig_set_power.emit(params['power'], self._power_channel, False)
        self._laser_controller.etalon_voltage = params['eta_voltage']
        self._laser_controller.motor_direction = params['motor_direction']

        self.parameters.update(params)

    @QtCore.Slot()
    def move_motor(self):
        self._laser_controller.move_motor_pulse()

    @QtCore.Slot(float, int, bool)
    def update_power(self, power, channel, calibrated):
        self.parameters['power'] = power
        self.sigGuiParamsUpdated.emit(self.parameters)
