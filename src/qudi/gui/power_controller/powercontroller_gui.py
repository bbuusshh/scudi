# -*- coding: utf-8 -*-
"""
This module contains a GUI for operating the spectrum logic module.

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
import pyqtgraph as pg
import numpy as np

from qudi.core.connector import Connector
from qudi.util.colordefs import QudiPalettePale as palette
from qudi.core.module import GuiBase
from qudi.util.widgets.plotting import colorbar
from qudi.util.colordefs import ColorScaleInferno
from qudi.util.colordefs import QudiPalette as palette
from qudi.core.statusvariable import StatusVar
from qudi.util.units import ScaledFloat
from qudi.util.mutex import Mutex
from qudi.util.widgets.fitting import FitWidget, FitConfigurationDialog
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class PowerControllerWindow(QtWidgets.QMainWindow):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_powercontroller.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class PowerControllerGui(GuiBase):
    """
    """
    
    # declare connectors
    powercontrollerlogic = Connector(interface='PowerControllerLogic')
    sigRecordSaturation = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        self._powercontrollerlogic = self.powercontrollerlogic()

        # setting up the window
        self._mw = PowerControllerWindow()

        #Vlad updates
        self.sigRecordSaturation.connect(self._powercontrollerlogic.run_saturation)
        self._powercontrollerlogic.sig_data_updated.connect(self.update_data)
        # giving the plots names allows us to link their axes together
        self._pw = self._mw.plotWidget  # pg.PlotWidget(name='Counter1')
        self._plot_item = self._pw.plotItem

        # create a new ViewBox, link the right axis to its coordinate system
        self._right_axis = pg.ViewBox()
        self._plot_item.showAxis('right')
        self._plot_item.scene().addItem(self._right_axis)
        self._plot_item.getAxis('right').linkToView(self._right_axis)
        self._right_axis.setXLink(self._plot_item)

        # create a new ViewBox, link the right axis to its coordinate system
        self._top_axis = pg.ViewBox()
        self._plot_item.showAxis('top')
        self._plot_item.scene().addItem(self._top_axis)
        self._plot_item.getAxis('top').linkToView(self._top_axis)
        self._top_axis.setYLink(self._plot_item)
        self._top_axis.invertX(b=True)

        # handle resizing of any of the elements

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('right', 'Number of Points', units='#')
        self._pw.setLabel('bottom', 'Wavelength', units='m')
        self._pw.setLabel('top', 'Relative Frequency', units='Hz')

        # Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen(palette.c1, width=2)

        self._curve2 = self._pw.plot()
        self._curve2.setPen(palette.c2, width=2)

        self.update_data()

        # Connect singals
        self._mw.calibrate_power_1_Action.triggered.connect(self.calibrate_power_wheel_1)

        self._mw.calibrate_power_2_Action.triggered.connect(self.calibrate_power_wheel_2)
        
        # self._mw.label_Power_1
        # self._mw.label_Power_2
        self._mw.p1HorizontalSlider.sliderReleased.connect(self.set_power_slider_1)
        # self._mw.p2HorizontalSlider


        self._mw.show()

        self._save_PNG = True



    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # disconnect signals

        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def set_power_slider_1(self):
        slider_val = float(self._mw.p1HorizontalSlider.value())
        powers_cal = self._powercontrollerlogic.power_calib[:, 1]
        vals = np.linspace(0, 360, powers_cal.shape[0])
        power = powers_cal[np.argmin(np.abs(vals - slider_val))]
        print("Set power", power)
        self._powercontrollerlogic.sig_set_power.emit(power, 3)


    def set_power_1(self):
        print("power", self._mw.power_1_doubleSpinBox.value())
        return 
    def set_power_2(self):
        print(self._mw.power_2_doubleSpinBox.value())
        return 

    def calibrate_power_wheel_1(self, is_checked):
        if is_checked:
            print("LEGO")
            self._mw.calibrate_power_1_Action.setChecked(True)
            self._powercontrollerlogic.stopRequested = False
            motor = 3
            self._powercontrollerlogic.sig_run_calibration.emit(motor)
        else:
            self._mw.calibrate_power_1_Action.setChecked(False)
            print("Remove calibration?")
            # self._powercontrollerlogic.stopRequested = True
    def calibrate_power_wheel_2(self, is_checked):
        if is_checked:
            self._mw.calibrate_power_2_Action.setChecked(True)
            self._powercontrollerlogic.stopRequested = False
            motor = 0
            self._powercontrollerlogic.sig_run_calibration.emit(motor)
        else:
            self._mw.calibrate_power_2_Action.setChecked(False)
            print("Remove calibration?")
            # self._powercontrollerlogic.stopRequested = True
    
    def update_data(self):

        """ The function that grabs the data and sends it to the plot.
        """
        self._mw.power_1_doubleSpinBox.setValue(self._powercontrollerlogic.current_power_1 * 1e9)
        self._mw.power_2_doubleSpinBox.setValue(self._powercontrollerlogic.current_power_2 * 1e3)
        
        data = self._powercontrollerlogic._saturation_data

        # erase previous fit line
        self._curve2.setData(x=[], y=[])
        
        # draw new data
        self._curve1.setData(x=data[0, :], y=data[1, :])

    def record_saturation(self):
        """ Handle resume of the scanning without resetting the data.
        """
        #FIX TIMING
        self.time_passed = 0
        self._mw.progressBar.setMaximum(1)
        self.sigRecordSaturation.emit(False)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateProgress)
        self.update_time = 500
        self.timer.start(self.update_time)
    
    def updateProgress(self):
        # int_time = self._mw.integration_time_doubleSpinBox.value()
        int_time = 1 #THIS IS WHAT?? fix

        self.time_passed += self.update_time/1000
        if self.time_passed >= int_time:
            self.timer.stop()
            self._mw.progressBar.setValue(int_time)
            return
        self._mw.progressBar.setValue(self.time_passed)

   
    # def save_spectrum_data(self):
    #     self._powercontrollerlogic.save_saturation_data()

    def correct_background(self):
        self._powercontrollerlogic.background_correction = self._mw.correct_background_Action.isChecked()

    def acquire_background(self):
        self.sigRecordSaturation.emit(True)
        # self._spectrum_logic.get_single_spectrum(background=True)

    # def save_background_data(self):
    #     self._powercontrollerlogic.save_saturation_data(background=True)

    
    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
      

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.measure_ToolBar)
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.background_ToolBar)

        return 0