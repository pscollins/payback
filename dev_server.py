#!/usr/bin/env python

# pylint: disable=unused-import

from payback.service import app
import payback.service.views


app.app.run(host='0.0.0.0', debug=True)
