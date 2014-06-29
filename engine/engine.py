#!/usr/bin/env python
from twilio.rest import TwilioRestClient
import collections
import requests
import face_client

from engine_cfg import TW_CLIENT_ID, TW_SECRET_KEY, \
    VM_SECRET_KEY, VM_CLIENT_ID, \
    SB_CLIENT_ID, SB_SECRET_KEY
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
        to_send = "/".join([self.BASE_URL, "oauth/authorize"])

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

        return req.url

    def person_from_auth_code(self, auth_code):
        to_send = "/".join([self.BASE_URL, "oauth/access_token"])

        data = {
            "client_id": self.client_id,
            "client_secret": self.secret_key,
            "code": auth_code
        }

        req = requests.post(to_send, data=data)

        LOG.debug("request sent: ", req)
        LOG.debug("req.url: ", req.url,
                  ", req.code: ", req.status_code)

        info = req.json()
        LOG.debug("req.json(): ", info)


        return Person(number=info["user"]["phone"],
                      name=info["user"]["display_name"],
                      email=info["user"]["email"] or "none@none.none",
                      access_token=info["access_token"])

    # Person * Person... -> void
    def make_payments(self, amount, to, *froms):
        for from_ in froms:
            self._make_payment(amount, to, from_)

    # Person * Person -> void
    def _make_payment(self, amount, to, from_):
        to_send = "/".join([self.BASE_URL, "payments"])

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
    BASE_FMT='''
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
    <Message>{}.</Message>
    </Response>
    '''


    RESP_FMT = BASE_FMT.format("Payment confirmed. Paid: {}")

    REJ_FMT = BASE_FMT.format("Payment rejected. Paid: $0.00")

    def __init__(self,
                 tw_client_id=TW_CLIENT_ID,
                 tw_secret_key=TW_SECRET_KEY):
        self.twilio = TwilioRestClient(tw_client_id, tw_secret_key)


    def send_auth_text(self, bill):
        amount = bill.amount
        person_to = bill.to
        person_from = bill.from_
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
        # for Person.objects(number=twilreq.number):

        # FIX ME LATER TO DO SMART THINGS
        if twilreq.body == "OK":
            to_bill_person = Person.objects(number=twilreq.from_)
            if len(to_bill_person) > 1 or len(to_bill_person) == 0:
                raise ImpossibleError

            return to_bill_person, Bill.object(from_=to_bill_person[0])

        else:
            return None, []

    def payment_conf(self, person_billed, bills_paid):
        paid_msgs = ",".join(["To {}: ${:.2f}".format(b.to.name, b.amount)
                    for b in bills_paid])

        return self.RESP_FMT.format(paid_msgs)

    def payment_rej(self,):
        return self.REJ_FMT

class SkyClient(object):
    NAMESPACE = "PayBackTest"
    MIN_CONF = 40

    def __init__(self, client_id=SB_CLIENT_ID,
                 secret_key=SB_SECRET_KEY):
        self.client = face_client.FaceClient(client_id, secret_key)

    # this is their format for whatever reason
    def _qualify(self, ident):
        return "{}@{}".format(ident, self.NAMESPACE)

    def _unqualify(self, ident):
        return ident.split("@")[0]

    # match on person.number b/c unique
    def train_for_user(self, person, *images):
        LOG.debug("Sending to faces_detect")

        resps = [self.client.faces_detect(file=im) for im in images]

        LOG.debug("Got responses: ", resps)

        for resp in resps:
            LOG.debug("resp: ", resp)

        # let's hope it only picked up one face
        tids = [resp['photos'][0]['tags'][0]['tid'] for resp in resps]

        LOG.debug("found tids: ", tids)
        LOG.debug("saving tags")

        self.client.tags_save(tids=",".join(tids),
                              uid=self._qualify(person.number),
                              label=person.name)

        LOG.debug("Training....")
        # LONG RUNNING!! and asynchronous
        self.client.faces_train(self._qualify(person.number))

    def find_user_numbers_in(self, image):
        resp = self.client.faces_recognize("all",
                                           file=image,
                                           namespace=self.NAMESPACE)

        LOG.debug("resp: ", resp)

        to_return = []

        for tag in resp['photos'][0]['tags']:
            LOG.debug("checking tag: ", tag)
            if tag['uids']:
                LOG.debug(tag['uids'])

                candidate = max(tag['uids'],
                                key=lambda x: x['confidence'])
                if candidate['confidence'] >= self.MIN_CONF:
                    to_return.append(self._unqualify(candidate['uid']))

        LOG.debug("got user phone numbers: ", to_return)

        return to_return
