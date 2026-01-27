import json
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Literal

from pydantic_ai import Agent, DeferredToolRequests, Tool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from homeassistant_api import HomeAssistantApiClient

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
model = OpenAIChatModel(model_name, provider=provider)
home_assistant_client = HomeAssistantApiClient()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def calculator(number_a: float, number_b: float, operator: Literal["+", "-", "*", "/"]) -> float:
    """Perform a basic arithmetic operation on two numbers."""
    if operator == "+":
        return number_a + number_b
    if operator == "-":
        return number_a - number_b
    if operator == "*":
        return number_a * number_b
    if number_b == 0:
        raise ValueError("Cannot divide by zero.")
    return number_a / number_b


def render_home_assistant_template(
    template: str, variables: dict | None = None
) -> dict[str, str | bool]:
    """Render a Home Assistant Jinja2 template using the built-in template API."""
    try:
        response = home_assistant_client.render_template(template, variables)
        if isinstance(response, str):
            return {"success": True, "result": response}
        if isinstance(response, dict):
            message = response.get("message", "Template rendering failed.")
            return {"success": False, "error": message}
        return {"success": False, "error": "Unexpected response from template API."}
    except Exception as exc:
        logger.exception(
            "Template render failed for template=%s variables=%s", template, variables
        )
        return {"success": False, "error": str(exc)}


agent = Agent(
    model,
    system_prompt=(
        "You are HomeAssistantAgent, a helpful assistant for Home Assistant users. "
        "Answer clearly and keep responses concise unless asked to elaborate."
    ),
    output_type=[str, DeferredToolRequests],
    tools=[
        Tool(calculator, requires_approval=True),
        Tool(render_home_assistant_template, requires_approval=False),
    ],
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
