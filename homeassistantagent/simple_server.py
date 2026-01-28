import json
import os
import sys
from pathlib import Path

import dotenv

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

dotenv.load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agents import ChatAgent

OPTIONS_PATH = Path("/data/options.json")
DEFAULT_MODEL = "gpt-5.2"


def load_options() -> dict:
    if OPTIONS_PATH.exists():
        with OPTIONS_PATH.open("r", encoding="utf-8") as options_file:
            return json.load(options_file)
    return {}


options = load_options()
openai_api_key = options.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")

provider = OpenAIProvider(api_key=openai_api_key)
model = OpenAIChatModel(DEFAULT_MODEL, provider=provider)
agent = ChatAgent.build_agent(model)

app = agent.to_web()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("simple_server:app", host="0.0.0.0", port=5050)
