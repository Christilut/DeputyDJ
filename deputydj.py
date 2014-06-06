import sys, logging, os, time, shutil, appdirs

from PyQt4 import QtGui, uic, QtCore

from popup.popup_about import popup_about
from popup.popup_disclaimer import popup_disclaimer
from popup.popup_settings_requests import popup_settings_requests
from src.utility.config import Config
from src.utility import resource_path, open_folder
from src.ui.ui_track_history import UITrackHistory
from src.ui.ui_track_requests import UITrackRequests


class MainWindow(QtGui.QMainWindow):


    def __init__(self):
        super(MainWindow, self).__init__()

        self.widget = uic.loadUi(resource_path('interface/mainwindow.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('res/icon.png')))
        self.setWindowFlags(QtCore.Qt.WindowMaximizeButtonHint)

        self.init_action_bar()

        self.widget.widgetRequests = UITrackRequests(self.widget.tabRequests)
        self.widget.widgetHistory = UITrackHistory(self.widget.tabHistory)


    def closeEvent(self, *args, **kwargs):
        self._exit()

    def init_action_bar(self):
        self.widget.actionOpenLog.triggered.connect(lambda: open_folder(appdirs.dirs.user_log_dir))
        self.widget.actionExit.triggered.connect(lambda: self._exit(True))

        self.widget.actionSettingsRequests.triggered.connect(lambda: popup_settings_requests(self.widget))

        self.widget.actionHelpAbout.triggered.connect(lambda: popup_about(self.widget))

        self.widget.actionLogoutWhatCD.triggered.connect(self._logout_whatcd)

    def _logout_whatcd(self):
        self.widget.widgetRequests.reset_credentials()

    @staticmethod
    def _exit(exit_application=False):
        cache_dir = appdirs.dirs.user_cache_dir
        shutil.rmtree(cache_dir, ignore_errors=True)
        logging.info('cleanup on aisle: ' + cache_dir)

        if exit_application:
            sys.exit()

def main():
    app = QtGui.QApplication(sys.argv)

    if not Config.option_exists('general', 'disclaimer_accepted'):
        popup_disclaimer()

    mainwindow = MainWindow()
    mainwindow.show()

    sys.exit(app.exec_())

if __name__ == '__main__':

    # Set data dirs
    appdirs.appauthor = ''        # USAGE: https://pypi.python.org/pypi/appdirs/1.2.0
    appdirs.appname = 'DeputyDJ'
    appdirs.dirs = appdirs.AppDirs(appdirs.appname, appdirs.appauthor)

    # Init logging
    if not os.path.exists(appdirs.dirs.user_log_dir): os.makedirs(appdirs.dirs.user_log_dir)
    logfile = appdirs.dirs.user_log_dir + '\\requests-' + time.strftime('%Y-%m-%d') + '.log'
    os.open(logfile, os.O_CREAT)
    logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Init config
    Config.init_config(appdirs.dirs.user_data_dir, 'config.ini')

    logging.info('started DeputyDJ')

    main()