import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

class LlamaChatPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      panel: { type: Object },
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
      }
      textarea {
        flex-grow: 1;
        padding: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        min-height: 56px;
        resize: vertical;
      }
    `;
  }

  constructor() {
    super();
    this._messages = [];
  }

  render() {
    if (!this.hass) {
      return html`Loading...`;
    }

    return html`
      <div class="header">
        <ha-icon icon="mdi:robot"></ha-icon>
        Llama Chat
      </div>
      <div class="content">
        <div class="chat-container">
          <div class="messages" id="messages">
            ${this._messages.map(
              (msg) => html`
                <div class="message ${msg.type}-message">
                  ${msg.text}
                </div>
              `
            )}
          </div>
          <div class="input-container">
            <textarea
              id="prompt"
              @keydown="${this._handleKeyDown}"
              placeholder="Type your message here..."
            ></textarea>
            <mwc-button raised @click="${this._sendMessage}">
              Send
            </mwc-button>
          </div>
        </div>
      </div>
    `;
  }

  _handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this._sendMessage();
    }
  }

  async _sendMessage() {
    const promptEl = this.shadowRoot.querySelector('#prompt');
    const prompt = promptEl.value.trim();
    if (!prompt) return;

    // Add user message
    this._messages = [...this._messages, { type: 'user', text: prompt }];
    promptEl.value = '';
    this.requestUpdate();

    try {
      // Call the llama_query service
      await this.hass.callService('llama_query', 'query', {
        prompt: prompt
      });
    } catch (error) {
      this._messages = [
        ...this._messages,
        { type: 'assistant', text: `Error: ${error.message}` }
      ];
      this.requestUpdate();
    }
  }

  connectedCallback() {
    super.connectedCallback();
    // Subscribe to llama_query_response events
    if (this.hass) {
      this.hass.connection.subscribeEvents(
        (event) => this._handleLlamaResponse(event),
        'llama_query_response'
      );
    }
  }

  _handleLlamaResponse(event) {
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