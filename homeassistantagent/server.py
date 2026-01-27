from pathlib import Path
import logging
import os
import traceback

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

from config_parser import load_config
from starlette.responses import StreamingResponse

APP_ROOT = Path(__file__).resolve().parent
WEB_DIST = APP_ROOT / "web" / "dist"
config = load_config()
openai_api_key = config.openai_api_key
model_name = config.model_name

provider = OpenAIProvider(api_key=openai_api_key)
model = OpenAIChatModel(model_name, provider=provider)

mcp_client: httpx.AsyncClient | None = None
mcp_server: MCPServerStreamableHTTP | None = None
if config.mcp_api_url:
    headers: dict[str, str] = {}
    if config.mcp_token:
        headers["Authorization"] = f"Bearer {config.mcp_token}"
    mcp_client = httpx.AsyncClient(
        headers=headers or None,
        timeout=httpx.Timeout(10.0),
    )
    mcp_server = MCPServerStreamableHTTP(
        config.mcp_api_url,
        http_client=mcp_client,
    )

toolsets = [mcp_server] if mcp_server is not None else None
agent = Agent(
    model,
    system_prompt=(
        "You are HomeAssistantAgent, a helpful assistant for Home Assistant users. "
        "Answer clearly and keep responses concise unless asked to elaborate."
    ),
    toolsets=toolsets,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp_client = mcp_client
    try:
        yield
    finally:
        if app.state.mcp_client is not None:
            await app.state.mcp_client.aclose()


app = FastAPI(lifespan=lifespan)
logger = logging.getLogger("homeassistantagent")
LOG_DIR = APP_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_path = LOG_DIR / "server.log"
file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger.info("Logging to %s (cwd=%s)", log_path, os.getcwd())


def _format_exception_group(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        lines = [f"{exc.__class__.__name__}: {exc}"]
        for idx, child in enumerate(exc.exceptions, start=1):
            lines.append(f"  [{idx}] {child.__class__.__name__}: {child}")
        return "\n".join(lines)
    return f"{exc.__class__.__name__}: {exc}"


async def _log_streaming_errors(response: StreamingResponse) -> StreamingResponse:
    original_iterator = response.body_iterator

    async def wrapped_iterator():
        try:
            async for chunk in original_iterator:
                yield chunk
        except Exception as exc:
            logger.error("Streaming error in /api/chat: %s", _format_exception_group(exc))
            logger.error("Streaming traceback:\n%s", traceback.format_exc())
            raise

    response.body_iterator = wrapped_iterator()
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(request: Request):
    try:
        logger.info("Incoming /api/chat request")
        response = await VercelAIAdapter.dispatch_request(request, agent=agent)
        if isinstance(response, StreamingResponse):
            return await _log_streaming_errors(response)
        return response
    except Exception as exc:
        logger.error("Unhandled error in /api/chat: %s", _format_exception_group(exc))
        logger.error("Unhandled traceback:\n%s", traceback.format_exc())
        raise


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception for %s %s: %s\n%s",
        request.method,
        request.url.path,
        _format_exception_group(exc),
        traceback.format_exc(),
    )
    raise exc


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=5050, log_level="info")
