import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

console.log("Llama Chat Panel loading..."); // Debug log

class LlamaChatPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      panel: { type: Object },
      _messages: { type: Array },
      _isLoading: { type: Boolean },
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
      ha-card {
        margin: 16px;
      }
    `;
  }

  constructor() {
    super();
    this._messages = [];
    this._isLoading = false;
    console.log("LlamaChatPanel constructor called"); // Debug log
  }

  render() {
    console.log("LlamaChatPanel render called", this.hass); // Debug log

    if (!this.hass) {
      return html`<ha-card><div class="card-content">Loading Home Assistant...</div></ha-card>`;
    }

    return html`
      <ha-card>
        <div class="card-content">
          <div class="messages" id="messages">
            ${this._messages.map(
              (msg) => html`
                <div class="message ${msg.type}-message">
                  ${msg.text}
                </div>
              `
            )}
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
          </div>
          <div class="input-container">
            <textarea
              id="prompt"
              @keydown="${this._handleKeyDown}"
              placeholder="Type your message here..."
              ?disabled="${this._isLoading}"
            ></textarea>
            <ha-button
              @click="${this._sendMessage}"
              .disabled="${this._isLoading}"
            >
              Send
            </ha-button>
          </div>
        </div>
      </ha-card>
    `;
  }

  firstUpdated() {
    console.log("LlamaChatPanel firstUpdated called"); // Debug log
  }

  updated(changedProps) {
    console.log("LlamaChatPanel updated called", changedProps); // Debug log
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
    console.log("_sendMessage called"); // Debug log
    const promptEl = this.shadowRoot.querySelector('#prompt');
    const prompt = promptEl.value.trim();
    if (!prompt || this._isLoading) return;

    // Add user message
    this._messages = [...this._messages, { type: 'user', text: prompt }];
    promptEl.value = '';
    this._isLoading = true;
    this.requestUpdate();

    try {
      console.log("Calling llama_query service"); // Debug log
      await this.hass.callService('llama_query', 'query', {
        prompt: prompt
      });
    } catch (error) {
      console.error("Error calling service:", error); // Debug log
      this._isLoading = false;
      this._messages = [
        ...this._messages,
        { type: 'assistant', text: `Error: ${error.message}` }
      ];
      this.requestUpdate();
    }
  }

  connectedCallback() {
    super.connectedCallback();
    console.log("LlamaChatPanel connected"); // Debug log
    if (this.hass) {
      this.hass.connection.subscribeEvents(
        (event) => this._handleLlamaResponse(event),
        'llama_query_response'
      );
    }
  }

  _handleLlamaResponse(event) {
    console.log("Received llama response:", event); // Debug log
    this._isLoading = false;
    if (event.data.success) {
      this._messages = [
        ...this._messages,
        { type: 'assistant', text: event.data.answer }
      ];
    } else {
      this._messages = [
        ...this._messages,
        { type: 'assistant', text: `Error: ${event.data.error}` }
      ];
    }
    this.requestUpdate();
  }
}

customElements.define("llama-chat-panel", LlamaChatPanel);
console.log("Llama Chat Panel registered"); // Debug log 