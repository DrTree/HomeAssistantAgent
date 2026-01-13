import importlib.util
import json
import os
import sys
import types
import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"


def load_server_module():
    fake_pydantic_ai = types.ModuleType("pydantic_ai")

    class Agent:
        def __init__(self, model, system_prompt):
            self.model = model
            self.system_prompt = system_prompt

    fake_pydantic_ai.Agent = Agent

    fake_ui = types.ModuleType("pydantic_ai.ui")

    class ChatUI:
        def __init__(self, agent):
            self.agent = agent
            self.app = object()

    fake_ui.ChatUI = ChatUI

    fake_models = types.ModuleType("pydantic_ai.models")
    fake_openai = types.ModuleType("pydantic_ai.models.openai")

    class OpenAIModel:
        def __init__(self, name, api_key):
            self.name = name
            self.api_key = api_key

    fake_openai.OpenAIModel = OpenAIModel

    sys_modules_backup = sys.modules.copy()
    sys.modules.update(
        {
            "pydantic_ai": fake_pydantic_ai,
            "pydantic_ai.ui": fake_ui,
            "pydantic_ai.models": fake_models,
            "pydantic_ai.models.openai": fake_openai,
        }
    )
    try:
        spec = importlib.util.spec_from_file_location("server_under_test", SERVER_PATH)
        module = importlib.util.module_from_spec(spec)
        loader = spec.loader
        if loader is None:
            raise RuntimeError("Unable to load server module")
        loader.exec_module(module)
        return module
    finally:
        sys.modules.clear()
        sys.modules.update(sys_modules_backup)


class ServerTests(unittest.TestCase):
    def test_load_api_key_from_env(self):
        with TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
                module = load_server_module()
                self.assertEqual(module.load_api_key(), "env-key")

    def test_load_api_key_from_options_file(self):
        with TemporaryDirectory() as tmpdir:
            options_path = Path(tmpdir) / "options.json"
            options_path.write_text(json.dumps({"openai_api_key": "file-key"}))
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
                module = load_server_module()
            with mock.patch.dict(os.environ, {}, clear=True):
                module.CONFIG_PATHS = (options_path,)
                self.assertEqual(module.load_api_key(), "file-key")


if __name__ == "__main__":
    unittest.main()
