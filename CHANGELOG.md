# Changelog

All notable changes to the AI Agent HA project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.99.3] - 2025-07-04
### Changed
- **Breaking**: Now requires Python 3.12+ for Home Assistant compatibility
- Updated all GitHub Actions workflows to use Python 3.12
- Updated mypy configuration for Python 3.12 compatibility
- Improved type annotations throughout codebase

### Fixed
- Fixed mypy type checking errors with Home Assistant 2025.1.x
- Fixed code formatting issues with black formatter
- Fixed test compatibility with Python 3.12
- Resolved CI/CD pipeline failures

### Added
- Comprehensive documentation updates for Python 3.12 requirement
- Enhanced development environment setup instructions
- Better error handling for AI provider imports

## [0.99.2] - Previous Release
### Added
- Contribution guidelines for the project
- Issue and pull request templates
- Code of Conduct
- Security policy
- Development guide
- Changelog

## [1.0.0] - YYYY-MM-DD (Replace with actual release date)
### Added
- Initial release of AI Agent HA
- Support for multiple AI providers (OpenAI, Google Gemini, Anthropic Claude, OpenRouter, Llama)
- Entity control through natural language
- Automation creation
- Dashboard creation
- Entity state queries
- Home Assistant panel integration
- Configuration flow setup
- Documentation

## How to Update This Changelog

For each new release, create a new section with:
- `[version number] - YYYY-MM-DD` as the heading
- Group changes under the following subheadings as needed:
  - **Added** - for new features
  - **Changed** - for changes in existing functionality
  - **Deprecated** - for soon-to-be removed features
  - **Removed** - for now removed features
  - **Fixed** - for bug fixes
  - **Security** - for security improvements and fixes
  
Example:
```
## [1.1.0] - 2023-12-15
### Added
- New feature X
- New provider Y

### Changed
- Improved handling of Z

### Fixed
- Bug in feature A
```

When adding items to the Unreleased section, follow the same format. When creating a release, rename "Unreleased" to the new version number and release date, then create a new "Unreleased" section. 