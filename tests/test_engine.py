#pylint: disable=protected-access,method-hidden

import unittest
import mock
import json
import service.models
import logging
import os.path
import copy
import hashlib

from PIL import Image

from payback.engine import engine
from photos_response import TEST_RESPONSE
from photos_for_tags import SMALL_PHOTO, VALID_SMALL_PHOTO
from payback.utils.easylogger import log_at, LOG
from skybio_responses import FACES_DETECT_TAG, FACES_DETECT_NO_TAGS,\
    FACES_RECOGNIZE_NO_TAGS, FACES_RECOGNIZE_TAG, CONFIDENT_UID,\
    UNCONFIDENT_UID


mock_models = mock.create_autospec(service.models)

TEST_PERSON_INFO = {
    "name": "Foo Bar",
    "number": "blahblah",
    "vm_auth_token": "foobar"
}


class TestSkyClient(unittest.TestCase):
    TEST_CLIENT_ID = "000000000"
    TEST_SECRET_KEY = "111111111"

    TEST_NAMESPACE = "TESTNS"

    @mock.patch("payback.engine.engine.face_client.FaceClient")
    def setUp(self, mock_face_client):
        self.client = engine.SkyClient(self.TEST_CLIENT_ID,
                                       self.TEST_SECRET_KEY,
                                       mock_face_client)
        self.client.NAMESPACE = self.TEST_NAMESPACE
        mock_face_client.assert_called_once_with(self.TEST_CLIENT_ID,
                                                 self.TEST_SECRET_KEY)

        # this is okay because we don't save() the person
        self.person = service.models.Person(**TEST_PERSON_INFO)

    def tearDown(self):
        self.client.client.reset_mock()

    @log_at(logging.INFO)
    def test__qualify(self):
        TO_QUALIFY = "foobar"

        self.assertEqual("foobar@TESTNS",
                         self.client._qualify(TO_QUALIFY))

    @log_at(logging.INFO)
    def test__unqualify(self):
        TO_UNQUALIFY = "foobar@bazbat"

        self.assertEqual("foobar",
                         self.client._unqualify(TO_UNQUALIFY))

    @log_at(logging.INFO)
    def test__train_person_on_tids(self):
        tids = ["1", "1", "2", "3"]

        self.client._train_person_on_tids(self.person, tids)

        self.client.client.tags_save.assert_called_once_with(
            tids="1,3,2",
            uid="blahblah@TESTNS",
            label="Foo Bar")
        self.client.client.faces_train.assert_called_once_with(
            "blahblah@TESTNS")

    @log_at(logging.INFO)
    def test_train_for_user_fails(self):
        response = copy.deepcopy(FACES_DETECT_NO_TAGS)
        self.client.client.faces_detect.return_value = response

        with self.assertRaises(engine.TooFewFacesError):
            self.client.train_for_user(self.person, ['not an image'])

        response['photos'][0]['tags'] = [FACES_DETECT_TAG, FACES_DETECT_TAG]
        # LOG.debug("new response:", response)
        # self.client.client.faces_detect.return_value = response

        with self.assertRaises(engine.TooManyFacesError):
            self.client.train_for_user(self.person, ['not an image'])

    @log_at(logging.INFO)
    def test__get_tids_to_train_for_user(self):
        response = copy.deepcopy(FACES_DETECT_NO_TAGS)
        response['photos'][0]['tags'] = [FACES_DETECT_TAG]

        self.client.client.faces_detect.return_value = response

        tids = self.client._get_tids_to_train_for_user(
            ['not an image', 'still not an image'])

        self.assertEqual(tids, ['test_tid', 'test_tid'])

    def test_train_for_user_passes(self):
        response = copy.deepcopy(FACES_DETECT_NO_TAGS)
        response['photos'][0]['tags'] = [FACES_DETECT_TAG]

        self.client.client.faces_detect.return_value = response

        self.client._train_person_on_tids = mock.MagicMock()

        self.client.train_for_user(self.person, ['not an image'])

        self.client._train_person_on_tids.assert_called_once_with(
            self.person, ['test_tid'])

    @log_at(logging.INFO)
    def test__find_matching_original(self):
        originals = [
            engine.TaggedPhoto("abc"),
            engine.TaggedPhoto("123")
        ]

        with self.assertRaises(engine.UnrecognizedUserError):
            self.client._find_matching_original(originals, "def")

        self.assertEqual(self.client._find_matching_original(originals, "abc"),
                         originals[0])

    @log_at(logging.INFO)
    def test__find_best_uid_from_tag_json(self):
        tag = copy.deepcopy(FACES_RECOGNIZE_TAG)

        self.assertEqual(self.client._find_best_uid_from_tag_json(tag),
                         (None, None))

        tag['uids'] = [UNCONFIDENT_UID, CONFIDENT_UID]

        self.assertEqual(self.client._find_best_uid_from_tag_json(tag),
                         ("confident@TESTNS", 98))

    @log_at(logging.INFO)
    def test__update_tids(self):
        tids = []

        self.client._update_tids(tids, [])

        self.assertEqual(tids, [])

        self.client._update_tids(tids, [engine.ConfidentTag(None, 0, "test1"),
                                        engine.ConfidentTag(None, 90, "test2")])

        self.assertEqual(tids, ["test2"])

    @log_at(logging.INFO)
    def test__recognize_for_person(self):
        self.client._recognize_for_person(self.person, foo="bar")

        self.client.client.faces_recognize.assert_called_once_with(
            "blahblah@TESTNS", foo="bar")

    @log_at(logging.INFO)
    def test__update_possible_tags(self):
        tag = copy.deepcopy(FACES_RECOGNIZE_TAG)
        self.client._find_best_uid_from_tag_json = mock.MagicMock(
            return_value=("blahblah@TESTNS", 25))

        original = mock.MagicMock(autospec=engine.TaggedPhoto)
        original.tag_matches.return_value = False

        possible_tags = []

        self.client._update_possible_tags(possible_tags, tag, self.person,
                                          original)

        self.assertEqual(possible_tags, [])

        original.tag_matches.return_value = True

        self.client._update_possible_tags(possible_tags, tag, self.person,
                                          original)

        self.assertEqual(possible_tags, [engine.ConfidentTag(
            engine.PhotoTag("blahblah", 64.75, 48.24),
            25,
            "testing_tid")])

    @mock.patch("payback.engine.engine.Image", autospec=True)
    @mock.patch("payback.engine.engine.TaggedPhoto", autospec=True)
    def test_taggedphoto_from_image(self, mock_taggedphoto, mock_image):
        self.client.client.faces_recognize = mock.MagicMock(
            return_value={'photos':["foo"]}, autospec=True)
        mock_image.open.return_value = "not a pil"

        self.client.taggedphoto_from_image("not an image")


        self.client.client.faces_recognize.assert_called_once_with(
            "all", file="not an image", namespace=self.client.NAMESPACE)
        mock_image.open.assert_called_once_with("not an image")
        mock_taggedphoto.from_skybio_resp.assert_called_once_with(
            "foo", pil="not a pil")


    def test__find_tids_for_facebook(self):
        resp = copy.deepcopy(FACES_RECOGNIZE_NO_TAGS)
        resp['photos'][0]['tags'] = [copy.deepcopy(FACES_RECOGNIZE_TAG)]
        resp['photos'][0]['tags'][0]['uids'] = [{
            'uid': 'blahblah@TESTNS', 'confidence': 15
        }]

        LOG.debug("response for testing: ", resp)
        original_photo = mock.MagicMock()
        original_photo.tag_matches.return_value = True

        self.client._find_matching_original = mock.MagicMock(
            return_value=original_photo)

        tids = self.client._find_tids_for_facebook(self.person,
                                                   [original_photo],
                                                   resp)

        self.assertEqual(tids, ["testing_tid"])

    def test_train_for_facebook(self):
        self.client._recognize_for_person = mock.MagicMock(
            return_value="some response")
        self.client._find_tids_for_facebook = mock.MagicMock(
            return_value=[])
        self.client._train_person_on_tids = mock.MagicMock()

        original_photos = [
            engine.TaggedPhoto('1'),
            engine.TaggedPhoto('2'),
            engine.TaggedPhoto('3')
        ]

        self.client.train_for_facebook(self.person, original_photos)

        self.client._recognize_for_person.assert_called_once_with(
            self.person, urls="1,2,3")
        self.client._find_tids_for_facebook.assert_called_once_with(
            self.person, original_photos, "some response")
        self.assertFalse(self.client._train_person_on_tids.called)

        self.client._find_tids_for_facebook.return_value = ['4', '5', '6']

        self.client.train_for_facebook(self.person, original_photos)

        self.client._train_person_on_tids.assert_called_once_with(
            self.person, ['4', '5', '6'])




