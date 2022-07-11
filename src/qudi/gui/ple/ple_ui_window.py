
from PySide2 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import qudi.util.uic as uic
import os
from qudi.util.widgets.advanced_dockwidget import AdvancedDockWidget
from qudi.util.widgets.fitting import FitWidget
import importlib
from qudi.interface.scanning_probe_interface import ScanData, ScannerAxis, ScannerChannel
from typing import Tuple, Union, Sequence
from typing import Optional, List
try:
    importlib.reload(ple_data_widget)
except NameError:
    import qudi.gui.ple.ple_data_widget as ple_data_widget
try:
    importlib.reload(matrix_widget)
except NameError:
    import qudi.gui.ple.matrix_widget as matrix_widget



class PLEScanMainWindow(QtWidgets.QMainWindow):

    def __init__(self,
                axes: Tuple[ScannerAxis],
                channel: ScannerChannel,
                parent: Optional[QtWidgets.QWidget] = None):
       
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ple_gui.ui')
        # Load it
        super(PLEScanMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

        self.centralwidget.hide()

        self.ple_widget = ple_data_widget.PLEDataWidget(axes, channel)
        self.ple_data_dockWidget.setWidget(self.ple_widget)

        self.matrix_widget = matrix_widget.PLE2DWidget(axes, channel)
        self.ple_matrix_dockWidget.setWidget(self.matrix_widget)

        self.add_dock_widget('repump')
        self.add_dock_widget('microwave')
        

    def add_dock_widget(self, name):

        if name == 'microwave':
            self.microwave_widget = PleMicrowaveWidget()
            widget = self.microwave_widget
        elif name == 'repump':
            self.repump_widget = PleRepumpWidget()
            widget = self.repump_widget

        setattr(self, f"{name}_dockWidget", QtWidgets.QDockWidget())
        dockWidget = getattr(self, f"{name}_dockWidget")
        dockWidget.setWindowTitle(name)
        dockWidget.setFloating(True)
       
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockWidget)
        dockWidget.setWidget(widget)



    def restore_view(self):
        # Resize main window
        # screen_size = QtWidgets.QApplication.instance().desktop().availableGeometry(self).size()
        # self.resize(screen_size.width() // 3, screen_size.height() // 2)

        # Rearrange DockWidget
        # if not self.action_show_data.isChecked():
        self.data_dockwidget.show()
        self.data_dockwidget.setFloating(False)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.data_dockwidget)

class PleMicrowaveWidget(QtWidgets.QWidget):
    sig_microwave_params_updated = QtCore.Signal(float, float)
    sig_microwave_enabled = QtCore.Signal(bool)

    params = {}
    def __init__(self, *args, **kwargs):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'microwave_widget.ui')
        super(PleMicrowaveWidget, self).__init__(*args, **kwargs)
        uic.loadUi(ui_file, self)
        
        self.enabledCheckBox.toggled.connect(
            lambda: self.sig_microwave_enabled.emit(self.enabledCheckBox.isChecked())
        )
        self.FreqDoubleSpinBox.valueChanged.connect(
            lambda: self.sig_microwave_params_updated.emit(self.FreqDoubleSpinBox.value(), self.PowerDoubleSpinBox.value())
        )
        self.PowerDoubleSpinBox.valueChanged.connect(
            lambda: self.sig_microwave_params_updated.emit(self.FreqDoubleSpinBox.value(), self.PowerDoubleSpinBox.value())
        )
            # self.FreqDoubleSpinBox.value()
            # self.PowerDoubleSpinBox.value()
        # self.show()
    @QtCore.Slot(dict)
    def update_params(self, params):
        self.FreqDoubleSpinBox.setValue(params['frequency'])
        self.PowerDoubleSpinBox.setValue(params['power'])
        
    @QtCore.Slot(bool)
    def enable_microwave(self, enabled):
        self.enabledCheckBox.setChecked(enabled)

    def set_constraints(self, constraints):
        self.FreqDoubleSpinBox.setRange(*constraints.frequency_limits)
        # self.FreqDoubleSpinBox.setDecimals(6)
        self.FreqDoubleSpinBox.setSuffix('Hz')

        self.PowerDoubleSpinBox.setRange(*constraints.power_limits)
        self.PowerDoubleSpinBox.setSuffix('dBm')

class PleRepumpWidget(QtWidgets.QWidget):
    sig_control_widget_updated = QtCore.Signal(dict)
    params = {}
    def __init__(self, *args, **kwargs):
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'repump_widget.ui')
        super(PleRepumpWidget, self).__init__(*args, **kwargs)
        uic.loadUi(ui_file, self)
        
        self.enabledCheckBox.toggled.connect(
            lambda: self.sig_control_widget_updated.emit({'enabled': self.enabledCheckBox.isChecked()})
        )

        self.PowerDoubleSpinBox.editingFinished.connect(
            lambda: self.sig_control_widget_updated.emit({'power': self.PowerDoubleSpinBox.value()})
        )
            # self.FreqDoubleSpinBox.value()
            # self.PowerDoubleSpinBox.value()
        # self.show()
    @QtCore.Slot(dict)
    def update_params(self, params):
        self.PowerDoubleSpinBox.setValue(params['power'])
        self.enabledCheckBox.setValue(params['enabled'])