import lastfmapi
from pprint import pprint
import re, logging

class LastFmLookup():

    __TOPALBUM_LIMIT = 50   # Should be enough to contain the releases of most artists

    # Make sure all keywords are in lowercase
    __UNWANTED_ALBUM_KEYWORDS = ['live']
    __UNWANTED_TAG_KEYWORDS = ['albums i own', 'seen live', 'female vocalists', 'alternative', 'american', 'awesome', 'cool', 'favorite', 'favorites', 'favourites', 'favorite albums', 'female', 'female vocalist', 'guitar',
                               'heard on pandora', 'love', 'male vocalists', 'piano', 'romantic', 'sad', 'sexy', 'shoegave']  # Remove all subjective and irrelevant tags
    __UNWANTED_TRACK_KEYWORDS = ['mix', 'remix', 'instrumental']


    def __init__(self, apikey):
        self.api = lastfmapi.LastFmApi(apikey)

    def get_album(self, artist, track, allow_radio_edit):
        """
        1. Get top albums, search for track until found  - ignore keywords such as Live
        If not found, search for track with track_getInfo because it might be in a compilation such as Monstercat

        When result found: use it to get some metadata, such as genre
        """

        if type(allow_radio_edit) != type(True):
            raise ValueError('Invalid parameter for allow_radio_edit, must be bool')

        if allow_radio_edit:
            if 'radio' in self.__UNWANTED_TRACK_KEYWORDS:
                self.__UNWANTED_TRACK_KEYWORDS.remove('radio')
        else:
            if 'radio' not in self.__UNWANTED_TRACK_KEYWORDS:
                self.__UNWANTED_TRACK_KEYWORDS.append('radio')

        # Convert to UTF-8 just to be sure
        artist = artist.encode('utf-8')
        track = track.encode('utf-8')
        track_terms = LastFmLookup._create_terms(track)

        logging.info('Started Last.FM search for ' + artist + ' - ' + track + ' with terms: ' + repr(track_terms))

        found_album = {}

        topalbum_result = self.api.artist_getTopAlbums(artist=artist, limit=self.__TOPALBUM_LIMIT)
        # pprint(topalbum_result)

        albums = []
        if 'album' in topalbum_result['topalbums']:
            for a in topalbum_result['topalbums']['album']:
                album_name = a['name']

                if self._contains_album_keywords(album_name):
                    continue

                albums.append(album_name)

            for i in range(0, len(albums)):
                album_info = self.api.album_getInfo(artist=artist, album=albums[i].encode('utf-8'))
                # pprint(album_info)
                # print 'Checking album: ' +  album_info['album']['name']
                correct_track_name, track_duration = self._album_contains_track(album_info, track_terms)
                if correct_track_name is not None:
                    found_album['artist'] = album_info['album']['artist'].encode('utf-8')
                    found_album['album_title'] = album_info['album']['name'].encode('utf-8')
                    found_album['image'] = self._find_best_image(album_info['album']['image'])
                    found_album['tags'] = self._find_best_tags(album_info['album']['toptags'])
                    found_album['url'] = album_info['album']['url'].encode('utf-8')
                    found_album['track_title'] = correct_track_name
                    if track_duration != '':
                        found_album['duration'] = int(track_duration) * 1000 # Album track results are in seconds
                    else:
                        found_album['duration'] = 0
                    break
        else:
            logging.info('Last.FM artist has no albums')

        if len(found_album) != 0:
            return found_album
        # Found album is None, so the track was not found in the top albums. Do a check by searching for artist title.

        logging.info('Falling back to single track search')

        track_info = self.api.track_getInfo(artist=artist, track=track)

        # pprint(track_info)

        if 'album' in track_info['track']:
            found_album['artist'] = track_info['track']['album']['artist'].encode('utf-8')
            found_album['album_title'] = track_info['track']['album']['title'].encode('utf-8')
            found_album['image'] = self._find_best_image(track_info['track']['album']['image'])
            found_album['tags'] = self._find_best_tags(track_info['track']['toptags'])
            found_album['url'] = track_info['track']['album']['url'].encode('utf-8')
            found_album['track_title'] = track_info['track']['name'].encode('utf-8')
            if track_info['track']['duration'] != '':
                found_album['duration'] = int(track_info['track']['duration'])   # These results are in milliseconds
            else:
                found_album['duration'] = 0
        else:
            logging.info('Fallback resulted in no albums')

        return found_album

    @staticmethod
    def _create_terms(input):
        terms = [x.lower() for x  in input.split(' ')]
        # Remove all terms that are non-alphanumeric, such as '&'
        for t in terms:
            if re.match(r'^\W?$', t, re.UNICODE):
                terms.remove(t)

        for i in range(0, len(terms)):
            terms[i] = re.sub(r'\W+', '', terms[i])
        return terms


    def _find_best_tags(self, tag_list):                                    # TODO filter all yearnumbers eg 2012
        if type(tag_list) != type(dict()):
            return 'unknown'

        cleaned_tag_list = []
        for n in tag_list['tag']:
            cleaned_tag_list.append(n['name'])

        return list(set(cleaned_tag_list).difference(set(self.__UNWANTED_TAG_KEYWORDS)))[0]    # Cross reference lists and take the top result


    def _find_best_image(self, image_list):
        def _find_proper_size(_image_list, size):
            for n in _image_list:
                if n['size'] == size:
                    return n['#text']
            return None

        result = _find_proper_size(image_list, 'extralarge')

        if result is None:
            result = _find_proper_size(image_list, 'large')

        return result

    def _album_contains_track(self, album_info, wanted_track_terms):
        def _check_terms(_track_terms, _wanted_track_terms):

            # print _track_terms, _wanted_track_terms
            overlap_terms = set(_track_terms).intersection(_wanted_track_terms)
            # print repr(_track_terms) + ', ' + repr(_wanted_track_terms) + ', overlap: ' + repr(overlap_terms)
            if len(overlap_terms) == len(_wanted_track_terms):
                # print overlap_terms
                # print repr(set(self.__UNWANTED_TRACK_KEYWORDS).intersection(_track_terms)) + ', ' + repr(set(self.__UNWANTED_TRACK_KEYWORDS).intersection(_wanted_track_terms))

                if set(self.__UNWANTED_TRACK_KEYWORDS).intersection(_track_terms) == set(self.__UNWANTED_TRACK_KEYWORDS).intersection(_wanted_track_terms):
                    return True
                else:
                    return False


        tracks = album_info['album']['tracks']['track']
        if type(tracks) == type(list()):
            for t in tracks:
                track_terms = LastFmLookup._create_terms(t['name'])
                if _check_terms(track_terms, wanted_track_terms):
                    return t['name'].encode('utf-8'), t['duration']
        elif type(tracks) == type(dict()):
            track_terms = LastFmLookup._create_terms(tracks['name'])
            if _check_terms(track_terms, wanted_track_terms):
                return tracks['name'].encode('utf-8'), tracks['duration']
        else:
            print 'Other type found: ' + str(type(tracks))

        return None, None

    def _contains_album_keywords(self, album):
        found_keyword = False
        for keyword in self.__UNWANTED_ALBUM_KEYWORDS:
            if keyword.lower() in album.lower():
                found_keyword = True
        return found_keyword


