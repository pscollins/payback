import unittest
import mock

import engine
import service.models

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

    TEST_PERSON = service.models.Person(
        name="Foo Bar",
        number="blahblah",
        vm_auth_token="foobar"
    )

    @mock.patch.multiple(engine.facebook.GraphAPI,
                         request=TEST_ME,
                         extend_access_token=TEST_AUTH_TOKEN)
    # @mock.patch.object("facebook.GraphAPI", autospec=True)
    @mock.patch.object(service.models.Person, "save")
    def setUp(self, mock_save, mock_request, mock_extend_access_token):
        self.fb_client = engine.FacebookUserClient(self.TEST_PERSON,
                                                   self.TEST_ACCESS_TOKEN,
                                                   self.TEST_CLIENT_ID,
                                                   self.TEST_SECRET_KEY)
        mock_save.assert_called_once_with()
        # mock_graph_api.assert_called_once_with(self.TEST_ACCESS_TOKEN)
        mock_request.assert_called_once_with("/me")
        mock_extend_access_token.assert_called_once_with(self.TEST_CLIENT_ID,
                                                         self.TEST_SECRET_KEY)

        return fb_client

    def test_init(self):
        # fb_client = self._build_client()
        self.assertEqual(self.fb_client._person.fb_access_token,
                         "CAAIE..")
        self.assertEqual(self.fb_client._person.fb_id,
                         "6666666666666666")






if __name__ == '__main__':
    unittest.main()
