
from PySide2 import QtCore, QtGui, QtWidgets
import qudi.util.uic as uic
import os
from qudi.util.widgets.scientific_spinbox import ScienDSpinBox
import pyqtgraph as pg

class ControllerWidget(QtWidgets.QWidget):
    sig_controller_params_updated = QtCore.Signal(dict)
    params = {}

    def __init__(self, name, *args, **kwargs):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'controller_widget.ui')
        super(ControllerWidget, self).__init__(*args, **kwargs)
        uic.loadUi(ui_file, self)

        self.power_SpinBox.setDecimals(2)
        self.power_SpinBox.setSuffix('a.u.')

        self.power_SpinBox.editingFinished.connect(self.update_params)
        self.etalon_SpinBox.editingFinished.connect(self.update_params)
        self.blue_radioButton.toggled.connect(self.update_params)
        self.red_radioButton.toggled.connect(self.update_params)

        self.set_constraints()

    def update_params(self):
        self.params = {
        "power": self.power_SpinBox.value(),
        "eta_voltage": self.etalon_SpinBox.value(),
        "motor_direction" : 1 if self.blue_radioButton.isChecked() else -1
        }
        self.sig_controller_params_updated.emit(self.params)
    
    def update_gui(self, params):
        self.params.update(params)
        self.power_SpinBox.setValue(params['power'])
        self.etalon_SpinBox.setValue(params['eta_voltage'])
        self.blue_radioButton.setChecked( True if params['motor_direction'] > 0 else False)

    def set_constraints(self, constraints=None):
        # #TODO get pulse streamer constraints
        # self.LengthDoubleSpinBox.setRange(*(0, 5))
        # self.LengthDoubleSpinBox.setDecimals(1)
        # self.LengthDoubleSpinBox.setSuffix('s')

        # self.PeriodDoubleSpinBox.setRange(*(0, 5))
        # self.PeriodDoubleSpinBox.setDecimals(1)
        # self.PeriodDoubleSpinBox.setSuffix('s')

        # #TODO get power constraints
        # self.PowerDoubleSpinBox.setRange(*(0.0, 1.0))
        # self.PowerDoubleSpinBox.setSuffix(' ')#'μW')
        # self.PowerDoubleSpinBox.setDecimals(1)

        # #TODO get pulse streamer constraints
        # self.LengthDoubleSpinBox.setRange(*(0, 5))
        # self.LengthDoubleSpinBox.setDecimals(1)
        # self.LengthDoubleSpinBox.setSuffix('s')

        # self.DelayDoubleSpinBox.setRange(*(0, 5))
        # self.DelayDoubleSpinBox.setDecimals(1)
        # self.DelayDoubleSpinBox.setSuffix('s')

        # #TODO get power constraints
        # self.PowerDoubleSpinBox.setRange(*(0.0, 1.0))
        # self.PowerDoubleSpinBox.setDecimals(1)
        # self.PowerDoubleSpinBox.setSuffix(' ')#'μW')
        pass
