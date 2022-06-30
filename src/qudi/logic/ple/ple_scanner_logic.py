# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module for controlling scans of the
fourth analog output channel.  It was originally written for
scanning laser frequency, but it can be used to control any parameter
in the experiment that is voltage controlled.  The hardware
range is typically -10 to +10 V.

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
from PySide2 import QtCore
import copy as cp
from qudi.logic.scanning_probe_logic import ScanningProbeLogic
from qudi.core.module import LogicBase
from qudi.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.util.widgets.fitting import FitConfigurationDialog, FitWidget


from qudi.util.datastorage import TextDataStorage
from qudi.util.datafitting import FitContainer, FitConfigurationsModel

class PLEScannerLogic(ScanningProbeLogic):

    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """


    _number_of_repeats = StatusVar(default=10)

    # config options

    _fit_config = StatusVar(name='fit_config', default=dict())
    _fit_region = StatusVar(name='fit_region', default=[0, 1])

  
    def __init__(self, config, **kwargs):
        super(PLEScannerLogic, self).__init__(config=config, **kwargs)
        """ Create VoltageScanningLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        #Took some from the spectrometer program, beacuse it's graaape
        self.refractive_index_air = 1.00028823
        self.speed_of_light = 2.99792458e8 / self.refractive_index_air
        self._fit_config_model = None
        self._fit_container = None

        self._wavelength = None
        self._fit_results = None
        self._fit_method = ''



    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # self._scanning_device = self.scanning_device()
        self._fit_config_model = FitConfigurationsModel(parent=self)
        self._fit_config_model.load_configs(self._fit_config)
        self._fit_container = FitContainer(parent=self, config_model=self._fit_config_model)
        self.fit_region = self._fit_region

        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._fit_config = self._fit_config_model.dump_configs()
