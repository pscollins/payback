

.PHONY: make-env
make-env:
	virtualenv-2.7 venv

start-env:
	source venv/bin/activate
