import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable
from urllib import parse

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed

DEFAULT_BASE_URL = os.environ.get("HOME_ASSISTANT_URL", "http://supervisor/core")
DEFAULT_TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HOME_ASSISTANT_TOKEN")
logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    READY = "ready"
    CLOSING = "closing"


@dataclass
class HomeAssistantWsError(Exception):
    code: str
    message: str
    details: Any | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass
class SubscriptionHandle:
    handle_id: int
    scope_id: str
    logical_name: str | None
    persistent: bool
    ttl_s: int | None
    created_at: float
    last_used_at: float
    spec_type: str
    spec: dict[str, Any] | None
    ha_subscription_id: int | None = None
    callbacks: list[Callable[[dict[str, Any]], Awaitable[None] | None]] = field(default_factory=list)
    dropped_events: int = 0

    def add_callback(
        self, callback: Callable[[dict[str, Any]], Awaitable[None] | None]
    ) -> None:
        self.callbacks.append(callback)


@dataclass
class SubscriptionSummary:
    handle_id: int
    scope_id: str
    logical_name: str | None
    persistent: bool
    ttl_s: int | None
    created_at: float
    last_used_at: float
    spec_type: str
    ha_subscription_id: int | None


@dataclass
class PendingMeta:
    command_type: str
    created_at: float
    is_write: bool


