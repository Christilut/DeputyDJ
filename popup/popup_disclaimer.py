from PyQt4 import QtGui, uic, QtCore
import logging, sys
from src.utility import resource_path
from src.utility.config import Config

def popup_disclaimer():
    popup = DisclaimerPopup()
    result = popup.exec_()

    if result != 1: # 0 is rejected
        logging.info('user declined disclaimer')
        sys.exit(0)

    logging.info('user accepted disclaimer')

class DisclaimerPopup(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self)
        self.popup = uic.loadUi(resource_path('interface/popup_disclaimer.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('res/icon.png')))
        self.setFixedSize(self.size())
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint)

        self.popup.buttonAccept.clicked.connect(self.button_accept)
        self.popup.buttonDecline.clicked.connect(self.popup.reject)

    def button_accept(self):
        if self.popup.checkNotShowAgain.isChecked():
            logging.info('user chose not to show disclaimer again')
            Config.set_general_option('disclaimer_accepted', True)

        self.popup.accept()