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
# 
# The Google App Engine API is Copyright 2007 Google Inc and is available
# under the Google App Engine terms of service: 
#
#     http://code.google.com/appengine/terms.html
#
# For more details, see http://maetl.net/pictures-api
#

#?replace-this=
API_KEY = '8asYFIAd+sfd!ggsdfgASDU#F*S'
API_ERROR_UNAUTHORIZED = 'Unauthorized'
API_ERROR_MISSING = 'Missing picture'
API_ERROR_INVALID = 'Picture must be one of .gif, .png or .jpg'
API_PICTURE_CREATED = 'Picture created'
API_PICTURE_UPDATED = 'Picture updated'
API_ERROR_NOT_SAVED = 'Picture not saved'
API_ERROR_EXISTS = 'Picture already exists'
API_PICTURE_DELETED = 'Picture deleted'

import os
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import images
from google.appengine.ext import db
from django.utils import simplejson


class Picture(db.Model):
    """
    Basic picture object
    """
    name = db.StringProperty()
    ext = db.StringProperty()
    mime_type = db.StringProperty()
    source = db.BlobProperty()
    thumb = db.BlobProperty()
    default = db.BlobProperty()
    caption = db.StringProperty()
    updated_at = db.DateTimeProperty()
    
    @classmethod
    def find(self, name, ext=False):
        """
        Find a single picture by name and file extension
        """
        query = self.all()
        query.filter('name =', name)
        if ext:
            query.filter('ext =', ext)
        
        return query.get()
    
    def encode_name(self, raw_picture, name=False, ext=False):
        """
        Encodes filename into URI friendly format.
        """
        if not name:
            basename = os.path.basename(raw_picture.filename)
            filename_part = basename.split('.')
            filename_part.pop()
            name = ''.join(filename_part)
        
        encoded_name = name.lower().replace(' ', '-').replace('_', '-')
        self.name = encoded_name
            
        if not ext:
            ext = raw_picture.type.split('/')[1].replace('jpeg', 'jpg')
        
        self.ext = ext
    
    def encode(self, raw_picture, name=False, ext=False):
        """
        Wraps the creation of resized pictures from uploaded data
        """
        self.encode_name(raw_picture, name, ext)
        
        self.mime_type = raw_picture.type
        self.source = db.Blob(raw_picture.value)
        
        self.thumb = images.resize(raw_picture.value, 120, 90)
        self.default = images.resize(raw_picture.value, 360)
    
    def save(self):
        """
        Set default timestamp on save
        """
        self.updated_at = datetime.datetime.today()
        try:
            self.put()
            return True
        except db.Error:
            return False

    def filename(self):
        """
        Recombine the pathname
        """
        return str(self.name) + '.' + str(self.ext)

    @classmethod
    def to_list(self):
        """
        Returns a dictionary of all the pictures
        """
        pictures = self.all()
        
        obj = { 'pictures': [ ] }
        for picture in pictures:
            obj['pictures'].append(picture.to_obj())
            
        return obj
 
    def to_obj(self):
        """
        Serializes the picture to an object.
        """
        obj = { 'picture': { 
                'name': self.name,
                'default': '/picture/' + self.filename(),
                'thumb': '/picture/thumb/' + self.filename(),
                'source': '/picture/source/' + self.filename(),
                'caption': self.caption,
                'updated_at': self.updated_at.isoformat()
            } }
        return obj


class ApiHandler(webapp.RequestHandler):
    """
    Base class for handling API responses and picture uploads
    """
    
    def success_response(self, status_code, message, name):
        """
        Triggers a success response from an action
        """
        self.response.set_status(status_code)
        self.response.headers['Content-Type'] = 'text/json'
        simplejson.dump({'success': { 'message': message, 'resource': '/picture/' + name } }, self.response.out)
    
    def error_response(self, status_code, message):
        """
        Triggers an error response from an action
        """
        self.response.set_status(status_code)
        self.response.headers['Content-Type'] = 'text/json'
        simplejson.dump({'error': { 'status': status_code, 'message': message } }, self.response.out)
    
    def check_picture_type(self, picture):
        """
        Return true if the uploaded 
        """
        return picture.type in ['image/jpeg', 'image/png', 'image/gif']
    
    def check_uploaded_picture(self):
        """
        Generic handler for processing picture uploads
        """
        if not self.check_api_key():
            self.error_response(401, API_ERROR_UNAUTHORIZED)
            return False
        
        if not self.request.get('picture'):
            self.error_response(400, API_ERROR_MISSING)
            return False
        
        if not self.check_picture_type(self.request.POST['picture']):
            self.error_response(400, API_ERROR_INVALID)
            return False
            
        return True
    
    def check_api_key(self):
        """
        Return false if API key is not provided
        """
        return self.request.get('api_key') == API_KEY


