import os
from qtpy import QtWidgets, QtCore
import numpy as np
import inspect # for getting name of functions

from qudi.core.connector import Connector
from qudi.core.module import GuiBase
from qudi.util import uic

class MagnetmainWindow(QtWidgets.QMainWindow):
    """Creates the Magnet GUI window.
    """

    def __init__(self, *args, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_vectormagnet_prelim.ui')

        # Load it
        super().__init__(*args, **kwargs)
        uic.loadUi(ui_file, self)


class MagnetWindow(GuiBase):
    # TODO: deactivate buttons during ramp
    ## declare connectors
    magnetlogic = Connector(interface = 'MagnetLogic')

    ## signals
    # internal signals

    # external signals
    # array: params [[axis0_start, axis0_stop, axis0_steps], [axis1_start, axis1_stop, axis1_steps], [axis2_start, axis2_stop, axis2_steps]]
    # float: integration time
    sigStartScanPressed = QtCore.Signal(np.ndarray, float)
    sigStopScanPressed = QtCore.Signal()
    # int: psw status. Either 0 (turn off) or 1 (turn on)
    sigChangePswStatus = QtCore.Signal(int)
    sigPauseRamp = QtCore.Signal()
    sigContinueRamp = QtCore.Signal()
    sigRamToZero = QtCore.Signal()
    sigRamp = QtCore.Signal(np.ndarray)
    sigAbortRamp = QtCore.Signal()
    sigGetValues = QtCore.Signal()
    sigGetRampingState = QtCore.Signal()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = True


    def on_activate(self):
        self._mw = MagnetmainWindow()

        self._magnetlogic = self.magnetlogic()

        ## connect buttons
        self._mw.start_scan_pushButton.clicked.connect(self.start_scan_pressed)
        self._mw.stop_scan_pushButton.clicked.connect(self.stop_scan_pressed)
        self._mw.heat_psw_pushButton.clicked.connect(self.heat_psw_pressed)
        self._mw.cool_psw_pushButton.clicked.connect(self.cool_psw_pressed)
        self._mw.pause_ramp_pushButton.clicked.connect(self.pause_ramp_pressed)
        self._mw.continue_ramp_pushButton.clicked.connect(self.continue_ramp_pressed)
        self._mw.ramp_to_zero_pushButton.clicked.connect(self.ramp_to_zero_pressed)
        self._mw.start_ramp_pushButton.clicked.connect(self.ramp_pressed)
        self._mw.stop_ramp_pushButton.clicked.connect(self.stop_ramp_pressed)
        self._mw.get_values_pushButton.clicked.connect(self.get_values_pressed)
        self._mw.get_ramping_state_pushButton.clicked.connect(self.get_ramping_state_pressed)


        ## connect signals
        self.sigStartScanPressed.connect(self._magnetlogic.set_up_scan)
        self.sigStartScanPressed.connect(self._magnetlogic.stop_scan)
        self.sigChangePswStatus.connect(self._magnetlogic.set_psw_status)
        self.sigPauseRamp.connect(self._magnetlogic.pause_ramp)
        self.sigContinueRamp.connect(self._magnetlogic.continue_ramp)
        self.sigRamToZero.connect(self._magnetlogic.ramp_to_zero)
        self.sigRamp.connect(self._magnetlogic.ramp)
        self.sigAbortRamp.connect(self._magnetlogic.abort_ramp)
        self.sigGetValues.connect(self._magnetlogic.emit_magnet_values)
        self.sigGetRampingState.connect(self._magnetlogic.emit_ramping_state)

        # from logic
        self._magnetlogic.sigGotMagnetValues.connect(self.got_values)
        self._magnetlogic.sigGotRampingState.connect(self.got_ramping_state)
        self._magnetlogic.sigScanFinished.connect(self._scan_has_finished)
        self._magnetlogic.sigRampFinished.connect(self._ramp_has_finished)

        self.show()


    def on_deactivate(self):
        """ Hide window
        """
        self._mw.close()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    
    def _ramp_has_finished(self):
        """Catches the signal from logic that ramping has finshed.
        """
        self.reactivate_ramping_buttons()
        return


    def _scan_has_finished(self):
        """Catches the signal from logic that scanning has finshed.
        """
        self.reactivate_ramping_buttons()
        self.switch_scan_button_status_scan_idle()
        return


    def start_scan_pressed(self):
        # TODO: (de)activate buttons
        if self.debug:
            print('start_scan_pressed')
        self.switch_scan_button_status_scan_running()
        # get scanning parameters from gui
        # B_abs
        ax0_start = self._mw.axis0_start_value_doubleSpinBox.value()
        ax0_stop = self._mw.axis0_stop_value_doubleSpinBox.value()
        ax0_steps = self._mw.axis0_steps_doubleSpinBox.value()
        ax0_steps = int(ax0_steps)
        # theta
        ax1_start = self._mw.axis1_start_value_doubleSpinBox.value()
        ax1_stop = self._mw.axis1_stop_value_doubleSpinBox.value()
        ax1_steps = self._mw.axis1_steps_doubleSpinBox.value()
        ax1_steps = int(ax1_steps)
        # phi
        ax2_start = self._mw.axis2_start_value_doubleSpinBox.value()
        ax2_stop = self._mw.axis2_stop_value_doubleSpinBox.value()
        ax2_steps = self._mw.axis2_steps_doubleSpinBox.value()
        ax2_steps = int(ax2_steps)
        # put them in an array
        params = np.array([[ax0_start,ax0_stop,ax0_steps],
                            [ax1_start,ax1_stop,ax1_steps],
                            [ax2_start,ax2_stop,ax2_steps]
                        ])
        # get integration time from gui
        int_time = self._mw.integration_time_doubleSpinBox.value()
        # emit the signal
        self.sigStartScanPressed.emit(params,int_time)
        return

    
    def stop_scan_pressed(self):
        self.switch_scan_button_status_scan_idle()
        self.sigStopScanPressed.emit()
        return


    def switch_scan_button_status_scan_running(self):
        self._mw.start_scan_pushButton.setEnabled(False)
        self._mw.stop_scan_pushButton.setEnabled(True)
        return


    def switch_scan_button_status_scan_idle(self):
        self._mw.start_scan_pushButton.setEnabled(True)
        self._mw.stop_scan_pushButton.setEnabled(False)
        return


    def heat_psw_pressed(self):
        # TODO: (de)activate buttons
        # TODO: catch sigal to reactivate the buttons
        if self.debug:
            print('heat_psw_pressed')
        self.sigChangePswStatus.emit(1)
        return


    def cool_psw_pressed(self):
        # TODO: (de)activate buttons
        if self.debug:
            print('cool_psw_pressed')
        self.sigChangePswStatus.emit(0)
        return


    def pause_ramp_pressed(self):
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self._mw.continue_ramp_pushButton.setEnabled(True)
        self._mw.pause_ramp_pushButton.setEnabled(False)
        self.sigPauseRamp.emit()
        return


    def continue_ramp_pressed(self):
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self._mw.continue_ramp_pushButton.setEnabled(False)
        self._mw.pause_ramp_pushButton.setEnabled(True)
        self.sigContinueRamp.emit()
        return

    
    def ramp_to_zero_pressed(self):
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self.sigRamToZero.emit()
        return


    def ramp_pressed(self):
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        # deactivate all buttons apart from stopping and pausing ramp
        self.deactivate_ramping_buttons()
        self.deactivate_scanning_buttons()
        self._mw.stop_ramp_pushButton.setEnabled(True)
        self._mw.pause_ramp_pushButton.setEnabled(True)
        # TODO: if pause ramp is pressed and start ramp is pressed afterwards, make sure old ramp is killed.
        ax0 = self._mw.axis0_doubleSpinBox.value()
        ax1 = self._mw.axis1_doubleSpinBox.value()
        ax2 = self._mw.axis2_doubleSpinBox.value()
        bx = ax0 * np.sin(np.deg2rad(ax1)) * np.cos(np.deg2rad(ax2))
        by = ax0 * np.sin(np.deg2rad(ax1)) * np.sin(np.deg2rad(ax2))
        bz = ax0 * np.cos(np.deg2rad(ax1))
        params = np.array([bx,by,bz])
        self.sigRamp.emit(params)
        return
        

    def stop_ramp_pressed(self):
        """Tells hardware to stop ramping and reactivates ramping buttons.

        CAUTION: Buttons get reactivated straight away but loop is still running until it checks again (most probably some seconds).
        """
        self.reactivate_ramping_buttons()
        self.reactivate_scanning_buttons()
        self.sigAbortRamp.emit()
        return


    def get_values_pressed(self):
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        # dectivate button
        self._mw.get_values_pushButton.setEnabled(False)
        self.sigGetValues.emit()
        return


    def got_values(self,values):
        """Updates values in gui and reactivates button.
        """
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        self._mw.bx_doubleSpinBox.setValue(values[0])
        self._mw.by_doubleSpinBox.setValue(values[1])
        self._mw.bz_doubleSpinBox.setValue(values[2])
        self._mw.b_doubleSpinBox.setValue(values[3])
        self._mw.theta_doubleSpinBox.setValue(values[4])
        self._mw.phi_doubleSpinBox.setValue(values[5])
        self._mw.get_values_pushButton.setEnabled(True)
        return


    def get_ramping_state_pressed(self):
        """ Sends signal to ask for the magnet status. Deactivates "get staus" button.
        """
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        self._mw.get_ramping_state_pushButton.setEnabled(False)
        self.sigGetRampingState.emit()
        return


    def got_ramping_state(self,ramping_state):
        """Updates values in gui and reactivates button.
        """
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        self._mw.ramping_state_x_doubleSpinBox.setValue(ramping_state[0])
        self._mw.ramping_state_y_doubleSpinBox.setValue(ramping_state[1])
        self._mw.ramping_state_z_doubleSpinBox.setValue(ramping_state[2])
        self._mw.get_ramping_state_pushButton.setEnabled(True)
        return


    def deactivate_scanning_buttons(self):
        """Deactivates all buttons that deal with the scanning of the magnetic field.
        """
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        status = False
        self._mw.start_scan_pushButton.setEnabled(status)
        self._mw.stop_scan_pushButton.setEnabled(status)
        return


    def reactivate_scanning_buttons(self):
        """Ractivates all buttons that deal with the scanning of the magnetic field.
        """
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        status = True
        self._mw.start_scan_pushButton.setEnabled(status)
        self._mw.stop_scan_pushButton.setEnabled(status)
        return


    def deactivate_ramping_buttons(self):
        """Deactivates all buttons that deal with the ramping of the magnetic field.
        """
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        status = False
        self._mw.start_ramp_pushButton.setEnabled(status)
        self._mw.stop_ramp_pushButton.setEnabled(status)
        self._mw.ramp_to_zero_pushButton.setEnabled(status)
        self._mw.continue_ramp_pushButton.setEnabled(status)
        self._mw.pause_ramp_pushButton.setEnabled(status)
        self._mw.heat_psw_pushButton.setEnabled(status)
        self._mw.cool_psw_pushButton.setEnabled(status)
        return


    def reactivate_ramping_buttons(self):
        """Reactivates all buttons that deal with the ramping of the magnetic field.
        """
        if self.debug:
            # prints name of file and function
            print(f'{__name__}, {inspect.stack()[0][3]}') 
        status = True
        self._mw.start_ramp_pushButton.setEnabled(status)
        self._mw.stop_ramp_pushButton.setEnabled(status)
        self._mw.ramp_to_zero_pushButton.setEnabled(status)
        self._mw.continue_ramp_pushButton.setEnabled(status)
        self._mw.pause_ramp_pushButton.setEnabled(status)
        self._mw.heat_psw_pushButton.setEnabled(status)
        self._mw.cool_psw_pushButton.setEnabled(status)
        return