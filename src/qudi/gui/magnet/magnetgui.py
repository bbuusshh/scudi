import os
from qtpy import QtWidgets, QtCore
import numpy as np

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


        ## connect signals
        self.sigStartScanPressed.connect(self._magnetlogic.set_up_scan)
        self.sigStartScanPressed.connect(self._magnetlogic.stop_scan)
        self.sigChangePswStatus.connect(self._magnetlogic.set_psw_status)
        

        self.show()


    def on_deactivate(self):
        """ Hide window
        """
        self._mw.close()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    
    def start_scan_pressed(self):
        # TODO: (de)activate buttons
        if self.debug:
            print('start_scan_pressed')
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
        # TODO: (de)activate buttons
        self.sigStopScanPressed.emit()
        return


    def heat_psw_pressed(self):
        # TODO: (de)activate buttons
        self.sigChangePswStatus.emit(1)
        return


    def cool_psw_pressed(self):
        # TODO: (de)activate buttons
        self.sigChangePswStatus.emit(0)
        return