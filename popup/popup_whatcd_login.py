from PyQt4 import QtGui, uic, QtCore

from src.utility.config import Config
from src.utility import resource_path


def popup_whatcd_login(parent):
    popup = RequestLoginPopup(parent=parent)
    dialog_result = popup.exec_()
    password = popup.whatcdpassword
    return dialog_result, password, popup.checkRememberMe.isChecked()

class RequestLoginPopup(QtGui.QDialog):
    whatcdpassword = None

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.popup = uic.loadUi(resource_path('interface/popup_whatcd_login.ui'), self)
        self.setFixedSize(self.size())
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.Dialog)

        if Config.option_exists('requests', 'whatcd_username'):
            self.popup.editWhatCDUsername.setText(Config.getstring('requests', 'whatcd_username'))

        if Config.option_exists('requests', 'whatcd_password'):
            self.popup.editWhatCDPassword.setText(Config.getstring('requests', 'whatcd_password'))

        self.popup.editWhatCDUsername.editingFinished.connect(self.whatcd_username_finished)
        self.popup.buttonBox.accepted.connect(self.popup_accepted)

    def whatcd_username_finished(self):
        username = self.popup.editWhatCDUsername.text()
        Config.set_requests_option('whatcd_username', username)

    def popup_accepted(self):
        self.whatcdpassword = str(self.popup.editWhatCDPassword.text())

        self.popup.accept()