# HomeAssistantAgent

This add-on runs a PydanticAI chat agent backed by the OpenAI `GPT-4o` model.
Configure the `openai_api_key` option in the add-on settings to supply your API key.
Optionally set `mcp_access_token` (and `mcp_url` if you need a custom endpoint) to
enable MCP tools; when `mcp_url` is not provided, the add-on will target `/api/mcp`.
Open the UI on port `5050` after the add-on starts, or launch it via Home Assistant
ingress.