class HomeAssistantWebSocketClient:
    """Long-lived Home Assistant WebSocket client for multi-loop agent processes.

    The client manages a single connection per Home Assistant instance, supports
    request/response multiplexing, subscription lifecycle management, and
    reconnect/backoff behavior suitable for long-lived services.
    """
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = DEFAULT_TOKEN,
        default_timeout_s: float = 10.0,
        max_in_flight: int = 100,
        max_message_size: int = 2_000_000,
        stall_timeout_s: float = 60.0,
        reconnect_backoff_initial_s: float = 0.5,
        reconnect_backoff_max_s: float = 30.0,
        reconnect_backoff_jitter: float = 0.2,
        janitor_interval_s: float = 300.0,
        default_subscription_ttl_s: int = 600,
        max_subscriptions_total: int = 50,
        max_non_persistent: int = 20,
        event_queue_max: int = 200,
    ) -> None:
        """Initialize the WebSocket client configuration.

        Args:
            base_url: Home Assistant base URL (http/https) used to derive WS URL.
            token: Long-lived access token for authentication.
            default_timeout_s: Default command timeout in seconds.
            max_in_flight: Maximum in-flight commands before raising BUSY.
            max_message_size: Maximum inbound message size in bytes.
            stall_timeout_s: Time in seconds without inbound messages before reconnecting.
            reconnect_backoff_initial_s: Initial reconnect delay in seconds.
            reconnect_backoff_max_s: Maximum reconnect delay in seconds.
            reconnect_backoff_jitter: Jitter added to reconnect delay.
            janitor_interval_s: Interval for subscription cleanup in seconds.
            default_subscription_ttl_s: Default TTL for non-persistent subscriptions.
            max_subscriptions_total: Total subscription cap before evicting.
            max_non_persistent: Non-persistent subscription cap before evicting.
            event_queue_max: Max queued events before dropping oldest.
        """
        self._base_url = base_url
        self._token = token
        self._default_timeout_s = default_timeout_s
        self._max_in_flight = max_in_flight
        self._max_message_size = max_message_size
        self._stall_timeout_s = stall_timeout_s
        self._reconnect_backoff_initial_s = reconnect_backoff_initial_s
        self._reconnect_backoff_max_s = reconnect_backoff_max_s
        self._reconnect_backoff_jitter = reconnect_backoff_jitter
        self._janitor_interval_s = janitor_interval_s
        self._default_subscription_ttl_s = default_subscription_ttl_s
        self._max_subscriptions_total = max_subscriptions_total
        self._max_non_persistent = max_non_persistent
        self._event_queue_max = event_queue_max

        self._state = ConnectionState.DISCONNECTED
        self._connect_lock = asyncio.Lock()
        self._ready_event = asyncio.Event()
        self._ws: WebSocketClientProtocol | None = None
        self._reader_task: asyncio.Task | None = None
        self._dispatcher_task: asyncio.Task | None = None
        self._janitor_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._last_received_at = 0.0

        self._next_id = 1
        self._pending: dict[int, asyncio.Future] = {}
        self._pending_meta: dict[int, PendingMeta] = {}

        self._subscriptions: dict[int, SubscriptionHandle] = {}
        self._subscriptions_by_name: dict[str, int] = {}
        self._next_subscription_handle = 1
        self._active_scopes: set[str] = set()
        self._subscription_lock = asyncio.Lock()
        self._event_queue: asyncio.Queue[tuple[int, dict[str, Any]]] = asyncio.Queue(
            maxsize=event_queue_max
        )

        self.reconnect_count = 0
        self.auth_fail_count = 0
        self.pending_timeouts = 0
        self.dropped_events = 0

    async def ensure_connected(self) -> None:
        """Ensure the WebSocket connection is authenticated and ready.

        Raises:
            HomeAssistantWsError: When the client is closing or authentication fails.
        """
        if self._state == ConnectionState.READY:
            return
        async with self._connect_lock:
            if self._state == ConnectionState.READY:
                return
            if self._state == ConnectionState.CLOSING:
                raise HomeAssistantWsError("DISCONNECTED", "Client is closing.")
            await self._connect_with_backoff()

    async def close(self) -> None:
        """Close the WebSocket client and cancel background tasks."""
        self._state = ConnectionState.CLOSING
        self._ready_event.clear()
        if self._reader_task:
            self._reader_task.cancel()
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
        if self._janitor_task:
            self._janitor_task.cancel()
        if self._reconnect_task:
            self._reconnect_task.cancel()
        if self._ws:
            await self._ws.close()
        self._ws = None
        await self._fail_pending("DISCONNECTED", "Client closed.")
        self._state = ConnectionState.DISCONNECTED

    async def send_command(
        self,
        command_type: str,
        payload: dict[str, Any],
        *,
        timeout_s: float | None = None,
        retry_read_once: bool = True,
        is_write: bool | None = None,
    ) -> dict[str, Any]:
        """Send a command over the WebSocket and await a result response.

        Args:
            command_type: Home Assistant WS command type (e.g., ``get_states``).
            payload: JSON payload to merge with the ``type`` and ``id`` fields.
            timeout_s: Per-command timeout in seconds (defaults to client default).
            retry_read_once: Retry once after reconnect for read-only commands.
            is_write: Force write classification; defaults to inferred classification.

        Returns:
            Parsed Home Assistant response message.

        Raises:
            HomeAssistantWsError: On disconnect, timeout, or HA error responses.
        """
        timeout_s = timeout_s or self._default_timeout_s
        if is_write is None:
            is_write = self._is_write_command(command_type)
        try:
            return await self._send_command_once(command_type, payload, timeout_s, is_write)
        except HomeAssistantWsError as exc:
            if exc.code == "DISCONNECTED" and retry_read_once and not is_write:
                await self.ensure_connected()
                return await self._send_command_once(command_type, payload, timeout_s, is_write)
            raise

    async def subscribe_events(
        self,
        event_type: str | None,
        *,
        scope_id: str,
        logical_name: str | None = None,
        persistent: bool = False,
        ttl_s: int | None = None,
    ) -> SubscriptionHandle:
        """Subscribe to Home Assistant events and return a subscription handle.

        Args:
            event_type: Event type filter or ``None`` for all events.
            scope_id: Agent-loop scope identifier for cleanup.
            logical_name: Optional unique name for lookup/unsubscribe.
            persistent: Whether the subscription persists across scopes.
            ttl_s: Optional TTL in seconds for non-persistent subscriptions.

        Returns:
            Subscription handle with Home Assistant subscription id populated.
        """
        spec = {"event_type": event_type} if event_type else {}
        handle = await self._create_subscription_handle(
            scope_id=scope_id,
            logical_name=logical_name,
            persistent=persistent,
            ttl_s=ttl_s,
            spec_type="events",
            spec=spec,
        )
        response = await self.send_command("subscribe_events", spec)
        handle.ha_subscription_id = response.get("result")
        return handle

    async def subscribe_trigger(
        self,
        trigger: dict[str, Any],
        *,
        scope_id: str,
        logical_name: str | None = None,
        persistent: bool = False,
        ttl_s: int | None = None,
    ) -> SubscriptionHandle:
        """Subscribe to a trigger payload and return a subscription handle.

        Args:
            trigger: Home Assistant trigger payload.
            scope_id: Agent-loop scope identifier for cleanup.
            logical_name: Optional unique name for lookup/unsubscribe.
            persistent: Whether the subscription persists across scopes.
            ttl_s: Optional TTL in seconds for non-persistent subscriptions.

        Returns:
            Subscription handle with Home Assistant subscription id populated.
        """
        handle = await self._create_subscription_handle(
            scope_id=scope_id,
            logical_name=logical_name,
            persistent=persistent,
            ttl_s=ttl_s,
            spec_type="trigger",
            spec=trigger,
        )
        response = await self.send_command("subscribe_trigger", {"trigger": trigger})
        handle.ha_subscription_id = response.get("result")
        return handle

    async def unsubscribe(self, handle_or_name: SubscriptionHandle | str) -> None:
        """Unsubscribe a subscription handle or named subscription.

        Args:
            handle_or_name: Subscription handle or logical name.
        """
        handle = self._resolve_subscription(handle_or_name)
        if not handle:
            return
        ha_id = handle.ha_subscription_id
        if ha_id is not None:
            await self.send_command("unsubscribe_events", {"subscription": ha_id})
        await self._remove_subscription(handle)

    async def close_scope(self, scope_id: str) -> None:
        """Unsubscribe non-persistent subscriptions belonging to a scope.

        Args:
            scope_id: Agent-loop scope identifier to close.
        """
        async with self._subscription_lock:
            self._active_scopes.discard(scope_id)
            handles = [
                sub
                for sub in self._subscriptions.values()
                if sub.scope_id == scope_id and not sub.persistent
            ]
        for handle in handles:
            await self.unsubscribe(handle)

    def list_subscriptions(self) -> list[SubscriptionSummary]:
        """Return summaries of current subscriptions."""
        return [
            SubscriptionSummary(
                handle_id=sub.handle_id,
                scope_id=sub.scope_id,
                logical_name=sub.logical_name,
                persistent=sub.persistent,
                ttl_s=sub.ttl_s,
                created_at=sub.created_at,
                last_used_at=sub.last_used_at,
                spec_type=sub.spec_type,
                ha_subscription_id=sub.ha_subscription_id,
            )
            for sub in self._subscriptions.values()
        ]

    def register_callback(
        self,
        handle_or_name: SubscriptionHandle | str,
        callback: Callable[[dict[str, Any]], Awaitable[None] | None],
    ) -> None:
        """Register a callback for a subscription handle or name.

        Args:
            handle_or_name: Subscription handle or logical name.
            callback: Callable invoked with the event payload.

        Raises:
            HomeAssistantWsError: When the subscription is not found.
        """
        handle = self._resolve_subscription(handle_or_name)
        if not handle:
            raise HomeAssistantWsError("NOT_FOUND", "Subscription not found.")
        handle.add_callback(callback)

    async def wait_for_event(
        self,
        handle_or_name: SubscriptionHandle | str,
        *,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """Wait for the next matching event and then auto-unsubscribe.

        Args:
            handle_or_name: Subscription handle or logical name.
            predicate: Optional filter function for matching events.
            timeout_s: Optional timeout for waiting on an event.

        Returns:
            The matched event payload.

        Raises:
            HomeAssistantWsError: When the subscription is not found.
        """
        handle = self._resolve_subscription(handle_or_name)
        if not handle:
            raise HomeAssistantWsError("NOT_FOUND", "Subscription not found.")
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        async def _callback(event: dict[str, Any]) -> None:
            if predicate and not predicate(event):
                return
            if not future.done():
                future.set_result(event)

        handle.add_callback(_callback)
        try:
            result = await asyncio.wait_for(future, timeout=timeout_s)
        finally:
            await self.unsubscribe(handle)
        return result

    def _resolve_subscription(
        self, handle_or_name: SubscriptionHandle | str
    ) -> SubscriptionHandle | None:
        if isinstance(handle_or_name, SubscriptionHandle):
            return handle_or_name
        handle_id = self._subscriptions_by_name.get(handle_or_name)
        if handle_id is None:
            return None
        return self._subscriptions.get(handle_id)

    async def _create_subscription_handle(
        self,
        *,
        scope_id: str,
        logical_name: str | None,
        persistent: bool,
        ttl_s: int | None,
        spec_type: str,
        spec: dict[str, Any] | None,
    ) -> SubscriptionHandle:
        async with self._subscription_lock:
            if logical_name and logical_name in self._subscriptions_by_name:
                raise HomeAssistantWsError("CONFLICT", "Subscription name already exists.")
            handle_id = self._next_subscription_handle
            self._next_subscription_handle += 1
            created = time.time()
            ttl_value = ttl_s if ttl_s is not None else self._default_subscription_ttl_s
            handle = SubscriptionHandle(
                handle_id=handle_id,
                scope_id=scope_id,
                logical_name=logical_name,
                persistent=persistent,
                ttl_s=ttl_value,
                created_at=created,
                last_used_at=created,
                spec_type=spec_type,
                spec=spec,
            )
            self._subscriptions[handle_id] = handle
            if logical_name:
                self._subscriptions_by_name[logical_name] = handle_id
            self._active_scopes.add(scope_id)
            return handle

    async def _remove_subscription(self, handle: SubscriptionHandle) -> None:
        async with self._subscription_lock:
            self._subscriptions.pop(handle.handle_id, None)
            if handle.logical_name:
                self._subscriptions_by_name.pop(handle.logical_name, None)

    async def _connect_with_backoff(self) -> None:
        backoff = self._reconnect_backoff_initial_s
        while self._state != ConnectionState.READY:
            try:
                await self._connect_once()
                return
            except HomeAssistantWsError as exc:
                if exc.code == "AUTH_INVALID":
                    raise
                jitter = random.random() * self._reconnect_backoff_jitter
                delay = min(self._reconnect_backoff_max_s, backoff + jitter)
                logger.warning("Reconnect attempt failed: %s (retrying in %.2fs)", exc, delay)
                self.reconnect_count += 1
                await asyncio.sleep(delay)
                backoff = min(self._reconnect_backoff_max_s, backoff * 2)

    async def _connect_once(self) -> None:
        if not self._token:
            raise HomeAssistantWsError("AUTH_INVALID", "Home Assistant token is not configured.")
        self._state = ConnectionState.CONNECTING
        ws_url = self._build_ws_url(self._base_url)
        logger.info("Connecting to Home Assistant WS %s", ws_url)
        self._ws = await websockets.connect(ws_url, max_size=self._max_message_size)
        self._state = ConnectionState.AUTHENTICATING
        auth_required = await self._recv_json(timeout_s=self._default_timeout_s)
        if auth_required.get("type") != "auth_required":
            raise HomeAssistantWsError("AUTH_INVALID", "Unexpected auth response.")
        await self._send_json({"type": "auth", "access_token": self._token})
        auth_response = await self._recv_json(timeout_s=self._default_timeout_s)
        if auth_response.get("type") == "auth_invalid":
            self.auth_fail_count += 1
            raise HomeAssistantWsError("AUTH_INVALID", "Authentication failed.", auth_response)
        if auth_response.get("type") != "auth_ok":
            raise HomeAssistantWsError("AUTH_INVALID", "Unexpected auth result.", auth_response)
        self._state = ConnectionState.READY
        self._ready_event.set()
        self._last_received_at = time.time()
        self._reader_task = asyncio.create_task(self._reader_loop())
        if not self._dispatcher_task or self._dispatcher_task.done():
            self._dispatcher_task = asyncio.create_task(self._dispatcher_loop())
        if not self._janitor_task or self._janitor_task.done():
            self._janitor_task = asyncio.create_task(self._janitor_loop())
        await self._rehydrate_subscriptions()

    async def _send_command_once(
        self,
        command_type: str,
        payload: dict[str, Any],
        timeout_s: float,
        is_write: bool,
    ) -> dict[str, Any]:
        await self.ensure_connected()
        await self._ready_event.wait()
        if len(self._pending) >= self._max_in_flight:
            raise HomeAssistantWsError("BUSY", "Too many in-flight requests.")
        command_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[command_id] = future
        self._pending_meta[command_id] = PendingMeta(
            command_type=command_type,
            created_at=time.time(),
            is_write=is_write,
        )
        message = {"id": command_id, "type": command_type, **payload}
        try:
            await self._send_json(message)
            response = await asyncio.wait_for(future, timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            self.pending_timeouts += 1
            self._pending.pop(command_id, None)
            self._pending_meta.pop(command_id, None)
            raise HomeAssistantWsError("TIMEOUT", "Request timed out.") from exc
        except HomeAssistantWsError:
            self._pending.pop(command_id, None)
            self._pending_meta.pop(command_id, None)
            raise
        except Exception as exc:
            self._pending.pop(command_id, None)
            self._pending_meta.pop(command_id, None)
            raise HomeAssistantWsError("DISCONNECTED", "Connection lost.") from exc
        finally:
            self._pending.pop(command_id, None)
            self._pending_meta.pop(command_id, None)

        if not response.get("success", True):
            raise HomeAssistantWsError("HA_ERROR", "Home Assistant error.", response.get("error"))
        return response

    async def _reader_loop(self) -> None:
        if not self._ws:
            return
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=self._stall_timeout_s)
                except asyncio.TimeoutError:
                    await self._handle_disconnect("STALL", "Connection stalled.")
                    return
                except ConnectionClosed as exc:
                    await self._handle_disconnect("DISCONNECTED", f"Connection closed: {exc}")
                    return
                if raw is None:
                    await self._handle_disconnect("DISCONNECTED", "Connection closed.")
                    return
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                if len(raw) > self._max_message_size:
                    await self._handle_disconnect("OVERSIZE", "Message too large.")
                    return
                self._last_received_at = time.time()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Failed to decode WS message: %s", raw)
                    continue
                if message.get("type") == "ping":
                    pong = {"type": "pong"}
                    if "id" in message:
                        pong["id"] = message["id"]
                    await self._send_json(pong)
                    continue
                if "id" in message and message.get("type") == "result":
                    await self._handle_result(message)
                    continue
                if message.get("type") == "event" and "id" in message:
                    await self._handle_event(message)
                    continue
                logger.debug("Unhandled WS message: %s", message)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            await self._handle_disconnect("DISCONNECTED", f"Reader error: {exc}")

    async def _handle_result(self, message: dict[str, Any]) -> None:
        command_id = message.get("id")
        future = self._pending.get(command_id)
        if future and not future.done():
            future.set_result(message)

    async def _handle_event(self, message: dict[str, Any]) -> None:
        ha_id = message.get("id")
        handle = next(
            (sub for sub in self._subscriptions.values() if sub.ha_subscription_id == ha_id),
            None,
        )
        if not handle:
            return
        event_payload = message.get("event", {})
        handle.last_used_at = time.time()
        await self._enqueue_event(handle.handle_id, event_payload)

    async def _enqueue_event(self, handle_id: int, event: dict[str, Any]) -> None:
        if self._event_queue.full():
            try:
                self._event_queue.get_nowait()
                self._event_queue.task_done()
            except asyncio.QueueEmpty:
                pass
            self.dropped_events += 1
        await self._event_queue.put((handle_id, event))

    async def _dispatcher_loop(self) -> None:
        while True:
            try:
                handle_id, event = await self._event_queue.get()
            except asyncio.CancelledError:
                return
            handle = self._subscriptions.get(handle_id)
            if not handle:
                self._event_queue.task_done()
                continue
            for callback in list(handle.callbacks):
                asyncio.create_task(self._invoke_callback(callback, event))
            self._event_queue.task_done()

    async def _invoke_callback(
        self,
        callback: Callable[[dict[str, Any]], Awaitable[None] | None],
        event: dict[str, Any],
    ) -> None:
        try:
            result = callback(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            logger.exception("Subscription callback failed")

    async def _janitor_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._janitor_interval_s)
                await self._cleanup_subscriptions()
            except asyncio.CancelledError:
                return

    async def _cleanup_subscriptions(self) -> None:
        now = time.time()
        async with self._subscription_lock:
            subs = list(self._subscriptions.values())
        expired = [
            sub
            for sub in subs
            if not sub.persistent and sub.ttl_s and (now - sub.created_at) > sub.ttl_s
        ]
        for sub in expired:
            logger.info("Subscription expired: %s", sub.handle_id)
            await self.unsubscribe(sub)
        await self._enforce_subscription_caps()

    async def _enforce_subscription_caps(self) -> None:
        async with self._subscription_lock:
            subs = list(self._subscriptions.values())
        if len(subs) <= self._max_subscriptions_total:
            return
        non_persistent = [sub for sub in subs if not sub.persistent]
        non_persistent.sort(key=lambda sub: sub.last_used_at)
        while len(subs) > self._max_subscriptions_total and non_persistent:
            sub = non_persistent.pop(0)
            await self.unsubscribe(sub)
            subs.remove(sub)
        non_persistent = [sub for sub in subs if not sub.persistent]
        if len(non_persistent) <= self._max_non_persistent:
            return
        non_persistent.sort(key=lambda sub: sub.last_used_at)
        while len(non_persistent) > self._max_non_persistent:
            sub = non_persistent.pop(0)
            await self.unsubscribe(sub)

    async def _rehydrate_subscriptions(self) -> None:
        async with self._subscription_lock:
            subs = list(self._subscriptions.values())
            active_scopes = set(self._active_scopes)
        now = time.time()
        for sub in subs:
            is_expired = not sub.persistent and sub.ttl_s and (now - sub.created_at) > sub.ttl_s
            if sub.persistent or (sub.scope_id in active_scopes and not is_expired):
                await self._resubscribe(sub)
            else:
                await self._remove_subscription(sub)

    async def _resubscribe(self, sub: SubscriptionHandle) -> None:
        if sub.spec_type == "events":
            payload = sub.spec or {}
            response = await self.send_command("subscribe_events", payload)
            sub.ha_subscription_id = response.get("result")
        elif sub.spec_type == "trigger":
            payload = {"trigger": sub.spec or {}}
            response = await self.send_command("subscribe_trigger", payload)
            sub.ha_subscription_id = response.get("result")

    async def _handle_disconnect(self, code: str, message: str) -> None:
        if self._state == ConnectionState.CLOSING:
            return
        logger.warning("WS disconnected: %s", message)
        self._ready_event.clear()
        self._state = ConnectionState.DISCONNECTED
        if self._ws:
            await self._ws.close()
        await self._fail_pending(code, message)
        self._schedule_reconnect()

    async def _fail_pending(self, code: str, message: str) -> None:
        error = HomeAssistantWsError(code, message)
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(error)
        self._pending.clear()
        self._pending_meta.clear()

    async def _send_json(self, message: dict[str, Any]) -> None:
        if not self._ws:
            raise HomeAssistantWsError("DISCONNECTED", "WebSocket not connected.")
        payload = json.dumps(message)
        await self._ws.send(payload)

    async def _recv_json(self, timeout_s: float) -> dict[str, Any]:
        if not self._ws:
            raise HomeAssistantWsError("DISCONNECTED", "WebSocket not connected.")
        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            raise HomeAssistantWsError("TIMEOUT", "Timed out waiting for response.") from exc
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def _build_ws_url(self, base_url: str) -> str:
        parsed = parse.urlparse(base_url)
        scheme = parsed.scheme
        if scheme in {"http", "https"}:
            scheme = "wss" if scheme == "https" else "ws"
        if scheme not in {"ws", "wss"}:
            raise HomeAssistantWsError("CONFIG", "Invalid base URL scheme.")
        netloc = parsed.netloc or parsed.path
        path = parsed.path if parsed.netloc else ""
        ws_path = f"{path.rstrip('/')}/api/websocket"
        return parse.urlunparse((scheme, netloc, ws_path, "", "", ""))

    def _is_write_command(self, command_type: str) -> bool:
        write_types = {
            "call_service",
            "fire_event",
            "set_state",
            "delete_state",
        }
        if command_type in write_types:
            return True
        if command_type.startswith("config/") and "update" in command_type:
            return True
        return False

    def _schedule_reconnect(self) -> None:
        if self._state == ConnectionState.CLOSING:
            return
        if self._reconnect_task and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        try:
            async with self._connect_lock:
                if self._state != ConnectionState.DISCONNECTED:
                    return
                await self._connect_with_backoff()
        except asyncio.CancelledError:
            return


"""Example usage:

client = HomeAssistantWebSocketClient()
await client.ensure_connected()
response = await client.send_command("get_states", {})

scope_id = "agent-loop-123"
handle = await client.subscribe_events(
    "state_changed",
    scope_id=scope_id,
    logical_name="state-watch",
)
await asyncio.sleep(10)
await client.close_scope(scope_id)
"""
