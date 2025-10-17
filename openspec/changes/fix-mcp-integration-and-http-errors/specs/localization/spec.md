## ADDED Requirements

### Requirement: Translation Context Variable Provision
The integration SHALL provide all required context variables for translation strings.

#### Scenario: Missing current_provider variable
- **WHEN** rendering translation strings that use the {current_provider} variable
- **THEN** the integration SHALL provide the current_provider value in the translation context
- **THEN** the integration SHALL validate that all required variables are provided before rendering
- **THEN** the integration SHALL log a warning if variables are missing with fallback values

#### Scenario: Translation context initialization
- **WHEN** initializing the config flow or option steps
- **THEN** the integration SHALL populate translation context with all necessary variables
- **THEN** the integration SHALL ensure context variables are available for all supported languages
- **THEN** the integration SHALL test translation rendering during development

### Requirement: Translation String Validation
The integration SHALL validate translation strings during development and runtime.

#### Scenario: Translation format validation
- **WHEN** loading translation files
- **THEN** the integration SHALL validate that all context variables have corresponding values
- **THEN** the integration SHALL provide clear error messages for missing variables
- **THEN** the integration SHALL fail gracefully without breaking the integration setup