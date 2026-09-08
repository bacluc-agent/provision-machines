---
name: test-opencode-plugins
description: Test opencode plugins by starting an opencode session with the plugin activated and running end-to-end tests with specially crafted prompts.
---

# Testing OpenCode Plugins

This skill covers how to test opencode plugins end-to-end. Plugin unit tests are not sufficient — you must perform end-to-end testing by starting an opencode session with the plugin activated and running it against real prompts.

## Overview

OpenCode plugins extend the opencode editor with custom functionality. Testing them requires more than unit tests — you need to verify the plugin works correctly in a real opencode session.

## Starting an OpenCode Session with a Plugin

To test a plugin, start an opencode session with that plugin activated:

```bash
# Start opencode with the plugin loaded
opencode --plugin <plugin-name>
```

The exact command depends on how the plugin is installed and configured. Check the plugin's README or configuration for the correct invocation.

## Running End-to-End Tests

Plugin tests in the repository are not good enough. You need to do end-to-end tests by running opencode with specially crafted prompts that exercise the plugin's functionality.

### Test Strategy

1. **Start an opencode session** with the plugin activated
2. **Craft prompts** that target the plugin's specific features:
   - Test the primary functionality the plugin provides
   - Test edge cases and error handling
   - Test interactions with other opencode features
3. **Observe the output** and verify the plugin behaves as expected
4. **Test with different prompt styles** — the plugin should handle various input patterns

### Example Test Prompts

Tailor your prompts to the specific plugin being tested. General categories include:

- **Core feature prompts**: Directly exercise the plugin's main capability
- **Integration prompts**: Test how the plugin interacts with opencode's built-in features
- **Error prompts**: Test how the plugin handles invalid or unexpected input
- **Boundary prompts**: Test edge cases and limits

## Important Notes

- **Do not rely solely on existing plugin tests** — they are not sufficient for end-to-end validation
- **Always test in a real opencode session** — the plugin may behave differently in isolation vs. in the full editor context
- **Document any issues found** — note which prompts caused unexpected behavior
- **Test with the latest opencode version** — plugin compatibility may change with opencode updates

## When to Use This Skill

This skill should be loaded whenever testing or developing opencode plugins, including:
- Adding new plugin functionality
- Fixing plugin bugs
- Verifying plugin compatibility with opencode updates
- Performing end-to-end validation of plugin behavior
