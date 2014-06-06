from PyQt4 import QtGui, uic, QtCore
from src.utility import resource_path

def popup_settings_requests(parent):
    popup = SettingRequestsPopup(parent=parent)
    return popup.exec_()

class SettingRequestsPopup(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.popup = uic.loadUi(resource_path('interface/popup_settings_requests.ui'), self)
        self.setFixedSize(self.size())
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.Dialog)

        self.popup.buttonClose.clicked.connect(self.accept)
        self.popup.checkAvoidRadio.stateChanged.connect(self.checkbox_avoid_radio)
