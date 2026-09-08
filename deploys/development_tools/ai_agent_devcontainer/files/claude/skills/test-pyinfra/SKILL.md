---
name: test-pyinfra
description: Test pyinfra deployments, linting, type checking, and provisioning on the provision-machines repository.
---

# Testing Pyinfra Deployments

This skill covers how to test pyinfra deployments in the `bacluc-agent/provision-machines` repository.

## Repository Overview

- **Deploys**: `deploys/` — individual deployment scripts for each software component
- **Operations**: `operations/` — reusable pyinfra operations
- **Inventory**: `inventory.py` — defines the target machines and groups
- **Tests**: `tests/` — Python test files using `*_test.py` naming convention

## Running the Test Suite

```bash
# Run all tests with coverage
uv run pytest

# Run a specific test file
uv run pytest tests/filesystem_test.py
```

Tests use `pytest` with `pytest-cov` for coverage reporting. Test files live in `tests/` and follow `*_test.py` naming.

## Linting

```bash
uv run ruff check .
```

## Type Checking

```bash
uv run mypy .
```

## Formatting Check

The project uses a prettier Docker container for formatting. Run the same command as in `.github/workflows/ci.yaml`:

```bash
# renovate: datasource=docker depName=ghcr.io/bacluc/prettier-image/prettier-image
prettier_image_version="5.1.0"
docker run --rm -v $PWD:/workdir -w /workdir -u $UID ghcr.io/bacluc/prettier-image/prettier-image:${prettier_image_version}
git diff --exit-code
```

If `git diff --exit-code` returns any changes, formatting is incorrect.

## Full Local Provisioning Run

Run the full pyinfra provisioning locally:

```bash
uv run scripts/run_pyinfra_local.py
```

This runs pyinfra against `inventory.py` with all deploy scripts in `deploys/`.

## Running a Single Deploy and Its Dependencies

To test only a changed deploy and all deploys that depend on it:

```bash
uv run scripts/run_pyinfra_single.py <deployment_script>
```

For example:
```bash
uv run scripts/run_pyinfra_single.py deploys/development_tools/deploy.py
```

## Verifying Resource Changes

After a provisioning run, verify:

- **All expected resources changed** — check that the deploy modified the intended files, packages, or services
- **Resources that should not change did not change** — review the pyinfra output to confirm no unintended modifications occurred

Pyinfra reports which operations were executed and which were skipped. Review this output carefully.

## Pyinfra Architecture

- **Deploys** (`deploys/`): Each file defines a deployment for a specific software component (e.g., `deploys/development_tools/deploy.py`)
- **Operations** (`operations/`): Reusable pyinfra operations imported by deploys
- **Inventory** (`inventory.py`): Defines target hosts and groups for pyinfra to configure

## When to Use This Skill

This skill should be loaded whenever developing pyinfra-related changes, including:
- Modifying deploy scripts in `deploys/`
- Changing operations in `operations/`
- Updating inventory configuration in `inventory.py`
- Adding or modifying tests in `tests/`
- Changing provisioning logic

Make sure the skill is loaded when the agent develops pyinfra things.
