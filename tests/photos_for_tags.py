# pylint: skip-file
SMALL_PHOTO = r'''{
      "id": "293721707474968",
      "from": {
        "id": "296581170522355",
        "name": "Kash Masud"
      },
      "picture": "https://scontent-b.xx.fbcdn.net/hphotos-xfp1/t1.0-9/p130x130/10489756_293721707474968_2424141139356918233_n.jpg",
      "source": "my_picture_url",
      "height": 720,
      "width": 720,
      "images": [
      ],
      "link": "https://www.facebook.com/photo.php?fbid=293721707474968&set=p.293721707474968&type=1",
      "icon": "https://fbstatic-a.akamaihd.net/rsrc.php/v2/yz/r/StEh3RhPvjk.gif",
      "tags": {
        "data": [
          {
            "id": "12345",
            "name": "Patrick Collins",
            "created_time": "2014-06-29T22:00:36+0000",
            "x": 33.33,
            "y": 66.66
          },
          {
            "id": "6789",
            "name": "Foo Bar",
            "created_time": "2014-06-29T22:00:36+0000"
          }
        ],
        "paging": {
          "cursors": {
            "before": "Mjk2NTgxMTcwNTIyMzU1",
            "after": "MTAyMDI2NTgyNDU5NjIyNjQ="
          }
        }
      },
      "comments": {
        "data": [
        ],
        "paging": {
          "cursors": {
            "before": "MTAxNTIxNjI2ODgyODIwNTA=",
            "after": "MTAyMDM5MDE5MDcyNTU2MjI="
          }
        }
      }
    }
'''

# Some weirdness trying to use relative paths here, so you need to run
# the test via "make test" to load this right.
VALID_SMALL_PHOTO = {
    'location': 'tests/test_photo.jpg',
    'facebook_json':  r'''
    {
      "source": "my_picture_url",
      "height": 720,
      "width": 720,
      "images": [
      ],
      "tags": {
        "data": [
          {
            "id": "12345",
            "name": "Patrick Collins",
            "created_time": "2014-06-29T22:00:36+0000",
            "x": 33.333335876465,
            "y": 58.911109924316
          }
        ]
      }
    }
    '''
}
