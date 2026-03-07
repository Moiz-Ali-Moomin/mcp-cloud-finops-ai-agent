# Development Guide

Welcome! This document will guide you through getting the project running locally and explaining the core development loop.

## Setup Environment

Ensure you have Python 3.11 or greater installed. We recommend using a virtual environment.

```sh
# Clone the repository
git clone https://github.com/Moiz-Ali-Moomin/mcp-cloud-finops-ai-agent.git
cd mcp-cloud-finops-ai-agent

# Set up a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the dependencies along with dev/test tools
make install
```

## Adding Cloud Credentials

Copy the included `.env.example` to `.env` and fill out your local test credentials.

```sh
cp .env.example .env
```

Ensure you export these before running the server locally.

## Running Locally

To start the MCP server using `stdio` (the standard way Claude Desktop communicates with it):

```sh
make dev
```

If you wish to test the server directly via HTTP/SSE instead of standard I/O, you can execute the module directly (if configured in `api/`):

```sh
python -m opsyield.api.main
```

## Running Tests

We use `pytest` for all unit and integration testing. Mocks are heavily utilized to prevent actual API calls during CI/CD.

```sh
make test
```

## Linting and Code Formatting

We maintain a strict code style using `black`, and static analysis via `ruff` and `mypy`.

To check formatting:
```sh
make lint
```

To automatically format files:
```sh
make format
```

## Building the Docker Image

To ensure your code functions properly in containerized environments:

```sh
make docker-build
```

You can run the generated image locally via:

```sh
make docker-run
```
