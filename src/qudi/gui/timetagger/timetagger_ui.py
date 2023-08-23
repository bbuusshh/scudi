# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'timetagger.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from pyqtgraph import PlotWidget


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(838, 720)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QSize(0, 0))
        MainWindow.setMaximumSize(QSize(16777215, 16777215))
        MainWindow.setTabShape(QTabWidget.Rounded)
        MainWindow.setDockNestingEnabled(True)
        MainWindow.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.GroupedDragging)
        self.actionFit_settings = QAction(MainWindow)
        self.actionFit_settings.setObjectName(u"actionFit_settings")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setEnabled(False)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget_6 = QDockWidget(MainWindow)
        self.dockWidget_6.setObjectName(u"dockWidget_6")
        self.dockWidget_6.setMinimumSize(QSize(0, 0))
        self.dockWidget_6.setMaximumSize(QSize(524287, 95))
        self.dockWidget_6.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dockWidget_6.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.dockWidgetContents_6 = QWidget()
        self.dockWidgetContents_6.setObjectName(u"dockWidgetContents_6")
        sizePolicy1 = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.dockWidgetContents_6.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents_6.setSizePolicy(sizePolicy1)
        self.verticalLayout = QVBoxLayout(self.dockWidgetContents_6)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.save_g2_name_label = QLabel(self.dockWidgetContents_6)
        self.save_g2_name_label.setObjectName(u"save_g2_name_label")

        self.horizontalLayout_2.addWidget(self.save_g2_name_label)

        self.saveTagLineEdit = QLineEdit(self.dockWidgetContents_6)
        self.saveTagLineEdit.setObjectName(u"saveTagLineEdit")
        sizePolicy2 = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.saveTagLineEdit.sizePolicy().hasHeightForWidth())
        self.saveTagLineEdit.setSizePolicy(sizePolicy2)
        self.saveTagLineEdit.setMinimumSize(QSize(0, 0))

        self.horizontalLayout_2.addWidget(self.saveTagLineEdit)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_7 = QLabel(self.dockWidgetContents_6)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setMinimumSize(QSize(71, 0))

        self.horizontalLayout.addWidget(self.label_7)

        self.currPathLabel = QLabel(self.dockWidgetContents_6)
        self.currPathLabel.setObjectName(u"currPathLabel")
        sizePolicy3 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.currPathLabel.sizePolicy().hasHeightForWidth())
        self.currPathLabel.setSizePolicy(sizePolicy3)
        font = QFont()
        font.setFamily(u"Segoe UI Light")
        font.setPointSize(8)
        self.currPathLabel.setFont(font)

        self.horizontalLayout.addWidget(self.currPathLabel)

        self.DailyPathPushButton = QPushButton(self.dockWidgetContents_6)
        self.DailyPathPushButton.setObjectName(u"DailyPathPushButton")
        self.DailyPathPushButton.setCheckable(True)
        self.DailyPathPushButton.setAutoExclusive(True)

        self.horizontalLayout.addWidget(self.DailyPathPushButton)

        self.newPathPushButton = QPushButton(self.dockWidgetContents_6)
        self.newPathPushButton.setObjectName(u"newPathPushButton")
        self.newPathPushButton.setCheckable(True)
        self.newPathPushButton.setAutoExclusive(True)

        self.horizontalLayout.addWidget(self.newPathPushButton)

        self.counter_checkBox = QCheckBox(self.dockWidgetContents_6)
        self.counter_checkBox.setObjectName(u"counter_checkBox")
        self.counter_checkBox.setAutoExclusive(True)

        self.horizontalLayout.addWidget(self.counter_checkBox)

        self.corr_checkBox = QCheckBox(self.dockWidgetContents_6)
        self.corr_checkBox.setObjectName(u"corr_checkBox")
        self.corr_checkBox.setAutoExclusive(True)

        self.horizontalLayout.addWidget(self.corr_checkBox)

        self.hist_checkBox = QCheckBox(self.dockWidgetContents_6)
        self.hist_checkBox.setObjectName(u"hist_checkBox")
        self.hist_checkBox.setAutoExclusive(True)

        self.horizontalLayout.addWidget(self.hist_checkBox)

        self.saveAllPushButton = QPushButton(self.dockWidgetContents_6)
        self.saveAllPushButton.setObjectName(u"saveAllPushButton")
        self.saveAllPushButton.setMaximumSize(QSize(75, 23))

        self.horizontalLayout.addWidget(self.saveAllPushButton)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.dockWidget_6.setWidget(self.dockWidgetContents_6)
        MainWindow.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget_6)
        self.corr_dockWidget = QDockWidget(MainWindow)
        self.corr_dockWidget.setObjectName(u"corr_dockWidget")
        self.corr_dockWidget.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.corr_dockWidgetContents = QWidget()
        self.corr_dockWidgetContents.setObjectName(u"corr_dockWidgetContents")
        sizePolicy.setHeightForWidth(self.corr_dockWidgetContents.sizePolicy().hasHeightForWidth())
        self.corr_dockWidgetContents.setSizePolicy(sizePolicy)
        self.gridLayout_7 = QGridLayout(self.corr_dockWidgetContents)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.corr_groupBox = QGroupBox(self.corr_dockWidgetContents)
        self.corr_groupBox.setObjectName(u"corr_groupBox")
        self.corr_groupBox.setMaximumSize(QSize(178, 100000))
        self.verticalLayout_3 = QVBoxLayout(self.corr_groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.formLayout_10 = QFormLayout()
        self.formLayout_10.setObjectName(u"formLayout_10")
        self.label_5 = QLabel(self.corr_groupBox)
        self.label_5.setObjectName(u"label_5")

        self.formLayout_10.setWidget(1, QFormLayout.LabelRole, self.label_5)

        self.corrBinWidthDoubleSpinBox = QDoubleSpinBox(self.corr_groupBox)
        self.corrBinWidthDoubleSpinBox.setObjectName(u"corrBinWidthDoubleSpinBox")
        self.corrBinWidthDoubleSpinBox.setMinimum(1.000000000000000)
        self.corrBinWidthDoubleSpinBox.setMaximum(1000000.000000000000000)

        self.formLayout_10.setWidget(1, QFormLayout.FieldRole, self.corrBinWidthDoubleSpinBox)


        self.verticalLayout_3.addLayout(self.formLayout_10)

        self.formLayout_9 = QFormLayout()
        self.formLayout_9.setObjectName(u"formLayout_9")
        self.label_6 = QLabel(self.corr_groupBox)
        self.label_6.setObjectName(u"label_6")

        self.formLayout_9.setWidget(0, QFormLayout.LabelRole, self.label_6)

        self.corrRecordLengthDoubleSpinBox = QDoubleSpinBox(self.corr_groupBox)
        self.corrRecordLengthDoubleSpinBox.setObjectName(u"corrRecordLengthDoubleSpinBox")
        self.corrRecordLengthDoubleSpinBox.setDecimals(3)
        self.corrRecordLengthDoubleSpinBox.setMaximum(1000.000000000000000)
        self.corrRecordLengthDoubleSpinBox.setSingleStep(0.100000000000000)

        self.formLayout_9.setWidget(0, QFormLayout.FieldRole, self.corrRecordLengthDoubleSpinBox)


        self.verticalLayout_3.addLayout(self.formLayout_9)

        self.formLayout_11 = QFormLayout()
        self.formLayout_11.setObjectName(u"formLayout_11")
        self.toggleCorrPushButton = QPushButton(self.corr_groupBox)
        self.toggleCorrPushButton.setObjectName(u"toggleCorrPushButton")
        self.toggleCorrPushButton.setMaximumSize(QSize(16777215, 16777215))
        self.toggleCorrPushButton.setCheckable(True)

        self.formLayout_11.setWidget(0, QFormLayout.LabelRole, self.toggleCorrPushButton)

        self.resetCorrPushButton = QPushButton(self.corr_groupBox)
        self.resetCorrPushButton.setObjectName(u"resetCorrPushButton")

        self.formLayout_11.setWidget(0, QFormLayout.FieldRole, self.resetCorrPushButton)


        self.verticalLayout_3.addLayout(self.formLayout_11)

        self.fitLayout = QGridLayout()
        self.fitLayout.setObjectName(u"fitLayout")

        self.verticalLayout_3.addLayout(self.fitLayout)


        self.gridLayout_7.addWidget(self.corr_groupBox, 0, 1, 1, 1)

        self.verticalSpacer_3 = QSpacerItem(20, 298, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout_7.addItem(self.verticalSpacer_3, 1, 1, 1, 1)

        self.corrGraphicsView = PlotWidget(self.corr_dockWidgetContents)
        self.corrGraphicsView.setObjectName(u"corrGraphicsView")

        self.gridLayout_7.addWidget(self.corrGraphicsView, 0, 0, 2, 1)

        self.corr_dockWidget.setWidget(self.corr_dockWidgetContents)
        MainWindow.addDockWidget(Qt.TopDockWidgetArea, self.corr_dockWidget)
        self.dockWidget_4 = QDockWidget(MainWindow)
        self.dockWidget_4.setObjectName(u"dockWidget_4")
        self.dockWidget_4.setEnabled(True)
        self.dockWidget_4.setMinimumSize(QSize(280, 218))
        self.dockWidget_4.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.dockWidgetContents_4 = QWidget()
        self.dockWidgetContents_4.setObjectName(u"dockWidgetContents_4")
        sizePolicy.setHeightForWidth(self.dockWidgetContents_4.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents_4.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QGridLayout(self.dockWidgetContents_4)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.histGraphicsView = PlotWidget(self.dockWidgetContents_4)
        self.histGraphicsView.setObjectName(u"histGraphicsView")

        self.gridLayout_2.addWidget(self.histGraphicsView, 0, 0, 2, 1)

        self.groupBox = QGroupBox(self.dockWidgetContents_4)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy4 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy4)
        self.groupBox.setMaximumSize(QSize(185, 16777215))
        self.groupBox.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.label_19 = QLabel(self.groupBox)
        self.label_19.setObjectName(u"label_19")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_19)

        self.histBinWidthDoubleSpinBox = QDoubleSpinBox(self.groupBox)
        self.histBinWidthDoubleSpinBox.setObjectName(u"histBinWidthDoubleSpinBox")
        self.histBinWidthDoubleSpinBox.setDecimals(0)
        self.histBinWidthDoubleSpinBox.setMinimum(1.000000000000000)
        self.histBinWidthDoubleSpinBox.setMaximum(1000000000.000000000000000)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.histBinWidthDoubleSpinBox)


        self.gridLayout.addLayout(self.formLayout, 0, 0, 1, 1)

        self.formLayout_2 = QFormLayout()
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.label_20 = QLabel(self.groupBox)
        self.label_20.setObjectName(u"label_20")

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.label_20)

        self.histRecordLengthDoubleSpinBox = QDoubleSpinBox(self.groupBox)
        self.histRecordLengthDoubleSpinBox.setObjectName(u"histRecordLengthDoubleSpinBox")
        self.histRecordLengthDoubleSpinBox.setDecimals(3)
        self.histRecordLengthDoubleSpinBox.setMinimum(0.001000000000000)
        self.histRecordLengthDoubleSpinBox.setMaximum(10000.000000000000000)

        self.formLayout_2.setWidget(0, QFormLayout.FieldRole, self.histRecordLengthDoubleSpinBox)


        self.gridLayout.addLayout(self.formLayout_2, 1, 0, 1, 1)

        self.formLayout_15 = QFormLayout()
        self.formLayout_15.setObjectName(u"formLayout_15")
        self.toggleHistPushButton = QPushButton(self.groupBox)
        self.toggleHistPushButton.setObjectName(u"toggleHistPushButton")
        self.toggleHistPushButton.setMaximumSize(QSize(16777215, 16777215))
        self.toggleHistPushButton.setCheckable(True)

        self.formLayout_15.setWidget(0, QFormLayout.LabelRole, self.toggleHistPushButton)

        self.resetHistPushButton = QPushButton(self.groupBox)
        self.resetHistPushButton.setObjectName(u"resetHistPushButton")

        self.formLayout_15.setWidget(0, QFormLayout.FieldRole, self.resetHistPushButton)


        self.gridLayout.addLayout(self.formLayout_15, 3, 0, 1, 1)

        self.formLayout_5 = QFormLayout()
        self.formLayout_5.setObjectName(u"formLayout_5")
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")

        self.formLayout_5.setWidget(0, QFormLayout.LabelRole, self.label_3)

        self.histChannelComboBox = QComboBox(self.groupBox)
        self.histChannelComboBox.setObjectName(u"histChannelComboBox")
        sizePolicy5 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.histChannelComboBox.sizePolicy().hasHeightForWidth())
        self.histChannelComboBox.setSizePolicy(sizePolicy5)

        self.formLayout_5.setWidget(0, QFormLayout.FieldRole, self.histChannelComboBox)


        self.gridLayout.addLayout(self.formLayout_5, 2, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 0, 1, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(20, 472, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_2, 1, 1, 1, 1)

        self.dockWidget_4.setWidget(self.dockWidgetContents_4)
        MainWindow.addDockWidget(Qt.TopDockWidgetArea, self.dockWidget_4)
        self.dockWidget_3 = QDockWidget(MainWindow)
        self.dockWidget_3.setObjectName(u"dockWidget_3")
        sizePolicy.setHeightForWidth(self.dockWidget_3.sizePolicy().hasHeightForWidth())
        self.dockWidget_3.setSizePolicy(sizePolicy)
        self.dockWidget_3.setFloating(False)
        self.dockWidget_3.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.dockWidgetContents_3 = QWidget()
        self.dockWidgetContents_3.setObjectName(u"dockWidgetContents_3")
        sizePolicy.setHeightForWidth(self.dockWidgetContents_3.sizePolicy().hasHeightForWidth())
        self.dockWidgetContents_3.setSizePolicy(sizePolicy)
        self.gridLayout_8 = QGridLayout(self.dockWidgetContents_3)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.counterGraphicsView = PlotWidget(self.dockWidgetContents_3)
        self.counterGraphicsView.setObjectName(u"counterGraphicsView")

        self.gridLayout_8.addWidget(self.counterGraphicsView, 0, 0, 3, 1)

        self.groupBox_3 = QGroupBox(self.dockWidgetContents_3)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setMaximumSize(QSize(181, 16777215))
        self.gridLayout_6 = QGridLayout(self.groupBox_3)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.formLayout_7 = QFormLayout()
        self.formLayout_7.setObjectName(u"formLayout_7")
        self.label = QLabel(self.groupBox_3)
        self.label.setObjectName(u"label")

        self.formLayout_7.setWidget(0, QFormLayout.LabelRole, self.label)

        self.counterCountFreqDoubleSpinBox = QDoubleSpinBox(self.groupBox_3)
        self.counterCountFreqDoubleSpinBox.setObjectName(u"counterCountFreqDoubleSpinBox")
        self.counterCountFreqDoubleSpinBox.setDecimals(0)
        self.counterCountFreqDoubleSpinBox.setMinimum(1.000000000000000)
        self.counterCountFreqDoubleSpinBox.setMaximum(100000.000000000000000)

        self.formLayout_7.setWidget(0, QFormLayout.FieldRole, self.counterCountFreqDoubleSpinBox)


        self.gridLayout_6.addLayout(self.formLayout_7, 0, 0, 1, 1)

        self.formLayout_8 = QFormLayout()
        self.formLayout_8.setObjectName(u"formLayout_8")
        self.label_2 = QLabel(self.groupBox_3)
        self.label_2.setObjectName(u"label_2")

        self.formLayout_8.setWidget(0, QFormLayout.LabelRole, self.label_2)

        self.counterCountLengthDoubleSpinBox = QDoubleSpinBox(self.groupBox_3)
        self.counterCountLengthDoubleSpinBox.setObjectName(u"counterCountLengthDoubleSpinBox")
        self.counterCountLengthDoubleSpinBox.setDecimals(0)
        self.counterCountLengthDoubleSpinBox.setMinimum(1.000000000000000)
        self.counterCountLengthDoubleSpinBox.setMaximum(1000000.000000000000000)

        self.formLayout_8.setWidget(0, QFormLayout.FieldRole, self.counterCountLengthDoubleSpinBox)


        self.gridLayout_6.addLayout(self.formLayout_8, 1, 0, 1, 1)

        self.counterChannelGridLayout = QGridLayout()
        self.counterChannelGridLayout.setObjectName(u"counterChannelGridLayout")
        self.label_4 = QLabel(self.groupBox_3)
        self.label_4.setObjectName(u"label_4")

        self.counterChannelGridLayout.addWidget(self.label_4, 0, 0, 1, 1)


        self.gridLayout_6.addLayout(self.counterChannelGridLayout, 2, 0, 1, 1)

        self.toggleCounterPushButton = QPushButton(self.groupBox_3)
        self.toggleCounterPushButton.setObjectName(u"toggleCounterPushButton")
        self.toggleCounterPushButton.setMaximumSize(QSize(16777215, 16777215))
        self.toggleCounterPushButton.setInputMethodHints(Qt.ImhNone)
        self.toggleCounterPushButton.setCheckable(True)
        self.toggleCounterPushButton.setAutoExclusive(False)
        self.toggleCounterPushButton.setAutoDefault(False)
        self.toggleCounterPushButton.setFlat(False)

        self.gridLayout_6.addWidget(self.toggleCounterPushButton, 3, 0, 1, 1)


        self.gridLayout_8.addWidget(self.groupBox_3, 0, 1, 1, 1)

        self.frame = QFrame(self.dockWidgetContents_3)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(171, 0))
        self.frame.setMaximumSize(QSize(171, 102))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.gridLayout_4 = QGridLayout(self.frame)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.count_display_comboBox = QComboBox(self.frame)
        self.count_display_comboBox.setObjectName(u"count_display_comboBox")

        self.verticalLayout_2.addWidget(self.count_display_comboBox)

        self.count_display_label = QLabel(self.frame)
        self.count_display_label.setObjectName(u"count_display_label")
        font1 = QFont()
        font1.setFamily(u"Segoe UI Semilight")
        font1.setPointSize(20)
        font1.setBold(False)
        font1.setWeight(50)
        self.count_display_label.setFont(font1)
        self.count_display_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.verticalLayout_2.addWidget(self.count_display_label)


        self.gridLayout_4.addLayout(self.verticalLayout_2, 0, 0, 1, 1)


        self.gridLayout_8.addWidget(self.frame, 1, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 277, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout_8.addItem(self.verticalSpacer, 2, 1, 1, 1)

        self.dockWidget_3.setWidget(self.dockWidgetContents_3)
        MainWindow.addDockWidget(Qt.TopDockWidgetArea, self.dockWidget_3)
        self.toolBar = QToolBar(MainWindow)
        self.toolBar.setObjectName(u"toolBar")
        MainWindow.addToolBar(Qt.TopToolBarArea, self.toolBar)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 838, 21))
        MainWindow.setMenuBar(self.menuBar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.toolBar.addAction(self.actionFit_settings)

        self.retranslateUi(MainWindow)

        self.toggleCounterPushButton.setDefault(False)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"TimeTagger", None))
        self.actionFit_settings.setText(QCoreApplication.translate("MainWindow", u"Fit settings", None))
        self.dockWidget_6.setWindowTitle(QCoreApplication.translate("MainWindow", u"Save", None))
        self.save_g2_name_label.setText(QCoreApplication.translate("MainWindow", u"Tag", None))
        self.saveTagLineEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"SampleName", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Curr. path:", None))
        self.currPathLabel.setText(QCoreApplication.translate("MainWindow", u"Default", None))
        self.DailyPathPushButton.setText(QCoreApplication.translate("MainWindow", u"Daily Path", None))
        self.newPathPushButton.setText(QCoreApplication.translate("MainWindow", u"New Path", None))
        self.counter_checkBox.setText(QCoreApplication.translate("MainWindow", u"Counter", None))
        self.corr_checkBox.setText(QCoreApplication.translate("MainWindow", u"Autcorrelation", None))
        self.hist_checkBox.setText(QCoreApplication.translate("MainWindow", u"Histogram", None))
        self.saveAllPushButton.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.corr_dockWidget.setWindowTitle(QCoreApplication.translate("MainWindow", u"Autocorrelation", None))
        self.corr_groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Bin Width", None))
        self.corrBinWidthDoubleSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" ps", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Record Length", None))
        self.corrRecordLengthDoubleSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" us", None))
        self.toggleCorrPushButton.setText(QCoreApplication.translate("MainWindow", u"Toggle", None))
        self.resetCorrPushButton.setText(QCoreApplication.translate("MainWindow", u"Reset", None))
        self.dockWidget_4.setWindowTitle(QCoreApplication.translate("MainWindow", u"Histogram", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"Bin Width", None))
        self.histBinWidthDoubleSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" ps", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"Record Length", None))
        self.histRecordLengthDoubleSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" us", None))
        self.toggleHistPushButton.setText(QCoreApplication.translate("MainWindow", u"Toggle", None))
        self.resetHistPushButton.setText(QCoreApplication.translate("MainWindow", u"Reset", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Channel Num.", None))
        self.dockWidget_3.setWindowTitle(QCoreApplication.translate("MainWindow", u"Counter", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Count Freq.", None))
        self.counterCountFreqDoubleSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" Hz", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Count Length", None))
        self.counterCountLengthDoubleSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" s", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Channels:", None))
        self.toggleCounterPushButton.setText(QCoreApplication.translate("MainWindow", u"Toggle", None))
        self.count_display_label.setText(QCoreApplication.translate("MainWindow", u"0 Hz", None))
        self.toolBar.setWindowTitle(QCoreApplication.translate("MainWindow", u"toolBar", None))
    # retranslateUi

