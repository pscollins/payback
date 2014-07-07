# pylint: skip-file
FACES_DETECT_TAG = {
    "tid" : "test_tid",
    "recognizable" : "true",
    "confirmed" : "false",
    "manual" : "false",
    "width" : 30.67,
    "height" : 28.12,
    "center" : { "x" : 56.53, "y" : 40.83},
    "eye_left" : { "x" : 66.93, "y" : 33.99},
    "eye_right" : { "x" : 51.73, "y" : 33.99},
    "yaw" : -16,
    "roll" : 0,
    "pitch" : 0,
    "attributes" : {
        "face" : { "value" : "true", "confidence" : 82 },
        "gender" : { "value" : "female", "confidence" : 80 },
        "glasses":{"value" : "true", "confidence" : 100},
        "dark_glasses":{"value" : "true", "confidence" : 72},
        "smiling":{"value" : "false", "confidence" : 35}
    }
}

FACES_DETECT_NO_TAGS = {
    "photos" : [
        {
            "url" : "http://tinyurl.com/673cksr",
            "pid" : "F@0c95576847e9cd7123f1e304476b59ae_59ec9bb2ad15f",
            "width" : 375,
            "height" : 409,
            "tags" : [
            ]
        }
    ],
    "status" : "success",
    "usage" : {
        "used" : 1,
        "remaining" : 99,
        "limit" : 100,
        "reset_time_text" : "Fri, 21 September 2012 12:57:19 +0000",
        "reset_time" : 1348232239
        }
}

CONFIDENT_UID = {
    "uid" : "confident@TESTNS",
    "confidence" : 98
}

UNCONFIDENT_UID = {
    "uid" : "unconfident@TESTNS",
    "confidence" : 2
}


FACES_RECOGNIZE_TAG = {
    "tid" : "testing_tid",
    "recognizable" : "true",
    "uids" : [
    ],
    "threshold" : 50,
    "label" : "",
    "confirmed" : "true",
    "manual" : "false",
    "width" :27.73,
    "height" : 37.03,
    "center" : { "x" : 64.75, "y" : 48.24 },
    "eye_left" : { "x" : 66.5, "y" : 39.24 },
    "eye_right" : { "x" : 53.12, "y" : 34.55 },
    "yaw" : 45,
    "roll" : 15,
    "pitch" : 0,
    "attributes" : {
        "face" : { "value" : "true", "confidence" : 71 }
    }
}

FACES_RECOGNIZE_NO_TAGS = {
    "photos" : [
        {
            "url" : "http://tinyurl.com/673cksa",
            "pid" : "F@053a763a06d9d578430b9f2d06c686bb_f0bf798c4c4e8",
            "width" : 1024,
            "height" : 767,
            "tags" : [
            ]
        }
    ],
    "status" : "success",
    "usage" : {
        "used" : 1,
        "remaining" : 99,
        "limit" : 100,
        "reset_time_text" : "Fri, 22 September 2012 12:57:19 +0000",
        "reset_time" : 1348232239
    }
}
