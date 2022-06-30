
from PySide2 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import qudi.util.uic as uic
import os

class PLEScanMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ple_gui.ui')

        # Load it
        super(PLEScanMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()
        