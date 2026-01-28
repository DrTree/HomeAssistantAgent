import asyncio
import unittest

from homeassistantagent.clients.homeassistant_ws_client import (
    HomeAssistantWebSocketClient,
    HomeAssistantWsError,
)
from homeassistantagent.tests.ws_test_helpers import FakeHomeAssistantServer


class HomeAssistantWsClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.server = FakeHomeAssistantServer()
        await self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.port}"

    async def asyncTearDown(self) -> None:
        if hasattr(self, "client"):
            await self.client.close()
        await self.server.close()

    async def test_auth_success(self) -> None:
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="token",
        )
        await self.client.ensure_connected()
        response = await self.client.send_command("get_states", {})
        self.assertTrue(response["success"])

    async def test_auth_failure(self) -> None:
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="bad-token",
            reconnect_backoff_initial_s=0.1,
            reconnect_backoff_max_s=0.1,
        )
        with self.assertRaises(HomeAssistantWsError) as context:
            await self.client.ensure_connected()
        self.assertEqual(context.exception.code, "AUTH_INVALID")

    async def test_out_of_order_responses(self) -> None:
        self.server.auto_response = False
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="token",
        )
        task_one = asyncio.create_task(self.client.send_command("get_states", {}))
        task_two = asyncio.create_task(self.client.send_command("get_services", {}))
        first = await self.server.command_queue.get()
        second = await self.server.command_queue.get()
        await self.server.send_result(second["id"], {"value": "second"})
        await self.server.send_result(first["id"], {"value": "first"})
        first_response, second_response = await asyncio.gather(task_one, task_two)
        self.assertEqual(first_response["result"]["value"], "first")
        self.assertEqual(second_response["result"]["value"], "second")

    async def test_timeout(self) -> None:
        self.server.drop_commands.add("get_states")
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="token",
            default_timeout_s=0.1,
        )
        with self.assertRaises(HomeAssistantWsError) as context:
            await self.client.send_command("get_states", {})
        self.assertEqual(context.exception.code, "TIMEOUT")

    async def test_disconnect_no_write_retry(self) -> None:
        self.server.close_on_command.add("call_service")
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="token",
            default_timeout_s=0.2,
        )
        with self.assertRaises(HomeAssistantWsError) as context:
            await self.client.send_command("call_service", {"domain": "light"}, is_write=True)
        self.assertEqual(context.exception.code, "DISCONNECTED")
        await asyncio.sleep(0.1)
        calls = [msg for msg in self.server.received if msg.get("type") == "call_service"]
        self.assertEqual(len(calls), 1)

    async def test_reconnect_rehydrates_subscriptions(self) -> None:
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="token",
            reconnect_backoff_initial_s=0.1,
            reconnect_backoff_max_s=0.1,
        )
        handle = await self.client.subscribe_events(
            "state_changed",
            scope_id="scope-1",
        )
        self.assertIsNotNone(handle.ha_subscription_id)
        await self.server.close_connections()
        await self.client.ensure_connected()
        await asyncio.sleep(0.1)
        self.assertGreaterEqual(len(self.server.subscribe_calls), 2)

    async def test_close_scope_unsubscribes(self) -> None:
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="token",
        )
        await self.client.subscribe_events("state_changed", scope_id="scope-2")
        await self.client.close_scope("scope-2")
        await asyncio.sleep(0.1)
        self.assertEqual(len(self.server.unsubscribe_calls), 1)

    async def test_ttl_janitor_evicts(self) -> None:
        self.client = HomeAssistantWebSocketClient(
            base_url=self.base_url,
            token="token",
            janitor_interval_s=0.05,
            default_subscription_ttl_s=0.05,
        )
        await self.client.subscribe_events("state_changed", scope_id="scope-3")
        await asyncio.sleep(0.2)
        self.assertGreaterEqual(len(self.server.unsubscribe_calls), 1)
