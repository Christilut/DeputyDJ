import pyaudio, wave, subprocess, json, ast, uuid, requests, time, os, appdirs, itertools
from collections import Counter
from PyQt4.QtCore import QThread
from PyQt4.Qt import SIGNAL


class ModuleTrackHistory(QThread):

    DEBUG = True

    FINGERPRINT_INTERVAL_SECONDS = 5

    ECHOPRINT_MINIMUM_SCORE = 20
    ECHOPRINT_SKIP_SCORE = 50      # With this score, or higher, the filtering is skipped and this track is assumed to be correct

    LIKELY_TRACK_MIN_OCCURENCE = 3  # This many occurences of the same result are required before considering it as the likely track
    TRACKS_SEPERATION_AMOUNT = 10   # This many tracks need to be found that are not the likely track, before concluding a new song is playing. THis takes a minimum of this*FINGERPRINT_INTERVAL_SECONDS

    most_likely_track = None
    most_likely_track_last_index = None
    num_different_tracks = 0

    previous_result = None

    running = False
    num_fingerprints_running = 0
    fingerprint_threads = []

    results = []

    signal_positive_result = SIGNAL('positive_result')

    def __init__(self):
        QThread.__init__(self)
        pass

    def run(self):
        self.running = True

        print 'Started audio fingerprinting'

        self.startFingerprintThread()

        lastFingerprintTimestamp = time.time()
        while self.running:
            if time.time() >= lastFingerprintTimestamp + self.FINGERPRINT_INTERVAL_SECONDS:   # x seconds have passed
                lastFingerprintTimestamp = time.time()
                self.startFingerprintThread()

    def testAdd(self):

        artist = str(uuid.uuid4().hex)
        title = str(uuid.uuid4().hex)

        self.emit(self.signal_positive_result, artist, title)


    def shutdown(self):
        self.running = False

        for n in self.fingerprint_threads:
            n.shutdown()

        if self.DEBUG: print 'waiting for audio fingerprint threads to finish'
        while len(self.fingerprint_threads) != 0:
            for n in self.fingerprint_threads:
                if not n.isRunning():
                    self.fingerprint_threads.remove(n)

    def startFingerprintThread(self):
        new_fingerprinter = AudioFingerprinter()
        self.fingerprint_threads.append(new_fingerprinter)

        self.connect(new_fingerprinter, new_fingerprinter.signal_echoprint_result, self.echoprint_result)

        new_fingerprinter.start()

        self.num_fingerprints_running += 1
        # self.testAdd()

    def process_positive_result(self, track_info):
        # Don't add the same result to the list twice
        if track_info != self.previous_result:
            self.previous_result = track_info
            self.emit(self.signal_positive_result, track_info['artist'], track_info['title'])

    def echoprint_result(self, result):
        # print result

        response = result['response']

        if response['status']['message'] != 'Success':
            print 'Invalid result found: ' + repr(result)

        if len(response['songs']) > 1:
            print 'Found multiple songs in result, unhandled.'
            return
        elif len(response['songs']) == 0:
            # This happens alot, dont print it
            if self.DEBUG: print 'Echoprint returned no songs'
            self.filter_results(artist=None, title=None)
            return

        # print response              # TODO {'status': {'code': 0, 'message': 'Success', 'version': '4.2'}, 'songs': [{'tag': 0, 'error': 'need codes in query for fingerprint matching'}]}
        artist = response['songs'][0]['artist_name']
        title = response['songs'][0]['title']
        score = response['songs'][0]['score']

        if score < self.ECHOPRINT_MINIMUM_SCORE:
            if self.DEBUG: print 'Below minimum score: ' + artist + ' - ' + title + ', score: ' + repr(score)
            return

        if self.DEBUG: print 'Song recognized as: ' + artist + ' - ' + title + ', score: ' + repr(score)

        if score >= self.ECHOPRINT_SKIP_SCORE:  # Don't filter if score is above threshold
            if self.DEBUG: print 'Song skipped filtering due to score'
            self.process_positive_result( {'artist': artist, 'title': title})
        else:
            self.filter_results(artist, title)


    def filter_results(self, artist, title):
        def most_common(lst):
            data = Counter(lst)
            return data.most_common(1)

        if artist is not None and title is not None:
            self.results.append( (artist, title) )

        most_common_track = most_common(self.results)

        if len(self.results) > 0:
            if most_common_track[0][1] >= self.LIKELY_TRACK_MIN_OCCURENCE and self.most_likely_track is None:
                self.most_likely_track = {'artist': most_common_track[0][0][0], 'title': most_common_track[0][0][1]}
                self.most_likely_track_last_index = len(self.results) - 1

            if self.most_likely_track != {'artist': artist, 'title': title}:
                self.num_different_tracks += 1
            else:
                self.num_different_tracks = 0
                self.most_likely_track_last_index = len(self.results) - 1

            if self.most_likely_track is not None and self.num_different_tracks == self.TRACKS_SEPERATION_AMOUNT:  # if 10 tracks occured that are not the likely track
                self.results = self.results[self.most_likely_track_last_index + 1:] # remove everything up to and including the last index of the likely track
                # print self.results
                # now we can conclude the likely track that was playing
                print 'Previous track was: ' + str(self.most_likely_track)

                # Send to UI
                self.process_positive_result(self.most_likely_track)

                # reset values
                self.most_likely_track = None
                self.most_likely_track_last_index = None
                self.num_different_tracks = 0

