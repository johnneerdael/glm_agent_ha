# Contributing to AI Agent HA

Thank you for your interest in contributing to AI Agent HA! 🎉 This Home Assistant custom integration wouldn't be possible without the help of amazing contributors like you.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming and inclusive environment. By participating, you are expected to uphold these values:

- Be respectful and inclusive
- Be collaborative and constructive
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### 🐛 Reporting Bugs
- Use the GitHub issue tracker
- Check if the issue already exists before creating a new one
- Include detailed information about your setup and the problem
- Provide steps to reproduce the issue

### 💡 Suggesting Features
- Open a GitHub issue with the "enhancement" label
- Clearly describe the feature and its benefits
- Explain how it would work with the existing codebase
- Consider backward compatibility

### 🔧 Contributing Code
- Fix bugs or implement new features
- Improve documentation
- Add support for new AI providers
- Enhance the user interface

### 📚 Improving Documentation
- Fix typos or unclear instructions
- Add examples and use cases
- Create tutorials or guides
- Translate documentation

## Getting Started

### Prerequisites
- Home Assistant 2023.3+
- Python 3.11+
- Git
- A development environment (VS Code recommended)
- API key for at least one supported AI provider

### Fork and Clone
1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai_agent_ha.git
   cd ai_agent_ha
   ```
3. Add the original repository as upstream:
   ```bash
   git remote add upstream https://github.com/sbenodiz/ai_agent_ha.git
   ```

## Development Setup

### Home Assistant Development Environment
1. Set up a Home Assistant development environment
2. Copy the `custom_components/ai_agent_ha` folder to your development HA instance
3. Restart Home Assistant
4. Configure the integration with your AI provider API key

### Local Development
```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (if available)
pre-commit install
```

### Project Structure
```
ai_agent_ha/
├── custom_components/ai_agent_ha/
│   ├── __init__.py           # Integration entry point
│   ├── config_flow.py        # Configuration flow
│   ├── const.py              # Constants
│   ├── agent.py              # Core AI agent logic
│   ├── ai_clients/           # AI provider implementations
│   ├── services.py           # Home Assistant services
│   └── www/                  # Frontend resources
├── docs/                     # Documentation
├── tests/                    # Test files
└── README.md
```

## Pull Request Process

### Before Submitting
1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Test your changes thoroughly
4. Update documentation if needed
5. Ensure your code follows the coding standards

### Submitting Your PR
1. Push your branch to your fork
2. Create a pull request from your branch to `main`
3. Fill out the PR template completely
4. Link any related issues
5. Request a review from maintainers

### PR Requirements
- [ ] Code follows the project coding standards
- [ ] All tests pass
- [ ] Documentation is updated (if applicable)
- [ ] Breaking changes are clearly documented
- [ ] Commit messages are clear and descriptive

## Issue Guidelines

### Bug Reports
Include the following information:
- **Home Assistant version**
- **AI Agent HA version**
- **AI provider and model being used**
- **Steps to reproduce**
- **Expected behavior**
- **Actual behavior**
- **Relevant logs** (check Home Assistant logs)
- **Configuration details** (anonymize sensitive data)

### Feature Requests
- Clearly describe the feature
- Explain the use case and benefits
- Consider implementation complexity
- Suggest possible approaches

### Questions and Support
- Check the [documentation](https://github.com/sbenodiz/ai_agent_ha/wiki) first
- Search existing issues
- Use [GitHub Discussions](https://github.com/sbenodiz/ai_agent_ha/discussions) for general questions

## Coding Standards

### Python Code Style
- Follow [PEP 8](https://pep8.org/)
- Use meaningful variable and function names
- Add docstrings to all public functions and classes
- Keep functions focused and reasonably sized
- Use type hints where appropriate

### Home Assistant Specific
- Follow [Home Assistant development guidelines](https://developers.home-assistant.io/)
- Use Home Assistant's logging system
- Implement proper error handling
- Follow integration best practices

### Frontend Code
- Use modern JavaScript/ES6+
- Follow consistent naming conventions
- Comment complex logic
- Ensure responsive design

### Example Code Style
```python
"""Example of proper code style."""
import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

class AIAgent:
    """AI Agent for processing natural language requests."""
    
    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the AI agent."""
        self.hass = hass
        self.config = config
    
    async def process_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Process a natural language request.
        
        Args:
            prompt: The user's natural language request
            
        Returns:
            Dict containing the response or None if error
        """
        try:
            # Implementation here
            return {"response": "success"}
        except Exception as err:
            _LOGGER.error("Error processing request: %s", err)
            return None
```

## Testing

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_agent.py

# Run with coverage
python -m pytest --cov=custom_components.ai_agent_ha
```

### Writing Tests
- Write tests for new functionality
- Include both positive and negative test cases
- Test edge cases and error conditions
- Mock external dependencies (AI APIs, Home Assistant)

### Test Structure
```python
"""Test example."""
import pytest
from unittest.mock import Mock, patch

from custom_components.ai_agent_ha.agent import AIAgent

@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    return Mock()

async def test_process_request_success(mock_hass):
    """Test successful request processing."""
    agent = AIAgent(mock_hass, {})
    result = await agent.process_request("turn on lights")
    assert result is not None
    assert "response" in result
```

## Documentation

### Documentation Standards
- Use clear, concise language
- Include practical examples
- Keep documentation up to date with code changes
- Use proper Markdown formatting

### Types of Documentation
- **README.md**: Project overview and quick start
- **Wiki**: Detailed guides and tutorials
- **Code comments**: Explain complex logic
- **Docstrings**: Document all public APIs
- **CHANGELOG.md**: Track version changes

## Community

### Getting Help
- **GitHub Discussions**: Ask questions and share ideas
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the wiki for guides

### Staying Updated
- Watch the repository for notifications
- Join discussions on new features
- Follow the project roadmap

### Recognition
Contributors are recognized in:
- README.md acknowledgments
- Release notes
- Special mentions for significant contributions

## Questions?

If you have any questions about contributing, please:
1. Check the existing documentation
2. Search through existing issues and discussions
3. Open a new discussion if you can't find an answer

Thank you for contributing to AI Agent HA! Your efforts help make Home Assistant smarter and more accessible for everyone. 🏠🤖