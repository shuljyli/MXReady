# MXReady 开发命令入口（Linux / macOS）
# 用法: make install | dev | test | lint | build | frontend | clean
PYTHON ?= python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff

.PHONY: install dev test lint build frontend clean

install:
	python3 -m venv $(VENV)
	$(PIP) install -e ".[dev]"
	cd frontend && npm ci

dev:
	$(VENV)/bin/uvicorn mxready.app:create_app --factory --reload --port 8000

test:
	$(PYTEST)

lint:
	$(RUFF) check backend runner scripts tests

build:
	cd frontend && npm run build

frontend:
	cd frontend && npm run dev

clean:
	rm -rf .pytest-temp
