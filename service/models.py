#!/usr/bin/env python
from service import app, db
from flask.ext.login import UserMixin

# BE AWARE THAT TWILIO AND VENMO FORMAT PHONE NUMBERS DIFFERENTLY AND
# THAT THIS MAY FUCK UP

class Person(db.Document, UserMixin):
    name = db.StringField(required=True)
    # number = db.StringField(required=True, unique=True)
    # FUCKS UP TESTING
    number = db.StringField(required=True)
    access_token = db.StringField(required=True)
    email = db.EmailField(required=True)
    friends = db.ListField(db.ReferenceField('Person'))

    portraits = db.ListField(db.ImageField())
    bills_paid = db.ListField(db.ReferenceField('Bill'))
    bills_owed = db.ListField(db.ReferenceField('Bill'))

    active = db.BooleanField(required=True, default=True)

    def is_active(self):
        return self.active

    def get_id(self):
        return unicode(self.number)


class Bill(db.Document):
    amount = db.FloatField(required=True)
    to = db.ReferenceField(Person, required=True)
    from_ = db.ReferenceField(Person, required=True)
