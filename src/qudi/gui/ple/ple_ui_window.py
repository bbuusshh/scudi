
from PySide2 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import qudi.util.uic as uic
import os
from qudi.util.widgets.advanced_dockwidget import AdvancedDockWidget
from qudi.util.widgets.fitting import FitWidget
import importlib

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
                *args, 
                **kwargs):
        # super().__init__(*args, **kwargs)
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ple_gui.ui')
        # axes_constr = self._scanning_logic().scanner_axes
        # axes_constr = tuple(axes_constr[ax] for ax in axes)
        # channel_constr = list(self._scanning_logic().scanner_channels.values())
        # Load it
        super(PLEScanMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

        self.centralwidget.hide()
        self.ple_widget = ple_data_widget.PLEDataWidget()
        self.ple_data_dockWidget.setWidget(self.ple_widget)

        self.matrix_widget = matrix_widget.PLE2DWidget()
        
        self.ple_matrix_dockWidget.setWidget(self.matrix_widget)

    def restore_view(self):
        # Resize main window
        # screen_size = QtWidgets.QApplication.instance().desktop().availableGeometry(self).size()
        # self.resize(screen_size.width() // 3, screen_size.height() // 2)

        # Rearrange DockWidget
        # if not self.action_show_data.isChecked():
        self.data_dockwidget.show()
        self.data_dockwidget.setFloating(False)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.data_dockwidget)