import unittest
import mock
import json
import service.models
import logging

from engine import engine
from photos_response import TEST_RESPONSE
from photos_for_tags import SMALL_PHOTO
from utils.easylogger import log_at


mock_models = mock.create_autospec(service.models)

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

    TEST_PERSON_INFO = {
        "name": "Foo Bar",
        "number": "blahblah",
        "vm_auth_token": "foobar"
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

        self.test_person = mock_models.Person(**self.TEST_PERSON_INFO)

        self.fb_client = engine.FacebookUserClient(self.test_person,
                                                   self.TEST_ACCESS_TOKEN,
                                                   self.TEST_CLIENT_ID,
                                                   self.TEST_SECRET_KEY,
                                                   mock_graph_api)

        self.addCleanup(self.fb_client._client.reset_mock)

    def tearDown(self):
        self.fb_client._client.reset_mock()
        self.test_person.reset_mock()

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

    def test_from_fb_resp(self):
        # self._test_tag_no_person()
        self._test_person_found()
        self._test_person_not_found()

    @mock.patch.object("engine.Person.objects")
    def _test_person_found(self, mocked_person_objects):
        mocked_person_objects.return_value.first.return_value = "5555555555"
        tagged_photo = engine.TaggedPhoto.from_fb_resp(self.TEST_PHOTO)

        self.assertEqual(tagged_photo.url, "my_picture_url")
        tags = tagged_photo.tags

        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].number, "5555555555")
        self.assertEqual(tags[0].x, 33.33)
        self.assertEqual(tags[0].y, 66.66)

    @mock.patch.object("engine.Person.objects")
    def _test_person_not_found(self, mocked_person_objects):
        mocked_person_objects.return_value.first.return_value = None

        tagged_photo = engine.TaggedPhoto.from_fb_resp(self.TEST_PHOTO)

        self.assertEqual(tagged_photo.url, "my_picture_url")
        tags = tagged_photo.tags

        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].number, "5555555555")
        self.assertEqual(tags[0].x, 33.33)
        self.assertEqual(tags[0].y, 66.66)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
