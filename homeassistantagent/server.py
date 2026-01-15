import json
import os
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from starlette.types import Receive, Scope, Send

PORT = 5050
CONFIG_PATHS = (
    Path("/data/options.json"),
    Path("/config/options.json"),
)
MODEL_NAME = "gpt-4o"


def load_api_key() -> str:
    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key
    data = load_options()
    api_key = data.get("openai_api_key", "").strip()
    if api_key:
        return api_key
    return ""


def load_options() -> dict:
    for path in CONFIG_PATHS:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
    return {}


def load_mcp_settings() -> tuple[str, str]:
    env_token = os.getenv("MCP_ACCESS_TOKEN", "").strip()
    env_url = os.getenv("MCP_URL", "").strip()
    if env_token:
        return env_token, env_url or "/api/mcp"

    data = load_options()
    token = data.get("mcp_access_token", "").strip()
    url = data.get("mcp_url", "").strip() or "/api/mcp"
    return token, url


api_key = load_api_key()
mcp_access_token, mcp_url = load_mcp_settings()
if api_key:
    os.environ.setdefault("OPENAI_API_KEY", api_key)
    if mcp_access_token:
        os.environ.setdefault("MCP_ACCESS_TOKEN", mcp_access_token)
        os.environ.setdefault("MCP_URL", mcp_url)
    model = OpenAIChatModel(MODEL_NAME)
    agent = Agent(
        model,
        system_prompt="You are a helpful Home Assistant companion.",
    )
    app = agent.to_web()
else:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        message = (
            "OpenAI API key not configured. "
            "Set openai_api_key in the add-on options and restart the add-on."
        )
        body = message.encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
