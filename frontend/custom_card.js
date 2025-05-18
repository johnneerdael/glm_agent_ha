class LlamaChatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this.config = config;

    this.shadowRoot.innerHTML = `
      <ha-card>
        <style>
          .chat-container {
            padding: 16px;
            max-width: 800px;
            margin: 0 auto;
          }
          .chat-messages {
            height: 400px;
            overflow-y: auto;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            margin-bottom: 16px;
            padding: 16px;
            background: var(--card-background-color);
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
            background: var(--card-background-color);
            color: var(--primary-text-color);
          }
          mwc-button {
            --mdc-theme-primary: var(--primary-color);
          }
        </style>
        <div class="chat-container">
          <div class="chat-messages" id="messages"></div>
          <div class="input-container">
            <textarea
              id="prompt"
              placeholder="Type your message here..."
              @keydown="${this._handleKeyDown}"
            ></textarea>
            <mwc-button raised @click="${this._sendMessage}">
              Send
            </mwc-button>
          </div>
        </div>
      </ha-card>
    `;

    this._messages = this.shadowRoot.getElementById('messages');
    this._prompt = this.shadowRoot.getElementById('prompt');
  }

  _handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this._sendMessage();
    }
  }

  async _sendMessage() {
    const prompt = this._prompt.value.trim();
    if (!prompt) return;

    // Add user message to chat
    this._addMessage(prompt, 'user');
    this._prompt.value = '';

    try {
      await this._hass.callService('llama_query', 'query', {
        prompt: prompt
      });
    } catch (error) {
      this._addMessage('Error: Unable to get response from Llama', 'assistant');
    }
  }

  _addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = text;
    this._messages.appendChild(messageDiv);
    this._messages.scrollTop = this._messages.scrollHeight;
  }

  set hass(hass) {
    this._hass = hass;
  }
}

customElements.define('llama-chat-card', LlamaChatCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'llama-chat-card',
  name: 'Llama Chat',
  description: 'A card that allows you to chat with Llama AI',
}); 