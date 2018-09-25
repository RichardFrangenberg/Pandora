# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PandoraChangeUser.ui'
#
# Created: Tue Jun 12 22:23:17 2018
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_ChangeUser(object):
    def setupUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setObjectName("dlg_ChangeUser")
        dlg_ChangeUser.resize(308, 101)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_ChangeUser)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(dlg_ChangeUser)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_name = QtWidgets.QLabel(self.widget)
        self.l_name.setObjectName("l_name")
        self.horizontalLayout.addWidget(self.l_name)
        self.e_name = QtWidgets.QLineEdit(self.widget)
        self.e_name.setObjectName("e_name")
        self.horizontalLayout.addWidget(self.e_name)
        self.verticalLayout.addWidget(self.widget)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_ChangeUser)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_ChangeUser)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_ChangeUser.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_ChangeUser.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_ChangeUser)

    def retranslateUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setWindowTitle(QtWidgets.QApplication.translate("dlg_ChangeUser", "Change User", None, -1))
        self.l_name.setText(QtWidgets.QApplication.translate("dlg_ChangeUser", "Username:", None, -1))

