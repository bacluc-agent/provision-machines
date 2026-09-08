---
name: test-github-actions
description: Test GitHub Actions workflows by verifying each job step locally, triggering workflow runs, and inspecting results.
---

# Testing GitHub Actions Workflows

This skill covers how to test GitHub Actions workflows in the `bacluc-agent/provision-machines` repository.

## Verifying Locally

Replicate each job step by step to verify the workflow works before pushing changes:

1. **Read the workflow file** — check `.github/workflows/ci.yaml` for the job definitions
2. **Identify each step** in every job
3. **Run each step locally** using the same commands and environment variables
4. **Compare results** — ensure local execution matches the expected CI behavior

For example, the `pyinfra_lint` job has these steps:
- Install dependencies with `uv sync --frozen --all-extras`
- Run tests with `uv run pytest`
- Run linting with `uv run ruff check .`
- Run type checking with `uv run mypy .`
- Run prettier formatting check via Docker container

## Triggering a Workflow Run

There are several ways to trigger a GitHub Actions workflow:

### Push a Branch
```bash
git push origin <branch-name>
```
Pushing to a branch triggers the workflow if configured for branch pushes.

### Open a Pull Request
```bash
gh pr create --base main --head <branch-name> --title "..." --body "..."
```
Opening a PR triggers the workflow if configured for PR events.

### Use `gh workflow run`
```bash
# List workflows
gh workflow list

# Trigger a specific workflow
gh workflow run <workflow-name.yml> --ref <branch-or-ref>
```

## Inspecting Run Results

After triggering a workflow, inspect the results:

```bash
# List recent runs
gh run list

# View a specific run
gh run view <run-id>

# View a specific run's logs
gh run view <run-id> --log

# View logs for a specific job
gh run view <run-id> --job <job-id>
```

## Re-running After Changes

After changes to a workflow, it must be run multiple times with different parameters to make sure it works afterwards:

1. **Make the workflow change**
2. **Run the workflow** with the default parameters
3. **Verify the results** — check all jobs pass
4. **Run the workflow again** with different parameters (e.g., different branch, different triggers)
5. **Verify the results** again
6. **Repeat** until confident the workflow is stable

This is important because workflows can behave differently depending on:
- The branch being targeted
- The event that triggered the run
- The state of the repository
- Environment variables and secrets

## When to Use This Skill

This skill should be loaded whenever modifying or testing GitHub Actions workflows, including:
- Changing workflow triggers
- Modifying job steps
- Adding new jobs
- Fixing workflow failures
- Adding new CI/CD pipelines
