# Anthropic-hass-api

A Home Assistant custom component that integrates Anthropic Claude with Home Assistant, allowing you to use Claude as a voice assistant with your API key.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Version](https://img.shields.io/badge/Version-1.2.1-brightgreen.svg)](https://github.com/slawa19/anthropic-hass-api/releases/tag/1.2.1)

## What's New in Version 1.2.1

- **Python 3.13 Compatibility**: Fixed syntax error in conversation_agent.py that was causing issues with Python 3.13
- **Improved Multilingual Support**: Enhanced language handling to properly switch between languages
- **Translation System Fixes**: Improved how translations are loaded and fallbacks are handled
- **Code Structure Improvements**: Fixed indentation issues in the _async_generate_prompt method

## Previous Updates (1.2.0)

- **Enhanced Error Handling**: Improved stability with robust error handling throughout the integration
- **Fixed Critical Issues**: Resolved issues with entity state processing that could cause conversation failures
- **Brightness Attribute Fix**: Fixed error when processing light entities with null brightness values
- **Translation System Improvements**: Added caching and better error handling for translations
- **Overall Stability Improvements**: Made the integration more resilient to unexpected conditions

## Features

- **Multilingual Support**: Automatically adapts to your Home Assistant interface language (English and Russian supported)
- **Use Anthropic Claude as a conversation agent in Home Assistant**
- **Control your Home Assistant devices using natural language**
- **Configure Claude's behavior with custom instructions**
- **Choose from different Claude models** (Claude 3 Opus, Sonnet, Haiku, and Claude 3.5 Sonnet)
- **Adjust parameters like temperature and max tokens**
- **Direct API Integration**: Uses direct HTTP requests to the Anthropic API for better compatibility

## Installation

### HACS (Home Assistant Community Store)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Go to HACS > Integrations
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/slawa19/anthropic-hass-api`
5. Select "Integration" as the category
6. Click "ADD"
7. Search for "Anthropic" in the integrations tab
8. Click "Install"
9. Restart Home Assistant

### Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/anthropic` directory to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Anthropic"
4. Follow the configuration steps:
   - Enter your Anthropic API key (get one at https://console.anthropic.com/settings/keys)
   - Configure options like instructions, model, and parameters

## API Key

This integration requires an Anthropic API key. To get one:

1. Sign up or log in at [Anthropic Console](https://console.anthropic.com/)
2. Enable billing with a valid credit card on the [plans page](https://console.anthropic.com/settings/plans)
3. Visit the [API Keys page](https://console.anthropic.com/settings/keys) to generate an API key

**Note:** This is a paid service. Monitor your costs in the [Anthropic portal](https://console.anthropic.com/settings/cost).

## Legal Notice

This integration uses the official Anthropic API. Please note that the Anthropic API is intended for B2B and not for individual use, [more info here](https://support.anthropic.com/en/articles/8987200-can-i-use-the-claude-api-for-individual-use). Therefore, this integration is intended for commercial uses.

## Usage

Once configured, you can interact with Claude through:

- The conversation panel in Home Assistant
- Voice assistants that use Home Assistant's conversation agent
- The conversation.process service

## Exposed Entities

Claude can only control or provide information about entities that are exposed to it. To manage which entities Claude can access:

1. Go to Settings > Voice Assistants
2. Select the "Exposed Entities" tab
3. Toggle entities you want Claude to be able to control

## Configuration Options

- **Custom Instructions for Claude**: Instructions for the AI on how it should respond to your requests
- **Allow Claude to Control Home Assistant**: Enable/disable Claude's ability to control your devices
- **Use Recommended Model & Settings**: Quickly set up with optimal defaults or customize advanced settings
- **Claude Model**: Choose between different Claude models (when recommended settings are disabled)
- **Maximum Response Length**: Control how verbose Claude's responses are (when recommended settings are disabled)
- **Response Creativity**: Adjust the balance between focused/deterministic and creative/varied responses (when recommended settings are disabled)

## Multilingual Support

The integration automatically adapts to your Home Assistant interface language:
- If your Home Assistant interface is set to English, the integration will display in English
- If your Home Assistant interface is set to Russian, the integration will display in Russian
- For other languages, English will be used as the default

## Uploading to GitHub

To upload this project to your GitHub repository:

1. Create a new repository on GitHub at https://github.com/slawa19/anthropic-hass-api
2. Initialize a git repository in the project directory:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/slawa19/anthropic-hass-api.git
   git push -u origin main
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.