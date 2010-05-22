#!/usr/bin/python
#
# Copyright 2010 Mark Rickerby <http://maetl.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib
import urllib2
import httplib2
import random

TEST_HOST = 'http://localhost:8084'
API_KEY = '8asYFIAd+sfd!ggsdfgASDU#F*S'

register_openers()

class TestPicturesService(unittest.TestCase):
    
    def getRandomFilename(self):
        return str(random.randrange(999, 9999999)) + '.jpg'
    
    def testMissingPictureThrowsError(self):
        http = httplib2.Http()
        response, content = http.request(TEST_HOST + '/picture/missing.jpg', 'GET')
        self.assertEquals(404, response.status)
    
    def testNoApiKeyOnPostThrowsError(self):
        http = httplib2.Http()
        response, content = http.request(TEST_HOST + '/picture/test.jpg', 'POST')
        self.assertEquals(401, response.status)
        
    def testMissingPictureOnPostThrowsError(self):
        http = httplib2.Http()
        params = urllib.urlencode({'api_key': API_KEY})
        response, content = http.request(TEST_HOST + '/picture/test.jpg', 'POST', params)
        self.assertEquals(400, response.status)
    
    def testPostToPictureResource(self):
        data, headers = multipart_encode({'picture': open('assets/disco-boogie.jpg', 'rb'), 'api_key': API_KEY, 'caption': 'a caption...'})
        request = urllib2.Request(TEST_HOST + '/picture/' + self.getRandomFilename(), data, headers)
        
        # valid upload should return 201
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            self.assertEquals(201, e.code)
        
        
if __name__ == "__main__":
    unittest.main()
