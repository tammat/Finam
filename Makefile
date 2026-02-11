SHELL := /bin/bash

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

GRPC_OUT := finam_bot/grpc_api
TMP_DIR := .grpc_tmp

FINAM_PROTO_REPO := https://github.com/FinamWeb/finam-trade-api.git
GOOGLE_PROTO_REPO := https://github.com/googleapis/googleapis.git

PROTO_SRC := $(TMP_DIR)/finam-trade-api/proto
PROTO_GOOGLE := $(TMP_DIR)/googleapis

PROTO_FILES := $(shell find $(PROTO_SRC)/grpc/tradeapi/v1 -name "*.proto" 2>/dev/null | grep -v "/metrics/")

.PHONY: help venv install clean grpc grpc-clean test lint run

help:
	@echo "Available commands:"
	@echo "  make venv        - create virtualenv"
	@echo "  make install     - install requirements"
	@echo "  make grpc        - regenerate grpc stubs"
	@echo "  make grpc-clean  - remove generated grpc"
	@echo "  make test        - run pytest"
	@echo "  make clean       - remove tmp + cache"
	@echo "  make run         - run main app"

venv:
	python3 -m venv .venv
	$(PIP) install --upgrade pip

install:
	$(PIP) install -r requirements.txt

grpc:
	@echo "=== CLEAN OLD GENERATED ==="
	rm -rf $(GRPC_OUT)
	rm -rf $(TMP_DIR)

	@echo "=== CLONE PROTO REPOS ==="
	mkdir -p $(TMP_DIR)
	cd $(TMP_DIR) && \
	git clone --depth 1 $(FINAM_PROTO_REPO) && \
	git clone --depth 1 $(GOOGLE_PROTO_REPO)

	@echo "=== GENERATE STUBS ==="
	mkdir -p $(GRPC_OUT)
	$(PYTHON) -m grpc_tools.protoc \
		-I=$(PROTO_SRC) \
		-I=$(PROTO_GOOGLE) \
		--python_out=$(GRPC_OUT) \
		--grpc_python_out=$(GRPC_OUT) \
		$$(find $(PROTO_SRC)/grpc/tradeapi/v1 -name "*.proto" | grep -v "/metrics/")

	@echo "=== ADD __init__.py FILES ==="
	find $(GRPC_OUT) -type d -exec touch {}/__init__.py \;

	@echo "=== FIX IMPORTS (grpc namespace) ==="
	find $(GRPC_OUT) -type f -name "*_pb2*.py" -exec \
	sed -i '' 's/from grpc.tradeapi/from finam_bot.grpc_api.grpc.tradeapi/g' {} \;

	@echo "=== CLEAN TMP ==="
	rm -rf $(TMP_DIR)

	@echo "=== GRPC READY ==="

grpc-clean:
	rm -rf $(GRPC_OUT)

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m flake8 finam_bot

run:
	$(PYTHON) -m finam_bot.app

clean:
	rm -rf $(TMP_DIR)
	rm -rf .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +