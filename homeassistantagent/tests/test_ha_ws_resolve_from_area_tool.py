import unittest
from unittest.mock import AsyncMock, patch

from homeassistantagent.tools.home_assistant_ws import ha_ws_resolve_from_area


class HaWsResolveFromAreaToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_by_area_id_calls_extract(self) -> None:
        response = {
            "success": True,
            "result": {
                "referenced_entities": ["light.kitchen"],
                "referenced_devices": ["device_1"],
                "referenced_areas": ["kitchen"],
                "missing_areas": [],
                "missing_devices": [],
                "missing_floors": [],
                "missing_labels": [],
            },
        }
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(return_value=response)
            result = await ha_ws_resolve_from_area(area_id="kitchen")

        ws_client.send_command.assert_awaited_once_with(
            "extract_from_target",
            {"target": {"area_id": ["kitchen"]}, "expand_group": True},
            is_write=False,
            timeout_s=10,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["area"]["area_id"], "kitchen")
        self.assertIsNone(result["area"]["name"])
        self.assertEqual(result["entity_ids"], ["light.kitchen"])
        self.assertEqual(result["device_ids"], ["device_1"])

    async def test_resolve_by_area_name(self) -> None:
        response = {
            "success": True,
            "result": {
                "referenced_entities": [],
                "referenced_devices": [],
                "referenced_areas": ["kitchen"],
                "missing_areas": [],
                "missing_devices": [],
                "missing_floors": [],
                "missing_labels": [],
            },
        }
        area_list = {
            "ok": True,
            "areas": [{"area_id": "kitchen", "name": "Kitchen", "picture": None}],
            "count": 1,
            "truncated": False,
        }
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(return_value=response)
            with patch(
                "homeassistantagent.tools.home_assistant_ws.ha_ws_area_registry_list",
                AsyncMock(return_value=area_list),
            ):
                result = await ha_ws_resolve_from_area(area_name="Kitchen")

        self.assertTrue(result["ok"])
        self.assertEqual(result["area"], {"area_id": "kitchen", "name": "Kitchen"})

    async def test_ambiguous_area_name(self) -> None:
        area_list = {
            "ok": True,
            "areas": [
                {"area_id": "kitchen", "name": "Kitchen", "picture": None},
                {"area_id": "kitchenette", "name": "Kitchenette", "picture": None},
            ],
            "count": 2,
            "truncated": False,
        }
        with patch(
            "homeassistantagent.tools.home_assistant_ws.ha_ws_area_registry_list",
            AsyncMock(return_value=area_list),
        ):
            result = await ha_ws_resolve_from_area(area_name="kit")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "AMBIGUOUS_AREA")
        self.assertIn("candidates", result)
        self.assertIn("candidates", result["error"]["details"])

    async def test_domain_filter_applied(self) -> None:
        response = {
            "success": True,
            "result": {
                "referenced_entities": ["sensor.temp", "light.kitchen", "switch.coffee"],
                "referenced_devices": [],
                "referenced_areas": ["kitchen"],
                "missing_areas": [],
                "missing_devices": [],
                "missing_floors": [],
                "missing_labels": [],
            },
        }
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(return_value=response)
            result = await ha_ws_resolve_from_area(
                area_id="kitchen",
                entity_domain_filter=["LIGHT", "switch"],
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["entity_ids"], ["light.kitchen", "switch.coffee"])

    async def test_truncation_flags(self) -> None:
        response = {
            "success": True,
            "result": {
                "referenced_entities": ["light.a", "light.b", "light.c"],
                "referenced_devices": ["device_1", "device_2", "device_3"],
                "referenced_areas": ["kitchen"],
                "missing_areas": [],
                "missing_devices": [],
                "missing_floors": [],
                "missing_labels": [],
            },
        }
        with patch("homeassistantagent.tools.home_assistant_ws.ws_client") as ws_client:
            ws_client.send_command = AsyncMock(return_value=response)
            result = await ha_ws_resolve_from_area(
                area_id="kitchen",
                max_entities=2,
                max_devices=1,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["truncated_entities"])
        self.assertTrue(result["truncated_devices"])
        self.assertEqual(result["entity_ids"], ["light.a", "light.b"])
        self.assertEqual(result["device_ids"], ["device_1"])
