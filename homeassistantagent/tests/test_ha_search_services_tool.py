import importlib
import unittest
from unittest.mock import AsyncMock, patch

ha_search_services_module = importlib.import_module("homeassistantagent.tools.ha_search_services")


def _ws_payload(services: dict[str, dict[str, dict]]) -> dict:
    return {"success": True, "result": services}


class HaSearchServicesToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_turn_on_query_orders_by_relevance(self) -> None:
        services = {
            "light": {
                "turn_on": {"name": "Turn on", "description": "Turn on a light"},
                "toggle": {"name": "Toggle", "description": "Toggle light"},
            },
            "switch": {
                "turn_on": {"name": "Turn on", "description": "Turn on a switch"},
            },
        }
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(query="turn on")

        self.assertTrue(result["ok"])
        self.assertEqual(result["services"][0]["domain"], "light")
        self.assertEqual(result["services"][0]["service"], "turn_on")

    async def test_domain_filter_limits_results(self) -> None:
        services = {
            "light": {"turn_on": {"name": "Turn on"}},
            "switch": {"turn_on": {"name": "Turn on"}},
        }
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(domain="light")

        self.assertTrue(result["ok"])
        self.assertEqual({item["domain"] for item in result["services"]}, {"light"})

    async def test_include_fields_truncates_schema(self) -> None:
        fields = {f"field_{idx}": {"description": f"Field {idx}"} for idx in range(30)}
        services = {"light": {"turn_on": {"fields": fields}}}
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(
                query="turn on", include_fields=True
            )

        service = result["services"][0]
        self.assertEqual(len(service["fields"]), 25)
        self.assertTrue(service["fields_truncated"])

    async def test_include_targets_returns_boolean_flags(self) -> None:
        services = {
            "light": {
                "turn_on": {
                    "target": {"entity": {"domain": "light"}, "device": {}, "area": {}},
                }
            }
        }
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(
                query="turn", include_targets=True
            )

        targets = result["services"][0]["targets"]
        self.assertTrue(targets["supports_entity_target"])
        self.assertFalse(targets["supports_device_target"])
        self.assertFalse(targets["supports_area_target"])

    async def test_empty_query_returns_note(self) -> None:
        services = {
            "light": {"turn_on": {"name": "Turn on"}},
            "switch": {"turn_on": {"name": "Turn on"}},
        }
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(limit=1)

        self.assertTrue(result["ok"])
        self.assertIn("note", result)
        self.assertEqual(result["count"], 1)

    async def test_limit_clamps_and_negative_offset_errors(self) -> None:
        services = {"light": {"turn_on": {"name": "Turn on"}}}
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(limit=55)

        self.assertTrue(result["ok"])
        self.assertEqual(result["limit"], 50)

        invalid = await ha_search_services_module.ha_search_services(offset=-1)
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["code"], "INVALID_ARGUMENT")

    async def test_domain_not_found_returns_candidates(self) -> None:
        services = {
            "light": {"turn_on": {"name": "Turn on"}},
            "switch": {"turn_on": {"name": "Turn on"}},
        }
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(domain="lig")

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "DOMAIN_NOT_FOUND")
        self.assertIn("light", result.get("candidates", []))

    async def test_scan_truncation_sets_truncated_flags(self) -> None:
        services = {
            "light": {
                f"service_{idx}": {"name": f"Service {idx}"} for idx in range(10_001)
            }
        }
        with patch.object(
            ha_search_services_module.ws_client,
            "send_command",
            new=AsyncMock(return_value=_ws_payload(services)),
        ):
            result = await ha_search_services_module.ha_search_services(query="service", limit=1)

        self.assertTrue(result["ok"])
        self.assertTrue(result["truncated_scan"])
        self.assertTrue(result["truncated"])
