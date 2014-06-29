#!/usr/bin/env python
from service import app, db

# BE AWARE THAT TWILIO AND VENMO FORMAT PHONE NUMBERS DIFFERENTLY AND
# THAT THIS MAY FUCK UP

class Person(db.Document):
    name = db.StringField(required=True)
    # number = db.StringField(required=True, unique=True)
    # FUCKS UP TESTING
    number = db.StringField(required=True)
    access_token = db.StringField(required=True)
    email = db.EmailField(required=True)
    friends = db.ListField(db.ReferenceField('Person'))

    portraits = db.ListField(db.ImageField())
    bills_owed = db.ListField(db.ReferenceField('Bill'))

class Bill(db.Document):
    amount = db.FloatField(required=True)
    to = db.ReferenceField(Person, required=True)
    from_ = db.ReferenceField(Person, required=True)
