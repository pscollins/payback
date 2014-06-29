#!/usr/bin/env python
from twilio.rest import TwilioRestClient
import collections

from engine_cfg import TW_CLIENT_ID, TW_SECRET_KEY
from utils import easylogger

LOG = easylogger.LOG

# TEMP
Person = collections.namedtuple("Person", ["number",
                                           "name",
                                           "has_outstanding"])
TwilReq = collections.namedtuple("TwilReq", ["from", "body"])

class Engine(object):
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
        self.venmo = None


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

        # IF THEY DO, PROCESS IT

        # FINALLY
        return self.RESP_FMT
