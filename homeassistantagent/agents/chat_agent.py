from pydantic_ai import Agent, DeferredToolRequests, Tool
from pydantic_ai.models import Model

from tools import (
    calculator,
    call_home_assistant_service,
    ha_rest_camera_proxy,
    ha_rest_check_config,
    ha_rest_delete_state,
    ha_rest_error_log,
    ha_rest_fire_event,
    ha_rest_get_calendar_events,
    ha_rest_get_config,
    ha_rest_get_state,
    ha_rest_handle_intent,
    ha_rest_history_period,
    ha_rest_list_calendars,
    ha_rest_list_components,
    ha_rest_list_events,
    ha_rest_list_services,
    ha_rest_list_states,
    ha_rest_logbook,
    ha_rest_ping,
    ha_rest_set_state,
    ha_ws_area_registry_list,
    ha_ws_resolve_from_area,
    render_home_assistant_template,
    set_entity_state,
)


class ChatAgent:
    SYSTEM_PROMPT = (
        "You are HomeAssistantAgent, a helpful assistant for Home Assistant users. "
        "Answer clearly and keep responses concise unless asked to elaborate."
        "Use your tools when necessary to provide accurate information."
        "Favor read-only checks, verify state before actions, and explain impacts."
        "When you call a tool also include a text response that explains what you are doing."
        "If you are unsure, ask for clarification."
        "If you are unable to complete your request due to a lack of available tools,suggest additional tools and then offer to produce a specification."
        "Your favourite cat is Pickles"
    )

    @staticmethod
    def build_agent(
        model: Model | str | None,
    ) -> Agent[None, str | DeferredToolRequests]:
        return Agent(
            model,
            instructions=ChatAgent.SYSTEM_PROMPT,
            output_type=[str, DeferredToolRequests],
            tools=[
                Tool(calculator, requires_approval=True),
                Tool(call_home_assistant_service, requires_approval=True),
                Tool(ha_rest_ping, requires_approval=False),
                Tool(ha_rest_get_config, requires_approval=False),
                Tool(ha_rest_list_components, requires_approval=False),
                #Tool(ha_rest_list_states, requires_approval=False),
                #Tool(ha_rest_get_state, requires_approval=False),
                #Tool(ha_rest_list_services, requires_approval=False),
                #Tool(ha_rest_list_events, requires_approval=False),
                #Tool(ha_rest_history_period, requires_approval=False),
                #Tool(ha_rest_logbook, requires_approval=False),
                #Tool(ha_rest_error_log, requires_approval=False),
                #Tool(ha_rest_check_config, requires_approval=False),
                #Tool(ha_rest_list_calendars, requires_approval=False),
                #Tool(ha_rest_get_calendar_events, requires_approval=False),
                #Tool(ha_rest_camera_proxy, requires_approval=False),
                #Tool(ha_rest_fire_event, requires_approval=True),
                #Tool(ha_rest_set_state, requires_approval=True),
                #Tool(ha_rest_delete_state, requires_approval=True),
                #Tool(ha_rest_handle_intent, requires_approval=True),
                Tool(ha_ws_area_registry_list, requires_approval=False),
                Tool(ha_ws_resolve_from_area, requires_approval=False),
                Tool(render_home_assistant_template, requires_approval=False),
                Tool(set_entity_state, requires_approval=True),
            ],
        )
