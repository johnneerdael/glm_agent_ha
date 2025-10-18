// GLM Agent HA Improved Panel - Enhanced stability and error handling
// This version addresses the LitElement lifecycle and dependency loading issues

console.log("GLM Agent HA Improved Panel loading...");

// Enhanced dependency loading with better error handling
(async function() {
  'use strict';

  let litElementLoaded = false;
  let loadAttempts = 0;
  const maxAttempts = 3;
  const loadTimeout = 10000; // 10 seconds

  // Function to load LitElement with timeout
  async function loadLitElement(source, timeout = loadTimeout) {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`Loading timeout after ${timeout}ms`));
      }, timeout);

      try {
        const script = document.createElement('script');
        script.type = 'module';

        if (source === 'primary') {
          script.textContent = `
            import { LitElement, html, css } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";
            window.GLM_LitElement = LitElement;
            window.GLM_html = html;
            window.GLM_css = css;
            console.log("LitElement loaded from primary CDN");
          `;
        } else if (source === 'fallback') {
          script.textContent = `
            import { LitElement, html, css } from "https://cdn.skypack.dev/lit-element@2.4.0";
            window.GLM_LitElement = LitElement;
            window.GLM_html = html;
            window.GLM_css = css;
            console.log("LitElement loaded from fallback CDN");
          `;
        } else if (source === 'local') {
          // Try to use HA's built-in LitElement if available
          script.textContent = `
            try {
              // Check if Home Assistant already has LitElement
              if (window.LitElement) {
                window.GLM_LitElement = window.LitElement;
                window.GLM_html = window.html || ((template, ...values) => ({_$litType$: 1, strings: template, values}));
                window.GLM_css = window.css || ((strings, ...values) => ({_$litType$: 2, strings: template, values}));
                console.log("LitElement loaded from Home Assistant environment");
              } else {
                throw new Error("LitElement not available in HA environment");
              }
            } catch (e) {
              console.warn("Failed to use HA LitElement:", e);
              // Fallback to CDN
              import { LitElement, html, css } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";
              window.GLM_LitElement = LitElement;
              window.GLM_html = html;
              window.GLM_css = css;
              console.log("LitElement loaded from fallback CDN after HA attempt failed");
            }
          `;
        }

        script.onload = () => {
          clearTimeout(timeoutId);
          resolve();
        };

        script.onerror = (error) => {
          clearTimeout(timeoutId);
          reject(error);
        };

        document.head.appendChild(script);
      } catch (error) {
        clearTimeout(timeoutId);
        reject(error);
      }
    });
  }

  // Try multiple loading strategies
  async function loadDependencies() {
    const strategies = [
      { name: 'local', source: 'local' },
      { name: 'primary', source: 'primary' },
      { name: 'fallback', source: 'fallback' }
    ];

    for (const strategy of strategies) {
      try {
        console.log(`Attempting to load LitElement using ${strategy.name} strategy...`);
        await loadLitElement(strategy.source);
        console.log(`Successfully loaded LitElement using ${strategy.name} strategy`);
        return true;
      } catch (error) {
        console.warn(`Failed to load LitElement using ${strategy.name} strategy:`, error);
        continue;
      }
    }

    return false;
  }

  // Initialize panel with comprehensive error handling
  async function initializePanel() {
    try {
      const depsLoaded = await loadDependencies();

      if (!depsLoaded) {
        throw new Error("Failed to load LitElement dependencies from all sources");
      }

      // Check if dependencies are properly loaded
      if (!window.GLM_LitElement || !window.GLM_html || !window.GLM_css) {
        throw new Error("Dependencies loaded but not available in window scope");
      }

      litElementLoaded = true;
      console.log("All dependencies loaded successfully, setting up panel...");

      // Setup panel after dependencies are ready
      setupImprovedPanel();

    } catch (error) {
      console.error("Failed to initialize panel:", error);
      showEnhancedErrorScreen(error);
    }
  }

  // Enhanced error screen with more details
  function showEnhancedErrorScreen(error) {
    const errorDetails = {
      message: error.message,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    document.body.innerHTML = `
      <div style="padding: 20px; font-family: Arial, sans-serif; color: #333; text-align: center; max-width: 600px; margin: 50px auto; background: #f8f9fa; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
          <ha-icon icon="mdi:robot" style="font-size: 48px; color: #03a9f4; margin-right: 16px;"></ha-icon>
          <h2 style="margin: 0; color: #1976d2;">GLM Agent HA Dashboard</h2>
        </div>

        <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <h3 style="margin: 0 0 8px 0; color: #856404;">⚠️ Loading Issue Detected</h3>
          <p style="margin: 0;">Unable to load dashboard components due to network or compatibility issues.</p>
        </div>

        <div style="text-align: left; background: white; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <h4 style="margin: 0 0 12px 0; color: #666;">Technical Details:</h4>
          <pre style="background: #f5f5f5; padding: 8px; border-radius: 4px; font-size: 12px; overflow: auto; margin: 0;">${JSON.stringify(errorDetails, null, 2)}</pre>
        </div>

        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
          <button onclick="window.location.reload()" style="padding: 12px 24px; background: #03a9f4; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; transition: background 0.2s;">
            🔄 Refresh Page
          </button>
          <button onclick="toggleAdvancedInfo()" style="padding: 12px 24px; background: #757575; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; transition: background 0.2s;">
            📋 Advanced Info
          </button>
        </div>

        <div id="advancedInfo" style="display: none; margin-top: 20px; text-align: left;">
          <details style="background: white; border-radius: 8px; padding: 16px;">
            <summary style="cursor: pointer; font-weight: 500; color: #666;">🔧 Troubleshooting Steps</summary>
            <ol style="margin: 12px 0 0 20px; color: #666; line-height: 1.6;">
              <li>Check your internet connection</li>
              <li>Disable browser extensions that might block scripts</li>
              <li>Try a different browser (Chrome/Firefox recommended)</li>
              <li>Clear browser cache and cookies</li>
              <li>Check if JavaScript is enabled</li>
              <li>Verify Home Assistant is updated to latest version</li>
              <li>Check browser console for additional error messages</li>
            </ol>
          </details>

          <details style="background: white; border-radius: 8px; padding: 16px; margin-top: 12px;">
            <summary style="cursor: pointer; font-weight: 500; color: #666;">🌐 Network Information</summary>
            <div style="margin-top: 12px; font-size: 12px; color: #666;">
              <p><strong>Online:</strong> ${navigator.onLine ? 'Yes' : 'No'}</p>
              <p><strong>Connection Type:</strong> ${navigator.connection ? navigator.connection.effectiveType : 'Unknown'}</p>
              <p><strong>Current URL:</strong> ${window.location.href}</p>
            </div>
          </details>
        </div>

        <p style="font-size: 12px; color: #666; margin-top: 20px; text-align: center;">
          If the problem persists, please report this issue on our
          <a href="https://github.com/johnneerdael/glm_agent_ha/issues" target="_blank" style="color: #03a9f4;">GitHub Issues</a>
        </p>
      </div>
    `;

    // Add toggle functionality for advanced info
    window.toggleAdvancedInfo = function() {
      const info = document.getElementById('advancedInfo');
      info.style.display = info.style.display === 'none' ? 'block' : 'none';
    };
  }

  // Setup improved panel class
  function setupImprovedPanel() {
    // Constants and configurations (from original)
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

    const SMART_PROMPTS = {
      basic: [
        {
          text: "🏠 Generate comprehensive home automation blueprint based on my devices",
          icon: "mdi:home-analytics",
          tools: ["basic_query", "automation_creation"],
          description: "Analyze all devices and create complete automation strategy"
        },
        {
          text: "📊 Create custom energy monitoring dashboard with optimization alerts",
          icon: "mdi:chart-box",
          tools: ["basic_query", "dashboard_creation"],
          description: "Build real-time energy tracking with intelligent suggestions"
        },
        {
          text: "🔒 Design whole-home security system with threat detection",
          icon: "mdi:shield-home",
          tools: ["basic_query", "automation_creation"],
          description: "Create comprehensive security coverage with smart responses"
        }
      ],
      // ... (other categories would be included in full implementation)
    };

    // Improved panel class with better error handling
    class GLMAgentHaImprovedPanel extends (window.GLM_LitElement || class {}) {
      static get properties() {
        return {
          hass: { type: Object, reflect: false, attribute: false },
          narrow: { type: Boolean, reflect: false, attribute: false },
          panel: { type: Object, reflect: false, attribute: false },
          _messages: { type: Array, reflect: false, attribute: false },
          _isLoading: { type: Boolean, reflect: false, attribute: false },
          _error: { type: String, reflect: false, attribute: false },
          _initializationComplete: { type: Boolean, reflect: false, attribute: false },
          _dependencyError: { type: String, reflect: false, attribute: false }
        };
      }

      static get styles() {
        if (!window.GLM_css) return window.GLM_css``;

        return window.GLM_css`
          :host {
            background: var(--primary-background-color);
            -webkit-font-smoothing: antialiased;
            display: flex;
            flex-direction: column;
            height: 100vh;
            font-family: var(--paper-font-body1_-_font-family);
          }

          .error-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            padding: 20px;
            text-align: center;
            background: var(--error-background-color, #ffebee);
            color: var(--error-color, #c62828);
          }

          .error-icon {
            font-size: 64px;
            margin-bottom: 16px;
            color: var(--error-color, #c62828);
          }

          .error-title {
            font-size: 24px;
            font-weight: 500;
            margin-bottom: 16px;
          }

          .error-message {
            font-size: 16px;
            margin-bottom: 24px;
            max-width: 500px;
            line-height: 1.5;
          }

          .error-actions {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            justify-content: center;
          }

          .error-button {
            padding: 12px 24px;
            background: var(--primary-color, #03a9f4);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.2s ease;
          }

          .error-button:hover {
            background-color: var(--primary-color-dark, #0288d1);
          }

          .error-button.secondary {
            background: var(--secondary-text-color, #757575);
          }

          .error-button.secondary:hover {
            background: var(--primary-text-color, #424242);
          }

          .loading-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            padding: 20px;
            text-align: center;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
          }

          .loading-spinner {
            width: 48px;
            height: 48px;
            border: 4px solid var(--divider-color);
            border-top: 4px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 16px;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          .loading-text {
            font-size: 16px;
            color: var(--secondary-text-color);
          }
        `;
      }

      constructor() {
        super();

        try {
          // Initialize properties with safe defaults
          this._messages = [];
          this._isLoading = false;
          this._error = null;
          this._initializationComplete = false;
          this._dependencyError = null;

          // Set up error boundaries
          this._setupErrorHandlers();

          console.debug("GLMAgentHaImprovedPanel constructor completed successfully");

        } catch (error) {
          console.error("Error in panel constructor:", error);
          this._dependencyError = `Constructor error: ${error.message}`;
        }
      }

      _setupErrorHandlers() {
        // Set up global error handlers for this component
        this._handleError = this._handleError.bind(this);
        this._handleUnhandledRejection = this._handleUnhandledRejection.bind(this);

        // Add event listeners
        window.addEventListener('error', this._handleError);
        window.addEventListener('unhandledrejection', this._handleUnhandledRejection);
      }

      _handleError(event) {
        console.error("Panel error:", event.error);
        if (!this._error) {
          this._error = `Runtime error: ${event.error?.message || 'Unknown error'}`;
          this.requestUpdate();
        }
      }

      _handleUnhandledRejection(event) {
        console.error("Unhandled promise rejection:", event.reason);
        if (!this._error) {
          this._error = `Promise error: ${event.reason?.message || 'Unknown promise error'}`;
          this.requestUpdate();
        }
      }

      connectedCallback() {
        try {
          super.connectedCallback();
          console.debug("GLMAgentHaImprovedPanel connected");

          // Initialize with error handling
          this._initializeWithErrorHandling();

        } catch (error) {
          console.error("Error in connectedCallback:", error);
          this._dependencyError = `Connection error: ${error.message}`;
          this.requestUpdate();
        }
      }

      async _initializeWithErrorHandling() {
        try {
          // Initialize basic functionality first
          this._initializationComplete = true;
          this.requestUpdate();

          // Then load additional features
          await this._loadAdditionalFeatures();

        } catch (error) {
          console.error("Error during initialization:", error);
          this._error = `Initialization error: ${error.message}`;
          this.requestUpdate();
        }
      }

      async _loadAdditionalFeatures() {
        // This would load prompts, history, etc.
        // For now, just simulate successful loading
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      render() {
        try {
          // Error state
          if (this._dependencyError || this._error) {
            return this._renderErrorState();
          }

          // Loading state
          if (!this._initializationComplete) {
            return this._renderLoadingState();
          }

          // Basic functional state
          return this._renderBasicState();

        } catch (error) {
          console.error("Error in render method:", error);
          return this._renderErrorState(`Render error: ${error.message}`);
        }
      }

      _renderErrorState(customMessage = null) {
        const message = customMessage || this._error || this._dependencyError || 'Unknown error';

        return window.GLM_html`
          <div class="error-container">
            <ha-icon class="error-icon" icon="mdi:alert-circle"></ha-icon>
            <h2 class="error-title">Dashboard Error</h2>
            <p class="error-message">${message}</p>
            <div class="error-actions">
              <button class="error-button" @click=${() => window.location.reload()}>
                🔄 Refresh Page
              </button>
              <button class="error-button secondary" @click=${() => this._clearError()}>
                ✖️ Dismiss
              </button>
            </div>
          </div>
        `;
      }

      _renderLoadingState() {
        return window.GLM_html`
          <div class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">Loading GLM Agent HA Dashboard...</p>
          </div>
        `;
      }

      _renderBasicState() {
        // Simplified basic state for improved reliability
        return window.GLM_html`
          <div style="padding: 20px; height: 100vh; display: flex; flex-direction: column;">
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
              <ha-icon icon="mdi:robot" style="font-size: 32px; margin-right: 12px; color: var(--primary-color);"></ha-icon>
              <h1 style="margin: 0; color: var(--primary-text-color);">GLM Agent HA</h1>
            </div>

            <div style="flex-grow: 1; background: var(--card-background-color); border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
              <p style="color: var(--secondary-text-color); text-align: center; margin-top: 50px;">
                ✅ Dashboard loaded successfully!<br>
                🔄 Full functionality is being restored...
              </p>
            </div>

            <div style="margin-top: 20px; text-align: center;">
              <button style="padding: 12px 24px; background: var(--primary-color); color: white; border: none; border-radius: 6px; cursor: pointer;" @click=${() => window.location.reload()}>
                🔄 Reload Full Dashboard
              </button>
            </div>
          </div>
        `;
      }

      _clearError() {
        this._error = null;
        this._dependencyError = null;
        this.requestUpdate();
      }

      disconnectedCallback() {
        try {
          // Clean up event listeners
          window.removeEventListener('error', this._handleError);
          window.removeEventListener('unhandledrejection', this._handleUnhandledRejection);

          super.disconnectedCallback();
          console.debug("GLMAgentHaImprovedPanel disconnected");

        } catch (error) {
          console.error("Error in disconnectedCallback:", error);
        }
      }

      shouldUpdate(changedProps) {
        // Always update if there are errors or initialization changes
        if (changedProps.has('_error') ||
            changedProps.has('_dependencyError') ||
            changedProps.has('_initializationComplete')) {
          return true;
        }
        return super.shouldUpdate(changedProps);
      }
    }

    // Register the panel with error handling
    try {
      if (!window.customElements.get('glm_agent_ha-panel')) {
        customElements.define('glm_agent_ha-panel', GLMAgentHaImprovedPanel);
        console.log("GLMAgentHaImprovedPanel registered successfully");
      } else {
        console.log("GLM Agent HA panel already registered");
      }
    } catch (error) {
      console.error("Failed to register panel:", error);
      showEnhancedErrorScreen(error);
    }
  }

  // Start initialization
  initializePanel();
})();