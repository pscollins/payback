#!/usr/bin/env python
import paypalrestsdk

from engine_cfg import ENDPOINT, CLIENT_ID, SECRET_KEY

class Engine(object):
    def __init__(self, endpoint=ENDPOINT,
                 client_id=CLIENT_ID,
                 secret_key=SECRET_KEY,
                 mode="sandbox"):
        self.api = paypalrestsdk.Api({
            "mode": mode,
            "client_id": client_id,
            "client_secret": secret_key
            })


    def get_login_url(self):
        return Tokeninfo.authorize_url({
            "scope": "openid email",
        })
