import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

console.log("Llama Chat Panel loading..."); // Debug log

class LlamaChatPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object, reflect: false, attribute: false },
      narrow: { type: Boolean, reflect: false, attribute: false },
      panel: { type: Object, reflect: false, attribute: false },
      _messages: { type: Array, reflect: false, attribute: false },
      _isLoading: { type: Boolean, reflect: false, attribute: false },
      _error: { type: String, reflect: false, attribute: false },
      _pendingAutomation: { type: Object, reflect: false, attribute: false },
      _retryCount: { type: Number, reflect: false, attribute: false },
      _maxRetries: { type: Number, reflect: false, attribute: false },
      _debounceTimeout: { type: Number, reflect: false, attribute: false }
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
      .header {
        background: var(--app-header-background-color);
        color: var(--app-header-text-color);
        padding: 16px 24px;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 20px;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }
      .clear-button {
        margin-left: auto;
        --mdc-theme-primary: var(--error-color);
        --mdc-theme-on-primary: var(--text-primary-color);
        --mdc-typography-button-font-size: 14px;
        --mdc-button-height: 36px;
        --mdc-button-padding: 0 16px;
      }
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
      }
      .messages {
        height: calc(100vh - 320px);
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
      .input-container {
        display: flex;
        gap: 12px;
        padding: 16px;
        background: var(--primary-background-color);
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
        width: 100%;
      }
      textarea {
        flex-grow: 1;
        padding: 12px 16px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        height: 56px;
        resize: none;
        font-size: 16px;
        line-height: 1.5;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
        background: var(--primary-background-color);
      }
      textarea:focus {
        outline: none;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(var(--primary-color-rgb), 0.1);
      }
      ha-button {
        --mdc-theme-primary: var(--primary-color);
        --mdc-theme-on-primary: var(--text-primary-color);
        --mdc-typography-button-font-size: 16px;
        --mdc-typography-button-text-transform: none;
        --mdc-typography-button-letter-spacing: 0;
        --mdc-typography-button-font-weight: 500;
        --mdc-button-height: 56px;
        --mdc-button-padding: 0 24px;
        border-radius: 8px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      ha-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
      ha-button:active {
        transform: translateY(0);
      }
      .loading {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
        padding: 12px 16px;
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
      .error {
        color: var(--error-color);
        padding: 16px;
        margin: 8px 0;
        border-radius: 12px;
        background: var(--error-background-color);
        border: 1px solid var(--error-color);
        animation: fadeIn 0.3s ease-out;
      }
      .automation-suggestion {
        background: var(--secondary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
      }
      .automation-title {
        font-weight: 500;
        margin-bottom: 8px;
      }
      .automation-description {
        margin-bottom: 16px;
        color: var(--secondary-text-color);
      }
      .automation-actions {
        display: flex;
        gap: 8px;
      }
      .automation-details {
        margin-top: 8px;
        padding: 8px;
        background: var(--primary-background-color);
        border-radius: 8px;
        font-family: monospace;
        white-space: pre-wrap;
        overflow-x: auto;
      }
    `;
  }

  constructor() {
    super();
    this._messages = [];
    this._isLoading = false;
    this._error = null;
    this._pendingAutomation = null;
    this._retryCount = 0;
    this._maxRetries = 3;
    this._debounceTimeout = null;
    this._eventUnsubscribe = null;
    console.debug("LlamaChatPanel constructor called");
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._eventUnsubscribe) {
      this._eventUnsubscribe();
    }
  }

  connectedCallback() {
    super.connectedCallback();
    console.debug("LlamaChatPanel connected");
    if (this.hass) {
      this._eventUnsubscribe = this.hass.connection.subscribeEvents(
        (event) => this._handleLlamaResponse(event),
        'llama_query_response'
      );
    }
  }

  _sanitizeInput(input) {
    // Basic XSS prevention
    return input.replace(/[&<>"']/g, (char) => {
      const entities = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      };
      return entities[char];
    });
  }

  async _sendMessage() {
    const promptEl = this.shadowRoot.querySelector('#prompt');
    const prompt = this._sanitizeInput(promptEl.value.trim());
    if (!prompt || this._isLoading) return;

    // Clear any existing debounce timeout
    if (this._debounceTimeout) {
      clearTimeout(this._debounceTimeout);
    }

    // Set a new debounce timeout
    this._debounceTimeout = setTimeout(async () => {
      console.debug("Sending message:", prompt);

      // Add user message
      this._messages = [...this._messages, { type: 'user', text: prompt }];
      promptEl.value = '';
      this._isLoading = true;
      this._error = null;
      this._retryCount = 0;

      try {
        console.debug("Calling llama_query service");
        await this.hass.callService('llama_query', 'query', {
          prompt: prompt
        });
      } catch (error) {
        console.error("Error calling service:", error);
        this._handleError(error);
      }
    }, 300); // 300ms debounce
  }

  _handleError(error) {
    if (this._retryCount < this._maxRetries) {
      this._retryCount++;
      console.debug(`Retrying request (${this._retryCount}/${this._maxRetries})`);
      setTimeout(() => this._sendMessage(), 1000 * this._retryCount);
    } else {
      this._error = this._getUserFriendlyError(error);
      this._isLoading = false;
      this._retryCount = 0;
    }
  }

  _getUserFriendlyError(error) {
    if (error.message.includes('timeout')) {
      return 'The request timed out. Please try again.';
    } else if (error.message.includes('network')) {
      return 'Network error. Please check your connection and try again.';
    } else if (error.message.includes('401')) {
      return 'Authentication error. Please check your API key.';
    } else if (error.message.includes('429')) {
      return 'Too many requests. Please wait a moment before trying again.';
    }
    return 'An error occurred while processing your request. Please try again.';
  }

  _handleLlamaResponse(event) {
    console.debug("Received llama response:", event);
    this._isLoading = false;
    this._retryCount = 0;

    if (event.data.success) {
      let message = { type: 'assistant', text: event.data.answer };
      
      try {
        const response = JSON.parse(event.data.answer);
        if (response.request_type === 'automation_suggestion') {
          message.automation = response.automation;
          this._pendingAutomation = response.automation;
        } else if (response.request_type === 'final_response') {
          message.text = response.response;
        }
      } catch (e) {
        console.debug("Response is not JSON, using as-is:", event.data.answer);
      }
      
      this._messages = [...this._messages, message];
    } else {
      this._error = event.data.error || 'An error occurred';
      this._messages = [
        ...this._messages,
        { type: 'assistant', text: `Error: ${this._error}` }
      ];
    }
  }

  async _approveAutomation(automation) {
    if (!this._validateAutomation(automation)) {
      this._error = 'Invalid automation configuration';
      return;
    }

    this._isLoading = true;
    try {
      const result = await this.hass.callService('llama_query', 'create_automation', {
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
      this._pendingAutomation = null;
    } catch (error) {
      console.error("Error creating automation:", error);
      this._error = this._getUserFriendlyError(error);
      this._messages = [...this._messages, {
        type: 'assistant',
        text: `Error: ${this._error}`
      }];
    }
    this._isLoading = false;
  }

  _validateAutomation(automation) {
    if (!automation || typeof automation !== 'object') return false;
    if (!automation.alias || typeof automation.alias !== 'string') return false;
    if (!automation.description || typeof automation.description !== 'string') return false;
    if (!automation.trigger || !Array.isArray(automation.trigger)) return false;
    if (!automation.action || !Array.isArray(automation.action)) return false;
    return true;
  }

  async _rejectAutomation() {
    if (confirm('Are you sure you want to reject this automation?')) {
      this._messages = [...this._messages, {
        type: 'assistant',
        text: 'Automation creation cancelled. Would you like to try something else?'
      }];
      this._pendingAutomation = null;
    }
  }

  _clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
      this._messages = [];
      this._error = null;
      this._pendingAutomation = null;
    }
  }

  render() {
    return html`
      <div class="header">
        <ha-icon icon="mdi:robot"></ha-icon>
        Llama Chat
        <ha-button
          class="clear-button"
          @click=${this._clearChat}
          .disabled=${this._isLoading}
        >Clear Chat</ha-button>
      </div>
      <div class="content">
        <div class="chat-container">
          <div class="messages" id="messages">
            ${this._messages.map(msg => html`
              <div class="message ${msg.type}-message">
                ${msg.text}
                ${msg.automation ? html`
                  <div class="automation-suggestion">
                    <div class="automation-title">${msg.automation.alias}</div>
                    <div class="automation-description">${msg.automation.description}</div>
                    <div class="automation-details">
                      ${JSON.stringify(msg.automation, null, 2)}
                    </div>
                    <div class="automation-actions">
                      <ha-button
                        @click=${() => this._approveAutomation(msg.automation)}
                        .disabled=${this._isLoading}
                      >Approve</ha-button>
                      <ha-button
                        @click=${() => this._rejectAutomation()}
                        .disabled=${this._isLoading}
                      >Reject</ha-button>
                    </div>
                  </div>
                ` : ''}
              </div>
            `)}
            ${this._isLoading ? html`
              <div class="loading">
                <span>Llama is thinking</span>
                <div class="loading-dots">
                  <div class="dot"></div>
                  <div class="dot"></div>
                  <div class="dot"></div>
                </div>
              </div>
            ` : ''}
            ${this._error ? html`
              <div class="error">${this._error}</div>
            ` : ''}
          </div>
          <div class="input-container">
            <textarea
              id="prompt"
              placeholder="Ask me anything about your Home Assistant..."
              ?disabled=${this._isLoading}
              @keydown=${this._handleKeyDown}
            ></textarea>
            <ha-button
              @click=${this._sendMessage}
              .disabled=${this._isLoading}
            >Send</ha-button>
          </div>
        </div>
      </div>
    `;
  }

  updated(changedProps) {
    console.debug("Updated called with:", changedProps);

    if (changedProps.has('_messages') || changedProps.has('_isLoading')) {
      this._scrollToBottom();
    }
  }

  _scrollToBottom() {
    const messages = this.shadowRoot.querySelector('#messages');
    if (messages) {
      messages.scrollTop = messages.scrollHeight;
    }
  }

  _handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !this._isLoading) {
      e.preventDefault();
      this._sendMessage();
    }
  }

  shouldUpdate(changedProps) {
    // Only update if internal state changes, not on every hass update
    return changedProps.has('_messages') || changedProps.has('_isLoading') || changedProps.has('_error');
  }
}

customElements.define("llama-chat-panel", LlamaChatPanel);

console.log("Llama Chat Panel registered");