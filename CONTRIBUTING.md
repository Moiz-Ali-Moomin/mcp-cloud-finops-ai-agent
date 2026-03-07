# Contributing to OpsYield MCP FinOps Server

First off, thank you for considering contributing to OpsYield! It's people like you that make OpsYield such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, make one! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

## Fork & create a branch

If this is something you think you can fix, then fork OpsYield and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```sh
git checkout -b 325-add-gcp-kubernetes-cost-collector
```

## Get the test suite running

Make sure you have Python 3.11+ installed.

```sh
make install
```

To run the tests, run:

```sh
make test
```

## Implement your fix or feature

At this point, you're ready to make your changes. Feel free to ask for help; everyone is a beginner at first.

## Code Quality

We use `ruff` for linting, `black` for formatting, and `mypy` for type checking.

Run the formatting and linting tools before submitting a PR:

```sh
make format
make lint
```

## Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with OpsYield's master branch:

```sh
git remote add upstream git@github.com:Moiz-Ali-Moomin/mcp-cloud-finops-ai-agent.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```sh
git checkout 325-add-gcp-kubernetes-cost-collector
git rebase master
git push --set-upstream origin 325-add-gcp-kubernetes-cost-collector
```

Finally, go to GitHub and make a Pull Request.

## Keeping your Pull Request updated

If a maintainer asks you to "rebase" your PR, they're saying that a lot of code has changed, and that you need to update your branch so it's easier to merge.
