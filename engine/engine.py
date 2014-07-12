#!/usr/bin/env python
import collections
import requests
import face_client
import itertools
import os
import hashlib

from twilio.rest import TwilioRestClient
from PIL import Image

from payback.engine import facebook
from payback.engine.engine_cfg import TW_CLIENT_ID, TW_SECRET_KEY, \
    VM_SECRET_KEY, VM_CLIENT_ID, \
    SB_CLIENT_ID, SB_SECRET_KEY, \
    FB_CLIENT_ID, FB_SECRET_KEY
from payback.utils import easylogger
from payback.service.models import Person, Bill

LOG = easylogger.LOG

class ImpossibleError(Exception):
    pass

class SkyBiometryError(Exception):
    pass

class TooManyFacesError(SkyBiometryError):
    pass

class TooFewFacesError(SkyBiometryError):
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

    @staticmethod
    def _plusify(num):
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

    @staticmethod
    def process_twilreq(twilreq):
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
                 secret_key=SB_SECRET_KEY,
                 face_client_constructor=face_client.FaceClient):
        self.client = face_client_constructor(client_id, secret_key)

    # this is their format for whatever reason
    def qualify(self, ident):
        return "{}@{}".format(ident, self.NAMESPACE)

    @staticmethod
    def unqualify(ident):
        return ident.split("@")[0]

    def _train_person_on_tids(self, person, tids):
        # set() because dupes break the API
        no_duplicates = set(tids)
        LOG.debug("dupes removed: ", no_duplicates)
        self.client.tags_save(tids=",".join(no_duplicates),
                              uid=self.qualify(person.number),
                              label=person.name)

        LOG.debug("Training....")
        # LONG RUNNING!! and asynchronous
        self.client.faces_train(self.qualify(person.number))

    def _get_tids_to_train_for_user(self, images):
        resps = [self.client.faces_detect(file=im) for im in images]

        LOG.debug("Got responses: ", resps)

        for resp in resps:
            LOG.debug("resp: ", resp)

        tids = []

        for resp in resps:
            for photo in resp['photos']:
                num_tags = len(photo['tags'])
                if num_tags == 0:
                    raise TooFewFacesError
                elif num_tags > 1:
                    raise TooManyFacesError
                else:
                    tids.append(photo['tags'][0]['tid'])

        return tids


    # match on person.number b/c unique
    def train_for_user(self, person, *images):
        LOG.debug("Sending to faces_detect")
        LOG.debug("Got images: ", images)

        tids = self._get_tids_to_train_for_user(images)

        LOG.debug("found tids: ", tids)
        LOG.debug("saving tags")
        self._train_person_on_tids(person, tids)

    @staticmethod
    def _find_matching_original(original_photos, url):
        # TODO: the name of this exception doesn't make sense
        try:
            return [photo for photo in original_photos
                    if photo.url == url][0]
        except IndexError:
            # should never see this
            raise UnrecognizedUserError

    @staticmethod
    def _find_best_uid_from_tag_json(tag):
        try:
            uid_and_conf = max(tag['uids'], key=lambda x: x['confidence'])
            return uid_and_conf['uid'], uid_and_conf['confidence']
        except ValueError:
            return None, None

    @staticmethod
    def _update_tids(tids, possible_tags):
        try:
            best_tag = max(possible_tags, key=lambda x: x.confidence)
            tids.append(best_tag.tid)
        except ValueError:
            pass

    def _recognize_for_person(self, person, **kwargs):
        qualified_person = self.qualify(person.number)
        return self.client.faces_recognize(self.qualify(person.number),
                                           **kwargs)

    def _update_possible_tags(self, possible_tags, tag, person, original):
        uid, confidence = self._find_best_uid_from_tag_json(tag)

        photo_tag = (uid == self.qualify(person.number)) and \
                    PhotoTag(person.number,
                             tag['center']['x'],
                             tag['center']['y'])

        LOG.debug("Checking if tags match. photo_tag: ", photo_tag)
        LOG.debug("orignal.tags: ", original.tags)

        if original.tag_matches(photo_tag):
            possible_tags.append(ConfidentTag(photo_tag,
                                              confidence,
                                              tag['tid']))


    def _find_tids_for_facebook(self, person, original_photos, resp):
        tids = []
        for photo in resp['photos']:
            original = self._find_matching_original(original_photos,
                                                    photo['url'])
            possible_tags = []
            LOG.debug("photo: ", photo)
            LOG.debug("tag to iterate on: ",
                      [tag for tag in photo['tags'] if tag['uids']])
            for tag in [tag for tag in photo['tags'] if tag['uids']]:
                LOG.debug("processing tag: ", tag)
                # Not sure if we ever have more than one uid here

                self._update_possible_tags(possible_tags, tag, person, original)

            LOG.debug("Got possible tags: ", possible_tags)

            self._update_tids(tids, possible_tags)

        return tids

    def train_for_facebook(self, person, original_photos):
        urls = ",".join([photo.url for photo in original_photos])
        # TOOD: what's "aggressive"? Do we want that?
        # TODO: also a "train" parameter here that's not documented
        # TODO: we should probably care about SkyBio's 'threshold'

        sky_resp = self._recognize_for_person(person, urls=urls)

        tids = self._find_tids_for_facebook(person,
                                            original_photos,
                                            sky_resp)
        LOG.debug("found tids: ", tids)

        if tids:
            LOG.debug("About to start training...")
            # We're getting duplicates in here for reasons that are
            # unclear to me
            self._train_person_on_tids(person, tids)
        else:
            LOG.debug("Didn't find any pictures to train on.")

    def taggedphoto_from_image(self, image):
        resp = self.client.faces_recognize("all",
                                           file=image,
                                           namespace=self.NAMESPACE)

        this_photo = resp['photos'][0]

        # need to "rewind" to open up the PIL.Image of this
        image.seek(0)

        taggedphoto = TaggedPhoto.from_skybio_resp(this_photo,
                                                   pil=Image.open(image))

        return taggedphoto

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
                    to_return.append(self.unqualify(candidate['uid']))

        LOG.debug("got user phone numbers: ", to_return)

        return to_return