class TestFacebookUserClient(unittest.TestCase):
    TEST_CLIENT_ID = "000000000"
    TEST_SECRET_KEY = "111111111"
    TEST_ACCESS_TOKEN = "azertyqwerty"

    TEST_ME = {
        "id": "6666666666666666",
        "first_name": "Patrick",
        "gender": "male",
        "last_name": "Collins",
        "link": "http://www.facebook.com/33333333333333",
        "locale": "en_US",
        "name": "Patrick Collins",
        "timezone": -5,
        "updated_time": "2013-12-30T21:05:19+0000",
        "verified": "true"
    }

    TEST_AUTH_TOKEN = {
        "access_token": "CAAIE..",
        "expires": "5132136"
    }

    MOCK_GRAPH_API_FOR_INIT = {
        "return_value.request.return_value": TEST_ME,
        "return_value.extend_access_token.return_value": TEST_AUTH_TOKEN
    }

    # def setUp(self):
        # self.test_person = mock_models.Person(**self.TEST_PERSON_INFO)

    # @mock.patch.multiple("engine.facebook.GraphAPI", request=TEST_ME,
    # # @mock.patch.object(engine.facebook.GraphAPI,
    #                      extend_access_token=TEST_AUTH_TOKEN)
    @mock.patch("engine.facebook.GraphAPI", **MOCK_GRAPH_API_FOR_INIT)
    def setUp(self, mock_graph_api):
        # mock_graph_api.return_value.request.return_value = {
        #     "/me": self.TEST_ME,
        # }
        # mock_graph_api.return_value.\
            # extend_access_token.return_value = self.TEST_AUTH_TOKEN

        self.test_person = mock_models.Person(**TEST_PERSON_INFO)

        self.fb_client = engine.FacebookUserClient(self.test_person,
                                                   self.TEST_ACCESS_TOKEN,
                                                   self.TEST_CLIENT_ID,
                                                   self.TEST_SECRET_KEY,
                                                   mock_graph_api)

        self.addCleanup(self.fb_client._client.reset_mock)

    def tearDown(self):
        self.fb_client._client.reset_mock()
        self.test_person.reset_mock()

    @mock.patch("engine.facebook.GraphAPI", **MOCK_GRAPH_API_FOR_INIT)
    def test_builder(self, mock_graph_api):
        builder = engine.FacebookUserClientBuilder(self.TEST_CLIENT_ID,
                                                   self.TEST_SECRET_KEY,
                                                   mock_graph_api)

        client = builder.client_for_person(self.test_person,
                                           self.TEST_ACCESS_TOKEN)

        for attr in ['_client_id', '_secret_key']:
            self.assertEqual(getattr(client, attr),
                             getattr(self.fb_client, attr))

        # Can't test the _person because it's a mock

    def test_init(self):
        self.fb_client._person.save.assert_called_once_with()

        self.fb_client._client.request.assert_called_once_with("/me")
        self.fb_client._client.extend_access_token.assert_called_once_with(
            self.TEST_CLIENT_ID,
            self.TEST_SECRET_KEY)

        # fb_client = self._build_client()
        self.assertEqual(self.fb_client._person.fb_access_token,
                         "CAAIE..")
        self.assertEqual(self.fb_client._person.fb_id,
                         "6666666666666666")

    @log_at(logging.INFO)
    def test_get_photos(self):
        test_resp = json.loads(TEST_RESPONSE)
        self.fb_client._client.request.return_value = test_resp

        r_lim1 = self.fb_client.get_photos(1)
        r_lim2 = self.fb_client.get_photos(2)
        r_lim3 = self.fb_client.get_photos(3)

        # We test the "meat" of the responses in TaggedPhoto, so let's
        # not worry about them here.
        self.assertEqual(len(r_lim1), 1)
        self.assertEqual(len(r_lim2), 2)
        self.assertEqual(len(r_lim3), 3)


    def test_get_friends(self):
        pass


