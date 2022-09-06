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

# from qudi.core.pi3_utils import delay
from time import sleep
import numpy as np

class CwaveLogic(LogicBase):
    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """
    # declare connectors
    cwavelaser = Connector(interface='CWave')
  
    queryInterval = ConfigOption('query_interval', 500)

    sig_update_gui = QtCore.Signal()
    sig_update_cwave_states = QtCore.Signal()
    sig_cwave_connected = QtCore.Signal()
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
        
        self.connect_cwave()
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
    
    def connect_cwave(self):
        
        self._cwavelaser.connect()
        self.connected = self._cwavelaser._connected
        if self.connected:
            self.shutters = self._cwavelaser.get_shutters()
            self.status_cwave = {}#self._cwavelaser.get_dial_done()
            self.cwave_log = self._cwavelaser.get_log()
            
        
            self.reg_modes = {}
        
            self.sig_update_cwave_states.connect(self.update_cwave_states)
            # Initialie data matrix
            # delay timer for querying laser
            self.queryTimer = QtCore.QTimer()
            self.queryTimer.setInterval(self.queryInterval)
            self.queryTimer.setSingleShot(True)
            self.queryTimer.timeout.connect(self.loop_body)#, QtCore.Qt.QueuedConnection)     
            self.queryTimer.start(self.queryInterval)
        self.sig_update_gui.emit()

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
        if opt_command == 'etalon':
            self._cwavelaser.optimize_etalon()
        elif opt_command == 'temp':
            self._cwavelaser.optimize_shg_temperature()
        else:
            self._cwavelaser.optimize_stop()


    @QtCore.Slot(str, bool)
    def change_shutter_state(self, shutter, state):
        # self._cwavelaser.shutters.update({shutter: state})
        self._cwavelaser.set_shutter(shutter, state)
        # self.shutters = self._cwavelaser.get_shutters()
        self.sig_update_gui.emit()

    @QtCore.Slot()
    def update_cwave_states(self):
        self.shutters = self._cwavelaser.get_shutters()
        # self.status_cwave = self._cwavelaser.get_status_dict()
        self.cwave_log = self._cwavelaser.get_log()
        self.connected = self._cwavelaser._connected

        for idx, channel in enumerate(PiezoChannel):
            # print("Chann", channel)
            # self._cwavelaser.get_piezo_mode(channel)
            self.reg_modes[channel.value] = self._cwavelaser.get_piezo_mode(channel)

        for idx, bit in enumerate(StatusBit):
            # print("Chann", channel)
            # self._cwavelaser.get_piezo_mode(channel)
            self.status_cwave[bit.name] = self._cwavelaser.test_status_bits([
            bit
        ])

        self.sig_update_gui.emit()
    
    @QtCore.Slot()
    def connection_cwave(self):
        """ Connect to the cwave """
        
        if not self.connected:
            self.connect_cwave()
            self.sig_cwave_connected.emit()
            # self._cwavelaser.connect()
            # self.queryTimer.start(self.queryInterval)
        else:
            self._cwavelaser.disconnect()
            self.queryTimer.stop()
        self.connected = self._cwavelaser._connected
        
        self.sig_update_gui.emit()

    @QtCore.Slot(int)
    def adj_thick_etalon(self, adj):
        # print("here_we_go", adj)
        self._cwavelaser.etalon_move(adj)
        # sleep(2)
        # delay(2)

    @QtCore.Slot(int)
    def adj_opo_lambda(self, adj):
        print("here_we_go", adj)
        self._cwavelaser.elements_move(adj)
        # sleep(5)

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
    def change_lock_mode(self, stage, mode): 
        self._cwavelaser.set_piezo_mode(stage, mode)
       
