# -*- coding: utf-8 -*
from collections import OrderedDict
import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
from time import sleep
from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from PyQt5.QtCore import QObject
from core.threadmanager import ThreadManager
from core.pi3_utils import delay
import numpy as np

class CwaveLogic(GenericLogic):
    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """
    # declare connectors
    cwavelaser = Connector(interface='CwaveLaser')
  
    queryInterval = ConfigOption('query_interval', 100)

    sig_update_gui = QtCore.Signal()
    sig_update_cwave_states = QtCore.Signal()
    sig_update_guiPanelPlots = QtCore.Signal()
    sig_update_guiPlotsRefInt = QtCore.Signal()
    sig_update_guiPlotsOpoReg = QtCore.Signal()
    sig_update_guiPlotsRefExt = QtCore.Signal()

    def __init__(self, **kwargs):
        """ Create CwaveScannerLogic object with connectors.
          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._cwavelaser = self.cwavelaser()

        self.shutters = self._cwavelaser.get_shutters()
        self.status_cwave = self._cwavelaser.get_status_dict()
        self.cwave_log = self._cwavelaser.get_log()
        self.connected = self._cwavelaser._connected
    
        self.reg_modes = self._cwavelaser.get_piezo_mode()
    
        self.sig_update_cwave_states.connect(self.update_cwave_states)
        # Initialie data matrix
        # delay timer for querying laser
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.loop_body)#, QtCore.Qt.QueuedConnection)     
        self.queryTimer.start(self.queryInterval)
        self.sig_update_gui.emit()
        return 

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        try:
            self._cwavelaser.disconnect()
        except:
            print("Oi oi")
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
        return 
    # @thread_safety
    def save_data(self):
        print("here we save")


    @QtCore.Slot()
    def loop_body(self):
        self.sig_update_cwave_states.emit()
        qi = self.queryInterval
        self.queryTimer.start(qi)
        self.sig_update_gui.emit()

    #! Laser control panel:
    @QtCore.Slot(str)
    def optimize_cwave(self, opt_command):
        self._cwavelaser.set_command(opt_command)

    @QtCore.Slot(str, bool)
    def change_shutter_state(self, shutter, state):
        self._cwavelaser.shutters.update({shutter: state})
        self._cwavelaser.set_shutters_states()
        self.shutters = self._cwavelaser.get_shutters()
        self.sig_update_gui.emit()

    @QtCore.Slot()
    def update_cwave_states(self):
        self.shutters = self._cwavelaser.get_shutters()
        self.status_cwave = self._cwavelaser.get_status_dict()
        self.cwave_log = self._cwavelaser.get_log()
        self.connected = self._cwavelaser._connected
    
        self.reg_modes = self._cwavelaser.get_piezo_mode()
     
        self.sig_update_gui.emit()
    
    @QtCore.Slot()
    def connection_cwave(self):
        """ Connect to the cwave """
        if self.connected == 0:
            self._cwavelaser.connect()
        else:
            self._cwavelaser.disconnect()
        self.connected = self._cwavelaser._connected
        print('CWAVE state:', self.connected)
        self.sig_update_gui.emit()

    @QtCore.Slot(int)
    def adj_thick_etalon(self, adj):
        # print("here_we_go", adj)
        self._cwavelaser.set_galvo_position(adj)
        delay(2)

    @QtCore.Slot(int)
    def adj_opo_lambda(self, adj):
        # print("here_we_go", adj)
        self._cwavelaser.set_wavelength(adj)
        delay(5)

    @QtCore.Slot(float)
    def refcav_setpoint(self, new_voltage):
        # print("New setpoint:", new_voltage)
        new_voltage_hex = int(65535 * new_voltage / 100)
        res = self._cwavelaser.set_int_value('x', new_voltage_hex)
        # delay(wait_time = 1)
        if res == 1:
            return
        else:
            raise Exception('The ref cavity set setpoint command failed.')
        self.setpoint  = new_voltage

    @QtCore.Slot(str, str)
    def change_lock_mode(self, param, mode): 
        if mode == 'control':
            self._cwavelaser.set_regmode_control(param)
        elif mode =='manual':
            self._cwavelaser.set_regmode_manual(param)