class TestTaggedPhoto(unittest.TestCase):
    # TEST_PHOTOS = json.loads(photos_response.TEST_RESPONSE)['data']
    TEST_PHOTO = json.loads(SMALL_PHOTO)

    # def test_from_fb_resp(self):
    #     self._test_person_no_position()
    #     self._test_person_found()
    #     self._test_person_not_found()

    @mock.patch("payback.service.models.Person.objects")
    def _build_test_photo(self, mocked_person_objects, photo_json=TEST_PHOTO):
        mocked_person_objects.return_value.\
            first.return_value = service.models.Person(**TEST_PERSON_INFO)
        tagged_photo = engine.TaggedPhoto.from_fb_resp(photo_json)

        return tagged_photo

    def test_person_found(self):
        tagged_photo = self._build_test_photo()
        self.assertEqual(tagged_photo.url, "my_picture_url")
        tags = tagged_photo.tags

        self.assertEqual(tags[0].number, "blahblah")
        self.assertEqual(tags[0].x, 33.33)
        self.assertEqual(tags[0].y, 66.66)

    @mock.patch("payback.service.models.Person.objects")
    def test_person_not_found(self, mocked_person_objects):
        mocked_person_objects.return_value.first.return_value = None

        tagged_photo = engine.TaggedPhoto.from_fb_resp(self.TEST_PHOTO)

        self.assertEqual(tagged_photo.url, "my_picture_url")
        tags = tagged_photo.tags

        self.assertEqual(tags[0].number, None)
        self.assertEqual(tags[0].x, 33.33)
        self.assertEqual(tags[0].y, 66.66)

    @mock.patch("payback.service.models.Person.objects")
    def test_person_no_position(self, mocked_person_objects):
        mocked_person_objects.return_value.first.return_value = None
        tagged_photo = engine.TaggedPhoto.from_fb_resp(self.TEST_PHOTO)

        calls = [mock.call(fb_id="12345"), mock.call().first(),
                 mock.call(fb_id="6789"), mock.call().first()]

        mocked_person_objects.assert_has_calls(calls)

        tags = tagged_photo.tags

        self.assertEqual(len(tags), 1)

    def test_from_skybio_resp(self):
        test_resp = copy.deepcopy(FACES_RECOGNIZE_NO_TAGS)

        def build_correct_tags_for_loc(x, y):
            return [engine.PhotoTag("confident", x, y),
                    engine.PhotoTag("unconfident", x, y)]

        tag1 = copy.deepcopy(FACES_RECOGNIZE_TAG)
        tag2 = copy.deepcopy(FACES_RECOGNIZE_TAG)

        tag1['center']['x'] = 10.0
        tag1['center']['y'] = 15.0

        tag2['center']['x'] = 5.0
        tag2['center']['y'] = 6.0

        tag1['uids'] = [UNCONFIDENT_UID, CONFIDENT_UID]
        tag2['uids'] = [CONFIDENT_UID, UNCONFIDENT_UID]

        test_resp['photos'][0]['tags'] = [tag1, tag2]

        to_test = engine.TaggedPhoto.from_skybio_resp(test_resp['photos'][0])

        self.assertEqual(len(to_test.tags), 4)
        self.assertEqual(to_test.url,"testing_url")

        LOG.debug("to_test.tags: ", to_test.tags)

        self.assertEqual(to_test.tags[:2],
                         build_correct_tags_for_loc(10.0, 15.0))
        self.assertEqual(to_test.tags[2:],
                         build_correct_tags_for_loc(5.0, 6.0))


    def test_tag_matches(self):
        tagged_photo = self._build_test_photo()

        tags = [
            engine.PhotoTag("blahblah", -1, -2),
            engine.PhotoTag("blahblah", 100, 100),
            engine.PhotoTag("nonumber", 33.33, 66.66),
            engine.PhotoTag("blahblah", 33.33, 66.66),
            engine.PhotoTag("blahblah", 32.33, 65.66),
            engine.PhotoTag("blahblah", 34.33, 67.66),
        ]

        do_matches = [tagged_photo.tag_matches(tag) for tag in tags]

        correct_results = [
            False,
            False,
            False,
            True,
            True,
            True
        ]

        for result, correct in zip(do_matches, correct_results):
            self.assertEqual(result, correct)

    def test_face_cutouts_errors(self):
        tagged_photo = self._build_test_photo()

        with self.assertRaises(ValueError):
            tagged_photo.get_face_cutouts()

        tagged_photo.pil = True

        tagged_photo.tags = []

        with self.assertRaises(ValueError):
            tagged_photo.get_face_cutouts()

    def test_face_cutouts(self):
        OUTDIR = "test_cutouts"
        OUTPATH = os.path.join("tests", OUTDIR, "1.jpg")

        photo_json = json.loads(VALID_SMALL_PHOTO['facebook_json'])
        tagged_photo = self._build_test_photo(photo_json=photo_json)
        pil = Image.open(VALID_SMALL_PHOTO['location'])
        tagged_photo.pil = pil
        pil_x, pil_y = pil.size

        face_cutouts = tagged_photo.get_face_cutouts()

        self.assertEqual(len(face_cutouts), 1)

        cutout = face_cutouts[0]

        cutout_x, cutout_y = cutout.size

        self.assertAlmostEqual(cutout_x,
                               tagged_photo.CROP_PORTION_WIDTH * pil_x * 2)
        self.assertAlmostEqual(cutout_y, tagged_photo.CROP_PORTION_HEIGHT * pil_y * 2)

        cutout.save(OUTPATH)

        LOG.info("Saved the test image in", OUTPATH, ". "
                 "You should open it to make sure that it looks okay.")