class FacebookUserClientBuilder(object):
    def __init__(self, client_id=FB_CLIENT_ID,
                 secret_key=FB_SECRET_KEY,
                 graph_api_constructor=facebook.GraphAPI):
        self._client_id = client_id
        self._secret_key = secret_key
        self._graph_api_constructor = graph_api_constructor

    def client_for_person(self, person, exchange_token):
        return FacebookUserClient(person, exchange_token,
                                  self._client_id,
                                  self._secret_key,
                                  self._graph_api_constructor)


class FacebookUserClient(object):
    def __init__(self, person, auth_token, client_id, secret_key,
                 graph_api_constructor=facebook.GraphAPI):
        self._client = graph_api_constructor(access_token=auth_token)
        self._client_id = client_id
        self._secret_key = secret_key
        self._person = person

        fb_access_token = self._get_auth_token()
        fb_id = self._get_fb_id()

        LOG.debug("Got an access_token and id: ", fb_access_token, fb_id)
        # self._person.update(set__fb_access_token=fb_access_token,
        #                     set__fb_id=fb_id)

        self._person.fb_access_token = fb_access_token
        self._person.fb_id = fb_id

        self._person.save()

    def _get_fb_id(self):
        resp = self._client.request("/me")

        return resp["id"]

    def _get_auth_token(self):
        resp = self._client.extend_access_token(self._client_id,
                                                self._secret_key)
        LOG.debug("facebook response: ", resp)

        return resp["access_token"]

    def get_photos(self, limit=3):
        # Looks like we get 20-30ish from the API without going
        # through cursor bullshit. Let's just use those for now
        # SMALL LIMIT FOR TESTING

        resp = self._client.request("{}/photos".format(self._person.fb_id))

        LOG.debug("got photo response: ", resp)
        ret = [TaggedPhoto.from_fb_resp(pic_resp) for pic_resp in resp["data"]]
        return ret[:limit]

    def get_friends(self):
        raise NotImplementedError

# .x and .y appear to correspond to the percentage position of the
# center of the face.

PhotoTag = collections.namedtuple("PhotoTag", ["number", "x", "y",])
ConfidentTag = collections.namedtuple("ConfidentTag", ["tag",
                                                       "confidence",
                                                       "tid"])

