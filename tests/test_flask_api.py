# This file is a part of Fedora Tagger
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301  USA
#
# Refer to the README.rst and LICENSE files for full details of the license
# -*- coding: utf-8 -*-

'''
taggerapi tests lib.
'''

__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import base64
import json
import unittest
import os
import sys
from werkzeug import wrappers

from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import taggerapi
import taggerapi.taggerlib
from taggerapi.taggerlib import model
from tests import Modeltests, FakeUser, create_package, create_tag, \
                  create_vote, create_rating, create_user


# pylint: disable=E1103
class Flasktests(Modeltests):
    """ Flask application tests. """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(Flasktests, self).setUp()

        taggerapi.APP.config['TESTING'] = True
        taggerapi.SESSION = self.session
        taggerapi.api.SESSION = self.session
        self.app = taggerapi.APP.test_client()
        wrappers.BaseRequest.remote_addr = '1.2.3'
        user = FakeUser()
        self.infos = None

    def request_with_auth(self, url, method, data):
        """ Make request to the specified url with the specified http
        method with the Authorization header.
        """
        auth = base64.b64encode(self.infos['name'] + ':' + self.infos['token'])
        return self.app.open(url,
                             method=method,
                             headers={'Authorization': 'Basic ' + auth},
                             data=data
                             )

    def test_pkg_get(self):
        """ Test the pkg_get function.  """

        output = self.app.get('/api/guake')
        self.assertEqual(output.status_code, 301)

        output = self.app.get('/api/guake/')
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Package "guake" not found')

        create_package(self.session)

        output = self.app.get('/api/guake/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['name'], 'guake')
        self.assertEqual(output['summary'], 'drop-down terminal for gnome')
        self.assertEqual(output['icon'],'https://apps.fedoraproject.org/'
                         'packages/images/icons/package_128x128.png')
        self.assertEqual(output['rating'], -1)
        self.assertEqual(output['tags'], [])

    def test_pkg_get_tag(self):
        """ Test the pkg_get_tag function.  """

        output = self.app.get('/api/guake/tag')
        self.assertEqual(output.status_code, 301)

        output = self.app.get('/api/guake/tag/')
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Package "guake" not found')

        create_package(self.session)

        output = self.app.get('/api/guake/tag/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['name'], 'guake')
        self.assertEqual(output['tags'], [])

        create_tag(self.session)

        output = self.app.get('/api/guake/tag/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['name'], 'guake')
        self.assertEqual(output['tags'][0]['tag'], 'gnome')
        self.assertEqual(output['tags'][0]['votes'], 2)
        self.assertEqual(output['tags'][0]['like'], 2)
        self.assertEqual(output['tags'][0]['dislike'], 0)
        self.assertEqual(output['tags'][1]['tag'], 'terminal')
        self.assertEqual(output['tags'][0]['votes'], 2)
        self.assertEqual(output['tags'][0]['like'], 2)
        self.assertEqual(output['tags'][0]['dislike'], 0)

    def test_tag_get(self):
        """ Test the tag_get function.  """

        output = self.app.get('/api/tag/gnome')
        self.assertEqual(output.status_code, 301)

        output = self.app.get('/api/tag/gnome/')
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Tag "gnome" not found')

        create_package(self.session)
        create_tag(self.session)

        output = self.app.get('/api/tag/gnome/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['tag'], 'gnome')
        self.assertEqual(len(output['packages']), 2)
        self.assertEqual(output['packages'][0]['package'], 'guake')

    def test_tag_put(self):
        """ Test the tag_pkg_put function.  """

        data = {'pkgname': 'guake', 'tags': 'terminal'}

        output = self.app.put('/api/tag/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'][0], 'tag: This field is required.')

        data = {'pkgname': 'guake', 'tag': 'terminal'}

        output = self.app.put('/api/tag/guake', data=data)
        self.assertEqual(output.status_code, 301)

        output = self.app.put('/api/tag/guake/', data=data)
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Package "guake" not found')

        create_package(self.session)

        output = self.app.put('/api/tag/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'ok')
        self.assertEqual(output['messages'][0],
                          'Tag "terminal" added to the package "guake"')

        output = self.app.put('/api/tag/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'],
                         'This tag is already associated to this package')

        data = {'pkgname': 'guake', 'tag': 'terminal,, gnome'}

        create_user(self.session)
        user = model.FASUser.by_name(self.session, 'pingou')
        self.infos = taggerapi.taggerlib.get_api_token(self.session, user)
        self.infos['token'] = 'fake'

        output = self.request_with_auth('/api/tag/guake/', 'PUT',
                                        data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Login invalid/expired')

        self.infos = taggerapi.taggerlib.get_api_token(self.session, user)

        output = self.request_with_auth('/api/tag/guake/', 'PUT',
                                        data=data)
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'ok')
        self.assertEqual(output['messages'][0],
                          'Tag "terminal" added to the package "guake"')
        self.assertEqual(output['messages'][1],
                          'Tag "gnome" added to the package "guake"')

        output = self.app.get('/api/guake/tag/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['name'], 'guake')
        self.assertEqual(output['tags'][0]['tag'], 'gnome')
        self.assertEqual(output['tags'][0]['votes'], 1)
        self.assertEqual(output['tags'][0]['like'], 1)
        self.assertEqual(output['tags'][0]['dislike'], 0)
        self.assertEqual(output['tags'][1]['tag'], 'terminal')
        self.assertEqual(output['tags'][1]['votes'], 2)
        self.assertEqual(output['tags'][1]['like'], 2)
        self.assertEqual(output['tags'][1]['dislike'], 0)

    def test_pkg_get_rating(self):
        """ Test the pkg_get_rating function.  """

        output = self.app.get('/api/guake/rating')
        self.assertEqual(output.status_code, 301)

        output = self.app.get('/api/guake/rating/')
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Package "guake" not found')

        create_package(self.session)

        output = self.app.get('/api/guake/rating/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['rating'], -1.0)
        self.assertEqual(output['name'], 'guake')

        create_rating(self.session)

        output = self.app.get('/api/guake/rating/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['rating'], 75.0)
        self.assertEqual(output['name'], 'guake')

    def test_rating_get(self):
        """ Test the rating_get function.  """

        output = self.app.get('/api/rating/75')
        self.assertEqual(output.status_code, 301)

        output = self.app.get('/api/rating/76/')
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'],
                         'No packages found with rating "76.0"')

        output = self.app.get('/api/rating/as/')
        self.assertEqual(output.status_code, 500)

        create_package(self.session)
        create_rating(self.session)

        output = self.app.get('/api/rating/75/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['rating'], 75)
        self.assertEqual(len(output['packages']), 1)
        self.assertEqual(output['packages'][0], 'guake')

    def test_rating_put(self):
        """ Test the rating_pkg_put function.  """

        data = {'pkgname': 'guake', 'ratings': 1}

        output = self.app.put('/api/rating/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'],
                         ["rating: This field is required."])

        data = {'pkgname': 'guake', 'rating': '110'}

        output = self.app.put('/api/rating/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'],
                         ["rating: Input is not a percentage"])

        data = {'pkgname': 'guake', 'rating': '-1'}

        output = self.app.put('/api/rating/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'],
                         ["rating: Input is not a percentage"])

        data = {'pkgname': 'guake', 'rating': 'asd'}

        output = self.app.put('/api/rating/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'],
                         ["rating: This field is required."])

        data = {'pkgname': 'guake', 'rating': 100}

        output = self.app.put('/api/rating/guake', data=data)
        self.assertEqual(output.status_code, 301)

        output = self.app.put('/api/rating/guake/', data=data)
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Package "guake" not found')

        create_package(self.session)

        output = self.app.put('/api/rating/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'ok')
        self.assertEqual(output['messages'], [
                         'Rating "100" added to the package "guake"'])

        output = self.app.put('/api/rating/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'You have already rated this package')

        data = {'pkgname': 'guake', 'rating': 50}
        create_user(self.session)
        user = model.FASUser.by_name(self.session, 'pingou')
        self.infos = taggerapi.taggerlib.get_api_token(self.session, user)

        output = self.request_with_auth('/api/rating/guake/', 'PUT', data=data)
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'ok')
        self.assertEqual(output['messages'], [
                         'Rating "50" added to the package "guake"'])

        output = self.app.get('/api/guake/rating/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['rating'], 75.0)
        self.assertEqual(output['name'], 'guake')

    def test_vote_put(self):
        """ Test the vote_tag_pkg_put function.  """

        ### Test with wrong input
        data = {'pkgname': 'guake', 'tags': 'terminal', 'vote':'1'}

        output = self.app.put('/api/vote/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'],
                         ["tag: This field is required."])

        data = {'pkgname': 'guake', 'tag': 'terminal', 'vote': '110'}

        output = self.app.put('/api/vote/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'],
                         ['vote: Input must be either -1 (dislike) '
        'or 1 (like)'])

        data = {'pkgname': 'guake', 'tag': 'terminal', 'vote': 'as'}

        output = self.app.put('/api/vote/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'Invalid input submitted')
        self.assertEqual(output['error_detail'],
                         ["vote: This field is required."])

        ### Test with right input format but non-existing package
        data = {'pkgname': 'guake', 'tag': 'terminal', 'vote': '-1'}

        output = self.app.put('/api/vote/guake', data=data)
        self.assertEqual(output.status_code, 301)

        output = self.app.put('/api/vote/guake/', data=data)
        self.assertEqual(output.status_code, 500)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'This tag could not be found '
                        'associated to this package')

        create_package(self.session)
        create_tag(self.session)

        output = self.app.put('/api/vote/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'ok')
        self.assertEqual(output['messages'], ['Vote added on the tag "terminal"'
        ' of the package "guake"'])

        output = self.app.put('/api/vote/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'ok')
        self.assertEqual(output['messages'], ['Your vote on the tag '
                                              '"terminal" for the package'
                                              ' "guake" did not changed'])

        data = {'pkgname': 'guake', 'tag': 'terminal', 'vote': '1'}

        output = self.app.put('/api/vote/guake/', data=data)
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'ok')
        self.assertEqual(output['messages'], ['Vote changed on the tag '
                                              '"terminal" of the package'
                                              ' "guake"'])

        output = self.app.get('/api/guake/tag/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output['name'], 'guake')
        self.assertEqual(output['tags'][0]['tag'], 'gnome')
        self.assertEqual(output['tags'][0]['votes'], 2)
        self.assertEqual(output['tags'][0]['like'], 2)
        self.assertEqual(output['tags'][0]['dislike'], 0)
        self.assertEqual(output['tags'][1]['tag'], 'terminal')
        self.assertEqual(output['tags'][1]['votes'], 3)
        self.assertEqual(output['tags'][1]['like'], 3)
        self.assertEqual(output['tags'][1]['dislike'], 0)

    def test_api(self):
        """ Test the front page """
        output = self.app.get('/api/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<title> API documentation  - Tagger API</title>'
                        in output.data)

    def test_tag_dump(self):
        """ Test tag_pkg_dump """
        output = self.app.get('/api/tag/dump/')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.data, '')

        create_package(self.session)
        create_tag(self.session)

        output = self.app.get('/api/tag/dump/')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.data, 'guake\tgnome\n'
        'guake\tterminal\n'
        'geany\tgnome\ngeany\tide')

    def test_rating_dump(self):
        """ Test rating_pkg_dump """
        output = self.app.get('/api/rating/dump/')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.data, '')

        create_package(self.session)
        create_rating(self.session)

        output = self.app.get('/api/rating/dump/')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.data, 'guake\t75.0\n'
        'geany\t100.0')

    def test_random(self):
        """ Test pkg_random """
        output = self.app.get('/api/random/')
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'No package could be found')

        create_package(self.session)
        create_rating(self.session)

        output = self.app.get('/api/random/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        keys = output.keys()
        keys.sort()
        self.assertEqual(output.keys(), ['rating', 'summary', 'name',
                         'tags', 'icon'])

    def test_statistics(self):
        """ Test statistics """
        output = self.app.get('/api/statistics/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output.keys(), ['summary'])
        self.assertEqual(0, output['summary']['with_tags'])
        self.assertEqual(0, output['summary']['no_tags'])
        self.assertEqual(0, output['summary']['tags_per_package'])
        self.assertEqual(0, output['summary']['tags_per_package_no_zeroes'])
        self.assertEqual(0, output['summary']['total_packages'])
        self.assertEqual(0, output['summary']['total_unique_tags'])

        create_package(self.session)

        output = self.app.get('/api/statistics/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual([ 'summary'], output.keys())
        self.assertEqual(0, output['summary']['with_tags'])
        self.assertEqual(3, output['summary']['no_tags'])
        self.assertEqual(0, output['summary']['tags_per_package'])
        self.assertEqual(0, output['summary']['tags_per_package_no_zeroes'])
        self.assertEqual(3, output['summary']['total_packages'])
        self.assertEqual(0, output['summary']['total_unique_tags'])

        create_tag(self.session)

        output = self.app.get('/api/statistics/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(['summary'], output.keys())
        self.assertEqual(2, output['summary']['with_tags'])
        self.assertEqual(1, output['summary']['no_tags'])
        self.assertEqual(4/float(3), output['summary']['tags_per_package'])
        self.assertEqual(2, output['summary']['tags_per_package_no_zeroes'])
        self.assertEqual(3, output['summary']['total_packages'])
        self.assertEqual(3, output['summary']['total_unique_tags'])

    def test_leaderboard(self):
        """ Test leaderboard """
        output = self.app.get('/api/leaderboard/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output.keys(), ['1'])

        create_package(self.session)
        create_tag(self.session)

        output = self.app.get('/api/leaderboard/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output.keys(), ['1', '3', '2', '5', '4', '6'])
        self.assertEqual(output['1'].keys(), ['score', 'gravatar', 'name'])
        self.assertEqual(output['1']['name'], 'pingou')
        self.assertEqual(output['1']['score'], 8)
        self.assertEqual(output['2']['name'], 'toshio')
        self.assertEqual(output['2']['score'], 2)
        self.assertEqual(output['5']['name'], 'ralph')
        self.assertEqual(output['6']['name'], '1.2.3')

    def test_score(self):
        """ Test the scores """
        output = self.app.get('/api/score/pingou/')
        self.assertEqual(output.status_code, 404)
        output = json.loads(output.data)
        self.assertEqual(output.keys(), ['output', 'error'])
        self.assertEqual(output['output'], 'notok')
        self.assertEqual(output['error'], 'User not found')

        create_package(self.session)
        create_tag(self.session)

        output = self.app.get('/api/score/pingou/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output.keys(), ['score', 'gravatar', 'name'])
        self.assertEqual(output['name'], 'pingou')
        self.assertEqual(output['score'], 8)

        output = self.app.get('/api/score/toshio/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output.keys(), ['score', 'gravatar', 'name'])
        self.assertEqual(output['name'], 'toshio')
        self.assertEqual(output['score'], 2)

    def test_login(self):
        """ Test the login page """
        output = self.app.get('/api/login/')
        self.assertEqual(output.status_code, 302)

        wrappers.BaseRequest.remote_addr = None

        output = self.app.get('/api/login/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<title>OpenID transaction in progress</title>'
                        in output.data)

        output = self.app.get('/api/login/?next=test')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<title>OpenID transaction in progress</title>'
                        in output.data)

    def test_token(self):
        """ Test the token page """
        output = self.app.get('/api/token/')
        self.assertEqual(output.status_code, 200)
        output = json.loads(output.data)
        self.assertEqual(output.keys(), ['token', 'name'])
        self.assertEqual(output['name'], '1.2.3')
        self.assertTrue(output['token'].startswith('dGFnZ2VyYXBp#'))


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(Flasktests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)