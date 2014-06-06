import logging, os

from PyQt4 import uic
from PyQt4.QtGui import QWidget, QPixmap

from popup.popup_whatcd_login import popup_whatcd_login
from src.modules.module_track_requests import ModuleTrackRequests
from src.utility import resource_path, open_folder
from src.utility.config import Config


class UITrackRequests(QWidget):

    track_requests = None # Request module

    _DEBUG_SEARCH = False

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.widget = uic.loadUi(resource_path('interface/tab_requests.ui'), self)

        self.track_requests = ModuleTrackRequests()
        self.track_requests.set_parent(self)

        # Get previously saved values
        if Config.option_exists('requests', 'allow_radio_edit'):
            self.widget.checkAllowRadioEdit.setChecked(Config.getboolean('requests', 'allow_radio_edit'))
        if self._DEBUG_SEARCH:
            if Config.option_exists('requests', 'debug_last_search_artist'):
                self.widget.textArtist.setText(Config.getstring('requests', 'debug_last_search_artist'))
            if Config.option_exists('requests', 'debug_last_search_title'):
                self.widget.textTitle.setText(Config.getstring('requests', 'debug_last_search_title'))

        # Connect signals
        self.widget.buttonSearch.clicked.connect(self._search)
        self.widget.buttonCancel.clicked.connect(self.track_requests.cancel_request)

        self.widget.buttonOpenFolder.clicked.connect(lambda: open_folder(self.track_requests.get_download_path()))

        self.connect(self.track_requests, self.track_requests.signal_album, self.widget.labelAlbum.setText)
        self.connect(self.track_requests, self.track_requests.signal_status, self.set_status)
        self.connect(self.track_requests, self.track_requests.signal_track, self.widget.labelTrack.setText)
        self.connect(self.track_requests, self.track_requests.signal_artist, self.widget.labelArtist.setText)
        self.connect(self.track_requests, self.track_requests.signal_bitrate, self.widget.labelBitrate.setText)
        self.connect(self.track_requests, self.track_requests.signal_genre, self.widget.labelGenre.setText)
        self.connect(self.track_requests, self.track_requests.signal_length, self.widget.labelLength.setText)
        self.connect(self.track_requests, self.track_requests.signal_filesize, self.widget.labelFilesize.setText)
        self.connect(self.track_requests, self.track_requests.signal_filename, self.widget.labelFilename.setText)
        self.connect(self.track_requests, self.track_requests.signal_progress, self.update_progress_bar)
        self.connect(self.track_requests, self.track_requests.signal_reset_credentials, self.widget.reset_credentials)
        self.connect(self.track_requests, self.track_requests.signal_coverart, self.widget.album_cover_art)
        self.connect(self.track_requests, self.track_requests.signal_occupied, self._buttons_occupied)

        self.widget.checkAllowRadioEdit.stateChanged.connect(self._check_allowradioedit)

        self.widget.textTitle.returnPressed.connect(self._search)
        self.widget.textArtist.returnPressed.connect(self._search)

    def reset_credentials(self):
        Config.set_requests_option('whatcd_session_saved', False)
        if os.path.isfile(self.track_requests.WHATCD_SESSION_PATH):
            os.remove(self.track_requests.WHATCD_SESSION_PATH)

    # Needs to be called later, not during init
    def connect_progress_bar(self):
        self.connect(self.track_requests.thread_progress, self.track_requests.thread_progress.signal_progress, self.update_progress_bar)

    def _buttons_occupied(self, occupied):
        self.widget.buttonSearch.setEnabled(not occupied)
        self.widget.buttonCancel.setEnabled(occupied)

    def _check_allowradioedit(self):
        Config.set_requests_option('allow_radio_edit', self.widget.checkAllowRadioEdit.isChecked())

    def _search(self):

        artist = str(self.widget.textArtist.text())
        track = str(self.widget.textTitle.text())

        if artist == '' or track == '':
            self.set_status('Please enter an artist and track')
            return

        if not Config.option_exists('requests', 'whatcd_session_saved') or not Config.getboolean('requests', 'whatcd_session_saved'):
            result, whatcdpassword, save_session = popup_whatcd_login(self.widget)  # open popup

            if result == 0: # cancelled
                logging.info('user cancelled whatcd login popup')
                return

            Config.set_requests_option('whatcd_session_saved', save_session)
            logging.info('saving whatcd session? ' + repr(save_session))

            username = Config.getstring('requests', 'whatcd_username')
            self.track_requests.set_whatcd_credentials(username, whatcdpassword, save_session)
            logging.info('user accepted whatcd login popup')


        if self._DEBUG_SEARCH:
            Config.set_requests_option('debug_last_search_artist', artist)
            Config.set_requests_option('debug_last_search_title', track)

        allowed = self.track_requests.set_wanted_track(artist, track, self.widget.checkAllowRadioEdit.isChecked())

        if allowed:
            self.track_requests.start()

    def update_progress_bar(self, progress):
        self.widget.progressDownload.setValue(progress * 100)

    def album_cover_art(self, filepath):
        if not filepath == '':
            pic = QPixmap(filepath, '1')  # no clue what the 1 means but without it, png files wont load
            pic = pic.scaledToHeight(self.widget.labelCoverArt.frameRect().height())
        else:
            pic = QPixmap()

        self.widget.labelCoverArt.setPixmap(pic)

    def set_status(self, status):
        if status is None:
            status = 'Idle'

        self.widget.labelStatus.setText(status)

