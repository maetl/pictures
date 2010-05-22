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
import urllib
import urllib2

TEST_HOST = 'http://localhost:8084'

class TestPicturesService(unittest.TestCase):
    
    def testMissingPictureThrows404(self):
        try:
            response = urllib2.urlopen(TEST_HOST + '/picture/missing.jpg')
        except urllib2.HTTPError, e:
            self.assertEquals(404, e.code)
    
    def testSingularPictureResource(self):
        data = { 'caption': 'this is a picture caption', 'file': open('assets/disco-boogie.jpg') }
        body = urllib.urlencode(data)
        try:
            response = urllib2.urlopen(TEST_HOST + '/picture/my-picture.jpg', body)
        except urllib2.HTTPError, e:
            print e.read()
        
        
        
        
if __name__ == "__main__":
    unittest.main()