class TestTaggedUsers(unittest.TestCase):
    TEST_LIST = [
        engine.PhotoTag("5", 5, 5),
        engine.PhotoTag("55", 5, 5),
        engine.PhotoTag("6", 6, 6),
        engine.PhotoTag("66", 6, 6)
    ]

    TEST_PHOTO = engine.TaggedPhoto("foo", TEST_LIST, None)

    def _build_from_taggedphoto(self):
        to_test = engine.TaggedUsers.from_taggedphoto(self.TEST_PHOTO)

        return to_test

    def test_from_taggedphoto(self):
        to_test = self._build_from_taggedphoto()

        self.assertEqual(to_test._tag_map[(5, 5)],
                         self.TEST_LIST[:2])
        self.assertEqual(to_test._tag_map[(6, 6)],
                         self.TEST_LIST[2:])

        dummy_tags = [engine.PhotoTag(None, 5, 5), engine.PhotoTag(None, 6, 6)]
        self.assertEqual(to_test._dummy_photo.tags, dummy_tags)
        self.assertEqual(to_test._dummy_photo.url, "foo")

    def test_get_cutouts_and_users(self):
        # Not testing the cutouts themselves here because that's done
        # elsewhere. It would be good to check that they're paired
        # with the right user, but I'm not going to right now.

        users = self._build_from_taggedphoto()
        users._dummy_photo = mock.MagicMock(autospec=True)
        users._dummy_photo.get_face_cutouts.return_value = [1, 2]

        to_test = users.get_cutouts_and_users()

        users._dummy_photo.get_face_cutouts.assert_called_once_with()

        self.assertEqual(len(to_test), 2)
        self.assertEqual(to_test[0],
                         (1, self.TEST_LIST[:2]))
        self.assertEqual(to_test[1],
                         (2, self.TEST_LIST[2:]))

    def test_count(self):
        to_test = self._build_from_taggedphoto()
        self.assertEqual(to_test.count(), 2)

