#!/usr/bin/env python

from flask import Flask
from flask.ext.mongoengine import MongoEngine

app = Flask(__name__, static_url_path='')

# debug with local mongoDB
#app.config.from_pyfile('./local-dev.cfg')

# debug with remtoe mongoDB
app.config.from_pyfile('./remote-dev.cfg')

# def init_db():
db = MongoEngine(app)

# import views
