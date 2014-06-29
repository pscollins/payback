#!/usr/bin/env python

from sklearn import preprocessing, svm, cross_validation, metrics
import cv2
import glob
import numpy as np
from scipy import misc
import cPickle

face_cascade = cv2.CascadeClassifier('../engine/haarcascades/haarcascade_frontalface_alt_tree.xml')
face_size = (64, 64)

# get training examples
ps = glob.glob('individual/*/*.jpg')
labels = []
ys = np.empty(len(ps))
xs = np.empty((len(ps), np.prod(face_size)))
for i, p in enumerate(ps):
    n = p.split('/')[1]
    if not n in labels: 
        labels.append(n)

    img = cv2.imread(p)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray)

    print i, p, len(faces)
    if len(faces) == 0:
        continue

    x, y, w, h = max(faces, key=lambda (x,y,w,h): w*h)

    xs[i] = misc.imresize(gray[y:y+h, x:x+w], face_size).reshape(-1)
    ys[i] = labels.index(n)

# save dataset
np.save('xs', xs)
np.save('ys', ys)

cv3 = cross_validation.StratifiedKFold(ys, 3)
scaler = preprocessing.StandardScaler()
clf = svm.SVC(probability=True)

for train, test in cv3:
    # standard scalar
    u = scaler.fit_transform(xs[train])
    v = scaler.transform(xs[test])
    
    #u, v = x[train], x[test]
    clf.fit(u, ys[train])
    z = clf.predict(v)
    roc = []
    for j in xrange(len(labels)):
        roc.append(metrics.roc_auc_score(ys[test]==j, z==j))
    print np.mean(roc), roc
    print metrics.classification_report(ys[test], z)


cPickle.dump(clf, open('svm.pkl', 'wb'))