class TestFileUploadManager(unittest.TestCase):
    TEST_IMAGE = Image.open(VALID_SMALL_PHOTO['location'])
    TEST_HASH = hashlib.md5(TEST_IMAGE.tostring()).hexdigest()

    def setUp(self):
        self.manager = engine.FileUploadManager(upload_dir="./test_uploads")

    def test_init(self):
        self.assertEqual(self.manager.upload_dir, "./test_uploads")

    def test__build_path(self):
        # platform-specific, will break on windows
        self.assertEqual(self.manager._build_path("foo"),
                         "./test_uploads/foo.jpg")

    def test_image_exists(self):
        self.assertTrue(self.manager.image_exists("test_exists"))

    def test_build_tempfile(self):
        # will break on windows
        TEST_PATH = "./test_uploads/{}.jpg".format(self.TEST_HASH)
        LOG.debug("self.TEST_HASH: ", self.TEST_HASH)

        if os.path.isfile(TEST_PATH):
            os.rm(TEST_PATH)

        to_test = self.manager.build_temp_file(self.TEST_IMAGE)

        self.assertEqual(to_test, self.TEST_HASH)

        self.assertTrue(os.path.isfile(TEST_PATH))

        os.rm(TEST_PATH)



def main():
    unittest.main()


if __name__ == '__main__':
    main()
