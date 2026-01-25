import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel

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
    options = load_options()
    api_key = options.get("openai_api_key", "").strip()
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


class ChatRequest(BaseModel):
    message: str


def build_app(agent: Agent | None) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, str]:
        if agent is None:
            message = (
                "OpenAI API key not configured. "
                "Set openai_api_key in the add-on options and restart the add-on."
            )
            raise HTTPException(status_code=503, detail=message)
        result = await agent.run(request.message)
        return {"response": str(result.output)}

    return app


api_key = load_api_key()
mcp_access_token, mcp_url = load_mcp_settings()
if api_key:
    os.environ.setdefault("OPENAI_API_KEY", api_key)
    if mcp_access_token:
        os.environ.setdefault("MCP_ACCESS_TOKEN", mcp_access_token)
        os.environ.setdefault("MCP_URL", mcp_url)
    model = OpenAIChatModel(MODEL_NAME)
    mcp_token, mcp_url = load_mcp_settings()
    toolsets = []
    if mcp_token:
        try:
            from pydantic_ai.mcp import MCPServerStreamableHTTP

            mcp_server = MCPServerStreamableHTTP(
                mcp_url,
                headers={"Authorization": f"Bearer {mcp_token}"},
            )
            toolsets.append(mcp_server)
        except ImportError:
            print("MCP tooling is unavailable because the MCP package is not installed.")
    else:
        print("MCP access token not configured; MCP tooling disabled.")
    agent = Agent(
        model,
        system_prompt="You are a helpful Home Assistant companion.",
        toolsets=toolsets,
    )
    app = build_app(agent)
else:
    app = build_app(None)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
