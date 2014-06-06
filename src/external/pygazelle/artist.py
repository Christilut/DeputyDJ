from HTMLParser import HTMLParser

class InvalidArtistException(Exception):
    pass

class Artist(object):
    """
    This class represents an Artist. It is created knowing only its ID. To reduce API accesses, load information using
    Artist.update_data() only as needed.
    """
    def __init__(self, id, parent_api):
        self.id = id
        self.parent_api = parent_api
        self.name = None
        self.notifications_enabled = None
        self.has_bookmarked = None
        self.image = None
        self.body = None
        self.vanity_house = None
        self.tags = []
        self.similar_artists_and_score = {}
        self.statistics = None
        self.torrent_groups = []
        self.requests = []
        self.fully_loaded = False

        self.parent_api.cached_artists[self.id] = self # add self to cache of known Artist objects

    def update_data(self):
        if self.id > 0:
            try:
                response = self.parent_api.request(action='artist', id=self.id)
            except Exception as e:
                raise InvalidArtistException(str(e))
        elif self.name:
            self.name = HTMLParser().unescape(self.name)
            try:
                response = self.parent_api.request(action='artist', artistname=self.name)
            except Exception:
                self.name = self.name.split(" & ")[0]
                response = self.parent_api.request(action='artist', artistname=self.name)
        else:
            raise InvalidArtistException("Neither ID or Artist Name is valid, can't update data.")
        self.set_data(response)
        self.fully_loaded = True

    def set_data(self, artist_json_response):
        if self.id > 0 and self.id != artist_json_response['id']:
            raise InvalidArtistException("Tried to update an artists's information from an 'artist' API call with a different id." +
                               " Should be %s, got %s" % (self.id, artist_json_response['id']) )
        elif self.name:
            self.id = artist_json_response['id']
            self.parent_api.cached_artists[self.id] = self

        self.name = HTMLParser().unescape(artist_json_response['name'])
        self.notifications_enabled = artist_json_response['notificationsEnabled']
        self.has_bookmarked = artist_json_response['hasBookmarked']
        self.image = artist_json_response['image']
        self.body = artist_json_response['body']
        self.vanity_house = artist_json_response['vanityHouse']

        self.tags = []
        for tag_dict in artist_json_response['tags']:
            tag = self.parent_api.get_tag(tag_dict['name'])
            tag.set_artist_count(self, tag_dict['count'])
            self.tags.append(tag)

        self.similar_artists_and_score = {}
        for similar_artist_dict in artist_json_response['similarArtists']:
            similar_artist = self.parent_api.get_artist(similar_artist_dict['artistId'], name=similar_artist_dict['name'])
            self.similar_artists_and_score[similar_artist] = similar_artist_dict['score']

        self.statistics = artist_json_response['statistics']

        self.torrent_groups = []
        for torrent_group_item in artist_json_response['torrentgroup']:
            torrent_group = self.parent_api.get_torrent_group(torrent_group_item['groupId'])
            torrent_group.set_artist_group_data(torrent_group_item)
            self.torrent_groups.append(torrent_group)

        self.requests = []
        for request_json_item in artist_json_response['requests']:
            request = self.parent_api.get_request(request_json_item['requestId'])
            request.set_data(request_json_item)
            self.requests.append(request)

    def __repr__(self):
        return "Artist: %s - ID: %s" % (self.name, self.id)

    def __dict__(self):
        wanted_attributes = ['id', 'name', 'notifications_enabled', 'has_bookmarked', 'image', 'body', 'vanity_house',
                             'statistics']

        output_dict = dict([(key, self.__getattribute__(key)) for key in wanted_attributes])

        output_dict['tags'] = [tag.__dict__() for tag in self.tags]

        output_dict['similar_artists'] = [{'id': artist.id, 'name': artist.name, 'score': score}
                                          for artist, score in self.similar_artists_and_score.iteritems()]

        output_dict['torrent_groups'] = [{'id': torrent_group.id, 'name': torrent_group.name,
                                          'torrents': [{'id': torrent.id, 'format': torrent.format, 'encoding': torrent.encoding}
                                                       for torrent in torrent_group.torrents]}
                                         for torrent_group in self.torrent_groups]

        output_dict['requests'] = [request.__dict__() for request in self.requests]

        return output_dict
