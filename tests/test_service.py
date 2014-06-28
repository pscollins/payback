import unittest
import tempfile

from os.path import join as pjoin

from service.server import app
from utils import easylogger

LOG = easylogger.LOG


class TestService(unittest.TestCase):
    RESOURCES = "resources"
    FACE1 = pjoin("tests", RESOURCES, "face1.jpg")
    FACE2 = pjoin("tests", RESOURCES, "face2.jpg")

    SUCCESS_CODE = "SUCCESS"


    def setUp(self):
        app.config["TESTING"] = True
        app.config["DATABASE"] = tempfile.mkstemp()
        self.app = app.test_client()


    def test_empty_get(self):
        with self.assertRaises(AttributeError):
                self.app.get("/")


    def test_upload_file(self):
        with open(self.FACE1, "rb") as f:
            my_resp = self.app.post(
                "/",
                # content_type="image/jpeg",
                data={
                    "file": f,
                })

            for el in my_resp.response:
                self.assertEqual(el, self.SUCCESS_CODE)



if __name__ == "__main__":
    unittest.main()
