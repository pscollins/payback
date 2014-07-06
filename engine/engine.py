#!/usr/bin/env python
from twilio.rest import TwilioRestClient
import collections
import requests
import face_client
import facebook

from engine_cfg import TW_CLIENT_ID, TW_SECRET_KEY, \
    VM_SECRET_KEY, VM_CLIENT_ID, \
    SB_CLIENT_ID, SB_SECRET_KEY, \
    FB_CLIENT_ID, FB_SECRET_KEY
from utils import easylogger
from service.models import Person, Bill

LOG = easylogger.LOG

class ImpossibleError(Exception):
    pass

class SkyBiometryError(Exception):
    pass

class TooManyFacesError(SkyBiometryError):
    pass

class UnrecognizedUserError(SkyBiometryError):
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
                      vm_access_token=info["access_token"])

    # Person * Person... -> void
    def make_payments(self, amount, to, *froms):
        for from_ in froms:
            self._make_payment(amount, to, from_)

    # Person * Person -> void
    def _make_payment(self, amount, to, from_):
        to_send = "/".join([self.BASE_URL, "payments"])

        data = {
            "access_token": from_.vm_access_token,
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
    BASE_FMT = '''
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
    <Message>{}.</Message>
    </Response>
    '''

    RESP_FMT = BASE_FMT.format("Payment confirmed. Paid: {}")

    REJ_FMT = BASE_FMT.format("Payment rejected. Paid: $0.00")

    OUR_NUM = "+16466473401"
    # OUR_NUM = "+13124362253"

    def __init__(self,
                 tw_client_id=TW_CLIENT_ID,
                 tw_secret_key=TW_SECRET_KEY):
        self.twilio = TwilioRestClient(tw_client_id, tw_secret_key)

    def _plusify(self, num):
        return ("+{}" if not "+" in num else "{}").format(num)

    def send_auth_text(self, bill):
        amount = bill.amount
        person_to = bill.to
        person_from = bill.from_
        to_num = self._plusify(person_to.number)

        LOG.debug("person_to.number ", to_num)
        LOG.debug("self.OUR_NUM ", self.OUR_NUM)

        message = self.twilio.messages.create(
            body=self.MSG_FMT.format(
                person_to.name,
                person_from.name,
                amount),
            to=self._plusify(to_num),
            from_=self.OUR_NUM)

            # from_)
            # from_=person_from.number)

        LOG.debug("message.sid: ", message.sid)
        return

    def process_twilreq(self, twilreq):
        # for Person.objects(number=twilreq.number):
        LOG.debug("inside process_twilreq")
        LOG.debug("twilreq: ", twilreq)

        # FIX ME LATER TO DO SMART THINGS
        if twilreq.body.lower() == "ok":
            to_bill_person = Person.objects(number=twilreq.from_)
            LOG.debug("to_bill_person: ",
                      to_bill_person)
            # if len(to_bill_person) > 1 or len(to_bill_person) == 0:
            #     raise ImpossibleError

            return to_bill_person, Bill.objects(from_=to_bill_person[0])

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
    MIN_CONF = 5

    def __init__(self, client_id=SB_CLIENT_ID,
                 secret_key=SB_SECRET_KEY):
        self.client = face_client.FaceClient(client_id, secret_key)

    # this is their format for whatever reason
    @classmethod
    def _qualify(cls, ident):
        return "{}@{}".format(ident, cls.NAMESPACE)

    @classmethod
    def _unqualify(cls, ident):
        return ident.split("@")[0]

    def _train_person_on_tids(self, person, tids):
        self.client.tags_save(tids=",".join(tids),
                              uid=self._qualify(person.number),
                              label=person.name)

        LOG.debug("Training....")
        # LONG RUNNING!! and asynchronous
        self.client.faces_train(self._qualify(person.number))

    # match on person.number b/c unique
    def train_for_user(self, person, *images):
        LOG.debug("Sending to faces_detect")
        LOG.debug("Got images: ", images)

        resps = [self.client.faces_detect(file=im) for im in images]

        LOG.debug("Got responses: ", resps)

        for resp in resps:
            LOG.debug("resp: ", resp)

        tids = []

        for resp in resps:
            for photo in resp['photos']:
                if len(photo['tags']) != 1:
                    raise TooManyFacesError
                else:
                    tids.append(photo['tags'][0]['tid'])

        LOG.debug("found tids: ", tids)
        LOG.debug("saving tags")
        self._train_person_on_tids(person, tids)


    def _find_matching_original(self, original_photos, url):
        try:
            return [photo for photo in original_photos
                    if photo.url == url][0]
        except IndexError:
            # should never see this
            raise UnrecognizedUserError

    def _find_best_uid_from_tag_json(self, tag):
        uid_and_conf = max(tag['uids'], key=lambda x: x['confidence'])
        return uid_and_conf['uid'], uid_and_conf['confidence']

    def _update_tids(self, tids, possible_tags):
        try:
            best_tag = max(possible_tags, key=lambda x: x.confidence)
            tids.append(best_tag.tid)
        except ValueError:
            pass

    def train_for_facebook(self, person, original_photos):
        urls = ",".join([photo.url for photo in original_photos])
        # TOOD: what's "aggressive"? Do we want that?
        # TODO: also a "train" parameter here that's not documented
        # TODO: we should probably care about SkyBio's 'threshold'

        qualified_person = self.qualify(person.number)
        resp = self.client.faces_recognize(self.qualify(person.number),
                                           urls=urls)
        tids = []
        for photo in resp['photos']:
            original = self._find_matching_original(original_photos, photo)
            possible_tags = []
            for tag in photo['tags']:
                LOG.debug("processing tag: ", tag)
                # Not sure if we ever have more than one uid here
                uid, confidence = self._find_best_uid_from_tag_json(tag)
                photo_tag = (uid == qualified_person) and \
                            PhotoTag(person.number,
                                     tag['center']['x'],
                                     tag['center']['y'])
                if original.tag_matches(photo_tag):
                    possible_tags.append(ConfidentTag(photo_tag,
                                                      confidence,
                                                      tag['tid']))

                LOG.debug("Got possible tags: ", possible_tags)
                self._update_tids(tids, possible_tags)

        LOG.debug("found tids: ", tids)
        LOG.debug("About to start training...")
        self._train_person_on_tids(person, tids)

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


class FacebookUserClientBuilder:
    def __init__(self, client_id=FB_CLIENT_ID, secret_key=FB_SECRET_KEY):
        self._client_id = client_id
        self._secret_key = secret_key

    def client_for_person(self, person, exchange_token):
        return FacebookUserClient(person, exchange_token, self._client_id,
                                  self._secret_key)


class FacebookUserClient:
    def __init__(self, person, auth_token, client_id, secret_key):
        self._client = facebook.GraphApi(access_token=auth_token)
        self._client_id = client_id
        self._secret_key = secret_key
        self._person = person

        self._get_auth_token()
        self._get_fb_id()

        self._person.update()

    def _get_fb_id(self):
        resp = self._client.request("/me")

        self._person.fb_id = resp["id"]

    def _get_auth_token(self):
        resp = self._client.extend_access_token(self._client_id,
                                                self._secret_key)
        LOG.debug("facebook response: ", resp)

        self._person.fb_access_token = resp["access_token"]

    def get_photos(self):
        # Looks like we get 20-30ish from the API without going
        # through cursor bullshit. Let's just use those for now

        resp = self._client.request("{}/photos".format(self._person.fb_id))

        LOG.debug("got photo response: ", resp)

        return [TaggedPhoto.from_fb_resp(pic_resp) for pic_resp in resp["data"]]

    def get_friends(self):
        raise NotImplementedError

# TODO: No clue what unit "x" and "y" are in. Seems to be "percentage
# distance from upper right corner of image." Also not clear if this
# is the center of the face, edge, or what.

# BUT whatever they are, it looks like they match up with Sky Biometry
# -- they appear to be centers of tagged areas.

PhotoTag = collections.namedtuple("PhotoTag", ["number", "x", "y",])
ConfidentTag = collections.namedtuple("ConfidentTag", ["tag",
                                                       "confidence",
                                                       "tid"])

class TaggedPhoto:
    # NOTE THAT WE AREN'T GOING THROUGH ANY OF THIS "PAGING" BULLSHIT
    # AND THAT MIGHT FUCK US UP
    CROP_PORTION_WIDTH = .05
    CROP_PORTION_HEIGHT = .05

    TAG_MARGIN = .05

    def __init__(self, url=None, tags=None, pil=None):
        self.url = url
        self.tags = tags
        self.pil = pil

    def __repr__(self):
        FMT = 'TaggedPhoto(url="{}", tags=[{}], pil={})'

        return FMT.format(self.url, ",".join(self.tags), self.pil)

    @classmethod
    def from_fb_resp(cls, fb_resp, pil=None):
        url = fb_resp["source"]
        tags = []
        for resp in fb_resp['tags']['data']:
            # This will be None if no person is in our db
            number = Person.objects(fb_id=resp['id']).first()
            tags.append(PhotoTag(number, float(resp["x"]),
                                 float(resp["y"])))

        return TaggedPhoto(url, tags, pil)


    @classmethod
    def from_skybio_resp(cls, skybio_resp, pil=None):
        # We have two different kinds of uids running around here -- that's bad
        url = skybio_resp["url"]
        tags = []
        raise NotImplementedError


    def check_tag_matches(self, tag):
        try:
            matching_tag = [x for x in self.tags if x.number == tag.number][0]
        except (IndexError, TypeError):
            # Fail if we were given None or a number that's not ours
            return False

        return ((abs(matching_tag.x - tag.x) <= self.TAG_MARGIN) and
                (abs(matching_tag.y - tag.y) <= self.TAG_MARGIN))

    def get_face_cutouts(self):
        if not (self.tags and self.pil):
            raise ValueError

        else:
            width_px, height_px = self.pil.size
            crop_width_px = self.CROP_PORTION_WIDTH * width_px
            crop_height_px = self.CROP_PORTION_HEIGHT * height_px

            ret = []
            for tag in self.tags:
                abs_x = tag.x * width_px
                abs_y = tag.y * height_px
                to_crop = (abs_x - crop_width_px, abs_y - crop_height_px,
                           abs_x + crop_width_px, abs_y - crop_height_px)

                ret.append(self.pil.crop(to_crop))

            return ret
