from pydantic_ai import Agent, DeferredToolRequests, Tool

from tools import calculator, render_home_assistant_template


class ChatAgent:
    SYSTEM_PROMPT = (
        "You are HomeAssistantAgent, a helpful assistant for Home Assistant users. "
        "Answer clearly and keep responses concise unless asked to elaborate."
    )

    @staticmethod
    def build_agent(model: object) -> Agent:
        return Agent(
            model,
            system_prompt=ChatAgent.SYSTEM_PROMPT,
            output_type=[str, DeferredToolRequests],
            tools=[
                Tool(calculator, requires_approval=True),
                Tool(render_home_assistant_template, requires_approval=False),
            ],
        )