class AudioFingerprinter(QThread):
    running = False

    FINGERPRINT_CACHE_DIR = None
    ECHOPRINT_APIKEY = 'QQGNBGUJJOZLUJY0N'

    AUDIOHASH_LENGTH = 15
    AUDIOHASH_OFFSET = 10   # in seconds
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    _pyaudio = None

    RECORD_SECONDS = 25

    FINGERPRINT_PHASE = 'idle'

    signal_echoprint_result = SIGNAL('echoprint_result')

    def __init__(self):
        QThread.__init__(self)

        self.FINGERPRINT_CACHE_DIR = appdirs.dirs.user_cache_dir + '\\fingerprints'

        if not os.path.exists(self.FINGERPRINT_CACHE_DIR):
            os.makedirs(self.FINGERPRINT_CACHE_DIR)

    def run(self):

        self.running = True

        filepath = self.FINGERPRINT_CACHE_DIR + '\\' + str(uuid.uuid4().hex)

        self.FINGERPRINT_PHASE = 'recording'

        try:
            self.record(filepath)
        except:
            raise

        self.FINGERPRINT_PHASE = 'codegen'

        try:
            command = 'echoprint\\codegen.exe ' + filepath + ' ' + str(self.AUDIOHASH_LENGTH) + ' ' + str(self.AUDIOHASH_OFFSET)
            raw = subprocess.check_output(command, cwd='echoprint')
            raw = raw[1:-3] # Remove leading and trailing [ ]
            audio_info = ast.literal_eval(raw)    # Parse string to dict
        except:
            raise

        self.FINGERPRINT_PHASE = 'echoprint'

        if 'error' in audio_info:
            print 'FFMPEG error: ' + audio_info['error']
        else:
            try:
                result = ast.literal_eval(self.echoprint(audio_info).content)
                self.emit(self.signal_echoprint_result, result)
            except:
                raise

        self.FINGERPRINT_PHASE = 'cleanup'

        try:
            self.cleanup(filepath)
        except:
            raise

    def shutdown(self): # TODO
        if self.FINGERPRINT_PHASE == 'recording':
            pass
        elif self.FINGERPRINT_PHASE == 'codegen':
            pass
        elif self.FINGERPRINT_PHASE == 'echoprint':
            pass
        elif self.FINGERPRINT_PHASE == 'cleanup':
            pass


    def record(self, filepath):
        self._pyaudio = pyaudio.PyAudio()

        self.open_stream()

        # print("* recording to " + WAVE_OUTPUT_FILENAME)

        frames = []
        for i in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
            data = self.stream.read(self.CHUNK)
            frames.append(data)

        # print("* done recording to " + WAVE_OUTPUT_FILENAME)

        self.stop_stream()

        wf = wave.open(filepath, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self._pyaudio.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def open_stream(self):
        self.stream = self._pyaudio.open(format=self.FORMAT,
                        channels=self.CHANNELS,
                        rate=self.RATE,
                        input=True,
                        frames_per_buffer=self.CHUNK)

    def stop_stream(self):
        self.stream.stop_stream()
        self.stream.close()
        self._pyaudio.terminate()



    def echoprint(self, audio_info):
        r = requests.post(
            'http://developer.echonest.com/api/v4/song/identify',
            data={'query': json.dumps(audio_info), 'api_key': self.ECHOPRINT_APIKEY, 'version': audio_info['metadata']['version']},
            headers={'content-type': 'application/x-www-form-urlencoded'}
        )
        return r

    def cleanup(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)
