import json
import os
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.ui._web.api import create_api_app
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

PORT = 5050
CONFIG_PATHS = (
    Path("/data/options.json"),
    Path("/config/options.json"),
)
MODEL_NAME = "gpt-4o"
STATIC_DIR = Path(__file__).resolve().parent / "static"


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


def build_app(agent: Agent | None) -> Starlette:
    async def index(_: Request) -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    routes = [
        Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
        Route("/", index, methods=["GET"]),
    ]

    if agent is None:
        message = (
            "OpenAI API key not configured. "
            "Set openai_api_key in the add-on options and restart the add-on."
        )

        async def not_configured(_: Request) -> PlainTextResponse:
            return PlainTextResponse(message)

        routes.insert(0, Route("/api/{path:path}", not_configured, methods=["GET", "POST", "OPTIONS"]))
    else:
        api_app = create_api_app(agent=agent)
        routes.insert(0, Mount("/api", app=api_app))

    return Starlette(routes=routes)


api_key = load_api_key()
if api_key:
    os.environ.setdefault("OPENAI_API_KEY", api_key)
    model = OpenAIChatModel(MODEL_NAME)
    agent = Agent(
        model,
        system_prompt="You are a helpful Home Assistant companion.",
    )
    app = build_app(agent)
else:
    app = build_app(None)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
