PYTHON = .venv/bin/python

.PHONY: setup venv install run

setup: venv install

venv:
	python3 -m venv .venv

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py $(ARGS)
