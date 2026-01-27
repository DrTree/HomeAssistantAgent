from pydantic_ai import Agent, DeferredToolRequests, Tool
from pydantic_ai.models import Model

from tools import calculator, call_home_assistant_service, render_home_assistant_template


class ChatAgent:
    SYSTEM_PROMPT = (
        "You are HomeAssistantAgent, a helpful assistant for Home Assistant users. "
        "Answer clearly and keep responses concise unless asked to elaborate."
        "Use your tools when necessary to provide accurate information."

    )

    @staticmethod
    def build_agent(
        model: Model | str | None,
    ) -> Agent[None, str | DeferredToolRequests]:
        return Agent(
            model,
            system_prompt=ChatAgent.SYSTEM_PROMPT,
            output_type=[str, DeferredToolRequests],
            tools=[
                Tool(calculator, requires_approval=True),
                Tool(call_home_assistant_service, requires_approval=True),
                Tool(render_home_assistant_template, requires_approval=True),
            ],
        )
