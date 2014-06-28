#!/usr/bin/env python

from flask import Flask
from flask.ext.mongoengine import MongoEngine

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('../local-dev.cfg')

db = MongoEngine(app)

import views
