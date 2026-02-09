PYTHON ?= python3
PYTHONPATH ?= src

.PHONY: setup test run format

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install -U pip
	. .venv/bin/activate && pip install -e .

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest

run:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m recokr_ocr_parser --input $(INPUT) --output $(OUTPUT)
