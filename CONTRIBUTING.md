# Contributing to OpsYield MCP FinOps Server

First off, thank you for considering contributing to OpsYield! It's people like you that make OpsYield such a great tool for the open-source community.

We welcome all variations of contributions: reporting bugs, suggesting features, adding new cloud providers, fixing typos, and improving docs. 

## Where do I go from here?

### Issue Reporting Guidelines
If you've noticed a bug or have a feature request, please open a GitHub Issue! When reporting a bug, ensure you provide:
- Your environment details (OS, Python version).
- Steps to reproduce the bug.
- Expected vs. actual behavior.
It's generally best if you get confirmation of your bug or approval for your feature request via an Issue before starting to code.

---

## Development Environment Setup

Ensure you have **Python 3.10+** (preferably 3.13) installed.

### Fork & Create a Branch
Fork the OpsYield repository and create a branch with a descriptive name. A good branch name would be (where issue `#325` is the ticket you're working on):
```sh
git checkout -b 325-add-kubernetes-cost-collector
```

### Installing Dependencies
We use a `Makefile` to simplify onboarding. From the root of the project, run:
```sh
make install
```
This installs the package in editable mode along with all `dev` and `test` dependencies.

---

## Code Quality and Workflows

### Code Style Rules
We enforce modern Python standards:
- **Async First**: Use `asyncio` wherever doing network/disk I/O.
- **Type Hints**: All functions and classes must be fully typed.
- **Ruff**: We use Ruff for fast holistic linting.
- **Black**: Used for standard code formatting.

### Running Linting
Before committing, ensure your code passes our lint checks:
```sh
make lint
make format
```

### Running Tests
Ensure your new features include relevant tests or don't break existing ones:
```sh
make test
```

---

## Project Architecture & Module Boundaries

When adding new features (like a new Cloud Provider), it's important to respect the established boundaries:

1. **`opsyield/collectors/`**: The lowest level. These modules isolate the actual network/SDK calls (e.g., `boto3`, `httpx` to OpenCost). They return raw lists or dicts of basic resources.
2. **`opsyield/providers/`**: The abstraction layer. Classes here inherit from `CloudProvider`. They instantiate the Collectors, normalize the responses into unified `Resource` or `NormalizedCost` schemas, and provide standard `get_status` hooks. 
3. **`opsyield/analysis/` (Engine)**: The core brain. It operates ONLY on normalized schemas. Do not write AWS or GCP specific logic here.
4. **`opsyield/api/` (Orchestrator)**: Handles the MCP logic and HTTP routing. It uses the `ProviderFactory` to dynamically load providers when user queries arrive.

---

## Pull Request Guidelines

When you are ready to submit your changes:

1. Update your feature branch from your local copy of master:
   ```sh
   git remote add upstream git@github.com:Moiz-Ali-Moomin/mcp-cloud-finops-ai-agent.git
   git pull upstream master
   git rebase master
   ```
2. Push your branch to origin:
   ```sh
   git push --set-upstream origin 325-add-kubernetes-cost-collector
   ```
3. Go to GitHub and open a Pull Request.
4. Ensure your PR description clearly states the *Why* and *How* of your changes. Link any associated issues.
5. If a maintainer asks you to "rebase" your PR, ensure you update your branch so it merges cleanly.
