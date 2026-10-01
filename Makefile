PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest
RUFF := .venv/bin/ruff
APP := .venv/bin/rr

.PHONY: help setup install test lint format check run clean

help:
	@echo "Role Radar"
	@echo
	@echo "  make setup    Create venv and install dev dependencies"
	@echo "  make install  Install/update dependencies"
	@echo "  make test     Run tests"
	@echo "  make lint     Run Ruff"
	@echo "  make format   Format Python code"
	@echo "  make check    Run lint + tests"
	@echo "  make run      Run Role Radar"
	@echo "  make clean    Remove generated files"

setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e '.[dev]'

install:
	$(PYTHON) -m pip install -e '.[dev]'

test:
	$(PYTEST)

lint:
	$(RUFF) check .

format:
	$(RUFF) format .
	$(RUFF) check . --fix

check: lint test

run:
	$(APP) run


clean:
	rm -rf build dist .pytest_cache .ruff_cache htmlcov
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
