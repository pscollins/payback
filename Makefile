

.PHONY: make-env
make-env:
	virtualenv -p python2.7 venv

start-env:
	. venv/bin/activate

test:
	. activate
	coverage run --branch tests/tests.py
	coverage report --omit=venv/*,engine/facebook*
