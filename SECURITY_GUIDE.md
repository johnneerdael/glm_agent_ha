# Security Guide for GLM Agent HA

## 🚨 Critical Security Information

This document outlines security considerations for the GLM Agent HA Home Assistant integration.

### Environment Variables Setup

**IMPORTANT**: The integration now uses environment variables for all API keys instead of hardcoded values. This is a critical security improvement.

#### Setup Instructions:

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file** with your actual API keys:
   ```
   Z_AI_API_KEY=your_actual_z_ai_key
   CONTEXT7_API_KEY=ctx7sk-your_actual_context7_key
   JINA_API_KEY=jina_your_actual_jina_key
   TAVILY_API_KEY=tvly-your_actual_tavily_key
   GITHUB_TOKEN=ghp_your_actual_github_token
   SUPABASE_ACCESS_TOKEN=sbp_your_actual_supabase_token
   ```

3. **Set up environment variables** in your system:
   - **Windows**: Use System Properties > Environment Variables
   - **Linux/Mac**: Add to `~/.bashrc`, `~/.zshrc`, or `/etc/environment`
   - **Docker**: Pass as `-e` flags or use an env file
   - **Home Assistant**: Use the Supervisor's environment variables

4. **Restart Home Assistant** after setting environment variables

### Security Best Practices

#### ✅ DO:
- Keep API keys confidential and secure
- Rotate API keys regularly (every 90 days recommended)
- Use the minimum required permissions for each API key
- Monitor API usage for unusual activity
- Use HTTPS for all communications
- Keep Home Assistant and dependencies updated

#### ❌ DON'T:
- Commit API keys to version control
- Share API keys in public forums or documentation
- Use production keys in development environments
- Log API keys or sensitive configuration data
- Use predictable file paths or naming for security-sensitive files

### API Key Security

#### Z.AI API Key
- **Purpose**: Image analysis, web search, AI tools
- **Security Impact**: High - can process images and access web content
- **Recommendation**: Use scoped permissions with rate limits

#### Context7 API Key
- **Purpose**: Documentation access for AI models
- **Security Impact**: Medium - access to technical documentation
- **Recommendation**: Use read-only access where possible

#### Jina API Key
- **Purpose**: Web search and content extraction
- **Security Impact**: Medium - can access web content
- **Recommendation**: Monitor usage for automated access patterns

#### Tavily API Key
- **Purpose**: Advanced web search capabilities
- **Security Impact**: Medium - comprehensive web search
- **Recommendation**: Set rate limits and monitor costs

#### GitHub Token
- **Purpose**: Code repository access and assistance
- **Security Impact**: High - repository access
- **Recommendation**: Use fine-grained personal access tokens with minimal scope

#### Supabase Token
- **Purpose**: Database operations
- **Security Impact**: High - database access
- **Recommendation**: Use read-only tokens where possible

### File System Security

The integration creates files in Home Assistant's `www` directory for media processing:

- **Location**: `/config/www/ai_task_media/`
- **Permissions**: Should be readable by Home Assistant, not publicly writable
- **Cleanup**: Automatic cleanup of temporary files is implemented
- **Validation**: File type and size restrictions are enforced

### Network Security

- All external API communications use HTTPS
- SSL certificate validation is enforced
- Request timeouts are configured to prevent hanging
- Rate limiting is implemented where supported

### Monitoring and Auditing

Enable debug logging to monitor API usage:
```yaml
logger:
  default: info
  logs:
    custom_components.glm_agent_ha: debug
```

### Incident Response

If you suspect API key compromise:

1. **Immediately revoke** the compromised API keys
2. **Generate new keys** from the respective service providers
3. **Update your environment variables**
4. **Restart Home Assistant**
5. **Monitor usage** for any unauthorized access
6. **Review logs** for any suspicious activity

### Security Updates

Security vulnerabilities should be reported privately:
- Create a GitHub issue with the "security" label
- Do not disclose security issues in public forums
- Follow responsible disclosure practices

For security questions or concerns, contact the maintainers through private channels.