import time, requests, urllib2, shutil, urlparse, os, re, logging, appdirs
import libtorrent as lt
import lastfmapi

from src.external import lastfm_lookup
from src.external.pygazelle import api, encoding
from PyQt4.QtCore import SIGNAL, QThread
from src.utility import resource_path, longest_common_substring


os.environ['REQUESTS_CA_BUNDLE'] = resource_path('cacert.pem')

class ModuleTrackRequests(QThread):

    _DEBUG = False
    _DEBUG_DISABLE_WHATCD = False

    WHATCD_SESSION_PATH = None

    what = None

    torrenthandle = None
    torrent_session = None

    whatcd_username = None
    whatcd_password = None
    whatcd_save_session = False

    target_dir = None
    cache_dir = None

    _wanted_track_artist = None
    _wanted_track_title = None
    _allow_radio_edit = None
    _wanted_track_filename = None
    _wanted_track_title_terms = None
    _wanted_encoding = None

    thread_progress = None  # keeps track of torrent download progress and updates GUI
    thread_coverart = None  # downloads coverart

    _occupied = False    # True if program is busy

    # Signals
    signal_status = SIGNAL('status')
    signal_album = SIGNAL('album')
    signal_artist = SIGNAL('artist')
    signal_track = SIGNAL('track')
    signal_bitrate = SIGNAL('bitrate')
    signal_genre = SIGNAL('genre')
    signal_length = SIGNAL('length')
    signal_filesize = SIGNAL('filesize')
    signal_filename = SIGNAL('filename')
    signal_reset_credentials = SIGNAL('reset_credentials')
    signal_coverart = SIGNAL('cover_art')
    signal_occupied = SIGNAL('occupied')
    signal_progress = SIGNAL('progress')


    def __init__(self):
        QThread.__init__(self)

        self.lastfm = lastfm_lookup.LastFmLookup(apikey='7267a8e796033112b57f12e6f7b3bf74')

        self.WHATCD_SESSION_PATH = appdirs.dirs.user_data_dir + '\\whatcd_session'

        self.target_dir = appdirs.dirs.user_data_dir + '\\Download\\'
        if not os.path.exists(self.target_dir): os.makedirs(self.target_dir)

        logging.info('started requests module')

    def set_parent(self, parent):
        self.parent = parent

    def set_whatcd_credentials(self, username, password, save_session):
        self.whatcd_username = username
        self.whatcd_password = password
        self.whatcd_save_session = save_session

    def set_wanted_track(self, artist, title, allow_radio_edit):
        if self._occupied:
            return False

        self._wanted_track_artist = artist
        self._wanted_track_title = title
        self._allow_radio_edit = allow_radio_edit

        if artist == '' or title == '':
            logging.error('artist or title not specified')
            raise ValueError('Artist and title must be specified')

        self.cache_dir = appdirs.dirs.user_cache_dir + '\\' + self._wanted_track_artist + ' - ' + self._wanted_track_title + '\\'

        if not os.path.exists(self.cache_dir): os.makedirs(self.cache_dir)

        return True

    def run(self):
        try:
            self._set_occupied(True)

            self._reset_interface(clearall=True)

            # Clean up torrent stuff
            self.torrenthandle = None
            self.torrent_session = None
            self.thread_progress = None

            logging.info('')
            logging.info('search commencing: ' + self._wanted_track_artist + ' - ' + self._wanted_track_title)

            self.emit(self.signal_status, 'Searching Last.FM for recording metadata')

            try:
                lastfm_result = self.lastfm.get_album(artist=self._wanted_track_artist, track=self._wanted_track_title, allow_radio_edit=self._allow_radio_edit)
            except lastfmapi.LastFmApiException as e:
                self._raise_exception_ui(e)
                return

            if len(lastfm_result) == 0:
                self._raise_exception_ui('No results on Last.FM: did you make a typo?')
                return

            # Search results
            _artist = lastfm_result['artist']
            _album = lastfm_result['album_title']
            _track = lastfm_result['track_title']
            _image = lastfm_result['image']
            _url = lastfm_result['url']
            _tag = lastfm_result['tags']
            _duration = lastfm_result['duration']

            # Emit signals to update UI and log them
            self.emit(self.signal_album, _album)
            logging.info('Last.FM album result: ' + _album)
            self.emit(self.signal_artist, _artist)
            logging.info('Last.FM artist result: ' + _artist)
            self.emit(self.signal_track, _track)
            logging.info('Last.FM track result: ' + _track)
            self.emit(self.signal_genre, _tag)
            logging.info('Last.FM tag (genre) result: ' + _tag)

            if not _duration == 0:
                minutes, seconds = divmod(_duration / 1000, 60)
                self.emit(self.signal_length, '%s:%02d' % (minutes, seconds))
                logging.info('Last.FM track length result (ms): ' + str(_duration))
            else:
                self.emit(self.signal_length, '?')
                logging.info('Last.FM reports unknown track length')

            # Start cover art thread
            self.thread_coverart = CoverArt(_image, self.cache_dir)
            self.connect(self.thread_coverart, self.thread_coverart.signal_coverart, self.parent.album_cover_art)
            self.thread_coverart.start()

            # Remember the search terms, this is for the whatcd lookup
            self._wanted_track_title_terms = _track.split(' ')

            if self._DEBUG: print('Last.FM album:', _album)

            if self._DEBUG_DISABLE_WHATCD: return

            self.emit(self.signal_status, 'Searching What.CD for matching torrent')
            try:
                try:
                    self._wanted_encoding = encoding.C320
                    torrentlink = self._get_whatcd_torrent(artist=self._wanted_track_artist, searchstr=_album, _encoding=self._wanted_encoding)
                except WhatCDNoResultException as e:
                    if self._DEBUG: print e
                    logging.error(e)
                    # No result found at 320 kbps, try a lower bitrate (V0)
                    try:
                        self._wanted_encoding = encoding.V0
                        torrentlink = self._get_whatcd_torrent(artist=self._wanted_track_artist, searchstr=_album, _encoding=self._wanted_encoding)
                    except WhatCDNoResultException as e:
                        self._raise_exception_ui(e)
                        return
            except api.LoginException as e:
                self._raise_exception_ui(e)
                self.emit(self.signal_reset_credentials)
                return
            except requests.Timeout as e:
                logging.error('WhatCD search timed out: ' + repr(e))
                self._raise_exception_ui('What.CD search timed out, try again')
                return


            torrentdir = appdirs.dirs.user_data_dir + '\\Torrent\\'

            if not os.path.exists(torrentdir):
                os.makedirs(torrentdir)

            torrentpath = self.download(torrentlink, torrentdir)

            self.emit(self.signal_status, 'Downloading torrent')

            try:
                self._download_torrent(torrentpath)
            except (TorrentInProgressException, IncorrectTorrentException) as e:
                self._cancel_torrent()
                self._set_occupied(False)
                self._raise_exception_ui(e)
                return
            except TrackExistsException as e:
                self._cancel_torrent()
                self._set_occupied(False)
                self._raise_exception_ui(e)
                self.emit(self.signal_progress, 1)
                pass
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            if self._DEBUG:
                raise
            logging.error('DJRequests module received exception', exc_info=True)
            self._raise_exception_ui('Unexcepted error. Please send the log file to the developer.')

    def _raise_exception_ui(self, exception):
        if self._DEBUG: print exception
        logging.error(exception)
        self._reset_interface(exception)
        self._set_occupied(False)

    def _set_occupied(self, oc):
        self._occupied = oc
        self.emit(self.signal_occupied, oc)

    def _reset_interface(self, errormessage=None, clearall=False):

        if errormessage is None:
            self.emit(self.signal_status, None)
        else:
            errormessage = str(errormessage)
            self.emit(self.signal_status, errormessage)

        if clearall:
            self.emit(self.signal_album, '')
            self.emit(self.signal_artist, '')
            self.emit(self.signal_track, '')
            self.emit(self.signal_bitrate, '')
            self.emit(self.signal_genre, '')
            self.emit(self.signal_length, '')
            self.emit(self.signal_filesize, '')
            self.emit(self.signal_filename, '')
            self.emit(self.signal_coverart, '')
            self.emit(self.signal_progress, 0)

    def get_download_path(self):
        return self.target_dir

    def download(self, target_url, download_dir):
        def getFileName(url,openUrl):
            if 'Content-Disposition' in openUrl.info():
                # If the response has Content-Disposition, try to get filename from it
                cd = dict(map(
                    lambda x: x.strip().split('=') if '=' in x else (x.strip(),''),
                    openUrl.info()['Content-Disposition'].split(';')))
                if 'filename' in cd:
                    filename = cd['filename'].strip("\"'")
                    if filename: return filename
            # if no filename was found above, parse it out of the final URL.
            return os.path.basename(urlparse.urlsplit(openUrl.url)[2])

        r = urllib2.urlopen(urllib2.Request(target_url, headers=self.what.default_headers))
        try:
            filepath = download_dir + getFileName(target_url, r).decode('utf-8')
            with open(filepath, 'wb') as f:
                shutil.copyfileobj(r,f)

            logging.info('saved .torrent to: ' + filepath)

            return filepath
        finally:
            r.close()


    def _get_whatcd_torrent(self, artist, searchstr, _encoding):
        if self.what is None:
            self.what = api.GazelleAPI(username=self.whatcd_username, password=self.whatcd_password, whatcd_session_path=self.WHATCD_SESSION_PATH)
            self.what.login(self.whatcd_save_session)
            logging.info('logged in to what.cd')
        else:
            logging.info('already logged in to what.cd')

        # Remove some non-alphanumeric characters
        searchstr = re.sub('\W+', ' ', searchstr)

        searchstr = searchstr.replace(' and ', ' ') # remove any possible ambiguous terms
        searchstr = searchstr.replace(' & ', '')
        searchstr = searchstr.replace('  ', ' ') # replace double space with single

        # If search title is in the search string, use search title instead
        # for t in self._wanted_track_title_terms:
        #     if searchstr.lower() in t.lower():
        #         searchstr = self._wanted_track_title

        logging.info('started search on what.cd with artist: ' + artist + ' and searchstr: ' + searchstr)

        whatresults = self.what.search_torrents(searchstr=searchstr, artistname=artist, encoding=_encoding)['results']

        whatresults.sort(key=lambda x: x.seeders, reverse=True) # sort it based on seeders, if two torrents have same amount of terms, the best seeded one is chosen (the first in the list)

        if self._DEBUG: print('What.CD results:', whatresults)

        logging.info('What.CD results: ' + repr(whatresults))

        # Split the title into term s
        album_terms = searchstr.split(' ')

        # Remove all terms that are non-alphanumeric, such as '&'
        for t in album_terms:
            if re.match(r'^\W?$', t, re.UNICODE):
                album_terms.remove(t)

        logging.info('checking what.cd albums with the following terms: ' + repr(album_terms))

        torrent_match = None
        terms_found = 0

        for n in range(0, len(whatresults)):
            track_file = whatresults[n]

            if track_file.seeders == 0:  # Ignore torrents without seeders
                continue

            terms_this_track = 0
            for t in album_terms:
                if t.lower() in track_file.group.name.lower():
                    terms_this_track += 1

            torrent_terms = track_file.group.name.split(' ')
            for t in torrent_terms:     # Remove all terms that are non-alphanumeric, such as '&'
                if re.match(r'^\W?$', t, re.UNICODE):
                    torrent_terms.remove(t)

            if terms_this_track > terms_found:# and len(torrent_terms) <= len(album_terms):
                terms_found = terms_this_track
                torrent_match = track_file

        bitrate = None
        if _encoding == encoding.C320: bitrate = '320kbps'
        if _encoding == encoding.V0: bitrate = 'V0'

        if torrent_match is None:
            msg = 'Nothing found on What.CD at ' + bitrate
            if _encoding == encoding.V0:
                msg += ' or 320'
            raise WhatCDNoResultException(msg)

        self.emit(self.signal_bitrate, bitrate)
        logging.info('found bitrate at ' + bitrate)

        logging.info('found matching torrent: ' + repr(torrent_match))

        return self.what.generate_torrent_link(torrent_match.id)

    def _download_torrent(self, torrentpath):

        logging.info('download to cache dir: ' + self.cache_dir)

        if self.torrenthandle is not None:
            raise TorrentInProgressException('Another torrent is already in progress')

        self.torrent_session = lt.session()
        self.torrent_session.listen_on(6881, 6891)
        self.torrent_session.stop_dht()

        settings = lt.session_settings()
        settings.max_pex_peers = 0
        self.torrent_session.set_settings(settings)

        logging.info('started torrent session')

        e = lt.bdecode(open(torrentpath, 'rb').read())
        torrentinfo = lt.torrent_info(e)

        self.torrenthandle = self.torrent_session.add_torrent({'ti': torrentinfo, 'save_path': self.cache_dir, 'storage_mode': lt.storage_mode_t.storage_mode_sparse})

        # Split the title into term s
        track_terms = self._wanted_track_title_terms

        # Remove all terms that are non-alphanumeric, such as '&'
        for t in track_terms:
            if re.match(r'^\W?$', t, re.UNICODE):
                track_terms.remove(t)

        logging.info('created track search terms: ' + repr(track_terms))

        # Count amount of terms found, the track with most common terms is the one we, hopefully, want
        terms_found = 0
        track_found = None
        track_index = None

        # Find the file we want
        filelist = torrentinfo.files()
        filtered_filelist = []   # List of files, without common terms (sometimes the artist name is in the filename)

        for n in range(0, len(filelist)):   # Filter the names
            torrent_content =  filelist[n].path.split('\\')
            track_name = torrent_content[-1].lower()    # take last part of the path, remove folders
            split_extension = track_name.split('.')
            extension = split_extension[-1].lower()

            track_name = track_name.replace('.' + extension, '')    # remove extension from trackname

            track_name = re.sub(r'([^\s\w]|_)+', '', track_name)    # remove non-alphanumeric (except space), since this also happens to the search string

            filtered_filelist.append({'track': track_name, 'extension': extension})

        common_substring = longest_common_substring(filtered_filelist[0]['track'], filtered_filelist[1]['track']) # Find common string in the first 2

        for n in range(0, len(filtered_filelist)):
            if filtered_filelist[n]['extension'] == 'mp3':
                new_substring = longest_common_substring(common_substring, filtered_filelist[n]['track'])
                # print new_substring
                if len(new_substring) < len(common_substring):
                    common_substring = new_substring

        logging.info('removing common substring in torrent filenames: ' + common_substring)

        # Now check if the common substring is also in the rest, if so, remove the substring from all filenames
        common_substring_in_all_filenames = True

        for n in range(0, len(filtered_filelist)):
            if filtered_filelist[n]['extension'] == 'mp3' and common_substring not in filtered_filelist[n]['track']:
                common_substring_in_all_filenames = False
                break # No need to continue

        if common_substring_in_all_filenames:
            for n in range(0, len(filtered_filelist)):
                filtered_filelist[n]['track'] = filtered_filelist[n]['track'].replace(common_substring, ' ')

        if self._DEBUG: print filtered_filelist

        for n in range(0, len(filtered_filelist)):
            track_name = filtered_filelist[n]['track']
            extension = filtered_filelist[n]['extension']

            if extension == 'mp3':  # Only allows mp3 files

                if not self._allow_radio_edit:
                    if 'radio' in track_name:    # Ignore radio edits
                        continue

                unwanted_term = False
                for t in track_terms:   # Check if special terms (such as 'remix') are in the search, if not, the special terms are unwanted
                    if 'mix' in t.lower():  # Checking for mix because this would catch 'remix' too
                        unwanted_term = True
                if not unwanted_term:
                    if 'mix' in track_name:
                        continue

                terms_this_track = 0
                for t in track_terms:
                    if t.lower() in track_name:
                        terms_this_track += 1

                if terms_this_track > terms_found:
                    terms_found = terms_this_track
                    track_found = track_name
                    track_index = n

        if track_index is None:
            raise IncorrectTorrentException('Track not found in torrent')

        filesize_mb = float(filelist[track_index].size) / 1024 / 1024
        filesize_string = '%.1f' % filesize_mb + 'MB'
        if self._wanted_encoding == encoding.C320:
            estimated_duration = ((filelist[track_index].size / 1024) * 8) / 320
            minutes, seconds = divmod(estimated_duration, 60)
            filesize_string += ' (~%s:%02d)' % (minutes, seconds)

        self.emit(self.signal_filesize, filesize_string )
        logging.info('track in torrent file is size (MB): ' + filesize_string)

        logging.info('closest match in album: ' + track_found + ' at torrent index: ' + str(track_index))

        self._wanted_track_filename = filelist[track_index].path
        self.emit(self.signal_filename, self._wanted_track_filename.split('\\')[-1])    # track name without path

        self._check_track_exists()

        # Set wanted file to normal priority
        num_files_skipped = [0] * torrentinfo.num_files()
        num_files_skipped[track_index] = 1
        self.torrenthandle.prioritize_files(num_files_skipped)

        # start thread that displays torrent info
        self.thread_progress = TorrentProgressThread(self.torrenthandle)
        self.parent.connect_progress_bar()
        self.connect(self.thread_progress, self.thread_progress.signal_complete, self._torrent_complete)
        self.thread_progress.start()



    def _torrent_complete(self):
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)
            logging.info('download dir did not exist, created it')

        assert self.cache_dir is not None

        # move wanted track to target dir
        fullpath = self.cache_dir + self._wanted_track_filename     # file in cache

        try:
            shutil.move(fullpath, self.target_dir)
            logging.info('moved track file to download dir')
        except shutil.Error as e:
            if self._DEBUG: print e
            logging.info(e)

        self._delete_cache()

        self.emit(self.signal_status, None)

        self._set_occupied(False)

    def _delete_cache(self):
        # delete temp cache folder
        if self.cache_dir is not None:
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            logging.info('deleted torrent cache dir')

    def _check_track_exists(self):
        assert self.target_dir is not None
        assert self._wanted_track_filename is not None

        if os.path.exists(self.target_dir + '\\' + self._wanted_track_filename.split('\\')[1]):
            raise TrackExistsException('Track already downloaded')

    def cancel_request(self):
        self._reset_interface(clearall=True)

        self._cancel_torrent()

        self._set_occupied(False)

    def _cancel_torrent(self):
        if self.torrent_session is None:
            return

        torrent = self.torrent_session.get_torrents()

        assert len(torrent) == 1

        self.torrent_session.remove_torrent(torrent[0])

        if self.thread_progress is not None:
            self.thread_progress.cancelled = True
            self.thread_progress.wait() # wait infinitely until thread is done, so we can safely delete cache files

        self._delete_cache()

