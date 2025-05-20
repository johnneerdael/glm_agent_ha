import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

console.log("Llama Chat v3 Panel loading..."); // Debug log

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
        padding: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 24px;
        font-weight: bold;
      }
      .content {
        flex-grow: 1;
        padding: 16px;
        overflow-y: auto;
      }
      .chat-container {
        max-width: 800px;
        margin: 0 auto;
      }
      .messages {
        height: calc(100vh - 200px);
        overflow-y: auto;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        margin-bottom: 16px;
        padding: 16px;
      }
      .message {
        margin-bottom: 16px;
        padding: 8px 12px;
        border-radius: 8px;
        max-width: 80%;
      }
      .user-message {
        background: var(--primary-color);
        color: var(--text-primary-color);
        margin-left: auto;
      }
      .assistant-message {
        background: var(--secondary-background-color);
        margin-right: auto;
      }
      .input-container {
        display: flex;
        gap: 8px;
        padding: 16px;
      }
      textarea {
        flex-grow: 1;
        padding: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        min-height: 56px;
        resize: vertical;
      }
      .loading {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        padding: 8px 12px;
        border-radius: 8px;
        background: var(--secondary-background-color);
        margin-right: auto;
        max-width: 80%;
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
      .error {
        color: var(--error-color);
        padding: 12px;
        margin: 8px 0;
        border-radius: 8px;
        background: var(--error-background-color);
        border: 1px solid var(--error-color);
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
}

customElements.define("llama-chat-panel", LlamaChatPanel);

console.log("Llama Chat Panel registered");