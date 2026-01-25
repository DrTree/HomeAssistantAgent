import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

APP_ROOT = Path(__file__).resolve().parent
WEB_DIST = APP_ROOT / "web" / "dist"
OPTIONS_PATH = Path("/data/options.json")


def load_options() -> dict:
    if OPTIONS_PATH.exists():
        with OPTIONS_PATH.open("r", encoding="utf-8") as options_file:
            return json.load(options_file)
    return {}


options = load_options()
openai_api_key = options.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

provider = OpenAIProvider(api_key=openai_api_key)
model = OpenAIModel(model_name, provider=provider)

agent = Agent(
    model,
    system_prompt=(
        "You are HomeAssistantAgent, a helpful assistant for Home Assistant users. "
        "Answer clearly and keep responses concise unless asked to elaborate."
    ),
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(request: Request):
    return await VercelAIAdapter.dispatch_request(request, agent=agent)


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=5050)
