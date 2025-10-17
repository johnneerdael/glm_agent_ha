## ADDED Requirements

### Requirement: LLM Assistant Provider
The system SHALL provide an LLM assistant provider that integrates with Home Assistant's Assist pipeline using the GLM Coding Plan API.

#### Scenario: Assistant provider registration
- **WHEN** the GLM Agent HA integration is loaded
- **THEN** it registers as an assistant provider with Home Assistant
- **AND** the provider appears in the Assist pipeline configuration options

#### Scenario: GLM assistant selection
- **WHEN** a user configures an Assist pipeline
- **THEN** they can select "GLM Agent" as the assistant provider
- **AND** the assistant uses the configured GLM Coding Plan API endpoint

#### Scenario: Assistant response processing
- **WHEN** a user interacts with the GLM assistant through the Assist pipeline
- **THEN** the assistant processes the request using the GLM Coding Plan API
- **AND** returns appropriate responses for Home Assistant control

### Requirement: Assist Pipeline Configuration
The system SHALL provide configuration options for the GLM assistant within the Assist pipeline settings.

#### Scenario: Model selection in pipeline
- **WHEN** configuring the GLM assistant in an Assist pipeline
- **THEN** users can select from available GLM Coding Plan models
- **AND** custom model names can be entered

#### Scenario: API key validation
- **WHEN** setting up the GLM assistant provider
- **THEN** the GLM Coding Plan API key is validated
- **AND** clear error messages are shown for invalid credentials