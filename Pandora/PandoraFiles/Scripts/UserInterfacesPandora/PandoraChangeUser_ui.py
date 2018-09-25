# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PandoraChangeUser.ui'
#
# Created: Tue Jun 12 22:23:17 2018
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_ChangeUser(object):
    def setupUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setObjectName("dlg_ChangeUser")
        dlg_ChangeUser.resize(308, 101)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_ChangeUser)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtGui.QWidget(dlg_ChangeUser)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtGui.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_name = QtGui.QLabel(self.widget)
        self.l_name.setObjectName("l_name")
        self.horizontalLayout.addWidget(self.l_name)
        self.e_name = QtGui.QLineEdit(self.widget)
        self.e_name.setObjectName("e_name")
        self.horizontalLayout.addWidget(self.e_name)
        self.verticalLayout.addWidget(self.widget)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(dlg_ChangeUser)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_ChangeUser)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_ChangeUser.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_ChangeUser.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_ChangeUser)

    def retranslateUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setWindowTitle(QtGui.QApplication.translate("dlg_ChangeUser", "Change User", None, QtGui.QApplication.UnicodeUTF8))
        self.l_name.setText(QtGui.QApplication.translate("dlg_ChangeUser", "Username:", None, QtGui.QApplication.UnicodeUTF8))

