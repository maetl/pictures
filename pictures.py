import os
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import pictures
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
        Wraps the creation of resized picture blobs from uploaded data
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

    def get_resized(self, format):
        """
        Returns the raw source for the resized image
        """
        if format == 'thumb':
            return self.thumb
        else:
            return self.source
    
    def to_obj(self):
        """
        Serializes the picture to an object.
        """
        obj = { 'picture': { } }
        obj['picture']['name'] = self.name
        filename = self.name + '.' + self.ext
        obj['picture']['default'] = '/picture/' + filename
        obj['picture']['thumb'] = '/picture/thumb/' + filename
        obj['picture']['source'] = '/picture/source' + filename
        obj['picture']['caption'] = self.caption
        obj['picture']['updated_at'] = self.updated_at.isoformat()
        return obj           

class ApiHandler(webapp.RequestHandler):
    """
    Base class for handling a RESTful JSON API
    """
    
    def creation_response(self, name):
        self.response.set_status(201)
        self.response.headers['Content-Type'] = 'text/json'
        simplejson.dump({'success': { 'status': 201, 'message': 'OK', 'path': '/picture/' + name } }, self.response.out)
    
    def error_response(self, status_code, message):
        self.response.set_status(status_code)
        self.response.headers['Content-Type'] = 'text/json'
        simplejson.dump({'error': { 'status': status_code, 'message': message } }, self.response.out)
    
    def validate_picture_type(self, raw):
        return raw.type in ['picture/jpeg', 'picture/png', 'picture/gif']

class PictureResource(ApiHandler):
    """
    Manage the picture resource
    """
    def get(self, name, ext):
        picture = Picture.gql('WHERE name = :1 AND ext = :2', name, ext).get()
        if picture:
            self.response.headers['Content-Type'] = picture.mime_type
            self.response.out.write(picture.default)
        else:
            self.error_response(404, 'Picture not found')
        
    def post(self, name, ext):
        """
        Handle RESTful picture creation
        """
        raw_picture = self.request.get('picture')
        
        if not raw_picture:
            self.error_response(400, 'Missing picture file')
            return
        
        if not self.validate_picture_type(raw_picture):
            self.error_response(400, 'Invalid picture type')
            return
        
        picture = Picture()
        picture.encode_name(raw_picture, name, ext)
        picture.encode_source(raw_picture)
        picture.caption = self.request.get('caption')
        picture.save()
        
        self.response.set_status(201)
        self.response.out.write("picture created...")
        
class PicturesCollection(ApiHandler):
    """Manages the pictures collection"""
    
    def get(self):
        pass
        
    def post(self):
        """
        Handle direct post to picture collection
        """
        uploaded_picture = self.request.get('picture')
        
        if not uploaded_picture:
            self.error_response(400, 'Invalid picture upload')
            return
            
        if not self.validate_picture_type(self.request.POST['picture']):
            self.error_response(400, 'Invalid picture type')
            return  
        
        picture = Picture()
        picture.encode_name(self.request.POST['picture'])
        picture.encode_source(self.request.POST['picture'])
        picture.caption = self.request.get('caption')
        picture.save()
        
        self.creation_response(picture.name + '.' + picture.ext)

class PictureMeta(webapp.RequestHandler):
    """
    Display properties of the picture object
    """
    def get(self, name):
        image = Image.gql('WHERE name = :1', name).get()
        if image:
            self.response.headers['Content-Type'] = 'text/json'
            simplejson.dump(image.to_obj(), self.response.out)
        else:
            self.error_response(404, 'Image not found')

class PictureResized(webapp.RequestHandler):
    """
    Display source and thumbnail pictures
    """
    def get(self, format, name, ext):
        picture = Picture.gql('WHERE name = :1 AND ext = :2', name, ext).get()
        if picture:
            self.response.headers['Content-Type'] = picture.mime_type
            self.response.out.write(picture.get_resized(format))
        else:
            self.error_response(404, 'Picture not found')        

class PicturesSearch(webapp.RequestHandler):
    """
    Search pictures by name
    """
    def get(self):
        pass

application = webapp.WSGIApplication(
		[
		    ('/picture/(source|thumb)/(.*).(jpg|png|gif)', PictureResized),
            ('/picture/(.*).(jpg|png|gif)', PictureResource),
            ('/picture/(.*).json', PictureMeta),
            ('/pictures', PicturesCollection),
            ('/pictures/search', PicturesSearch)
		],
      debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()