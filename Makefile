

.PHONY: make-env
make-env:
	virtualenv-2.7 venv

start-env:
	. venv/bin/activate
