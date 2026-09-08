---
name: test-ecamp3-frontend
description: Test the ecamp3 frontend (Vue.js with Vite) by running unit tests, using playwright-cli for end-to-end testing, and capturing screenshots for PR comparison.
---

# Testing the ecamp3 Frontend

This skill covers how to test the ecamp3 frontend, which lives in the `ecamp/ecamp3` repository under `frontend/`. The frontend is built with Vue.js and Vite, using Vitest for unit testing and Playwright for end-to-end testing.

## Repository Location

- **Frontend code**: `ecamp/ecamp3/frontend/`
- **Frontend tests**: `ecamp/ecamp3/frontend/tests/`
- **Frontend config**: `ecamp/ecamp3/frontend/vite.config.js`, `frontend/package.json`

## Running Unit Tests

Run the unit test suite with Vitest and coverage:

```bash
cd ecamp/ecamp3/frontend
npm run test:unit
```

This runs Vitest with coverage reporting.

## Starting the Full Stack

Start the entire frontend stack and wait for all services to be ready:

```bash
cd ecamp/ecamp3
docker compose up -d
```

Wait until all services are healthy before proceeding. Check the status with:
```bash
docker compose ps
```

## End-to-End Testing with Playwright CLI

Use the `playwright-cli` skill to navigate to the changed components and test all interactions there.

### Desktop Testing

1. **Start playwright-cli** with a browser session
2. **Navigate to the changed components** on the ecamp3 frontend
3. **Test all interactions** — clicks, forms, navigation, etc.
4. **Verify the UI behaves correctly**

### Mobile Testing

1. **Start playwright-cli simulating a mobile device**
2. **Navigate to the changed components** on the ecamp3 frontend
3. **Test all interactions** on the mobile view
4. **Verify responsive behavior**

## Capturing Screenshots for PR Comparison

Take screenshots of the changed views and attach them to the PR for comparison:

### Desktop Screenshots

1. Use playwright-cli to navigate to each changed view on `ecamp3/devel`
2. Take a screenshot:
   ```bash
   playwright-cli screenshot --filename=<name>-desktop.png
   ```
3. Attach the screenshots to the PR

### Mobile Screenshots

1. Use playwright-cli simulating a mobile device to navigate to each changed view on `ecamp3/devel`
2. Take a screenshot:
   ```bash
   playwright-cli screenshot --filename=<name>-mobile.png
   ```
3. Attach the screenshots to the PR

## When to Use This Skill

This skill should be loaded whenever working on the ecamp3 frontend, including:
- Modifying Vue.js components
- Changing Vite configuration
- Adding or modifying frontend tests
- Updating CSS or styling
- Fixing frontend bugs
- Adding new frontend features
