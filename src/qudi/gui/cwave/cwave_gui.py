
import numpy as np
import os
import pyqtgraph as pg
import time

from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from core.pi3_utils import delay, wavelength_to_freq


class CwaveWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'cwave.ui')

        # Load it
        super(CwaveWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class CwaveGui(GUIBase):
    """
    """
    # declare connectors
    cwavelogic = Connector(interface='CwaveLogic')
    
    sig_adj_thick_etalon = QtCore.Signal(int)
    sig_adj_opo = QtCore.Signal(int)
    sig_set_refcav = QtCore.Signal(float)
    
    sig_connect_cwave = QtCore.Signal()
    sig_set_shutter_state = QtCore.Signal(str, bool)
    sig_optimize_cwave = QtCore.Signal(str)
    sig_change_lock_mode = QtCore.Signal(str, str)
    sig_save_measurement = QtCore.Signal()
    

    def on_deactivate(self):
        """ Reverse steps of activation
        @return int: error code (0:OK, -1:error)
        """
        #turn off the regulation 
        self._mw.close()
        return 0

    def on_activate(self):
        """ 
        """
        self._cwavelogic = self.cwavelogic()
        self._savelogic = self.savelogic()
        self._mw = CwaveWindow()     
        #! Get the images from the logic
        self.set_up_images()
        self.set_up_cwave_control_panel()
        self._cwavelogic.sig_update_gui.connect(self.update_gui)
        self._mw.show()

    def set_up_cwave_control_panel(self):
        self._mw.pushButton_connectCwave.clicked.connect(self.changeCwaveState)
        for shutter in self._cwavelogic.shutters.keys():
            eval(f"self._mw.checkBox_{shutter}.stateChanged.connect(self.flip_shutter)")
         
        self._mw.pushButtonOpt_opt_stop.clicked.connect(self.optimizing)
        self._mw.pushButtonOpt_opt_tempshg.clicked.connect(self.optimizing)
        self._mw.pushButtonOpt_regeta_catch.clicked.connect(self.optimizing)

        self._mw.eta_lock_checkBox.clicked.connect(self.change_lock_mode)
        self._mw.opo_lock_checkBox.clicked.connect(self.change_lock_mode)
        self._mw.thick_eta_spinBox.editingFinished.connect(self.adjust_thick_etalon)
        self._mw.opo_lambda_spinBox.editingFinished.connect(self.adjust_opo_lambda)
        self._mw.ref_cav_doubleSpinBox.editingFinished.connect(self.update_setpoint)

        #? Connect signals
        self.sig_set_shutter_state.connect(self._cwavelogic.change_shutter_state)
        self.sig_optimize_cwave.connect(self._cwavelogic.optimize_cwave)
        self.sig_connect_cwave.connect(self._cwavelogic.connection_cwave)
        self.sig_change_lock_mode.connect(self._cwavelogic.change_lock_mode)
        self.sig_adj_thick_etalon.connect(self._cwavelogic.adj_thick_etalon)
        self.sig_adj_opo.connect(self._cwavelogic.adj_opo_lambda)
        self.sig_set_refcav.connect(self._cwavelogic.refcav_setpoint)
    
    
    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
    
    @QtCore.Slot()
    def update_gui(self):
        self.update_cwave_panel()

    @QtCore.Slot()
    def adjust_thick_etalon(self, delta_eta=None):
        if delta_eta is None:
            delta_eta = int(self._mw.thick_eta_spinBox.value())
      
        self.sig_adj_thick_etalon.emit(delta_eta) 
    @QtCore.Slot()
    def adjust_opo_lambda(self, delta_lam = None):
        if delta_lam is None:
            delta_lam = int(self._mw.opo_lambda_spinBox.value())

        self.sig_adj_opo.emit(delta_lam) 
    @QtCore.Slot()
    def update_setpoint(self, setpoint=None):
        if setpoint is None:
            setpoint = self._mw.ref_cav_doubleSpinBox.value()
        self.sig_set_refcav.emit(setpoint)
    @QtCore.Slot()
    def change_lock_mode(self, param=None, mode=None):
        if (param is None) or (mode is None):
            sender = self.sender()
            if "_lock_checkBox" in sender.objectName():
                    param = sender.objectName().split('_lock_checkBox')[0].strip()
                    mode = 'control' if sender.isChecked() else 'manual'
            else:
                raise Exception("Wrong button for this function!")
                return
        self.sig_change_lock_mode.emit(param, mode)
    @QtCore.Slot()
    def optimizing(self, opt_param=None):
        if opt_param is None: 
            sender = self.sender()
            if "pushButtonOpt_" in sender.objectName():
                opt_param = sender.objectName().split('pushButtonOpt_')[-1].strip()
            else:
                raise Exception("Wrong button for this function!")
                return
        self.sig_optimize_cwave.emit(opt_param)

    @QtCore.Slot()
    def flip_shutter(self, shutter=None, state=None):
        if (shutter is None) or (state is None):
            sender = self.sender()
            state = sender.isChecked()
            if "checkBox_shtter" in sender.objectName():
                shutter = sender.objectName().split('checkBox_')[-1].strip()
            elif "checkBox_laser_en" in sender.objectName():
                shutter = sender.objectName().split('checkBox_')[-1].strip()
            else:
                raise Exception("Wrong button for this function!")
                return  
        self.sig_set_shutter_state.emit(shutter, state)
    @QtCore.Slot()
    def update_cwave_panel(self):
        """ Logic told us to update our button states, so set the buttons accordingly. """
        #! connect button 
        if self._cwavelogic.cwstate == 0:
            self._mw.pushButton_connectCwave.setText('Connect')
            self._mw.radioButton_connectCwave.setChecked(False)
        else:
            self._mw.pushButton_connectCwave.setText('Disconnect')
            self._mw.radioButton_connectCwave.setChecked(True)
        

        #! shutters:
        for shutter, state in self._cwavelogic.shutters.items():
            eval(f"self._mw.checkBox_{shutter}.setChecked({state})")
        #! states:
        for param, state in self._cwavelogic.status_cwave.items():
            eval(f"self._mw.radioButton_{param}.setChecked({state})")

        #! wavelength
        #TODO: read wavelength from the wavelengthmeter
      
        #! photodiodes  
        self._mw.label_laserPD.setText(f"{self._cwavelogic.laserPD}")
        self._mw.label_opoPD.setText(f"{self._cwavelogic.opoPD}")
        self._mw.label_shgPD.setText(f"{self._cwavelogic.shgPD}")
        if self._cwavelogic.reg_modes is not None:
            self._mw.eta_lock_checkBox.setEnabled(True)
            self._mw.opo_lock_checkBox.setEnabled(True)
            self._mw.eta_lock_checkBox.setChecked(True if self._cwavelogic.reg_modes['eta'] == 2 else False)
            self._mw.opo_lock_checkBox.setChecked(True if self._cwavelogic.reg_modes['opo'] == 2 else False)
        else:
            self._mw.eta_lock_checkBox.setEnabled(False)
            self._mw.opo_lock_checkBox.setEnabled(False)
    @QtCore.Slot()
    def changeCwaveState(self):
        # print(self._cwavelogic.cwstate)
        self.sig_connect_cwave.emit()