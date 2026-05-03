PYTHON ?= python3
VENV_PYTHON = .venv/bin/python

.PHONY: setup models analyze analyze-llm test api

setup:
	./scripts/setup_local.sh

models:
	./scripts/pull_models.sh

analyze:
	./scripts/analyze_export.sh

analyze-llm:
	WITH_LLM=1 ./scripts/analyze_export.sh

test:
	PYTHONPATH=src $(VENV_PYTHON) -m pytest -q

api:
	PYTHONPATH=src $(VENV_PYTHON) -m uvicorn social_graph_service.api:app --reload
