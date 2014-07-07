#!/usr/bin/env python

# pylint: disable=unused-import

from payback.service.app import app
import payback.service.views


app.run(host='0.0.0.0', debug=True)