class TorrentProgressThread(QThread):
    cancelled = False

    signal_progress = SIGNAL('progress_update')
    signal_complete = SIGNAL('download_complete')

    def __init__(self, torrenthandle):
        QThread.__init__(self)
        self.torrenthandle = torrenthandle

    def run(self):
        s = self.torrenthandle.status()

        state_str = ['queued', 'checking', 'downloading metadata',
                     'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']

        while s.progress != 1 and not self.cancelled:    # while not finished

            # if DJRequests.DEBUG:
                # print '%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % \
                #     (s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000, \
                #     s.num_peers, state_str[s.state])

            self.emit(self.signal_progress, s.progress)

            time.sleep(0.1)

            s = self.torrenthandle.status()


        if self.cancelled:    # thread cancelled
            logging.info('torrent info thread terminated')
            self.emit(self.signal_progress, 0)
        else:
            logging.info('torrent download complete')
            self.emit(self.signal_progress, 1)
            self.emit(self.signal_complete)

class CoverArt(QThread):
        signal_coverart = SIGNAL('cover_art')
        def __init__(self, _url, _cache_dir):
            QThread.__init__(self)

            self.cache_dir = _cache_dir
            self.url = _url

        def fallback_cover_art(self):
            self.emit(self.signal_coverart, resource_path('res/CoverNotAvailable.jpg'))

        def run(self):
            if not self.url.startswith('http://'):
                self.url = 'http://' + self.url # urllib would like links to start with http://

            logging.info('got album art from: ' + self.url)

            split = self.url.split('.')
            extension = split[-1]

            import urllib
            save_path = self.cache_dir + 'cover.' + extension
            try:
                urllib.urlretrieve(self.url, save_path)    # The actual file download
            except (urllib2.HTTPError, IOError) as e:
                logging.error(e)
                return

            logging.info('saved album art to: ' + save_path)

            self.emit(self.signal_coverart, save_path)


class RequestException(Exception):

    def __init__(self, message=None, errors=None):

        Exception.__init__(self, message)
        self.errors = errors

class TrackExistsException(RequestException):
    pass

class IncorrectTorrentException(RequestException):
    pass

class TorrentInProgressException(RequestException):
    pass

class WhatCDNoResultException(RequestException):
    pass

class LastFMNoResultException(RequestException):
    pass