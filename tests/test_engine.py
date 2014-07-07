import unittest
import mock
import json

from engine import engine
from test_photos_response import TEST_RESPONSE
import service.models

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


    def test_get_photos(self):
        test_resp = json.loads(TEST_RESPONSE)






if __name__ == '__main__':
    unittest.main()
