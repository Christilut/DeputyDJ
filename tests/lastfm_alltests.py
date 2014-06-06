import unittest
from src.external.lastfm_lookup import LastFmLookup
from tests import search_tests, lastfm_apikey

class LastFMTest(unittest.TestCase):

    lookup = LastFmLookup(apikey=lastfm_apikey)

    def test_all_searches(self):

        for search in search_tests:
            allow_radio_edit = False
            if 'radio_edit' in search:
                allow_radio_edit = search['radio_edit']
            result = self.lookup.get_album(artist=search['artist'], track=search['track'], allow_radio_edit=allow_radio_edit)
            print result
            if 'album_title' in result:
                self.assertEqual(result['album_title'].lower(), search['result'].lower())
            else:
                print 'No results for ' + search['artist'] + ' - ' + search['track']