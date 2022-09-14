# -*- coding: utf-8 -*-

"""
This file contains a custom QWidget class to provide optimizer settings for each scanner axis.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

__all__ = ('TemperatureRegimeDialog', 'TemperatureRegimeWidget')

import copy as cp
from PySide2 import QtCore, QtGui, QtWidgets

from qudi.logic.scanning_optimize_logic import OptimizerScanSequence

class TemperatureRegimeDialog(QtWidgets.QDialog):
    """ User configurable settings for the scanner optimizer logic
    """

    def __init__(self):
        super().__init__()
        self.setObjectName('temperature_regime_dialog')
        self.setWindowTitle('Temperature Regime')

        self.regime_widget = TemperatureRegimeWidget()

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                     QtWidgets.QDialogButtonBox.Cancel,
                                                     QtCore.Qt.Horizontal,
                                                     self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.regime_widget)
        layout.addWidget(self.button_box)
        layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.setLayout(layout)
    
    @property
    def regime(self):
        return self.regime_widget.regime

class TemperatureRegimeWidget(QtWidgets.QWidget):
    """ User configurable settings for the scanner optimizer logic
    """

    def __init__(self):
        super().__init__()
        self.setObjectName('temperature_regime_widget')

        font = QtGui.QFont()
        font.setBold(True)

        self.regimes_combobox = QtWidgets.QComboBox()
        self.regimes_combobox.addItems(["Room Temperature", "Low Temperature"])

        regime_groupbox = QtWidgets.QGroupBox('Temperature Regime')
        regime_groupbox.setFont(font)
        regime_groupbox.setLayout(QtWidgets.QGridLayout())
        regime_groupbox.layout().addWidget(self.regimes_combobox, 0, 0)
        # regime_groupbox.layout().setColumnStretch(1, 1)
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(regime_groupbox)
        self.setLayout(layout)

    @property
    def regime(self):
        return self.regimes_combobox.currentText()