class TaggedUsers(object):
    def __init__(self, tag_map, photo=None):
        self._tag_map = tag_map
        self._dummy_photo = photo


    @classmethod
    def from_taggedphoto(cls, taggedphoto):
        tag_list = taggedphoto.tags
        tag_map = {location:list(users) for location, users in
                   itertools.groupby(tag_list, key=lambda tag: (tag.x, tag.y))}

        # Ugly, I'm sorry.
        dummy_tags = [PhotoTag(None, key[0], key[1]) for key in sorted(tag_map)]
        dummy_photo = TaggedPhoto(taggedphoto.url, dummy_tags, taggedphoto.pil)

        return cls(tag_map, dummy_photo)

    def count(self):
        return len(self._tag_map)

    def get_cutouts_and_users(self):
        # Note that we rely on the *ordering* of the tags in
        # dummy_tags here. Specifically, we assume that the tags are
        # ordered from left-to-right so that we match them with people
        # correctly when we zip them together. This should be okay
        # because we're the ones who set up dummy_photo.

        # Also, if we want this to work as it should (ordered by
        # confidence), we need to do that when we build the initial
        # TaggedPhoto

        # THIS IS NOT A GOOD NAME FOR THIS BECAUSE WE REALLY JUST
        # RETURN THE PHONE NUMBER
        cutouts = self._dummy_photo.get_face_cutouts()
        people = [people for place, people in sorted(self._tag_map.items())]
        return zip(cutouts, people)


class TaggedPhoto(object):
    # NOTE THAT WE AREN'T GOING THROUGH ANY OF THIS "PAGING" BULLSHIT
    # AND THAT MIGHT FUCK US UP
    CROP_PORTION_WIDTH = .05
    CROP_PORTION_HEIGHT = .05

    TAG_MARGIN = 1

    def __init__(self, url=None, tags=None, pil=None):
        self.url = url
        self.tags = tags
        self.pil = pil

    def __repr__(self):
        FMT = 'TaggedPhoto(url="{}", tags=[{}], pil={})'

        return FMT.format(self.url,
                          ",".join([str(x) for x in self.tags]),
                          self.pil)

    @classmethod
    def from_fb_resp(cls, fb_resp, pil=None):
        url = fb_resp["source"]
        tags = []
        for resp in fb_resp['tags']['data']:
            # This will be None if no person is in our db
            try:
                person = Person.objects(fb_id=resp['id']).first()
                number = person.number if person else None
                tags.append(PhotoTag(number, float(resp["x"]),
                                     float(resp["y"])))
            except KeyError:
                pass

        return TaggedPhoto(url, tags, pil)


    @classmethod
    def from_skybio_resp(cls, skybio_resp, pil=None):
        # We have two different kinds of uids running around here -- that's bad

        url = skybio_resp["url"]
        phototags = []

        for tag in skybio_resp['tags']:
            LOG.debug("processing tag: ", tag)

            x = float(tag['center']['x'])
            y = float(tag['center']['y'])

            # We need to order the tags by confidence when we drop
            # them in, or else they'll come out wrong when we display
            # them for 'confirmation'

            for uid in sorted(tag['uids'],
                              key=lambda el: el['confidence'],
                              reverse=True):
                number = SkyClient.unqualify(uid['uid'])
                phototags.append(PhotoTag(number, x, y))

        photo = TaggedPhoto(url, phototags, pil)

        return photo


    def tag_matches(self, tag):
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

            LOG.debug("image width:", width_px)
            LOG.debug("image height:", height_px)

            LOG.debug("crop width: ", crop_width_px)
            LOG.debug("crop height: ", crop_height_px)


            ret = []
            for tag in self.tags:
                # .x and .y are percentage offsets
                abs_x = (tag.x / 100) * width_px
                abs_y = (tag.y / 100) * height_px

                LOG.debug("tag: ", tag)
                LOG.debug("abs_x:", abs_x)
                LOG.debug("abs_y:", abs_y)

                # Errors if it hits floats
                to_crop = (int(abs_x - crop_width_px),
                           int(abs_y - crop_height_px),
                           int(abs_x + crop_width_px),
                           int(abs_y + crop_height_px))

                ret.append(self.pil.crop(to_crop))

            return ret

class FileUploadManager(object):
    UPLOAD_DIR = os.path.join(".", "uploads")
    MAX_SIZE_MB = 2
    IMG_FMT = "{}.jpg"

    def __init__(self, upload_dir=UPLOAD_DIR, max_size_mb=MAX_SIZE_MB):
        self.upload_dir = upload_dir
        self._max_size_mb = max_size_mb

    def _build_path(self, img_name):
        return self.IMG_FMT.format(os.path.join(self.upload_dir, img_name))

    def resize_to_max(self, image):
        raise NotImplementedError

    def build_temp_file(self, image):
        hashed_image = hashlib.md5(image.tostring()).hexdigest()
        image.save(self._build_path(hashed_image))

        return hashed_image

    def image_exists(self, identifier):
        path = self._build_path(identifier)

        LOG.debug("checking path: ", path)

        return os.path.isfile(path)

    def path_from_file_hash(self, hashed_image):
        return self._build_path(hashed_image)
