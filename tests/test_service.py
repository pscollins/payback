import unittest

from service.server import app

from os.path import join as pjoin



class TestService(unittest.TestCase):
    RESOURCES = "resources"
    FACE1 = pjoin(RESOURCES, "face1.jpg")
    FACE2 = pjoin(RESOURCES, "face2.jpg")

    SUCCESS_CODE = "SUCCESS"


    def setUp(self):
        app.config["TESTING"] = True
        self.app = app.test_client()


    def test_empty_get(self):
        with self.assertRaises(AttributeError):
                self.app.get("/")


    def test_upload_file(self):
        self.assertEqual


if __name__ == "__main__":
    unittest.main()
