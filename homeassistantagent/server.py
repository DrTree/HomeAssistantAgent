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
    for path in CONFIG_PATHS:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            api_key = data.get("openai_api_key", "").strip()
            if api_key:
                return api_key
    return ""


api_key = load_api_key()
if api_key:
    os.environ.setdefault("OPENAI_API_KEY", api_key)
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
