# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module to operate the voltage (laser) scanner.
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
import os
import numpy as np
import copy as cp
from typing import Union, Tuple
from functools import partial
from PySide2 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

import qudi.util.uic as uic
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.interface.scanning_probe_interface import ScanData
from qudi.core.module import GuiBase
from qudi.logic.scanning_optimize_logic import OptimizerScanSequence


class PLEScanMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ple_gui.ui')

        # Load it
        super(PLEScanMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class PLEScanGui(GuiBase):
    """
    """
    
    # declare connectors
    scannerlogic = Connector(interface='PLEScannerLogic')

    def on_deactivate(self):
        """ Reverse steps of activation
        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def on_activate(self):
        """ 
        """
        self._scan_logic = self.scannerlogic()
        self._mw = PLEScanMainWindow()
        self._mw.show()

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def run_stop(self, is_checked):
        """ Manages what happens if scan is started/stopped """
        self._mw.action_run_stop.setEnabled(False)
        if is_checked:
            pass

    def scan_started(self):
        self._mw.action_run_stop.setEnabled(True)

    def scan_stopped(self):
        self._mw.action_run_stop.setEnabled(True)
        self._mw.action_run_stop.setChecked(False)
