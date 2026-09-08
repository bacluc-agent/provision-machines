---
name: test-ecamp3-api
description: Test the ecamp3 API (PHP/Symfony) by running tests, static analysis, and formatting checks via Docker Compose.
---

# Testing the ecamp3 API

This skill covers how to test the ecamp3 API, which lives in the `ecamp/ecamp3` repository under `api/`. The API is built with PHP and Symfony, using PHPUnit for testing.

## Repository Location

- **API code**: `ecamp/ecamp3/api/`
- **API Dockerfile**: `ecamp/ecamp3/api/Dockerfile`
- **API Docker config**: `ecamp/ecamp3/api/docker/`
- **CI environment file**: `ecamp/ecamp3/.env.ci` (contains CI-specific env vars; may need to be disabled in a GitHub Action)

## Running API Tests with Docker Compose

From the ecamp3 repository root, run the API tests using Docker Compose:

```bash
# Run PHPUnit tests
docker compose run --rm api composer test

# Or run phpunit directly
docker compose run --rm api php bin/phpunit
```

## PHPStan Static Analysis

Run PHPStan to check for static analysis issues:

```bash
docker compose run --rm api php vendor/bin/phpstan analyse
```

## PHP-CS-Fixer Formatting

Check code formatting with PHP-CS-Fixer:

```bash
docker compose run --rm api php php-cs-fixer fix --dry-run --diff
```

If any files need formatting changes, they will be listed in the diff output.

## Docker Configuration

The API Dockerfile and configuration are located at:
- `api/Dockerfile` — defines the FrankenPHP-based Docker image
- `api/docker/` — contains Docker configuration files (caddy, php, varnish)

The `api/docker/php/` directory contains the PHP Docker configuration including `docker-entrypoint.sh` and `migrate-database.sh`.

## Environment Variables

The `.env.ci` file at the repository root contains CI-specific environment variables:
```
USER_ID=1001
XDEBUG_MODE=off
APP_ENV=e2e
```

**Note**: When running in a GitHub Action, you may need to disable or override `.env.ci` to avoid CI-specific configuration interfering with local testing.

## Testing the API in Production

After running unit tests and static analysis, also verify the API works in production:

1. **Start the API service** using Docker Compose
2. **Send API requests** against the running service to verify it works correctly
3. **Test all endpoints** that were changed or affected

```bash
# Start the full stack
docker compose up -d

# Test the API
curl http://localhost:8000/api/...
```

## When to Use This Skill

This skill should be loaded whenever working on the ecamp3 API, including:
- Modifying PHP/Symfony code in `api/`
- Changing API endpoints or controllers
- Updating database migrations
- Modifying Docker configuration
- Fixing API bugs or adding new features