class PictureResource(ApiHandler):
    """
    Manage the picture resource
    """
    
    def get(self, name, ext):
        """
        Return the default representation of the picture
        """
        picture = Picture.find(name, ext)
        if picture:
            self.response.headers['Content-Type'] = picture.mime_type
            self.response.out.write(picture.default)
        else:
            self.error_response(404, API_ERROR_MISSING)
        
    def post(self, name, ext):
        """
        Handle resource based picture creation to /pictures/{name}.{ext}
        """
        if not self.check_uploaded_picture():
            return
        
        picture = Picture.find(name, ext)
        
        if not picture:
            picture = Picture()
            picture.encode(self.request.POST['picture'], name, ext)
            picture.caption = self.request.get('caption')
            picture.save()
            self.success_response(201, API_PICTURE_CREATED, picture.filename())         
        else:
            self.error_response(403, API_ERROR_EXISTS)

    def put(self, name, ext):
        """
        Update an existing picture.
        """
        if not self.check_uploaded_picture():
            return
            
        picture = Picture.find(name, ext)
        if picture:
            picture = Picture()
            picture.encode(raw_picture, name, ext)
            picture.caption = self.request.get('caption')
            picture.save()
            self.success_response(201, API_PICTURE_UPDATED, picture.filename())
        else:            
            self.error_response(403, API_ERROR_MISSING)

    def delete(self, name, ext):
        """
        Handle deletion of pictures
        """
        #if not self.check_api_key():
        #    self.error_response(401, API_ERROR_UNAUTHORIZED)
        #    return

        picture = Picture.find(name, ext)
        if picture:
            name = picture.filename()
            picture.delete()
            self.success_response(201, API_PICTURE_DELETED, name)
        else:
            self.error_response(404, API_ERROR_MISSING)


class PictureMeta(ApiHandler):
    """
    Display properties of the picture object
    """
    def get(self, name):
        picture = Picture.find(name)
        if picture:
            self.response.headers['Content-Type'] = 'text/json'
            simplejson.dump(picture.to_obj(), self.response.out)
        else:
            self.error_response(404, API_ERROR_MISSING)


class PictureResized(ApiHandler):
    """
    Display source and thumbnail pictures
    """
    def get(self, format, name, ext):
        picture = Picture.find(name, ext)
        if picture:
            self.response.headers['Content-Type'] = picture.mime_type
            self.response.out.write(getattr(picture, format))
        else:
            self.error_response(404, API_ERROR_MISSING)


class PicturesCollection(ApiHandler):
    """
    Manages the pictures collection
    """
    
    def get(self):
        """
        Returns the full index of images
        """
        index = Picture.to_list()
        
        self.response.headers['Content-Type'] = 'text/json'
        simplejson.dump(index, self.response.out)
        
    def post(self):
        """
        Handle direct post to picture collection
        """
        if not self.check_uploaded_picture():
            return
        
        picture = Picture()
        picture.encode(self.request.POST['picture'])
        picture.caption = self.request.get('caption')
        
        if not picture.save():
            self.error_response(403, API_ERROR_NOT_SAVED)
        
        self.success_response(201, API_PICTURE_CREATED, picture.filename())


class PicturesSearch(ApiHandler):
    """
    Search for pictures by name
    """
    def get(self):
        picture = Picture.find_list(q)
        if picture:
            self.response.headers['Content-Type'] = picture.mime_type
            self.response.out.write(picture.get_resized(format))
        else:
            self.error_response(404, API_ERROR_MISSING)



application = webapp.WSGIApplication(
		[
		    ('/picture/(source|thumb)/(.*).(jpg|png|gif)', PictureResized),
		    ('/picture/(.*).(jpg|png|gif)', PictureResource),
            ('/picture/(.*)', PictureMeta),
            ('/pictures', PicturesCollection),
            ('/pictures/search', PicturesSearch)
		],
      debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()