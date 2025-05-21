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
      _error: { type: String, reflect: false, attribute: false }
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
    `;
  }

  constructor() {
    super();
    this._messages = [];
    this._isLoading = false;
    this._error = null;
    console.debug("LlamaChatPanel constructor called");
  }

  render() {
    console.debug("Rendering with state:", {
      messages: this._messages,
      isLoading: this._isLoading,
      error: this._error
    });

    return html`
      <div class="header">
        <ha-icon icon="mdi:robot"></ha-icon>
        Llama Chat
      </div>
      <div class="content">
        <div class="chat-container">
          <div class="messages" id="messages">
            ${this._messages.map(msg => html`
              <div class="message ${msg.type}-message">
                ${msg.text}
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

  async _sendMessage() {
    const promptEl = this.shadowRoot.querySelector('#prompt');
    const prompt = promptEl.value.trim();
    if (!prompt || this._isLoading) return;

    console.debug("Sending message:", prompt);

    // Add user message
    this._messages = [...this._messages, { type: 'user', text: prompt }];
    promptEl.value = '';
    this._isLoading = true;
    this._error = null;

    try {
      console.debug("Calling llama_query service");
      await this.hass.callService('llama_query', 'query', {
        prompt: prompt
      });
    } catch (error) {
      console.error("Error calling service:", error);
      this._error = error.message || 'An error occurred while processing your request';
      this._isLoading = false;
    }
  }

  connectedCallback() {
    super.connectedCallback();
    console.debug("LlamaChatPanel connected");
    if (this.hass) {
      this.hass.connection.subscribeEvents(
        (event) => this._handleLlamaResponse(event),
        'llama_query_response'
      );
    }
  }

  _handleLlamaResponse(event) {
    console.debug("Received llama response:", event);
    this._isLoading = false;
    if (event.data.success) {
      this._messages = [
        ...this._messages,
        { type: 'assistant', text: event.data.answer }
      ];
    } else {
      this._error = event.data.error || 'An error occurred';
      this._messages = [
        ...this._messages,
        { type: 'assistant', text: `Error: ${this._error}` }
      ];
    }
  }

  shouldUpdate(changedProps) {
    // Only update if internal state changes, not on every hass update
    return changedProps.has('_messages') || changedProps.has('_isLoading') || changedProps.has('_error');
  }
}

customElements.define("llama-chat-panel", LlamaChatPanel);

console.log("Llama Chat Panel registered");