#!/usr/bin/env python

from flask import Flask
from flask.ext.mongoengine import MongoEngine

DB_PATH = ""

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('./local-dev.cfg')

# def init_db():
db = MongoEngine(app)

# import views
