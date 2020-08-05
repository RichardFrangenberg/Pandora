# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'RenderHandler.ui',
# licensing of 'RenderHandler.ui' applies.
#
# Created: Thu Dec  6 23:10:54 2018
#      by: pyside2-uic  running on PySide2 5.9.0a1.dev1528389443
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets


class Ui_mw_RenderHandler(object):
    def setupUi(self, mw_RenderHandler):
        mw_RenderHandler.setObjectName("mw_RenderHandler")
        mw_RenderHandler.resize(1348, 834)
        mw_RenderHandler.setDockNestingEnabled(False)
        self.centralwidget = QtWidgets.QWidget(mw_RenderHandler)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter_3 = QtWidgets.QSplitter(self.centralwidget)
        self.splitter_3.setOrientation(QtCore.Qt.Vertical)
        self.splitter_3.setHandleWidth(5)
        self.splitter_3.setObjectName("splitter_3")
        self.gb_jobs = QtWidgets.QGroupBox(self.splitter_3)
        self.gb_jobs.setObjectName("gb_jobs")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.gb_jobs)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.splitter_2 = QtWidgets.QSplitter(self.gb_jobs)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.tw_jobs = QtWidgets.QTableWidget(self.splitter_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(10)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_jobs.sizePolicy().hasHeightForWidth())
        self.tw_jobs.setSizePolicy(sizePolicy)
        self.tw_jobs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_jobs.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_jobs.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tw_jobs.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_jobs.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_jobs.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_jobs.setShowGrid(False)
        self.tw_jobs.setGridStyle(QtCore.Qt.NoPen)
        self.tw_jobs.setObjectName("tw_jobs")
        self.tw_jobs.setColumnCount(0)
        self.tw_jobs.setRowCount(0)
        self.tw_jobs.horizontalHeader().setCascadingSectionResizes(False)
        self.tw_jobs.horizontalHeader().setHighlightSections(False)
        self.tw_jobs.horizontalHeader().setStretchLastSection(True)
        self.tb_jobs = QtWidgets.QTabWidget(self.splitter_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(7)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tb_jobs.sizePolicy().hasHeightForWidth())
        self.tb_jobs.setSizePolicy(sizePolicy)
        self.tb_jobs.setObjectName("tb_jobs")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.tab)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.tw_taskList = QtWidgets.QTableWidget(self.tab)
        self.tw_taskList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_taskList.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_taskList.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_taskList.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_taskList.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_taskList.setShowGrid(False)
        self.tw_taskList.setObjectName("tw_taskList")
        self.tw_taskList.setColumnCount(0)
        self.tw_taskList.setRowCount(0)
        self.tw_taskList.horizontalHeader().setHighlightSections(False)
        self.tw_taskList.horizontalHeader().setStretchLastSection(True)
        self.tw_taskList.verticalHeader().setVisible(False)
        self.verticalLayout_7.addWidget(self.tw_taskList)
        self.tb_jobs.addTab(self.tab, "")
        self.tab_7 = QtWidgets.QWidget()
        self.tab_7.setObjectName("tab_7")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.tab_7)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.tw_jobSettings = QtWidgets.QTableWidget(self.tab_7)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_jobSettings.sizePolicy().hasHeightForWidth())
        self.tw_jobSettings.setSizePolicy(sizePolicy)
        self.tw_jobSettings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_jobSettings.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.tw_jobSettings.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tw_jobSettings.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_jobSettings.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_jobSettings.setObjectName("tw_jobSettings")
        self.tw_jobSettings.setColumnCount(0)
        self.tw_jobSettings.setRowCount(0)
        self.tw_jobSettings.horizontalHeader().setHighlightSections(False)
        self.tw_jobSettings.horizontalHeader().setStretchLastSection(True)
        self.tw_jobSettings.verticalHeader().setVisible(False)
        self.tw_jobSettings.verticalHeader().setHighlightSections(False)
        self.verticalLayout_6.addWidget(self.tw_jobSettings)
        self.tb_jobs.addTab(self.tab_7, "")
        self.t_coordSettings = QtWidgets.QWidget()
        self.t_coordSettings.setObjectName("t_coordSettings")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.t_coordSettings)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.tw_coordSettings = QtWidgets.QTableWidget(self.t_coordSettings)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_coordSettings.sizePolicy().hasHeightForWidth())
        self.tw_coordSettings.setSizePolicy(sizePolicy)
        self.tw_coordSettings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_coordSettings.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.tw_coordSettings.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tw_coordSettings.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_coordSettings.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_coordSettings.setObjectName("tw_coordSettings")
        self.tw_coordSettings.setColumnCount(0)
        self.tw_coordSettings.setRowCount(0)
        self.tw_coordSettings.horizontalHeader().setHighlightSections(False)
        self.tw_coordSettings.horizontalHeader().setStretchLastSection(True)
        self.tw_coordSettings.verticalHeader().setVisible(False)
        self.tw_coordSettings.verticalHeader().setHighlightSections(False)
        self.verticalLayout_8.addWidget(self.tw_coordSettings)
        self.tb_jobs.addTab(self.t_coordSettings, "")
        self.t_coordLog = QtWidgets.QWidget()
        self.t_coordLog.setObjectName("t_coordLog")
        self.verticalLayout_12 = QtWidgets.QVBoxLayout(self.t_coordLog)
        self.verticalLayout_12.setObjectName("verticalLayout_12")
        self.te_coordLog = QtWidgets.QTextEdit(self.t_coordLog)
        self.te_coordLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.te_coordLog.setReadOnly(True)
        self.te_coordLog.setObjectName("te_coordLog")
        self.verticalLayout_12.addWidget(self.te_coordLog)
        self.widget_2 = QtWidgets.QWidget(self.t_coordLog)
        self.widget_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.l_coordLogSize = QtWidgets.QLabel(self.widget_2)
        self.l_coordLogSize.setText("")
        self.l_coordLogSize.setObjectName("l_coordLogSize")
        self.horizontalLayout_2.addWidget(self.l_coordLogSize)
        spacerItem = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_2.addItem(spacerItem)
        self.label_2 = QtWidgets.QLabel(self.widget_2)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.sp_coordFilter = QtWidgets.QSpinBox(self.widget_2)
        self.sp_coordFilter.setMaximumSize(QtCore.QSize(40, 16777215))
        self.sp_coordFilter.setObjectName("sp_coordFilter")
        self.horizontalLayout_2.addWidget(self.sp_coordFilter)
        self.verticalLayout_12.addWidget(self.widget_2)
        self.tb_jobs.addTab(self.t_coordLog, "")
        self.t_coordWarnings = QtWidgets.QWidget()
        self.t_coordWarnings.setObjectName("t_coordWarnings")
        self.verticalLayout_10 = QtWidgets.QVBoxLayout(self.t_coordWarnings)
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        self.tw_coordWarnings = QtWidgets.QTableWidget(self.t_coordWarnings)
        self.tw_coordWarnings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_coordWarnings.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_coordWarnings.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_coordWarnings.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_coordWarnings.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_coordWarnings.setColumnCount(2)
        self.tw_coordWarnings.setObjectName("tw_coordWarnings")
        self.tw_coordWarnings.setColumnCount(2)
        self.tw_coordWarnings.setRowCount(0)
        self.tw_coordWarnings.horizontalHeader().setVisible(False)
        self.tw_coordWarnings.horizontalHeader().setStretchLastSection(True)
        self.tw_coordWarnings.verticalHeader().setHighlightSections(False)
        self.verticalLayout_10.addWidget(self.tw_coordWarnings)
        self.tb_jobs.addTab(self.t_coordWarnings, "")
        self.verticalLayout_5.addWidget(self.splitter_2)
        self.gb_slaves = QtWidgets.QGroupBox(self.splitter_3)
        self.gb_slaves.setObjectName("gb_slaves")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.gb_slaves)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.splitter = QtWidgets.QSplitter(self.gb_slaves)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.tw_slaves = QtWidgets.QTableWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_slaves.sizePolicy().hasHeightForWidth())
        self.tw_slaves.setSizePolicy(sizePolicy)
        self.tw_slaves.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_slaves.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_slaves.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tw_slaves.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_slaves.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_slaves.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_slaves.setShowGrid(False)
        self.tw_slaves.setGridStyle(QtCore.Qt.NoPen)
        self.tw_slaves.setObjectName("tw_slaves")
        self.tw_slaves.setColumnCount(0)
        self.tw_slaves.setRowCount(0)
        self.tw_slaves.horizontalHeader().setHighlightSections(False)
        self.tw_slaves.horizontalHeader().setStretchLastSection(True)
        self.tb_slaves = QtWidgets.QTabWidget(self.splitter)
        self.tb_slaves.setObjectName("tb_slaves")
        self.tab_5 = QtWidgets.QWidget()
        self.tab_5.setObjectName("tab_5")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.tab_5)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.tw_slaveSettings = QtWidgets.QTableWidget(self.tab_5)
        self.tw_slaveSettings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_slaveSettings.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.tw_slaveSettings.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tw_slaveSettings.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_slaveSettings.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_slaveSettings.setObjectName("tw_slaveSettings")
        self.tw_slaveSettings.setColumnCount(0)
        self.tw_slaveSettings.setRowCount(0)
        self.tw_slaveSettings.horizontalHeader().setHighlightSections(False)
        self.tw_slaveSettings.horizontalHeader().setStretchLastSection(True)
        self.tw_slaveSettings.verticalHeader().setVisible(False)
        self.tw_slaveSettings.verticalHeader().setHighlightSections(False)
        self.verticalLayout_3.addWidget(self.tw_slaveSettings)
        self.tb_slaves.addTab(self.tab_5, "")
        self.tab_6 = QtWidgets.QWidget()
        self.tab_6.setObjectName("tab_6")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.tab_6)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.te_slaveLog = QtWidgets.QTextEdit(self.tab_6)
        self.te_slaveLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.te_slaveLog.setReadOnly(True)
        self.te_slaveLog.setObjectName("te_slaveLog")
        self.verticalLayout_2.addWidget(self.te_slaveLog)
        self.widget = QtWidgets.QWidget(self.tab_6)
        self.widget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_slaveLogSize = QtWidgets.QLabel(self.widget)
        self.l_slaveLogSize.setText("")
        self.l_slaveLogSize.setObjectName("l_slaveLogSize")
        self.horizontalLayout.addWidget(self.l_slaveLogSize)
        spacerItem1 = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout.addItem(spacerItem1)
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.sp_slaveFilter = QtWidgets.QSpinBox(self.widget)
        self.sp_slaveFilter.setMaximumSize(QtCore.QSize(40, 16777215))
        self.sp_slaveFilter.setObjectName("sp_slaveFilter")
        self.horizontalLayout.addWidget(self.sp_slaveFilter)
        self.verticalLayout_2.addWidget(self.widget)
        self.tb_slaves.addTab(self.tab_6, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout(self.tab_2)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.tw_slaveWarnings = QtWidgets.QTableWidget(self.tab_2)
        self.tw_slaveWarnings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_slaveWarnings.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_slaveWarnings.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_slaveWarnings.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_slaveWarnings.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.tw_slaveWarnings.setColumnCount(2)
        self.tw_slaveWarnings.setObjectName("tw_slaveWarnings")
        self.tw_slaveWarnings.setColumnCount(2)
        self.tw_slaveWarnings.setRowCount(0)
        self.tw_slaveWarnings.horizontalHeader().setVisible(False)
        self.tw_slaveWarnings.horizontalHeader().setStretchLastSection(True)
        self.tw_slaveWarnings.verticalHeader().setHighlightSections(False)
        self.verticalLayout_9.addWidget(self.tw_slaveWarnings)
        self.tb_slaves.addTab(self.tab_2, "")
        self.verticalLayout_4.addWidget(self.splitter)
        self.verticalLayout.addWidget(self.splitter_3)
        mw_RenderHandler.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(mw_RenderHandler)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1348, 21))
        self.menubar.setObjectName("menubar")
        self.menuOptions = QtWidgets.QMenu(self.menubar)
        self.menuOptions.setObjectName("menuOptions")
        mw_RenderHandler.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(mw_RenderHandler)
        self.statusbar.setObjectName("statusbar")
        mw_RenderHandler.setStatusBar(self.statusbar)
        self.actionShowCoord = QtWidgets.QAction(mw_RenderHandler)
        self.actionShowCoord.setCheckable(True)
        self.actionShowCoord.setObjectName("actionShowCoord")
        self.menubar.addAction(self.menuOptions.menuAction())

        self.retranslateUi(mw_RenderHandler)
        self.tb_jobs.setCurrentIndex(0)
        self.tb_slaves.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(mw_RenderHandler)

    def retranslateUi(self, mw_RenderHandler):
        mw_RenderHandler.setWindowTitle(
            QtWidgets.QApplication.translate("mw_RenderHandler", "Render Handler", None, -1)
        )
        self.gb_jobs.setTitle(
            QtWidgets.QApplication.translate("mw_RenderHandler", "Jobs", None, -1)
        )
        self.tw_jobs.setSortingEnabled(True)
        self.tw_taskList.setSortingEnabled(True)
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.tab),
            QtWidgets.QApplication.translate("mw_RenderHandler", "Task List", None, -1),
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.tab_7),
            QtWidgets.QApplication.translate("mw_RenderHandler", "Settings", None, -1),
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.t_coordSettings),
            QtWidgets.QApplication.translate(
                "mw_RenderHandler", "Coordinator Settings", None, -1
            ),
        )
        self.label_2.setText(
            QtWidgets.QApplication.translate("mw_RenderHandler", "Filter Level:", None, -1)
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.t_coordLog),
            QtWidgets.QApplication.translate(
                "mw_RenderHandler", "Coordinator Log", None, -1
            ),
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.t_coordWarnings),
            QtWidgets.QApplication.translate(
                "mw_RenderHandler", "Coordinator Warnings", None, -1
            ),
        )
        self.gb_slaves.setTitle(
            QtWidgets.QApplication.translate("mw_RenderHandler", "Slaves", None, -1)
        )
        self.tw_slaves.setSortingEnabled(True)
        self.tb_slaves.setTabText(
            self.tb_slaves.indexOf(self.tab_5),
            QtWidgets.QApplication.translate("mw_RenderHandler", "Settings", None, -1),
        )
        self.label.setText(
            QtWidgets.QApplication.translate("mw_RenderHandler", "Filter Level:", None, -1)
        )
        self.tb_slaves.setTabText(
            self.tb_slaves.indexOf(self.tab_6),
            QtWidgets.QApplication.translate("mw_RenderHandler", "Log", None, -1),
        )
        self.tb_slaves.setTabText(
            self.tb_slaves.indexOf(self.tab_2),
            QtWidgets.QApplication.translate("mw_RenderHandler", "Warnings", None, -1),
        )
        self.menuOptions.setTitle(
            QtWidgets.QApplication.translate("mw_RenderHandler", "Options", None, -1)
        )
        self.actionShowCoord.setText(
            QtWidgets.QApplication.translate(
                "mw_RenderHandler", "Show Coordinator", None, -1
            )
        )
