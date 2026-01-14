import json
import os
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from starlette.types import ASGIApp, Receive, Scope, Send

PORT = 5050
CONFIG_PATHS = (
    Path("/data/options.json"),
    Path("/config/options.json"),
)
MODEL_NAME = "gpt-4o"


class IngressPathMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in {"http", "websocket"}:
            headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            ingress_path = headers.get("x-ingress-path")
            updated_scope = None
            if ingress_path:
                updated_scope = dict(scope) if updated_scope is None else updated_scope
                updated_scope["root_path"] = ingress_path.rstrip("/")
            path = scope.get("path", "")
            if path.startswith("//"):
                updated_scope = dict(scope) if updated_scope is None else updated_scope
                normalized_path = "/" + path.lstrip("/")
                updated_scope["path"] = normalized_path
                raw_path = scope.get("raw_path")
                if isinstance(raw_path, (bytes, bytearray)):
                    updated_scope["raw_path"] = normalized_path.encode("ascii")
            if updated_scope is not None:
                scope = updated_scope
        await self.app(scope, receive, send)


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
    app.add_middleware(IngressPathMiddleware)
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

    app = IngressPathMiddleware(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
