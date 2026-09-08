---
name: test-ecamp3-pr-deployment
description: Test ecamp3 PR deployments by finding the deployment URL from the PR comment and using playwright-cli to test the deployed frontend on dev.ecamp3.ch.
---

# Testing ecamp3 PR Deployments

This skill covers how to test ecamp3 PR deployments on `dev.ecamp3.ch`. When a PR is opened, a deployment is created and its URL is posted as a comment on the PR.

## Finding the Deployment URL

1. **Go to the PR** that should be tested
2. **Find the comment** showing the URL to the deployment
3. The deployment URL will be on `dev.ecamp3.ch`

Use the GitHub CLI to find the deployment comment:
```bash
gh pr view <pr-number> --comments
```

Look for a comment containing the deployment URL on `dev.ecamp3.ch`.

## End-to-End Testing with Playwright CLI

Use the `playwright-cli` skill to navigate to the changed components and test all interactions on the deployed site.

### Desktop Testing

1. **Start playwright-cli** with a browser session
2. **Navigate to the deployment URL** on `dev.ecamp3.ch`
3. **Navigate to the changed components**
4. **Test all interactions** — clicks, forms, navigation, etc.
5. **Verify the UI behaves correctly** on the deployed version

### Mobile Testing

1. **Start playwright-cli simulating a mobile device**
2. **Navigate to the deployment URL** on `dev.ecamp3.ch`
3. **Navigate to the changed components**
4. **Test all interactions** on the mobile view
5. **Verify responsive behavior** on the deployed version

## Capturing Screenshots for PR Comparison

Take screenshots of the changed views on the deployed site and attach them to the PR for comparison:

### Desktop Screenshots

1. Use playwright-cli to navigate to each changed view on `dev.ecamp3.ch`
2. Take a screenshot:
   ```bash
   playwright-cli screenshot --filename=<name>-deployment-desktop.png
   ```
3. Attach the screenshots to the PR

### Mobile Screenshots

1. Use playwright-cli simulating a mobile device to navigate to each changed view on `dev.ecamp3.ch`
2. Take a screenshot:
   ```bash
   playwright-cli screenshot --filename=<name>-deployment-mobile.png
   ```
3. Attach the screenshots to the PR

## Important Notes

- **Always test on the actual deployment** — the deployed version may differ from local development
- **Compare with the base branch** — ensure the changes look correct relative to the existing site
- **Test all user flows** that are affected by the PR changes
- **Check both desktop and mobile** views

## When to Use This Skill

This skill should be loaded whenever testing a PR deployment for ecamp3, including:
- Verifying PR changes on the deployed site
- Testing frontend changes in the deployment environment
- Checking responsive design on the deployed version
- Validating that PR changes work correctly before merging
