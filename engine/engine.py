#!/usr/bin/env python
from twilio.rest import TwilioRestClient
import collections
import requests

from engine_cfg import TW_CLIENT_ID, TW_SECRET_KEY, \
    VM_SECRET_KEY, VM_CLIENT_ID
from utils import easylogger
from service.models import Person, Bill

LOG = easylogger.LOG

class ImpossibleError(Exception):
    pass

# TEMP
# Person = collections.namedtuple("Person", ["number",
#                                            "name",
#                                            "email",
#                                            "access_token"
#                                            ])
TwilReq = collections.namedtuple("TwilReq", ["from_", "body"])

class VenmoClient(object):
    BASE_URL = "https://api.venmo.com/v1"
    DEFAULT_NOTE = "Payment from {} via Pay Back."

    def __init__(self, client_id=VM_CLIENT_ID,
                 secret_key=VM_SECRET_KEY):
        self.client_id = client_id
        self.secret_key = secret_key

    def get_auth_url(self):
        to_send = [self.BASE_URL, "oauth/authorize"].join("/")

        # send us back to our redirect uri and let us get a new token
        params = {
            "client_id": self.client_id,
            "scope": "make_payments access_phone access_friends",
            "response_type": "code"
        }

        req = requests.get(to_send, params=params)

        LOG.debug("request sent: ", req)
        LOG.debug("req.url: ", req.url,
                  ", req.code: ", req.status_code)

    def person_from_auth_code(self, auth_code):
        to_send = [self.BASE_URL, "oauth/access_token"].join("/")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code
        }

        req = requests.post(to_send, data=data)

        LOG.debug("request sent: ", req)
        LOG.debug("req.url: ", req.url,
                  ", req.code: ", req.status_code)

        info = req.json()
        LOG.debug("req.json(): ", info)

        return Person(number=info["number"],
                      name=info["name"],
                      email=info["email"],
                      access_token=info["access_token"])

    # Person * Person... -> void
    def make_payments(self, amount, to, *froms):
        for from_ in froms:
            self._make_payment(amout, to, from_)

    # Person * Person -> void
    def _make_payment(self, amount, to, from_):
        to_send = [self.BASE_URL, "payments"].join('/')

        data = {
            "access_token": from_.access_token,
            "email": to.email,
            "amount": amount,
            "note": self.DEFAULT_NODE.format(to.name)
        }

        req = requests.post(to_send, data=data)

        LOG.debug("request sent: ", req)
        LOG.debug("req.url: ", req.url,
                  ", req.code: ", req.status_code)


class TwilioClient(object):
    MSG_FMT = '''Hey {}!
    You owe {} ${:.2f}! Reply OK to authorize payment.
    '''

    RESP_FMT = '''
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
    <Message>Payment confirmed.</Message>
    </Response>
    '''

    def __init__(self,
                 tw_client_id=TW_CLIENT_ID,
                 tw_secret_key=TW_SECRET_KEY):
        self.twilio = TwilioRestClient(tw_client_id, tw_secret_key)


    def send_auth_text(self, amount, person_to, person_from):
        message = self.twilio.sms.messages.create(
            body=self.MSG_FMT.format(
                person_to.name,
                person_from.name,
                amount),
            to=person_to.number,
            from_=person_from.number)

        LOG.debug("message.sid: ", message.sid)
        return

    def process_twilreq(self, twilreq):
        # FIND PERSON IN THE DB AND CHECK IF THEY HAVE OUTSTANDING
        # PAYMENT

        # for Person.objects(number=twilreq.number):

        if twilreq.body = "OK":
            to_bill_person = Person.objects(number=twilreq.number)
            if len(to_bills) > 1 or len(to_bills) == 0:
                raise ImpossibleError

            return Bill.object(from_=to_bill_person[0])

        else:
            return []
