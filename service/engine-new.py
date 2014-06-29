#!/usr/bin/env python

from scipy import misc
import numpy as np
import cv2


face_cascade = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_alt_tree.xml')
face_size = (64, 64)

def find_faces(image_buffer):
    img = cv2.imdecode(image_buffer)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray)

    for x, y, w, h in faces:
        yield gray[y:y+h, x:x+w]


def recognize(model, faces):
    fs = np.empty((len(faces), prod(face_size))
    for i, face in enumerate(faces):
        fs[i] = misc.imresize(face, face_size).reshape(1, -1)
    ps = model.predict_proba()
    return ps
