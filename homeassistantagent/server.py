import json
import logging
import os
import sys
from pathlib import Path

import dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

dotenv.load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agents import ChatAgent
from pydantic_ai.run import AgentRunResult

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

ALLOWED_MODELS = {
    "gpt-5.2",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5.2-chat-latest",
    "gpt-5.1-chat-latest",
    "gpt-5-chat-latest",
    "gpt-5.2-codex",
}

provider = OpenAIProvider(api_key=openai_api_key)
model = OpenAIChatModel(model_name, provider=provider)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


agent = ChatAgent.build_agent(model)

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
    async def log_on_complete(result: AgentRunResult):
        u = result.usage()
        # cache_read_tokens corresponds to "cached input tokens" in OpenAI pricing terms
        logger.info(
            f"[TOKENS] requests={u.requests} "
            f"in={u.input_tokens} cache_read={u.cache_read_tokens} cache_write={u.cache_write_tokens} "
            f"out={u.output_tokens} tool_calls={u.tool_calls} details={u.details}"
        )
        return

    model_override = None
    body_bytes = await request.body()
    if body_bytes:
        try:
            payload = json.loads(body_bytes)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            requested_model = payload.get("model")
            if isinstance(requested_model, str) and requested_model in ALLOWED_MODELS:
                model_override = requested_model

    model_override_instance = (
        OpenAIChatModel(model_override, provider=provider) if model_override else None
    )

    return await VercelAIAdapter.dispatch_request(
        request,
        agent=agent,
        model=model_override_instance,
        on_complete=log_on_complete,
    )


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=5050)
