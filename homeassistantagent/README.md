# HomeAssistantAgent

This add-on runs a PydanticAI chat agent backed by the OpenAI `GPT-4o` model.
Configure the `openai_api_key` option in the add-on settings to supply your API key.
Optionally set `mcp_access_token` (and `mcp_url` if you need a custom endpoint) to
enable MCP tools; when `mcp_url` is not provided, the add-on will target `/api/mcp`.
Open the UI on port `5050` after the add-on starts, or launch it via Home Assistant
ingress.

## MCP setup

Set `mcp_access_token` in the add-on options to authenticate MCP requests. The MCP
endpoint defaults to `/api/mcp`; override it by setting `mcp_url` if you need a
different path or full URL. Store the access token in Home Assistant secrets (or a
similar secure store), avoid committing it to source control, and only send it over
HTTPS or a trusted internal network.

Example add-on configuration:

```yaml
openai_api_key: "your-openai-api-key"
mcp_access_token: "your-mcp-token"
mcp_url: "/api/mcp"
```
