# Release Notes for v1.2.1

## Overview

This release addresses a critical syntax error in the `conversation_agent.py` file that was causing issues with Python 3.13 compatibility. We've also improved the multilingual support to ensure proper language switching and enhanced the translation system.

## What's New

### Python 3.13 Compatibility
- Fixed syntax error in `conversation_agent.py` that was causing issues with Python 3.13
- Fixed indentation issues in the `_async_generate_prompt` method
- Updated GitHub workflow to include Python 3.13 in the test matrix

### Improved Multilingual Support
- Enhanced language handling to properly switch between languages
- Fixed issues with prompt translation in different language interfaces
- Improved how translations are loaded and fallbacks are handled

### Code Structure Improvements
- Fixed duplicate method declarations
- Improved code organization and readability
- Enhanced error handling in language-specific code paths

## Upgrading

To upgrade to version 1.2.1:

1. Go to HACS > Integrations
2. Find "Anthropic" in your installed integrations
3. Click on it and select "Upgrade"
4. Restart Home Assistant

## Technical Details

### Key Changes

- Fixed syntax error in the `_async_generate_prompt` method where a `try` block was missing its corresponding `except` block
- Removed duplicate method declaration that was causing indentation issues
- Ensured proper handling of language selection in the translation system
- Updated GitHub workflow to test against Python 3.13

### Contributors

- @slawa19

## Feedback

If you encounter any issues or have suggestions for improvements, please [open an issue](https://github.com/slawa19/anthropic-hass-api/issues) on GitHub.