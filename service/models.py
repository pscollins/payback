#!/usr/bin/env python

from service import app, db

class User(db.Document):
    paypal_secret = db.StringField()
    
    name = db.StringField()
    portraits = db.ListField(db.ImageField())

