# Changelog

## [1.2.1] - 2025-04-06

### Fixed
- Fixed syntax error in conversation_agent.py that was causing issues with Python 3.13
- Fixed indentation issues in the _async_generate_prompt method
- Improved multilingual support to properly handle language switching
- Enhanced translation system to better handle fallbacks to English

## [1.2.0] - 2025-04-06

### Added
- Enhanced error handling throughout the integration
- Added caching for translations to improve performance
- Added additional logging for better troubleshooting

### Fixed
- Fixed critical issue with brightness attribute processing that could cause conversation failures
- Fixed potential infinite recursion in system prompt generation
- Fixed error handling in translation system
- Improved entity state processing to handle unexpected attribute values

### Changed
- Refactored error handling in entity state processing for better stability
- Improved robustness of the translation system
- Enhanced overall stability with multi-level error handling

## [1.1.0] - 2025-03-15

### Added
- Support for Claude 3.5 Sonnet model
- Improved multilingual support with Russian translations
- Enhanced entity state reporting

### Changed
- Optimized API request handling
- Improved conversation context management

## [1.0.0] - 2025-02-20

### Added
- Initial release
- Support for Claude 3 models (Opus, Sonnet, Haiku)
- Custom instructions configuration
- Home Assistant device control capability
- Adjustable parameters (temperature, max tokens)
- Basic multilingual support