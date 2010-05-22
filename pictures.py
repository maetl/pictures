"""

.::.            .       .:;P;:. .:;.;:.         .: P;:. 
P  P    .:;p;:' P:;p;:'       P P  P    P  P  P P  P  P 
`:;P;:'         `       `:;P;:' `:;P;:' `:;P;:' `:;P :'


A Simple App Engine Picture API
 
Google App Engine APIs are licensed under the Google App Engine
terms of service: http://code.google.com/appengine/terms.html

"""

import os
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import pictures
from google.appengine.ext import db
from django.utils import simplejson

#?replace-this=
PICTURES_API_KEY = '8asYFIAd+sfd!ggsdfgASDU#F*S'

#?response-messages=
API_ERROR_UNAUTHORIZED = 'Unauthorized'
API_ERROR_MISSING = 'Missing picture'
API_ERROR_INVALID = 'Picture must be one of .gif, .png or .jpg'
API_PICTURE_CREATED = 'Picture created'
API_PICTURE_UPDATED = 'Picture updated'
API_ERROR_NOT_SAVED = 'Picture not saved'
API_ERROR_EXISTS = 'Picture already exists'
API_PICTURE_DELETED = 'Picture deleted'

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
        Find a single picture with given parameters
        """
        query = self.all()
        if name:
            query.filter('name =', name)
        if ext:
            query.filter('ext =', ext)
        
        return query.get()
    
    def encode_name(self, raw, name=False, ext=False):
        """
        Encodes filename into URI friendly format.
        """
        if not name:
            filename_part = raw.filename.split('.')
            filename_part.pop()
            name = ''.join(filename_part)
        
        encoded_name = name.lower().replace(' ', '-').replace('_', '-')
        self.name = encoded_name
            
        if not ext:
            ext = raw.type.split('/')[1].replace('jpeg', 'jpg')
        
        self.ext = ext
    
    def encode_source(self, raw):
        """
        Wraps the creation of resized pictures from uploaded data
        """
        self.mime_type = raw.type
        self.source = db.Blob(raw.value)
        
        self.thumb = pictures.resize(raw.value, 120, 90)
        self.default = pictures.resize(raw.value, 360)
    
    def save(self):
        """
        Set default timestamp on save
        """
        self.updated_at = datetime.datetime.today()
        self.put()

    def filename(self):
        """
        Recombine the pathname
        """
        return str(self.name) + '.' + str(self.ext)

    def find_list(self):
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
        obj = { 'picture': { } }
        obj['picture']['name'] = self.name
        obj['picture']['default'] = '/picture/' + self.filename()
        obj['picture']['thumb'] = '/picture/thumb/' + self.filename()
        obj['picture']['source'] = '/picture/source/' + self.filename()
        obj['picture']['caption'] = self.caption
        obj['picture']['updated_at'] = self.updated_at.isoformat()
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
        simplejson.dump({'success': { 'message': message, 'resource': name } }, self.response.out)
    
    def error_response(self, status_code, message):
        """
        Triggers an error response from an action
        """
        self.response.set_status(status_code)
        self.response.headers['Content-Type'] = 'text/json'
        simplejson.dump({'error': { 'status': status_code, 'message': message } }, self.response.out)
    
    def check_picture_type(self, raw_picture):
        """
        Return true if the uploaded 
        """
        return raw_picture.type in ['image/jpeg', 'image/png', 'image/gif']
    
    def check_uploaded_picture(self, raw_picture):
        """
        Generic handler for processing picture uploads
        """
        if not self.check_api_key(self.request.get('api_key')):
            self.error_response(401, API_ERROR_UNAUTHORIZED)
            return False
        
        if not raw_picture:
            self.error_response(400, API_ERROR_MISSING)
            return False
        
        if not self.check_picture_type(raw_picture):
            self.error_response(400, API_ERROR_INVALID)
            return False
            
        return True
    
    def check_api_key(self, api_key):
        """
        Stub method to verify post requests with an API key
        """
        return api_key == PICTURES_API_KEY


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
        if not self.validate_uploaded_picture():
            return
        
        picture = Picture.find(name, ext)
        
        if not picture:
            picture = Picture()
            picture.encode_name(raw_picture, name, ext)
            picture.encode_source()
            picture.caption = self.request.get('caption')
            picture.save()
            self.success_response(201, API_PICTURE_CREATED, picture.filename())         
        else:
            self.error_response(403, API_ERROR_EXISTS)

    def put(self, name, ext):
        """
        Update an existing picture.
        """
        if not self.validate_uploaded_picture():
            return
            
        picture = Picture.find(name, ext)
        if picture:
            picture = Picture()
            picture.encode_name(raw_picture, name, ext)
            picture.encode_source()
            picture.caption = self.request.get('caption')
            picture.save()
            self.success_response(201, API_PICTURE_UPDATED, picture.filename())
        else:            
            self.error_response(403, API_ERROR_MISSING)

    def delete(self, name, ext):
        """
        Handle deletion of pictures
        """
        if not self.check_api_key(self.request.get('api_key')):
            self.error_response(401, API_ERROR_UNAUTHORIZED)
            return

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
        if image:
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
        index = Picture.find_list()
        
        self.response.headers['Content-Type'] = 'text/json'
        simplejson.dump(index, self.response.out)
        
    def post(self):
        """
        Handle direct post to picture collection
        """
        if not self.accept_picture_request():
            return False
        
        picture = Picture()
        picture.encode_name(self.request.POST['picture'])
        picture.encode_source(self.request.POST['picture'])
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