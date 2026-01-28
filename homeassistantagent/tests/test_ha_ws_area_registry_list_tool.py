import unittest
from unittest.mock import AsyncMock, patch

from homeassistantagent.clients.homeassistant_ws_client import HomeAssistantWsError
from homeassistantagent.tools.home_assistant_ws import ha_ws_area_registry_list


class HaWsAreaRegistryListToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_maps_fields(self) -> None:
        response = {
            "success": True,
            "result": [
                {
                    "area_id": "kitchen",
                    "name": "Kitchen",
                    "picture": None,
                    "extra": "ignore-me",
                }
            ],
        }
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(return_value=response)
            result = await ha_ws_area_registry_list()

        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["truncated"])
        self.assertEqual(
            result["areas"],
            [{"area_id": "kitchen", "name": "Kitchen", "picture": None}],
        )

    async def test_empty_area_list(self) -> None:
        response = {"success": True, "result": []}
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(return_value=response)
            result = await ha_ws_area_registry_list()

        self.assertTrue(result["ok"])
        self.assertEqual(result["areas"], [])
        self.assertEqual(result["count"], 0)
        self.assertFalse(result["truncated"])

    async def test_ha_error_response(self) -> None:
        error_payload = {"code": "invalid_format", "message": "Bad format"}
        exc = HomeAssistantWsError("HA_ERROR", "Home Assistant error.", error_payload)
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(side_effect=exc)
            result = await ha_ws_area_registry_list()

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "HA_WS_ERROR")
        self.assertEqual(result["error"]["message"], "Bad format")
        self.assertEqual(result["error"]["details"], "invalid_format")

    async def test_truncation_when_max_items_exceeded(self) -> None:
        response = {
            "success": True,
            "result": [
                {"area_id": "kitchen", "name": "Kitchen", "picture": None},
                {"area_id": "living", "name": "Living", "picture": None},
                {"area_id": "bedroom", "name": "Bedroom", "picture": None},
            ],
        }
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(return_value=response)
            result = await ha_ws_area_registry_list(max_items=2)

        self.assertTrue(result["ok"])
        self.assertTrue(result["truncated"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["areas"]), 2)
