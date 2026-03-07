.PHONY: install dev test lint format docker-build docker-run help

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies and dev tools"
	@echo "  dev          - Run the MCP server locally (stdio)"
	@echo "  test         - Run unit tests with pytest"
	@echo "  lint         - Run ruff and mypy for linting and type checking"
	@echo "  format       - Run black for code formatting"
	@echo "  docker-build - Build the Docker image"
	@echo "  docker-run   - Run the Docker container"

install:
	pip install -e .[dev]
	pip install pytest ruff black mypy

dev:
	python -m opsyield.api.main

test:
	pytest tests/ -v

lint:
	ruff check .
	mypy opsyield/

format:
	black .

docker-build:
	docker build -t opsyield-mcp .

docker-run:
	docker run --rm -i -e GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-sa.json -v $(PATH_TO_GCP_JSON):/app/gcp-sa.json opsyield-mcp
