
from PySide2 import QtCore, QtGui, QtWidgets
import os
import qudi.util.uic as uic
class PleRepumpWidget(QtWidgets.QWidget):
    sig_repump_params_updated = QtCore.Signal(dict)
    sig_repump_enabled = QtCore.Signal(bool)
    sig_repump_pulsed = QtCore.Signal(bool)

    params = {}
    def __init__(self, name, *args, **kwargs):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'repump_widget.ui')
        super(PleRepumpWidget, self).__init__(*args, **kwargs)
        uic.loadUi(ui_file, self)
        
        self.enabledCheckBox.toggled.connect(
            lambda: self.sig_repump_enabled.emit(self.enabledCheckBox.isChecked())
        )

        self.pulsedCheckBox.toggled.connect(
            lambda: self.sig_repump_pulsed.emit(self.pulsedCheckBox.isChecked())
        )
        self.PowerDoubleSpinBox.editingFinished.connect(
            lambda: self.sig_repump_params_updated.emit({'power': self.PowerDoubleSpinBox.value()})
        )
        self.DelayDoubleSpinBox.editingFinished.connect(
            lambda: self.sig_repump_params_updated.emit({'delay': self.DelayDoubleSpinBox.value()})
        )
        self.LengthDoubleSpinBox.editingFinished.connect(
            lambda: self.sig_repump_params_updated.emit( {'length': self.LengthDoubleSpinBox.value()})
        )
        self.set_constraints()
            # self.FreqDoubleSpinBox.value()
            # self.PowerDoubleSpinBox.value()
        # self.show()
    
    @QtCore.Slot(str, dict)
    def update_params(self, type, params):
        if type != 'repump':
            return 
        params = params[type]
        self.DelayDoubleSpinBox.setValue(params['delay'])
        self.LengthDoubleSpinBox.setValue(params['length'])
        self.PowerDoubleSpinBox.setValue(params['power'])
        self.enabledCheckBox.setChecked(params['enabled'])
        self.pulsedCheckBox.setChecked(params['pulsed'])

    @QtCore.Slot(bool)
    def enable_pulsed(self, enabled):
        self.enabledCheckBox.setChecked(enabled)

    def set_constraints(self, constraints=None):
        #TODO get pulse streamer constraints
        self.LengthDoubleSpinBox.setRange(*(0, 5))
        self.LengthDoubleSpinBox.setDecimals(1)
        self.LengthDoubleSpinBox.setSuffix('s')

        self.DelayDoubleSpinBox.setRange(*(0, 5))
        self.DelayDoubleSpinBox.setDecimals(1)
        self.DelayDoubleSpinBox.setSuffix('s')

        #TODO get power constraints
        self.PowerDoubleSpinBox.setRange(*(0.0, 1.0))
        self.PowerDoubleSpinBox.setDecimals(1)
        self.PowerDoubleSpinBox.setSuffix(' ')#'μW')



    
class PlePulseWidget(QtWidgets.QWidget):
    sig_pulser_params_updated = QtCore.Signal(dict)
    sig_pulser_enabled = QtCore.Signal(bool)
    sig_pulser_pulsed = QtCore.Signal(bool)

    params = {}
    def __init__(self, name, *args, **kwargs):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'pulse_widget.ui')
        super(PlePulseWidget, self).__init__(*args, **kwargs)
        uic.loadUi(ui_file, self)
        
        self.enabledCheckBox.toggled.connect(
            lambda: self.sig_pulser_enabled.emit(self.enabledCheckBox.isChecked())
        )
        self.pulsedCheckBox.toggled.connect(
            lambda: self.sig_pulser_pulsed.emit(self.pulsedCheckBox.isChecked())
        )

        self.PowerDoubleSpinBox.editingFinished.connect(
            lambda: self.sig_pulser_params_updated.emit({'power': self.PowerDoubleSpinBox.value()})
        )
        self.PeriodDoubleSpinBox.editingFinished.connect(
            lambda: self.sig_pulser_params_updated.emit({'period': self.PeriodDoubleSpinBox.value()})
        )
        self.LengthDoubleSpinBox.editingFinished.connect(
            lambda: self.sig_pulser_params_updated.emit({'length': self.LengthDoubleSpinBox.value()})
        )
        self.set_constraints()
            # self.FreqDoubleSpinBox.value()
            # self.PowerDoubleSpinBox.value()
        # self.show()
    
    @QtCore.Slot(str, dict)
    def update_params(self, type, params):
        if type != 'resonant':
            return 
        params = params[type]
        self.PeriodDoubleSpinBox.setValue(params['period'])
        self.LengthDoubleSpinBox.setValue(params['length'])
        self.PowerDoubleSpinBox.setValue(params['power'])
        self.enabledCheckBox.setChecked(params['enabled'])
        self.pulsedCheckBox.setChecked(params['pulsed'])

    @QtCore.Slot(bool)
    def enable_pulsed(self, enabled):
        self.enabledCheckBox.setChecked(enabled)

    def set_constraints(self, constraints=None):
        #TODO get pulse streamer constraints
        self.LengthDoubleSpinBox.setRange(*(0, 5))
        self.LengthDoubleSpinBox.setDecimals(1)
        self.LengthDoubleSpinBox.setSuffix('s')

        self.PeriodDoubleSpinBox.setRange(*(0, 5))
        self.PeriodDoubleSpinBox.setDecimals(1)
        self.PeriodDoubleSpinBox.setSuffix('s')

        #TODO get power constraints
        self.PowerDoubleSpinBox.setRange(*(0.0, 1.0))
        self.PowerDoubleSpinBox.setSuffix(' ')#'μW')
        self.PowerDoubleSpinBox.setDecimals(1)

