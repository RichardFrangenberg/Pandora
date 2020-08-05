# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'RenderHandler.ui'
#
# Created: Thu Dec  6 23:10:54 2018
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui


class Ui_mw_RenderHandler(object):
    def setupUi(self, mw_RenderHandler):
        mw_RenderHandler.setObjectName("mw_RenderHandler")
        mw_RenderHandler.resize(1348, 834)
        mw_RenderHandler.setDockNestingEnabled(False)
        self.centralwidget = QtGui.QWidget(mw_RenderHandler)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter_3 = QtGui.QSplitter(self.centralwidget)
        self.splitter_3.setOrientation(QtCore.Qt.Vertical)
        self.splitter_3.setHandleWidth(5)
        self.splitter_3.setObjectName("splitter_3")
        self.gb_jobs = QtGui.QGroupBox(self.splitter_3)
        self.gb_jobs.setObjectName("gb_jobs")
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.gb_jobs)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.splitter_2 = QtGui.QSplitter(self.gb_jobs)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.tw_jobs = QtGui.QTableWidget(self.splitter_2)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(10)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_jobs.sizePolicy().hasHeightForWidth())
        self.tw_jobs.setSizePolicy(sizePolicy)
        self.tw_jobs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_jobs.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tw_jobs.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.tw_jobs.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tw_jobs.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_jobs.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_jobs.setShowGrid(False)
        self.tw_jobs.setGridStyle(QtCore.Qt.NoPen)
        self.tw_jobs.setObjectName("tw_jobs")
        self.tw_jobs.setColumnCount(0)
        self.tw_jobs.setRowCount(0)
        self.tw_jobs.horizontalHeader().setCascadingSectionResizes(False)
        self.tw_jobs.horizontalHeader().setHighlightSections(False)
        self.tw_jobs.horizontalHeader().setStretchLastSection(True)
        self.tb_jobs = QtGui.QTabWidget(self.splitter_2)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(7)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tb_jobs.sizePolicy().hasHeightForWidth())
        self.tb_jobs.setSizePolicy(sizePolicy)
        self.tb_jobs.setObjectName("tb_jobs")
        self.tab = QtGui.QWidget()
        self.tab.setObjectName("tab")
        self.verticalLayout_7 = QtGui.QVBoxLayout(self.tab)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.tw_taskList = QtGui.QTableWidget(self.tab)
        self.tw_taskList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_taskList.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tw_taskList.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tw_taskList.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_taskList.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_taskList.setShowGrid(False)
        self.tw_taskList.setObjectName("tw_taskList")
        self.tw_taskList.setColumnCount(0)
        self.tw_taskList.setRowCount(0)
        self.tw_taskList.horizontalHeader().setHighlightSections(False)
        self.tw_taskList.horizontalHeader().setStretchLastSection(True)
        self.tw_taskList.verticalHeader().setVisible(False)
        self.verticalLayout_7.addWidget(self.tw_taskList)
        self.tb_jobs.addTab(self.tab, "")
        self.tab_7 = QtGui.QWidget()
        self.tab_7.setObjectName("tab_7")
        self.verticalLayout_6 = QtGui.QVBoxLayout(self.tab_7)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.tw_jobSettings = QtGui.QTableWidget(self.tab_7)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_jobSettings.sizePolicy().hasHeightForWidth())
        self.tw_jobSettings.setSizePolicy(sizePolicy)
        self.tw_jobSettings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_jobSettings.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
        self.tw_jobSettings.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tw_jobSettings.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_jobSettings.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_jobSettings.setObjectName("tw_jobSettings")
        self.tw_jobSettings.setColumnCount(0)
        self.tw_jobSettings.setRowCount(0)
        self.tw_jobSettings.horizontalHeader().setHighlightSections(False)
        self.tw_jobSettings.horizontalHeader().setStretchLastSection(True)
        self.tw_jobSettings.verticalHeader().setVisible(False)
        self.tw_jobSettings.verticalHeader().setHighlightSections(False)
        self.verticalLayout_6.addWidget(self.tw_jobSettings)
        self.tb_jobs.addTab(self.tab_7, "")
        self.t_coordSettings = QtGui.QWidget()
        self.t_coordSettings.setObjectName("t_coordSettings")
        self.verticalLayout_8 = QtGui.QVBoxLayout(self.t_coordSettings)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.tw_coordSettings = QtGui.QTableWidget(self.t_coordSettings)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_coordSettings.sizePolicy().hasHeightForWidth())
        self.tw_coordSettings.setSizePolicy(sizePolicy)
        self.tw_coordSettings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_coordSettings.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
        self.tw_coordSettings.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tw_coordSettings.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_coordSettings.setHorizontalScrollMode(
            QtGui.QAbstractItemView.ScrollPerPixel
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
        self.t_coordLog = QtGui.QWidget()
        self.t_coordLog.setObjectName("t_coordLog")
        self.verticalLayout_12 = QtGui.QVBoxLayout(self.t_coordLog)
        self.verticalLayout_12.setObjectName("verticalLayout_12")
        self.te_coordLog = QtGui.QTextEdit(self.t_coordLog)
        self.te_coordLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.te_coordLog.setReadOnly(True)
        self.te_coordLog.setObjectName("te_coordLog")
        self.verticalLayout_12.addWidget(self.te_coordLog)
        self.widget_2 = QtGui.QWidget(self.t_coordLog)
        self.widget_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.widget_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.l_coordLogSize = QtGui.QLabel(self.widget_2)
        self.l_coordLogSize.setText("")
        self.l_coordLogSize.setObjectName("l_coordLogSize")
        self.horizontalLayout_2.addWidget(self.l_coordLogSize)
        spacerItem = QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum
        )
        self.horizontalLayout_2.addItem(spacerItem)
        self.label_2 = QtGui.QLabel(self.widget_2)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.sp_coordFilter = QtGui.QSpinBox(self.widget_2)
        self.sp_coordFilter.setMaximumSize(QtCore.QSize(40, 16777215))
        self.sp_coordFilter.setObjectName("sp_coordFilter")
        self.horizontalLayout_2.addWidget(self.sp_coordFilter)
        self.verticalLayout_12.addWidget(self.widget_2)
        self.tb_jobs.addTab(self.t_coordLog, "")
        self.t_coordWarnings = QtGui.QWidget()
        self.t_coordWarnings.setObjectName("t_coordWarnings")
        self.verticalLayout_10 = QtGui.QVBoxLayout(self.t_coordWarnings)
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        self.tw_coordWarnings = QtGui.QTableWidget(self.t_coordWarnings)
        self.tw_coordWarnings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_coordWarnings.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tw_coordWarnings.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tw_coordWarnings.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_coordWarnings.setHorizontalScrollMode(
            QtGui.QAbstractItemView.ScrollPerPixel
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
        self.gb_slaves = QtGui.QGroupBox(self.splitter_3)
        self.gb_slaves.setObjectName("gb_slaves")
        self.verticalLayout_4 = QtGui.QVBoxLayout(self.gb_slaves)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.splitter = QtGui.QSplitter(self.gb_slaves)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.tw_slaves = QtGui.QTableWidget(self.splitter)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tw_slaves.sizePolicy().hasHeightForWidth())
        self.tw_slaves.setSizePolicy(sizePolicy)
        self.tw_slaves.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_slaves.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tw_slaves.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tw_slaves.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tw_slaves.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_slaves.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_slaves.setShowGrid(False)
        self.tw_slaves.setGridStyle(QtCore.Qt.NoPen)
        self.tw_slaves.setObjectName("tw_slaves")
        self.tw_slaves.setColumnCount(0)
        self.tw_slaves.setRowCount(0)
        self.tw_slaves.horizontalHeader().setHighlightSections(False)
        self.tw_slaves.horizontalHeader().setStretchLastSection(True)
        self.tb_slaves = QtGui.QTabWidget(self.splitter)
        self.tb_slaves.setObjectName("tb_slaves")
        self.tab_5 = QtGui.QWidget()
        self.tab_5.setObjectName("tab_5")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.tab_5)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.tw_slaveSettings = QtGui.QTableWidget(self.tab_5)
        self.tw_slaveSettings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_slaveSettings.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
        self.tw_slaveSettings.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tw_slaveSettings.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_slaveSettings.setHorizontalScrollMode(
            QtGui.QAbstractItemView.ScrollPerPixel
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
        self.tab_6 = QtGui.QWidget()
        self.tab_6.setObjectName("tab_6")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.tab_6)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.te_slaveLog = QtGui.QTextEdit(self.tab_6)
        self.te_slaveLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.te_slaveLog.setReadOnly(True)
        self.te_slaveLog.setObjectName("te_slaveLog")
        self.verticalLayout_2.addWidget(self.te_slaveLog)
        self.widget = QtGui.QWidget(self.tab_6)
        self.widget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtGui.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_slaveLogSize = QtGui.QLabel(self.widget)
        self.l_slaveLogSize.setText("")
        self.l_slaveLogSize.setObjectName("l_slaveLogSize")
        self.horizontalLayout.addWidget(self.l_slaveLogSize)
        spacerItem1 = QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum
        )
        self.horizontalLayout.addItem(spacerItem1)
        self.label = QtGui.QLabel(self.widget)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.sp_slaveFilter = QtGui.QSpinBox(self.widget)
        self.sp_slaveFilter.setMaximumSize(QtCore.QSize(40, 16777215))
        self.sp_slaveFilter.setObjectName("sp_slaveFilter")
        self.horizontalLayout.addWidget(self.sp_slaveFilter)
        self.verticalLayout_2.addWidget(self.widget)
        self.tb_slaves.addTab(self.tab_6, "")
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_9 = QtGui.QVBoxLayout(self.tab_2)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.tw_slaveWarnings = QtGui.QTableWidget(self.tab_2)
        self.tw_slaveWarnings.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_slaveWarnings.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tw_slaveWarnings.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tw_slaveWarnings.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_slaveWarnings.setHorizontalScrollMode(
            QtGui.QAbstractItemView.ScrollPerPixel
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
        self.menubar = QtGui.QMenuBar(mw_RenderHandler)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1348, 21))
        self.menubar.setObjectName("menubar")
        self.menuOptions = QtGui.QMenu(self.menubar)
        self.menuOptions.setObjectName("menuOptions")
        mw_RenderHandler.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(mw_RenderHandler)
        self.statusbar.setObjectName("statusbar")
        mw_RenderHandler.setStatusBar(self.statusbar)
        self.actionShowCoord = QtGui.QAction(mw_RenderHandler)
        self.actionShowCoord.setCheckable(True)
        self.actionShowCoord.setObjectName("actionShowCoord")
        self.menubar.addAction(self.menuOptions.menuAction())

        self.retranslateUi(mw_RenderHandler)
        self.tb_jobs.setCurrentIndex(0)
        self.tb_slaves.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(mw_RenderHandler)

    def retranslateUi(self, mw_RenderHandler):
        mw_RenderHandler.setWindowTitle(
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Render Handler", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.gb_jobs.setTitle(
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Jobs", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.tw_jobs.setSortingEnabled(True)
        self.tw_taskList.setSortingEnabled(True)
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.tab),
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Task List", None, QtGui.QApplication.UnicodeUTF8
            ),
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.tab_7),
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Settings", None, QtGui.QApplication.UnicodeUTF8
            ),
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.t_coordSettings),
            QtGui.QApplication.translate(
                "mw_RenderHandler",
                "Coordinator Settings",
                None,
                QtGui.QApplication.UnicodeUTF8,
            ),
        )
        self.label_2.setText(
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Filter Level:", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.t_coordLog),
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Coordinator Log", None, QtGui.QApplication.UnicodeUTF8
            ),
        )
        self.tb_jobs.setTabText(
            self.tb_jobs.indexOf(self.t_coordWarnings),
            QtGui.QApplication.translate(
                "mw_RenderHandler",
                "Coordinator Warnings",
                None,
                QtGui.QApplication.UnicodeUTF8,
            ),
        )
        self.gb_slaves.setTitle(
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Slaves", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.tw_slaves.setSortingEnabled(True)
        self.tb_slaves.setTabText(
            self.tb_slaves.indexOf(self.tab_5),
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Settings", None, QtGui.QApplication.UnicodeUTF8
            ),
        )
        self.label.setText(
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Filter Level:", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.tb_slaves.setTabText(
            self.tb_slaves.indexOf(self.tab_6),
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Log", None, QtGui.QApplication.UnicodeUTF8
            ),
        )
        self.tb_slaves.setTabText(
            self.tb_slaves.indexOf(self.tab_2),
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Warnings", None, QtGui.QApplication.UnicodeUTF8
            ),
        )
        self.menuOptions.setTitle(
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Options", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.actionShowCoord.setText(
            QtGui.QApplication.translate(
                "mw_RenderHandler", "Show Coordinator", None, QtGui.QApplication.UnicodeUTF8
            )
        )
