TEST_OMIT=venv/*,engine/facebook*,tests/*,utils/*


.PHONY: make-env
make-env:
	virtualenv -p python2.7 venv

start-env:
	. venv/bin/activate

test:
	. ./activate
	coverage run --branch tests/test_engine.py
	coverage report --omit=$(TEST_OMIT)

test-html:
	. ./activate
	coverage run --branch tests/test_engine.py
	coverage html --omit=$(TEST_OMIT) --rcfile=.coveragerc
