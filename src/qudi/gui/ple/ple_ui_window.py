
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


class PLEScanMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ple_gui.ui')

        # Load it
        super(PLEScanMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

        self.centralwidget.hide()
        self.ple_widget = ple_data_widget.PLEDataWidget()
        # self.data_dockwidget = AdvancedDockWidget('PLE Data', parent=self)
        self.ple_data_dockWidget.setWidget(self.ple_widget)

        # self.fit_widget = FitWidget()
        # self.fit_dockWidgetContents.addWidget(self.fit_widget)
        
        # self.data_dockwidget.show()
        # self.data_dockwidget.setFloating(False)
        # self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.data_dockwidget)
    
    def restore_view(self):
        # Resize main window
        # screen_size = QtWidgets.QApplication.instance().desktop().availableGeometry(self).size()
        # self.resize(screen_size.width() // 3, screen_size.height() // 2)

        # Rearrange DockWidget
        # if not self.action_show_data.isChecked():
        self.data_dockwidget.show()
        self.data_dockwidget.setFloating(False)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.data_dockwidget)