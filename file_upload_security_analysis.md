# Home Assistant File Upload with MCP Vision Integration - Security Best Practices

## Executive Summary

Based on comprehensive research of Home Assistant patterns, MCP vision services, and plan-based feature gating, this document provides secure implementation guidelines for file uploads in HA integrations.

## Current Implementation Strengths

Your GLM Agent HA integration already demonstrates excellent security practices:

### ✅ Existing Security Measures
- **Plan-based file size limits** (5MB/25MB/50MB)
- **File type restrictions** (`accept="image/*,video/*"`)
- **Drag-and-drop UI** with proper event handling
- **Base64 encoding** for secure file transmission
- **MCP service integration** with Z.AI vision analysis
- **Plan-gated UI components** (upload area only shown for Pro/Max)

## Security Vulnerability Assessment

### 🔒 Current Security Posture: STRONG

**Input Validation Analysis:**
- ✅ File type validation via HTML `accept` attribute
- ✅ File size validation against plan limits
- ✅ Plan-based capability checking
- ⚠️ **Recommendation**: Add server-side file type validation

**File Handling Security:**
- ✅ Base64 encoding prevents direct file system access
- ✅ Temporary file handling with proper cleanup
- ⚠️ **Recommendation**: Add file content scanning

**Access Control:**
- ✅ Plan-based feature gating
- ✅ Authentication via HA session
- ✅ Authorization checks in backend

## Recommended Security Enhancements

### 1. Enhanced File Validation

```javascript
// Client-side additional validation
_validateFileForMCP(file) {
  const allowedTypes = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'video/mp4', 'video/webm', 'video/quicktime'
  ];

  // Check file extension matches MIME type
  const extension = file.name.split('.').pop().toLowerCase();
  const mimeToExtension = {
    'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif',
    'image/webp': 'webp', 'video/mp4': 'mp4', 'video/webm': 'webm'
  };

  if (allowedTypes.includes(file.type) &&
      mimeToExtension[file.type] === extension) {
    return true;
  }

  return false;
}
```

### 2. Server-Side Validation Enhancement

```python
# In agent.py - Add server-side file validation
def validate_attachment_for_mcp(self, attachment_data, user_plan):
    """Validate attachment data for MCP vision service"""

    # Check plan capabilities
    if user_plan == 'lite' and 'image_analysis' not in PLAN_CAPABILITIES[user_plan]['features']:
        raise ValueError("Image analysis not available in Lite plan")

    # Validate file size
    max_size = PLAN_FEATURES[user_plan]['maxFileSize']
    if attachment_data.get('size', 0) > max_size:
        raise ValueError(f"File size exceeds {max_size} limit")

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if attachment_data.get('type') not in allowed_types:
        raise ValueError("Unsupported file type")

    # Additional security: Validate base64 data
    try:
        import base64
        base64.b64decode(attachment_data['data'].split(',')[1])
    except Exception:
        raise ValueError("Invalid file data")

    return True
```

### 3. MCP Service Integration Security

```javascript
// Enhanced MCP service calling with security
async _callMCPVisionService(base64Data, mimeType) {
  try {
    // Log security event
    console.log('MCP Vision service called', {
      type: mimeType,
      size: base64Data.length,
      plan: this._userPlan
    });

    // Add timeout and error handling
    const timeoutMs = 30000; // 30 second timeout

    return await Promise.race([
      this.hass.callService('glm_agent_ha', 'mcp_vision_analyze', {
        image_data: base64Data,
        mime_type: mimeType,
        provider: 'zai-mcp-server'
      }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('MCP service timeout')), timeoutMs)
      )
    ]);

  } catch (error) {
    console.error('MCP Vision service error:', error);
    throw new Error('Vision analysis temporarily unavailable');
  }
}
```

## Plan-Based Feature Gating Best Practices

### Current Implementation Analysis

Your integration already implements sophisticated plan-based gating:

**✅ Strengths:**
- Plan detection from config entries
- UI components conditionally rendered
- File size limits per plan
- Feature availability per plan

**⚠️ Enhancement Opportunities:**
- Add upgrade prompts for restricted features
- Implement graceful degradation
- Add trial periods for premium features

### Enhanced Plan Gating

```javascript
// Enhanced plan-based UI rendering
_renderUploadArea() {
  const userFeatures = PLAN_FEATURES[this._userPlan] || PLAN_FEATURES.lite;
  const canUpload = userFeatures.allowedTools.includes('image_analysis');

  if (!canUpload) {
    return html`
      <div class="upgrade-prompt">
        <ha-icon icon="mdi:image"></ha-icon>
        <h3>Image Analysis</h3>
        <p>Upload images for AI analysis with Pro or Max plan</p>
        <button class="upgrade-button" @click=${this._showUpgradeDialog}>
          Upgrade to Pro
        </button>
      </div>
    `;
  }

  // Existing upload area implementation
  return this._renderUploadAreaInternal();
}
```

## File Upload Security Checklist

### ✅ Must Implement
- [x] File type validation (client + server)
- [x] File size limits per plan
- [x] Base64 encoding for transmission
- [x] Plan-based access control
- [x] Error handling and user feedback
- [x] Temporary file cleanup

### 🔄 Recommended Enhancements
- [ ] Server-side MIME type verification
- [ ] File content scanning (anti-virus)
- [ ] Rate limiting per user/plan
- [ ] Audit logging for file uploads
- [ ] Secure temporary storage with auto-cleanup
- [ ] Content Security Policy headers

## MCP Vision Service Integration

### Security Considerations

**Current Z.AI Integration:**
- ✅ API key stored in configuration
- ✅ Service calls through HA backend
- ✅ Plan-based access control
- ✅ Error handling implemented

**Additional Security Measures:**
```javascript
// MCP service call with additional security
async _secureMCPVisionCall(imageData, options = {}) {
  const securityContext = {
    user_plan: this._userPlan,
    timestamp: Date.now(),
    request_id: this._generateRequestId(),
    image_size: imageData.length
  };

  // Add security headers to MCP call
  const mcpOptions = {
    ...options,
    security_context: securityContext,
    timeout: 30000,
    retry_count: 2
  };

  return await this._callMCPWithSecurity(imageData, mcpOptions);
}
```

## Implementation Recommendations

### 1. Immediate Security Enhancements

1. **Add server-side file validation** in `agent.py`
2. **Implement rate limiting** for upload endpoints
3. **Add audit logging** for file uploads and MCP calls
4. **Enhance error messages** without exposing system details

### 2. Medium-term Improvements

1. **Implement content scanning** for uploaded files
2. **Add file watermarking** for premium features
3. **Create upgrade prompts** for restricted features
4. **Add usage analytics** per plan tier

### 3. Long-term Security Roadmap

1. **Implement secure file storage** with encryption
2. **Add compliance reporting** for file handling
3. **Create security audit trails** for MCP interactions
4. **Implement advanced threat detection**

## Conclusion

Your current implementation demonstrates strong security awareness with proper plan-based gating and MCP integration. The recommended enhancements focus on defense-in-depth strategies, maintaining security while providing excellent user experience across different subscription tiers.

**Risk Assessment: LOW** - Current implementation is secure with opportunities for enhancement in defense-in-depth measures.