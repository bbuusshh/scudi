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

class WavemeterInterfuseLogic(LogicBase):
    sigGuiParamsUpdated = QtCore.Signal(object,  QtCore.Qt.QueuedConnection)
    sigTimingPlotUpdated = QtCore.Signal(object,  QtCore.Qt.QueuedConnection)
    _wavelogger = Connector(name='wavelogger', interface="WavemeterLoggerLogic")


    default_params = {
        'bin_width':20e6, #20 MHz
        'start_value':350e12, # 350 THz
        'stop_value':351e12 # 351 THz
    }
        
    parameters = StatusVar(name="parameters", default=default_params)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    
    def on_activate(self):
        self._wavelogger = self._wavelogger()
        # self.switch = self._switchlogic()

        
    def on_deactivate(self):
       
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
        
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            pass
        return 

    @QtCore.Slot(dict)
    def params_updated(self, params):
        self.parameters['power'] = params['power']
        print(params['power'])
        self._power_controller.sig_set_power.emit(params['power'], self._power_channel, False)
    
    @QtCore.Slot(float, int, bool)
    def update_power(self, power, channel, calibrated):
        self.parameters['power'] = power
        self.sigGuiParamsUpdated.emit(self.parameters)
