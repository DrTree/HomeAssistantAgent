import asyncio
import json

from websockets import serve


class FakeHomeAssistantServer:
    def __init__(self, token: str = "token") -> None:
        self.token = token
        self._server = None
        self.port: int | None = None
        self.connections = []
        self.command_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.auto_response = True
        self.drop_commands: set[str] = set()
        self.close_on_command: set[str] = set()
        self.subscribe_counter = 1
        self.subscriptions: dict[int, dict] = {}
        self.received: list[dict] = []
        self.unsubscribe_calls: list[dict] = []
        self.subscribe_calls: list[dict] = []

    async def start(self) -> None:
        self._server = await serve(self._handler, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def close(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def close_connections(self) -> None:
        for websocket in list(self.connections):
            await websocket.close()

    async def send_result(self, command_id: int, result: dict | int | None = None) -> None:
        if not self.connections:
            raise RuntimeError("No active connection.")
        payload = {
            "id": command_id,
            "type": "result",
            "success": True,
            "result": result,
        }
        await self.connections[-1].send(json.dumps(payload))

    async def send_event(self, ha_subscription_id: int, event: dict) -> None:
        if not self.connections:
            raise RuntimeError("No active connection.")
        payload = {
            "id": ha_subscription_id,
            "type": "event",
            "event": event,
        }
        await self.connections[-1].send(json.dumps(payload))

    async def _handler(self, websocket) -> None:
        self.connections.append(websocket)
        await websocket.send(json.dumps({"type": "auth_required"}))
        try:
            raw = await websocket.recv()
        except Exception:
            return
        message = json.loads(raw)
        if message.get("type") != "auth" or message.get("access_token") != self.token:
            await websocket.send(json.dumps({"type": "auth_invalid"}))
            await websocket.close()
            return
        await websocket.send(json.dumps({"type": "auth_ok"}))
        async for raw in websocket:
            message = json.loads(raw)
            self.received.append(message)
            await self.command_queue.put(message)
            command_type = message.get("type")
            if command_type == "subscribe_events":
                self.subscribe_calls.append(message)
                ha_id = self.subscribe_counter
                self.subscribe_counter += 1
                self.subscriptions[ha_id] = message
                await websocket.send(
                    json.dumps(
                        {
                            "id": message["id"],
                            "type": "result",
                            "success": True,
                            "result": ha_id,
                        }
                    )
                )
                continue
            if command_type == "subscribe_trigger":
                self.subscribe_calls.append(message)
                ha_id = self.subscribe_counter
                self.subscribe_counter += 1
                self.subscriptions[ha_id] = message
                await websocket.send(
                    json.dumps(
                        {
                            "id": message["id"],
                            "type": "result",
                            "success": True,
                            "result": ha_id,
                        }
                    )
                )
                continue
            if command_type == "unsubscribe_events":
                self.unsubscribe_calls.append(message)
                await websocket.send(
                    json.dumps(
                        {
                            "id": message["id"],
                            "type": "result",
                            "success": True,
                            "result": None,
                        }
                    )
                )
                continue
            if command_type in self.close_on_command:
                await websocket.close()
                continue
            if command_type in self.drop_commands:
                continue
            if not self.auto_response:
                continue
            await websocket.send(
                json.dumps(
                    {
                        "id": message["id"],
                        "type": "result",
                        "success": True,
                        "result": {"echo": command_type},
                    }
                )
            )
