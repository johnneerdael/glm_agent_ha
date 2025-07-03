# Security Policy

## Reporting a Vulnerability

The AI Agent HA project takes security seriously. We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

### How to Report a Security Vulnerability

If you believe you've found a security vulnerability in AI Agent HA, please follow these steps:

1. **Do Not** disclose the vulnerability publicly (e.g., in GitHub issues, discussion forums, etc.)
2. Email the project maintainer directly at benodiz111@gmail.com with:
   - A detailed description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact of the vulnerability
   - Any suggestions for mitigation or fixes (if you have them)
   - Your name/handle if you'd like to be credited for the discovery

### What to Expect

After submitting a security vulnerability report:

- You'll receive an acknowledgment of your report within 48-72 hours
- We'll investigate and determine the potential impact and severity
- We'll develop and test a fix
- When a fix is ready, we'll coordinate with you on the disclosure timeline
- We'll credit you in the security advisory (unless you prefer to remain anonymous)

### Security Best Practices for Users

1. **Keep Home Assistant Updated**: Always use the latest version of Home Assistant
2. **Use Strong API Keys**: Generate strong, unique API keys for each AI provider
3. **Secure Your Network**: Ensure Home Assistant is behind a secure network with appropriate firewall rules
4. **Follow Principle of Least Privilege**: When integrating AI Agent HA with other systems, provide only necessary permissions
5. **Enable Two-Factor Authentication**: Use 2FA for your Home Assistant instance if possible
6. **Review Logs Regularly**: Monitor Home Assistant logs for unusual activity

### Security Considerations

The AI Agent HA integration:

- Stores API keys securely in Home Assistant's encrypted storage
- Uses HTTPS for all communications with AI providers
- Does not send sensitive information from your Home Assistant to external services without your knowledge
- Validates inputs to prevent injection attacks
- Limits the actions the AI can perform based on permissions

We appreciate your help in keeping AI Agent HA and its users safe and secure. 