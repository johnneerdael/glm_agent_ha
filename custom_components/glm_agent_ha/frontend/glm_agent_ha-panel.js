import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

console.log("GLM Agent HA Modern Panel loading...");

const PROVIDERS = {
  openai: "GLM Coding Plan OpenAI",
};

const PLAN_FEATURES = {
  lite: {
    maxFileSize: 5 * 1024 * 1024, // 5MB
    allowedTools: ['basic_query', 'automation_creation', 'dashboard_creation'],
    smartCategories: ['basic', 'automation']
  },
  pro: {
    maxFileSize: 25 * 1024 * 1024, // 25MB
    allowedTools: ['basic_query', 'automation_creation', 'dashboard_creation', 'image_analysis', 'performance_monitoring'],
    smartCategories: ['basic', 'automation', 'visual', 'diagnostics']
  },
  max: {
    maxFileSize: 50 * 1024 * 1024, // 50MB
    allowedTools: ['basic_query', 'automation_creation', 'dashboard_creation', 'image_analysis', 'video_analysis', 'performance_monitoring', 'security_analysis', 'web_search'],
    smartCategories: ['basic', 'automation', 'visual', 'diagnostics', 'security', 'advanced']
  }
};

// Smart Quick Questions organized by capability and complexity
const SMART_PROMPTS = {
  basic: [
    {
      text: "Show me my home's energy usage patterns",
      icon: "mdi:chart-line",
      tools: ["basic_query"],
      description: "Analyze energy consumption across devices"
    },
    {
      text: "Optimize my lighting automation",
      icon: "mdi:lightbulb-auto",
      tools: ["automation_creation", "basic_query"],
      description: "Create intelligent lighting schedules"
    },
    {
      text: "Review my security setup",
      icon: "mdi:shield-check",
      tools: ["basic_query", "security_analysis"],
      description: "Check security sensors and coverage"
    }
  ],
  automation: [
    {
      text: "Create adaptive routines based on my habits",
      icon: "mdi:brain",
      tools: ["automation_creation", "performance_monitoring"],
      description: "AI learns from your usage patterns"
    },
    {
      text: "Build multi-room scene automations",
      icon: "mdi:home-group",
      tools: ["automation_creation", "basic_query"],
      description: "Coordinate devices across areas"
    },
    {
      text: "Energy optimization automations",
      icon: "mdi:leaf",
      tools: ["automation_creation", "performance_monitoring"],
      description: "Reduce consumption intelligently"
    }
  ],
  visual: [
    {
      text: "📷 Analyze security camera snapshot",
      icon: "mdi:camera",
      tools: ["image_analysis"],
      requiresUpload: true,
      description: "Upload photo for AI analysis"
    },
    {
      text: "🏠 Room optimization from photo",
      icon: "mdi:home-analytics",
      tools: ["image_analysis", "automation_creation"],
      requiresUpload: true,
      description: "Suggest improvements from room photo"
    },
    {
      text: "📸 Decode appliance error message",
      icon: "mdi:wrench",
      tools: ["image_analysis"],
      requiresUpload: true,
      description: "Analyze error displays and codes"
    }
  ],
  diagnostics: [
    {
      text: "🔍 Complete system health check",
      icon: "mdi:pulse",
      tools: ["performance_monitoring", "basic_query"],
      description: "Comprehensive performance analysis"
    },
    {
      text: "📊 Performance bottleneck analysis",
      icon: "mdi:speedometer",
      tools: ["performance_monitoring"],
      description: "Identify and fix slow operations"
    },
    {
      text: "🔧 Entity relationship diagnostics",
      icon: "mdi:connection",
      tools: ["basic_query"],
      description: "Find device conflicts and issues"
    }
  ],
  security: [
    {
      text: "🛡️ Security threat assessment",
      icon: "mdi:shield-alert",
      tools: ["security_analysis", "performance_monitoring"],
      description: "Analyze security logs and patterns"
    },
    {
      text: "🚨 Suspicious activity detection",
      icon: "mdi:eye-check",
      tools: ["security_analysis"],
      description: "Review unusual access patterns"
    },
    {
      text: "🔐 Access control optimization",
      icon: "mdi:lock",
      tools: ["security_analysis", "automation_creation"],
      description: "Improve security automations"
    }
  ],
  advanced: [
    {
      text: "🧠 Teach me advanced HA techniques",
      icon: "mdi:school",
      tools: ["web_search", "basic_query"],
      description: "Learn from your setup patterns"
    },
    {
      text: "🎯 Custom AI agent training",
      icon: "mdi:robot",
      tools: ["basic_query", "performance_monitoring"],
      description: "Optimize AI for your home"
    },
    {
      text: "📹 Video analysis for security",
      icon: "mdi:video",
      tools: ["video_analysis"],
      requiresUpload: true,
      description: "Analyze security footage"
    }
  ]
};

class GLMAgentHaPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object, reflect: false, attribute: false },
      narrow: { type: Boolean, reflect: false, attribute: false },
      panel: { type: Object, reflect: false, attribute: false },
      _messages: { type: Array, reflect: false, attribute: false },
      _isLoading: { type: Boolean, reflect: false, attribute: false },
      _error: { type: String, reflect: false, attribute: false },
      _pendingAutomation: { type: Object, reflect: false, attribute: false },
      _promptHistory: { type: Array, reflect: false, attribute: false },
      _showPredefinedPrompts: { type: Boolean, reflect: false, attribute: false },
      _showPromptHistory: { type: Boolean, reflect: false, attribute: false },
      _selectedPrompts: { type: Array, reflect: false, attribute: false },
      _selectedProvider: { type: String, reflect: false, attribute: false },
      _availableProviders: { type: Array, reflect: false, attribute: false },
      _selectedModel: { type: String, reflect: false, attribute: false },
      _userPlan: { type: String, reflect: false, attribute: false },
      _showAdvancedDashboard: { type: Boolean, reflect: false, attribute: false },
      _uploadedFile: { type: Object, reflect: false, attribute: false },
      _dragActive: { type: Boolean, reflect: false, attribute: false },
      _performanceMetrics: { type: Object, reflect: false, attribute: false },
      _securityReport: { type: Object, reflect: false, attribute: false },
      _mcpStatus: { type: Object, reflect: false, attribute: false }
    };
  }

  static get styles() {
    return css`
      :host {
        background: var(--primary-background-color);
        -webkit-font-smoothing: antialiased;
        display: flex;
        flex-direction: column;
        height: 100vh;
      }

      /* Header Styles */
      .header {
        background: var(--app-header-background-color);
        color: var(--app-header-text-color);
        padding: 16px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 20px;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        position: relative;
        min-height: 64px;
      }

      .header-title {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-grow: 1;
        min-width: 0;
      }

      .header-badges {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .plan-badge {
        background: var(--primary-color);
        color: var(--text-primary-color);
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
      }

      .plan-badge.pro {
        background: var(--success-color, #4caf50);
      }

      .plan-badge.max {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .icon-button {
        appearance: none;
        border: none;
        background: transparent;
        color: var(--app-header-text-color);
        cursor: pointer;
        padding: 8px;
        border-radius: 8px;
        transition: background-color 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .icon-button:hover {
        background: rgba(255, 255, 255, 0.1);
      }

      .clear-button {
        appearance: none;
        border: none;
        border-radius: 16px;
        background: var(--error-color);
        color: white;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 0 12px;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(0,0,0,0.08);
        height: 32px;
        flex-shrink: 0;
        margin-left: 12px;
      }

      .clear-button[disabled] {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .clear-button:hover:not([disabled]) {
        opacity: 0.9;
        box-shadow: 0 2px 6px rgba(0,0,0,0.13);
      }

      /* Content Area */
      .content {
        flex-grow: 1;
        padding: 24px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
      }

      .chat-container {
        width: 100%;
        padding: 0;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        height: 100%;
      }

      /* Messages */
      .messages {
        overflow-y: auto;
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        margin-bottom: 24px;
        padding: 0;
        background: var(--primary-background-color);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        flex-grow: 1;
        width: 100%;
      }

      .message {
        margin-bottom: 16px;
        padding: 12px 16px;
        border-radius: 12px;
        max-width: 80%;
        line-height: 1.5;
        animation: fadeIn 0.3s ease-out;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        word-wrap: break-word;
      }

      .user-message {
        background: var(--primary-color);
        color: var(--text-primary-color);
        margin-left: auto;
        border-bottom-right-radius: 4px;
      }

      .assistant-message {
        background: var(--secondary-background-color);
        margin-right: auto;
        border-bottom-left-radius: 4px;
      }

      .message-attachment {
        margin-top: 8px;
        padding: 8px;
        background: rgba(0, 0, 0, 0.05);
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .message-attachment ha-icon {
        color: var(--primary-color);
      }

      /* Smart Prompts Section */
      .prompts-section {
        margin-bottom: 12px;
        padding: 16px;
        background: var(--secondary-background-color);
        border-radius: 16px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
        border: 1px solid var(--divider-color);
      }

      .prompts-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
      }

      .prompts-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--primary-text-color);
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .prompts-categories {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
        flex-wrap: wrap;
      }

      .category-tab {
        background: var(--primary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 20px;
        padding: 6px 12px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 12px;
        font-weight: 500;
        color: var(--secondary-text-color);
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .category-tab.active {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border-color: var(--primary-color);
      }

      .category-tab:hover:not(.active) {
        border-color: var(--primary-color);
        color: var(--primary-color);
      }

      .prompt-bubbles {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .smart-prompt {
        background: var(--primary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        padding: 12px 16px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 13px;
        line-height: 1.4;
        color: var(--primary-text-color);
        max-width: 300px;
        position: relative;
        overflow: hidden;
      }

      .smart-prompt:hover {
        border-color: var(--primary-color);
        background: var(--primary-color);
        color: var(--text-primary-color);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      }

      .smart-prompt-content {
        display: flex;
        align-items: flex-start;
        gap: 8px;
      }

      .smart-prompt-icon {
        --mdc-icon-size: 20px;
        flex-shrink: 0;
        margin-top: 2px;
      }

      .smart-prompt-text {
        flex-grow: 1;
        font-weight: 500;
      }

      .smart-prompt-description {
        font-size: 11px;
        opacity: 0.8;
        margin-top: 4px;
        font-weight: 400;
      }

      .smart-prompt-upload-indicator {
        position: absolute;
        top: 6px;
        right: 6px;
        background: var(--warning-color, #ff9800);
        color: white;
        border-radius: 50%;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 600;
      }

      /* History Section */
      .history-bubble {
        background: var(--primary-background-color);
        border: 1px solid var(--accent-color);
        border-radius: 20px;
        padding: 6px 12px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 12px;
        line-height: 1.3;
        color: var(--accent-color);
        white-space: nowrap;
        max-width: 180px;
        overflow: hidden;
        text-overflow: ellipsis;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .history-bubble:hover {
        background: var(--accent-color);
        color: var(--text-primary-color);
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }

      .history-delete {
        opacity: 0;
        transition: opacity 0.2s ease;
        color: var(--error-color);
        cursor: pointer;
        --mdc-icon-size: 14px;
      }

      .history-bubble:hover .history-delete {
        opacity: 1;
        color: var(--text-primary-color);
      }

      /* File Upload Area */
      .upload-area {
        border: 2px dashed var(--divider-color);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        text-align: center;
        transition: all 0.2s ease;
        background: var(--secondary-background-color);
      }

      .upload-area.drag-active {
        border-color: var(--primary-color);
        background: rgba(var(--primary-color-rgb), 0.05);
      }

      .upload-area:hover {
        border-color: var(--primary-color);
      }

      .upload-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }

      .upload-icon {
        --mdc-icon-size: 48px;
        color: var(--secondary-text-color);
      }

      .upload-text {
        color: var(--primary-text-color);
        font-size: 14px;
        font-weight: 500;
      }

      .upload-subtext {
        color: var(--secondary-text-color);
        font-size: 12px;
      }

      .upload-button {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .upload-button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
      }

      /* File Preview */
      .file-preview {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: var(--secondary-background-color);
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid var(--divider-color);
      }

      .file-preview-info {
        flex-grow: 1;
      }

      .file-preview-name {
        font-weight: 500;
        color: var(--primary-text-color);
        font-size: 14px;
      }

      .file-preview-size {
        color: var(--secondary-text-color);
        font-size: 12px;
      }

      .file-preview-remove {
        background: var(--error-color);
        color: white;
        border: none;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      /* Input Container */
      .input-container {
        position: relative;
        width: 100%;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
      }

      .input-container:focus-within {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(var(--primary-color-rgb), 0.1);
      }

      .input-main {
        display: flex;
        align-items: flex-end;
        padding: 12px;
        gap: 12px;
      }

      .input-wrapper {
        flex-grow: 1;
        position: relative;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
      }

      textarea {
        width: 100%;
        min-height: 24px;
        max-height: 200px;
        padding: 12px 16px;
        border: none;
        outline: none;
        resize: none;
        font-size: 16px;
        line-height: 1.5;
        background: transparent;
        color: var(--primary-text-color);
        font-family: inherit;
        border-radius: 8px;
      }

      textarea::placeholder {
        color: var(--secondary-text-color);
      }

      .input-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px 12px 16px;
        border-top: 1px solid var(--divider-color);
        background: var(--card-background-color);
        border-radius: 0 0 12px 12px;
      }

      .input-controls {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .provider-selector {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .provider-label {
        font-size: 12px;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }

      .provider-button {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        background: var(--secondary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        cursor: pointer;
        font-size: 12px;
        font-weight: 500;
        color: var(--primary-text-color);
        transition: all 0.2s ease;
        min-width: 120px;
      }

      .provider-button:hover {
        background-color: var(--primary-background-color);
        border-color: var(--primary-color);
      }

      .send-button {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .send-button:hover:not(:disabled) {
        opacity: 0.9;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }

      .send-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      /* Loading States */
      .loading {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
        padding: 16px;
        border-radius: 12px;
        background: var(--secondary-background-color);
        margin-right: auto;
        max-width: 80%;
        animation: fadeIn 0.3s ease-out;
      }

      .loading-dots {
        display: flex;
        gap: 4px;
      }

      .dot {
        width: 8px;
        height: 8px;
        background: var(--primary-color);
        border-radius: 50%;
        animation: bounce 1.4s infinite ease-in-out;
      }

      .dot:nth-child(1) { animation-delay: -0.32s; }
      .dot:nth-child(2) { animation-delay: -0.16s; }

      @keyframes bounce {
        0%, 80%, 100% {
          transform: scale(0);
        }
        40% {
          transform: scale(1.0);
        }
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      /* Error State */
      .error {
        color: var(--error-color);
        padding: 16px;
        margin: 8px 0;
        border-radius: 12px;
        background: var(--error-background-color);
        border: 1px solid var(--error-color);
        animation: fadeIn 0.3s ease-out;
      }

      /* Advanced Dashboard */
      .advanced-dashboard {
        position: fixed;
        top: 0;
        right: -400px;
        width: 400px;
        height: 100vh;
        background: var(--primary-background-color);
        box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
        transition: right 0.3s ease;
        z-index: 1000;
        display: flex;
        flex-direction: column;
      }

      .advanced-dashboard.open {
        right: 0;
      }

      .dashboard-header {
        padding: 16px;
        border-bottom: 1px solid var(--divider-color);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }

      .dashboard-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .dashboard-content {
        flex-grow: 1;
        overflow-y: auto;
        padding: 16px;
      }

      .dashboard-section {
        margin-bottom: 24px;
      }

      .dashboard-section-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-text-color);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .dashboard-metric {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
      }

      .dashboard-metric-label {
        font-size: 13px;
        color: var(--secondary-text-color);
      }

      .dashboard-metric-value {
        font-size: 13px;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      /* Automation and Dashboard Suggestions */
      .automation-suggestion, .dashboard-suggestion {
        background: var(--secondary-background-color);
        border: 1px solid var(--primary-color);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        position: relative;
        z-index: 10;
      }

      .automation-title, .dashboard-title {
        font-weight: 500;
        margin-bottom: 8px;
        color: var(--primary-color);
        font-size: 16px;
      }

      .automation-description, .dashboard-description {
        margin-bottom: 16px;
        color: var(--secondary-text-color);
        line-height: 1.4;
      }

      .automation-actions, .dashboard-actions {
        display: flex;
        gap: 8px;
        margin-top: 16px;
        justify-content: flex-end;
      }

      .automation-actions ha-button, .dashboard-actions ha-button {
        --mdc-button-height: 40px;
        --mdc-button-padding: 0 20px;
        --mdc-typography-button-font-size: 14px;
        --mdc-typography-button-font-weight: 600;
        border-radius: 20px;
      }

      .automation-actions ha-button:first-child,
      .dashboard-actions ha-button:first-child {
        --mdc-theme-primary: var(--success-color, #4caf50);
        --mdc-theme-on-primary: #fff;
      }

      .automation-actions ha-button:last-child,
      .dashboard-actions ha-button:last-child {
        --mdc-theme-primary: var(--error-color);
        --mdc-theme-on-primary: #fff;
      }

      .automation-details, .dashboard-details {
        margin-top: 8px;
        padding: 8px;
        background: var(--primary-background-color);
        border-radius: 8px;
        font-family: monospace;
        font-size: 12px;
        white-space: pre-wrap;
        overflow-x: auto;
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid var(--divider-color);
      }

      /* Responsive Design */
      @media (max-width: 768px) {
        .header {
          padding: 12px 16px;
          font-size: 18px;
          min-height: 56px;
        }

        .content {
          padding: 16px;
        }

        .smart-prompt {
          max-width: 100%;
        }

        .advanced-dashboard {
          width: 100vw;
          right: -100vw;
        }

        .prompts-categories {
          gap: 4px;
        }

        .category-tab {
          font-size: 11px;
          padding: 4px 8px;
        }
      }

      @media (max-width: 480px) {
        .header {
          padding: 10px 12px;
          font-size: 16px;
          min-height: 48px;
        }

        .content {
          padding: 12px;
        }

        .clear-button span {
          display: none;
        }

        .header-badges {
          display: none;
        }
      }
    `;
  }

  constructor() {
    super();
    this._messages = [];
    this._isLoading = false;
    this._error = null;
    this._pendingAutomation = null;
    this._promptHistory = [];
    this._promptHistoryLoaded = false;
    this._showPredefinedPrompts = true;
    this._showPromptHistory = true;
    this._selectedPrompts = [];
    this._selectedProvider = null;
    this._selectedModel = 'GLM-4.6';
    this._models = ['GLM-4.6', 'GLM-4.5', 'GLM-4.5-air'];
    this._availableProviders = [];
    this._showProviderDropdown = false;
    this.providersLoaded = false;
    this._eventSubscriptionSetup = false;
    this._serviceCallTimeout = null;

    // New properties for modern features
    this._userPlan = 'lite';
    this._showAdvancedDashboard = false;
    this._uploadedFile = null;
    this._dragActive = false;
    this._performanceMetrics = null;
    this._securityReport = null;
    this._mcpStatus = null;
    this._activeCategory = 'basic';

    console.debug("GLM Agent HA Modern Panel constructor called");
  }

  _getSmartPromptsForCategory(category) {
    const prompts = SMART_PROMPTS[category] || [];
    const userFeatures = PLAN_FEATURES[this._userPlan] || PLAN_FEATURES.lite;

    // Filter prompts based on user's plan capabilities
    return prompts.filter(prompt => {
      return prompt.tools.some(tool => userFeatures.allowedTools.includes(tool));
    });
  }

  _getRandomPrompts(category = null) {
    const categories = category ? [category] : PLAN_FEATURES[this._userPlan]?.smartCategories || ['basic'];
    const allPrompts = [];

    categories.forEach(cat => {
      allPrompts.push(...this._getSmartPromptsForCategory(cat));
    });

    // Shuffle and take 3-5 prompts
    const shuffled = [...allPrompts].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, Math.min(3, shuffled.length));
  }

  async connectedCallback() {
    super.connectedCallback();
    console.debug("GLM Agent HA Modern Panel connected");

    if (this.hass && !this._eventSubscriptionSetup) {
      this._eventSubscriptionSetup = true;
      this.hass.connection.subscribeEvents(
        (event) => this._handleResponse(event),
        'glm_agent_ha_response'
      );
      console.debug("Event subscription set up in connectedCallback()");
      await this._loadPromptHistory();
      await this._detectUserPlan();
      await this._loadAdvancedData();
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!this.shadowRoot.querySelector('.provider-selector')?.contains(e.target)) {
        this._showProviderDropdown = false;
      }
    });
  }

  async _detectUserPlan() {
    try {
      // Try to detect user plan from config entries
      const allEntries = await this.hass.callWS({ type: 'config_entries/get' });
      const aiAgentEntries = allEntries.filter(entry => entry.domain === 'glm_agent_ha');

      if (aiAgentEntries.length > 0) {
        const entry = aiAgentEntries[0];
        const plan = entry.data?.plan || entry.options?.plan || 'lite';
        this._userPlan = plan;
        console.debug("Detected user plan:", plan);

        // Update selected prompts based on plan
        this._selectedPrompts = this._getRandomPrompts();
      }
    } catch (error) {
      console.error("Error detecting user plan:", error);
      this._userPlan = 'lite';
    }
  }

  async _loadAdvancedData() {
    if (this._userPlan === 'pro' || this._userPlan === 'max') {
      try {
        // Load performance metrics
        const perfResult = await this.hass.callService('glm_agent_ha', 'performance_current');
        if (perfResult && !perfResult.error) {
          this._performanceMetrics = perfResult;
        }

        // Load security report
        const secResult = await this.hass.callService('glm_agent_ha', 'security_report', { hours: 24 });
        if (secResult && !secResult.error) {
          this._securityReport = secResult;
        }
      } catch (error) {
        console.debug("Error loading advanced data:", error);
      }
    }
  }

  async updated(changedProps) {
    console.debug("Updated called with:", changedProps);

    // Set up event subscription when hass becomes available
    if (changedProps.has('hass') && this.hass && !this._eventSubscriptionSetup) {
      this._eventSubscriptionSetup = true;
      this.hass.connection.subscribeEvents(
        (event) => this._handleResponse(event),
        'glm_agent_ha_response'
      );
      console.debug("Event subscription set up in updated()");
    }

    // Load providers when hass becomes available
    if (changedProps.has('hass') && this.hass && !this.providersLoaded) {
      this.providersLoaded = true;

      try {
        console.debug("Loading AI providers...");
        const allEntries = await this.hass.callWS({ type: 'config_entries/get' });
        const aiAgentEntries = allEntries.filter(entry => entry.domain === 'glm_agent_ha');

        if (aiAgentEntries.length > 0) {
          this._availableProviders = aiAgentEntries.map(entry => {
            let provider = "unknown";

            if (entry.data && entry.data.ai_provider) {
              provider = entry.data.ai_provider;
            } else {
              const titleToProviderMap = {
                "GLM Coding Plan Agent HA (GLM Coding Plan OpenAI Endpoint)": "openai",
                "GLM Coding Plan Agent HA (GLM Coding Plan API)": "openai",
              };
              provider = titleToProviderMap[entry.title] || "unknown";
            }

            // Detect plan from entry
            const plan = entry.data?.plan || entry.options?.plan || 'lite';
            if (plan !== this._userPlan) {
              this._userPlan = plan;
              this._selectedPrompts = this._getRandomPrompts();
            }

            return {
              value: provider,
              label: PROVIDERS[provider] || provider,
              plan: plan
            };
          });

          console.debug("Available AI providers:", this._availableProviders);

          if (!this._selectedProvider && this._availableProviders.length > 0) {
            this._selectedProvider = this._availableProviders[0].value;
            console.debug("Auto-selected first provider:", this._selectedProvider);
          }
        } else {
          console.debug("No 'glm_agent_ha' config entries found via WebSocket.");
          this._availableProviders = [];
        }
      } catch (error) {
        console.error("Error fetching config entries via WebSocket:", error);
        this._error = error.message || 'Failed to load AI provider configurations.';
        this._availableProviders = [];
      }
      this.requestUpdate();
    }

    // Load prompt history when hass becomes available
    if (changedProps.has('hass') && this.hass && !this._promptHistoryLoaded) {
      this._promptHistoryLoaded = true;
      await this._loadPromptHistory();
    }

    // Load prompt history when provider changes
    if (changedProps.has('_selectedProvider') && this._selectedProvider && this.hass) {
      await this._loadPromptHistory();
    }

    if (changedProps.has('_messages') || changedProps.has('_isLoading')) {
      this._scrollToBottom();
    }
  }

  _renderPromptsSection() {
    const categories = Object.keys(SMART_PROMPTS).filter(cat =>
      PLAN_FEATURES[this._userPlan]?.smartCategories.includes(cat)
    );

    return html`
      <div class="prompts-section">
        <div class="prompts-header">
          <div class="prompts-title">
            <ha-icon icon="mdi:lightbulb"></ha-icon>
            Smart Actions
          </div>
          <div style="display: flex; gap: 12px;">
            <div class="prompts-toggle" @click=${() => this._togglePredefinedPrompts()}>
              <ha-icon icon="${this._showPredefinedPrompts ? 'mdi:chevron-up' : 'mdi:chevron-down'}"></ha-icon>
              <span>Actions</span>
            </div>
            ${this._promptHistory.length > 0 ? html`
              <div class="prompts-toggle" @click=${() => this._togglePromptHistory()}>
                <ha-icon icon="${this._showPromptHistory ? 'mdi:chevron-up' : 'mdi:chevron-down'}"></ha-icon>
                <span>Recent</span>
              </div>
            ` : ''}
          </div>
        </div>

        ${this._showPredefinedPrompts ? html`
          <div class="prompts-categories">
            ${categories.map(category => html`
              <div class="category-tab ${this._activeCategory === category ? 'active' : ''}"
                   @click=${() => this._selectCategory(category)}>
                <ha-icon icon="mdi:${this._getCategoryIcon(category)}"></ha-icon>
                ${this._capitalizeFirst(category)}
              </div>
            `)}
          </div>

          <div class="prompt-bubbles">
            ${this._selectedPrompts.map(prompt => html`
              <div class="smart-prompt" @click=${() => this._useSmartPrompt(prompt)}>
                <div class="smart-prompt-content">
                  <ha-icon class="smart-prompt-icon" icon="${prompt.icon}"></ha-icon>
                  <div>
                    <div class="smart-prompt-text">${prompt.text}</div>
                    <div class="smart-prompt-description">${prompt.description}</div>
                  </div>
                </div>
                ${prompt.requiresUpload ? html`
                  <div class="smart-prompt-upload-indicator">
                    <ha-icon icon="mdi:upload"></ha-icon>
                  </div>
                ` : ''}
              </div>
            `)}
          </div>
        ` : ''}

        ${this._showPromptHistory && this._promptHistory.length > 0 ? html`
          <div class="prompt-bubbles">
            ${this._promptHistory.slice(-3).reverse().map((prompt, index) => html`
              <div class="history-bubble" @click=${(e) => this._useHistoryPrompt(e, prompt)}>
                <span style="flex-grow: 1; overflow: hidden; text-overflow: ellipsis;">${prompt}</span>
                <ha-icon
                  class="history-delete"
                  icon="mdi:close"
                  @click=${(e) => this._deleteHistoryItem(e, prompt)}
                ></ha-icon>
              </div>
            `)}
          </div>
        ` : ''}
      </div>
    `;
  }

  _getCategoryIcon(category) {
    const icons = {
      basic: 'star',
      automation: 'robot',
      visual: 'image',
      diagnostics: 'pulse',
      security: 'shield',
      advanced: 'brain'
    };
    return icons[category] || 'help-circle';
  }

  _capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  _selectCategory(category) {
    this._activeCategory = category;
    this._selectedPrompts = this._getRandomPrompts(category);
    this.requestUpdate();
  }

  _togglePredefinedPrompts() {
    this._showPredefinedPrompts = !this._showPredefinedPrompts;
    if (this._showPredefinedPrompts) {
      this._selectedPrompts = this._getRandomPrompts(this._activeCategory);
    }
  }

  _togglePromptHistory() {
    this._showPromptHistory = !this._showPromptHistory;
  }

  _useSmartPrompt(prompt) {
    if (this._isLoading) return;

    if (prompt.requiresUpload && !this._uploadedFile) {
      // Focus on upload area
      this.shadowRoot.querySelector('.upload-area')?.scrollIntoView({ behavior: 'smooth' });
      return;
    }

    const promptEl = this.shadowRoot.querySelector('#prompt');
    if (promptEl) {
      promptEl.value = prompt.text;
      promptEl.focus();
    }
  }

  _usePrompt(prompt) {
    if (this._isLoading) return;
    const promptEl = this.shadowRoot.querySelector('#prompt');
    if (promptEl) {
      promptEl.value = prompt;
      promptEl.focus();
    }
  }

  _useHistoryPrompt(event, prompt) {
    event.stopPropagation();
    if (this._isLoading) return;
    const promptEl = this.shadowRoot.querySelector('#prompt');
    if (promptEl) {
      promptEl.value = prompt;
      promptEl.focus();
    }
  }

  async _deleteHistoryItem(event, prompt) {
    event.stopPropagation();
    this._promptHistory = this._promptHistory.filter(p => p !== prompt);
    await this._savePromptHistory();
    this.requestUpdate();
  }

  async _addToHistory(prompt) {
    if (!prompt || prompt.trim().length === 0) return;

    this._promptHistory = this._promptHistory.filter(p => p !== prompt);
    this._promptHistory.push(prompt);

    if (this._promptHistory.length > 20) {
      this._promptHistory = this._promptHistory.slice(-20);
    }

    await this._savePromptHistory();
    this.requestUpdate();
  }

  async _loadPromptHistory() {
    // Implementation remains the same as original
    if (!this.hass) return;

    console.debug('Loading prompt history...');
    try {
      const result = await this.hass.callService('glm_agent_ha', 'load_prompt_history', {
        provider: this._selectedProvider
      });

      if (result && result.response && result.response.history) {
        this._promptHistory = result.response.history;
        this.requestUpdate();
      }
    } catch (error) {
      console.error('Error loading prompt history:', error);
    }
  }

  async _savePromptHistory() {
    if (!this.hass) return;

    try {
      await this.hass.callService('glm_agent_ha', 'save_prompt_history', {
        history: this._promptHistory,
        provider: this._selectedProvider
      });
    } catch (error) {
      console.error('Error saving prompt history:', error);
    }
  }

  _renderUploadArea() {
    const userFeatures = PLAN_FEATURES[this._userPlan] || PLAN_FEATURES.lite;
    const canUpload = userFeatures.allowedTools.includes('image_analysis');

    if (!canUpload) return '';

    return html`
      ${!this._uploadedFile ? html`
        <div class="upload-area ${this._dragActive ? 'drag-active' : ''}"
             @dragover=${this._handleDragOver}
             @dragleave=${this._handleDragLeave}
             @drop=${this._handleDrop}>
          <div class="upload-content">
            <ha-icon class="upload-icon" icon="mdi:cloud-upload"></ha-icon>
            <div class="upload-text">Drop image here or click to upload</div>
            <div class="upload-subtext">
              Max size: ${Math.round(userFeatures.maxFileSize / (1024 * 1024))}MB
            </div>
            <button class="upload-button" @click=${this._handleFileSelect}>
              Choose File
            </button>
            <input type="file"
                   id="file-input"
                   style="display: none"
                   accept="image/*,video/*"
                   @change=${this._handleFileChange}>
          </div>
        </div>
      ` : html`
        <div class="file-preview">
          <ha-icon icon="mdi:file-image"></ha-icon>
          <div class="file-preview-info">
            <div class="file-preview-name">${this._uploadedFile.name}</div>
            <div class="file-preview-size">${this._formatFileSize(this._uploadedFile.size)}</div>
          </div>
          <button class="file-preview-remove" @click=${this._removeUploadedFile}>
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
      `}
    `;
  }

  _handleDragOver(e) {
    e.preventDefault();
    this._dragActive = true;
  }

  _handleDragLeave(e) {
    e.preventDefault();
    this._dragActive = false;
  }

  _handleDrop(e) {
    e.preventDefault();
    this._dragActive = false;

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      this._processFile(files[0]);
    }
  }

  _handleFileSelect() {
    const fileInput = this.shadowRoot.querySelector('#file-input');
    if (fileInput) {
      fileInput.click();
    }
  }

  _handleFileChange(e) {
    const files = e.target.files;
    if (files.length > 0) {
      this._processFile(files[0]);
    }
  }

  async _processFile(file) {
    const userFeatures = PLAN_FEATURES[this._userPlan] || PLAN_FEATURES.lite;

    if (file.size > userFeatures.maxFileSize) {
      this._error = `File too large. Maximum size is ${Math.round(userFeatures.maxFileSize / (1024 * 1024))}MB`;
      this.requestUpdate();
      return;
    }

    this._uploadedFile = file;
    this._error = null;
    this.requestUpdate();
  }

  _removeUploadedFile() {
    this._uploadedFile = null;
    const fileInput = this.shadowRoot.querySelector('#file-input');
    if (fileInput) {
      fileInput.value = '';
    }
    this.requestUpdate();
  }

  _formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  render() {
    console.debug("Rendering with state:", {
      messages: this._messages,
      isLoading: this._isLoading,
      error: this._error,
      userPlan: this._userPlan,
      uploadedFile: this._uploadedFile
    });

    return html`
      <div class="header">
        <div class="header-title">
          <ha-icon icon="mdi:robot"></ha-icon>
          GLM Agent HA
          <div class="header-badges">
            <div class="plan-badge ${this._userPlan}">
              ${this._userPlan.toUpperCase()}
            </div>
          </div>
        </div>
        <div class="header-actions">
          ${(this._userPlan === 'pro' || this._userPlan === 'max') ? html`
            <button class="icon-button" @click=${this._toggleAdvancedDashboard}
                    title="Advanced Dashboard">
              <ha-icon icon="mdi:chart-box"></ha-icon>
            </button>
          ` : ''}
          <button class="clear-button" @click=${this._clearChat} ?disabled=${this._isLoading}>
            <ha-icon icon="mdi:delete-sweep"></ha-icon>
            <span>Clear</span>
          </button>
        </div>
      </div>

      <div class="content">
        <div class="chat-container">
          <div class="messages" id="messages">
            ${this._messages.map(msg => html`
              <div class="message ${msg.type}-message">
                ${msg.text}
                ${msg.attachment ? html`
                  <div class="message-attachment">
                    <ha-icon icon="mdi:file-image"></ha-icon>
                    <span>${msg.attachment.name}</span>
                  </div>
                ` : ''}
                ${msg.automation ? this._renderAutomationSuggestion(msg.automation) : ''}
                ${msg.dashboard ? this._renderDashboardSuggestion(msg.dashboard) : ''}
              </div>
            `)}
            ${this._isLoading ? this._renderLoadingIndicator() : ''}
            ${this._error ? html`<div class="error">${this._error}</div>` : ''}
          </div>

          ${this._renderUploadArea()}
          ${this._renderPromptsSection()}

          <div class="input-container">
            <div class="input-main">
              <div class="input-wrapper">
                <textarea
                  id="prompt"
                  placeholder="Ask me anything about your Home Assistant... ${this._uploadedFile ? '(with attached file)' : ''}"
                  ?disabled=${this._isLoading}
                  @keydown=${this._handleKeyDown}
                  @input=${this._autoResize}
                ></textarea>
              </div>
            </div>

            <div class="input-footer">
              <div class="input-controls">
                <div class="provider-selector">
                  <span class="provider-label">Provider:</span>
                  <select
                    class="provider-button"
                    @change=${(e) => this._selectProvider(e.target.value)}
                    .value=${this._selectedProvider || ''}
                  >
                    ${this._availableProviders.map(provider => html`
                      <option
                        value=${provider.value}
                        ?selected=${provider.value === this._selectedProvider}
                      >
                        ${provider.label}
                      </option>
                    `)}
                  </select>
                </div>
                <div class="provider-selector">
                  <span class="provider-label">Model:</span>
                  <select
                    class="provider-button"
                    @change=${this._selectModel}
                    .value=${this._selectedModel}
                  >
                    ${this._models.map(model => html`
                      <option value=${model} ?selected=${model === this._selectedModel}>
                        ${model}
                      </option>
                    `)}
                  </select>
                </div>
              </div>

              <button class="send-button" @click=${this._sendMessage}
                      ?disabled=${this._isLoading || !this._hasProviders()}>
                <ha-icon icon="mdi:send"></ha-icon>
                Send
              </button>
            </div>
          </div>
        </div>
      </div>

      ${this._renderAdvancedDashboard()}
    `;
  }

  _renderLoadingIndicator() {
    return html`
      <div class="loading">
        <span>AI Agent is thinking</span>
        <div class="loading-dots">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>
    `;
  }

  _renderAutomationSuggestion(automation) {
    return html`
      <div class="automation-suggestion">
        <div class="automation-title">${automation.alias}</div>
        <div class="automation-description">${automation.description}</div>
        <div class="automation-details">
          ${JSON.stringify(automation, null, 2)}
        </div>
        <div class="automation-actions">
          <ha-button @click=${() => this._approveAutomation(automation)} .disabled=${this._isLoading}>
            Approve
          </ha-button>
          <ha-button @click=${() => this._rejectAutomation()} .disabled=${this._isLoading}>
            Reject
          </ha-button>
        </div>
      </div>
    `;
  }

  _renderDashboardSuggestion(dashboard) {
    return html`
      <div class="dashboard-suggestion">
        <div class="dashboard-title">${dashboard.title}</div>
        <div class="dashboard-description">Dashboard with ${dashboard.views ? dashboard.views.length : 0} view(s)</div>
        <div class="dashboard-details">
          ${JSON.stringify(dashboard, null, 2)}
        </div>
        <div class="dashboard-actions">
          <ha-button @click=${() => this._approveDashboard(dashboard)} .disabled=${this._isLoading}>
            Create Dashboard
          </ha-button>
          <ha-button @click=${() => this._rejectDashboard()} .disabled=${this._isLoading}>
            Cancel
          </ha-button>
        </div>
      </div>
    `;
  }

  _renderAdvancedDashboard() {
    if (this._userPlan === 'lite') return '';

    return html`
      <div class="advanced-dashboard ${this._showAdvancedDashboard ? 'open' : ''}">
        <div class="dashboard-header">
          <div class="dashboard-title">Advanced Dashboard</div>
          <button class="icon-button" @click=${this._toggleAdvancedDashboard}>
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        <div class="dashboard-content">
          ${this._userPlan === 'pro' || this._userPlan === 'max' ? html`
            <div class="dashboard-section">
              <div class="dashboard-section-title">
                <ha-icon icon="mdi:pulse"></ha-icon>
                Performance Metrics
              </div>
              ${this._performanceMetrics ? html`
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Total Requests</span>
                  <span class="dashboard-metric-value">${this._performanceMetrics.total_requests || 0}</span>
                </div>
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Average Response Time</span>
                  <span class="dashboard-metric-value">${this._performanceMetrics.avg_response_time || 0}ms</span>
                </div>
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Success Rate</span>
                  <span class="dashboard-metric-value">${this._performanceMetrics.success_rate || 0}%</span>
                </div>
              ` : html`
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Loading...</span>
                </div>
              `}
            </div>
          ` : ''}

          ${this._userPlan === 'max' ? html`
            <div class="dashboard-section">
              <div class="dashboard-section-title">
                <ha-icon icon="mdi:shield"></ha-icon>
                Security Report
              </div>
              ${this._securityReport ? html`
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Security Events</span>
                  <span class="dashboard-metric-value">${this._securityReport.total_events || 0}</span>
                </div>
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Threats Detected</span>
                  <span class="dashboard-metric-value">${this._securityReport.event_counts?.injection || 0}</span>
                </div>
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Blocked IPs</span>
                  <span class="dashboard-metric-value">${this._securityReport.blocked_ips?.length || 0}</span>
                </div>
              ` : html`
                <div class="dashboard-metric">
                  <span class="dashboard-metric-label">Loading...</span>
                </div>
              `}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  _toggleAdvancedDashboard() {
    this._showAdvancedDashboard = !this._showAdvancedDashboard;
    if (this._showAdvancedDashboard) {
      this._loadAdvancedData();
    }
    this.requestUpdate();
  }

  _scrollToBottom() {
    const messages = this.shadowRoot.querySelector('#messages');
    if (messages) {
      messages.scrollTop = messages.scrollHeight;
    }
  }

  _autoResize(e) {
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  }

  _handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !this._isLoading) {
      e.preventDefault();
      this._sendMessage();
    }
  }

  async _selectProvider(provider) {
    const previousProvider = this._selectedProvider;
    this._selectedProvider = provider;
    console.debug("Provider changed from:", previousProvider, "to:", provider);
    await this._loadPromptHistory();
    this.requestUpdate();
  }

  _selectModel(e) {
    this._selectedModel = e.target.value;
  }

  async _sendMessage() {
    const promptEl = this.shadowRoot.querySelector('#prompt');
    const prompt = promptEl.value.trim();
    if (!prompt || this._isLoading) return;

    console.debug("Sending message:", prompt);
    console.debug("With uploaded file:", this._uploadedFile);

    await this._addToHistory(prompt);

    // Add user message
    const userMessage = { type: 'user', text: prompt };
    if (this._uploadedFile) {
      userMessage.attachment = {
        name: this._uploadedFile.name,
        size: this._uploadedFile.size,
        type: this._uploadedFile.type
      };
    }
    this._messages = [...this._messages, userMessage];

    promptEl.value = '';
    promptEl.style.height = 'auto';
    this._isLoading = true;
    this._error = null;

    // Clear any existing timeout
    if (this._serviceCallTimeout) {
      clearTimeout(this._serviceCallTimeout);
    }

    // Set timeout
    this._serviceCallTimeout = setTimeout(() => {
      if (this._isLoading) {
        console.warn("Service call timeout - clearing loading state");
        this._isLoading = false;
        this._error = 'Request timed out. Please try again.';
        this._messages = [...this._messages, {
          type: 'assistant',
          text: 'Sorry, the request timed out. Please try again.'
        }];
        this.requestUpdate();
      }
    }, 60000);

    try {
      console.debug("Calling glm_agent_ha service");

      const serviceData = {
        prompt: prompt,
        provider: this._selectedProvider,
        model: this._selectedModel
      };

      // Add file data if available
      if (this._uploadedFile) {
        serviceData.attachment = {
          name: this._uploadedFile.name,
          size: this._uploadedFile.size,
          type: this._uploadedFile.type,
          data: await this._fileToBase64(this._uploadedFile)
        };
      }

      await this.hass.callService('glm_agent_ha', 'query', serviceData);

      // Clear uploaded file after sending
      this._removeUploadedFile();

    } catch (error) {
      console.error("Error calling service:", error);
      this._clearLoadingState();
      this._error = error.message || 'An error occurred while processing your request';
      this._messages = [...this._messages, {
        type: 'assistant',
        text: `Error: ${this._error}`
      }];
    }
  }

  async _fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = error => reject(error);
    });
  }

  _clearLoadingState() {
    this._isLoading = false;
    if (this._serviceCallTimeout) {
      clearTimeout(this._serviceCallTimeout);
      this._serviceCallTimeout = null;
    }
  }

  _handleResponse(event) {
    console.debug("Received response:", event);

    try {
      this._clearLoadingState();
      if (event.data.success) {
        if (!event.data.answer || event.data.answer.trim() === '') {
          console.warn("AI agent returned empty response");
          this._messages = [
            ...this._messages,
            { type: 'assistant', text: 'I received your message but I\'m not sure how to respond. Could you please try rephrasing your question?' }
          ];
          return;
        }

        let message = { type: 'assistant', text: event.data.answer };

        try {
          console.debug("Attempting to parse response as JSON:", event.data.answer);
          let jsonText = event.data.answer;

          const jsonMatch = jsonText.match(/\{[\s\S]*\}/);
          if (jsonMatch && jsonMatch[0] !== jsonText.trim()) {
            console.debug("Found JSON within mixed response, extracting:", jsonMatch[0]);
            jsonText = jsonMatch[0];
          }

          const response = JSON.parse(jsonText);
          console.debug("Parsed JSON response:", response);

          if (response.request_type === 'automation_suggestion') {
            console.debug("Found automation suggestion");
            message.automation = response.automation;
            message.text = response.message || 'I found an automation that might help you. Would you like me to create it?';
          } else if (response.request_type === 'dashboard_suggestion') {
            console.debug("Found dashboard suggestion:", response.dashboard);
            message.dashboard = response.dashboard;
            message.text = response.message || 'I created a dashboard configuration for you. Would you like me to create it?';
          } else if (response.request_type === 'final_response') {
            message.text = response.response || response.message || event.data.answer;
          } else if (response.message) {
            message.text = response.message;
          } else if (response.response) {
            message.text = response.response;
          }
        } catch (e) {
          console.debug("Response is not JSON, using as-is:", event.data.answer);
        }

        console.debug("Adding message to UI:", message);
        this._messages = [...this._messages, message];
      } else {
        this._error = event.data.error || 'An error occurred';
        this._messages = [
          ...this._messages,
          { type: 'assistant', text: `Error: ${this._error}` }
        ];
      }
    } catch (error) {
      console.error("Error in _handleResponse:", error);
      this._clearLoadingState();
      this._error = 'An error occurred while processing the response';
      this._messages = [...this._messages, {
        type: 'assistant',
        text: 'Sorry, an error occurred while processing the response. Please try again.'
      }];
      this.requestUpdate();
    }
  }

  async _approveAutomation(automation) {
    if (this._isLoading) return;
    this._isLoading = true;
    try {
      const result = await this.hass.callService('glm_agent_ha', 'create_automation', {
        automation: automation
      });

      console.debug("Automation creation result:", result);

      if (result && result.message) {
        this._messages = [...this._messages, {
          type: 'assistant',
          text: result.message
        }];
      } else {
        this._messages = [...this._messages, {
          type: 'assistant',
          text: `Automation "${automation.alias}" has been created successfully!`
        }];
      }
    } catch (error) {
      console.error("Error creating automation:", error);
      this._error = error.message || 'An error occurred while creating the automation';
      this._messages = [...this._messages, {
        type: 'assistant',
        text: `Error: ${this._error}`
      }];
    } finally {
      this._clearLoadingState();
    }
  }

  _rejectAutomation() {
    this._messages = [...this._messages, {
      type: 'assistant',
      text: 'Automation creation cancelled. Would you like to try something else?'
    }];
  }

  async _approveDashboard(dashboard) {
    if (this._isLoading) return;
    this._isLoading = true;
    try {
      const result = await this.hass.callService('glm_agent_ha', 'create_dashboard', {
        dashboard_config: dashboard
      });

      console.debug("Dashboard creation result:", result);

      if (result && result.message) {
        this._messages = [...this._messages, {
          type: 'assistant',
          text: result.message
        }];
      } else {
        this._messages = [...this._messages, {
          type: 'assistant',
          text: `Dashboard "${dashboard.title}" has been created successfully!`
        }];
      }
    } catch (error) {
      console.error("Error creating dashboard:", error);
      this._error = error.message || 'An error occurred while creating the dashboard';
      this._messages = [...this._messages, {
        type: 'assistant',
        text: `Error: ${this._error}`
      }];
    } finally {
      this._clearLoadingState();
    }
  }

  _rejectDashboard() {
    this._messages = [...this._messages, {
      type: 'assistant',
      text: 'Dashboard creation cancelled. Would you like me to create a different dashboard?'
    }];
  }

  shouldUpdate(changedProps) {
    return changedProps.has('_messages') ||
           changedProps.has('_isLoading') ||
           changedProps.has('_error') ||
           changedProps.has('_promptHistory') ||
           changedProps.has('_showPredefinedPrompts') ||
           changedProps.has('_showPromptHistory') ||
           changedProps.has('_availableProviders') ||
           changedProps.has('_selectedProvider') ||
           changedProps.has('_showProviderDropdown') ||
           changedProps.has('_selectedModel') ||
           changedProps.has('_userPlan') ||
           changedProps.has('_showAdvancedDashboard') ||
           changedProps.has('_uploadedFile') ||
           changedProps.has('_activeCategory') ||
           changedProps.has('_dragActive');
  }

  _clearChat() {
    this._messages = [];
    this._clearLoadingState();
    this._error = null;
    this._pendingAutomation = null;
    this._uploadedFile = null;
  }

  _getProviderInfo(providerId) {
    return this._availableProviders.find(p => p.value === providerId);
  }

  _hasProviders() {
    return this._availableProviders && this._availableProviders.length > 0;
  }
}

customElements.define("glm_agent_ha-panel", GLMAgentHaPanel);

console.log("GLM Agent HA Modern Panel registered");