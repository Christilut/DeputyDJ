from PyQt4 import QtGui, uic, QtCore
from src.utility import resource_path

def popup_about(parent):
    popup = AboutPopup(parent=parent)
    return popup.exec_()

class AboutPopup(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.popup = uic.loadUi(resource_path('interface/popup_about.ui'), self)
        self.setFixedSize(self.size())
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.Dialog)

    def mouseReleaseEvent(self, *args, **kwargs):
        self.accept()

    def keyPressEvent(self, QKeyEvent):
        self.accept()
