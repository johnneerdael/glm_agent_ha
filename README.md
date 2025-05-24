# AI Agent HA Custom Integration

A Home Assistant custom component that provides an AI-powered agent capable of generating automations based on natural language queries. The agent connects to all entities in your Home Assistant instance and uses OpenAI's API to translate user requests into valid Home Assistant automations.

---

## Features

* **Natural Language Automation**: Ask the agent to create automations in plain English.
* **Entity-Aware**: Automatically discovers and uses your existing Home Assistant entities.
* **UI Integration**: Manage and approve suggested automations directly from Home Assistant's UI (see screenshot below).

![AI Agent HA Usage Screenshot](./assets/screenshot.png)

---

## Installation

1. Clone or download this repository:

   ```bash
   git clone https://github.com/sbenodiz/ai_agent_ha.git
   ```

2. Copy the `ai_agent_ha` folder into your Home Assistant `custom_components` directory:

   ```bash
   cp -R ai_agent_ha /config/custom_components/
   ```

3. Restart Home Assistant.

4. In the Home Assistant UI, go to **Settings → Devices & Services → Integrations**.

5. Click **Add Integration** and search for **AI Agent HA**.

6. Follow the prompts to configure your OpenAI API key (if required).

---

## Configuration

The integration will automatically register a new panel in the sidebar named **AI Agent HA**. No YAML configuration is required. If you need to customize:

```yaml
# Example (optional)
ai_agent_ha:
  api_key: YOUR_OPENAI_API_KEY
  model: gpt-4
  max_tokens: 512
```

Place this under `configuration.yaml` if you want to override defaults.

---

## Usage

1. Navigate to the **AI Agent HA** panel.
2. Type a natural language request, for example:

   > *"Create an automation to turn off all lights every day at 1am"*
3. Review the generated automation suggestion.
4. Click **Approve** to add it to your configuration, or **Reject** to discard.

The component will create the automation under `.storage/ai_agent_ha_automations` and reload automations automatically.

---

## Development

* Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```
* Run tests:

  ```bash
  pytest
  ```

---

## Contributing

Contributions are welcome! Please open issues or pull requests on [GitHub](https://github.com/sbenodiz/ai_agent_ha).

---

## License

MIT License. See [LICENSE](./LICENSE) for details.
