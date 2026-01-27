import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parent
OPTIONS_PATH = Path("/data/options.json")
LOCAL_OPTIONS_PATH = APP_ROOT / "data" / "options.json"
DEFAULT_MCP_API_URL = "http://supervisor/core/api/mcp"


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str | None
    model_name: str
    mcp_api_url: str
    mcp_token: str | None


def _load_json(path: Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as options_file:
            return json.load(options_file)
    return {}


def load_config() -> AppConfig:
    load_dotenv()

    options = _load_json(OPTIONS_PATH)
    if not options:
        options = _load_json(LOCAL_OPTIONS_PATH)
    openai_api_key = options.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    mcp_api_url = (
        options.get("mcp_api_url")
        or os.environ.get("MCP_API_URL")
        or DEFAULT_MCP_API_URL
    )
    mcp_token = os.environ.get("SUPERVISOR_TOKEN")

    return AppConfig(
        openai_api_key=openai_api_key,
        model_name=model_name,
        mcp_api_url=mcp_api_url,
        mcp_token=mcp_token,
    )
