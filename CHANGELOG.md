# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Standard Open Source community files (`LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`).
- Comprehensive documentation in `docs/` (`architecture.md`, `providers.md`, `development.md`, `finops-engine.md`).
- Makefile for developer experience improvements (`install`, `test`, `lint`, `format`, `docker-build`, etc.).
- Examples folder containing `claude_desktop_config.json`, `docker-compose.yml`, and `sample_queries.md`.
- Basic GitHub Actions CI workflow for linting, testing, and building (`python-ci.yml`).
- `.env.example` file and environment variable validation on startup.
- Python code quality tooling (`ruff`, `black`, `mypy`).
- Structured logging with trace tracking for MCP requests.

## [1.3.0] - Initial Core Features
### Added
- Production-grade multi-cloud FinOps MCP backend supporting AWS, GCP, and Azure.
- Integration endpoints for Claude Desktop.
- Core orchestrator and cloud resource collectors.
