#!/usr/bin/env python

from flask import Flask
from flask.ext.mongoengine import MongoEngine
from flask.ext.login import LoginManager

app = Flask(__name__, static_url_path='')

# debug with local mongoDB
#app.config.from_pyfile('./local-dev.cfg')

# debug with remtoe mongoDB
app.config.from_pyfile('./remote-dev.cfg')

db = MongoEngine(app)

login_manager = LoginManager()
login_manager.init_app(app)

import views
