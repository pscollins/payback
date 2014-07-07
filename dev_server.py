#!/usr/bin/env python

import service.app
import service.views


service.app.app.run(host='0.0.0.0', debug=True)
