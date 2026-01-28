# HomeAssistantWebSocketClient

A long‑lived, resilient WebSocket client for **Home Assistant**, designed for agent‑style and service‑style Python applications.

This client maintains a single authenticated WebSocket connection, supports concurrent request/response commands, manages event and trigger subscriptions, and automatically handles reconnects, backoff, and subscription rehydration.

---

## Features

* Single persistent WebSocket connection per Home Assistant instance
* Async request/response multiplexing
* Event and trigger subscriptions
* Subscription scopes, TTLs, and persistence
* Automatic reconnect with exponential backoff
* Automatic re‑subscription after reconnect
* Back‑pressure, timeouts, and safety caps for long‑running processes

---

## Installation / Requirements

* Python 3.10+
* `websockets`
* An existing Home Assistant instance with WebSocket API enabled
* A **long‑lived access token**

---

## Configuration

The client can be configured explicitly or via environment variables.

### Environment variables

| Variable               | Description                                                     |
| ---------------------- | --------------------------------------------------------------- |
| `HOME_ASSISTANT_URL`   | Base URL for Home Assistant (default: `http://supervisor/core`) |
| `SUPERVISOR_TOKEN`     | Long‑lived access token (preferred in add‑ons)                  |
| `HOME_ASSISTANT_TOKEN` | Fallback token variable                                         |

### Programmatic configuration

```python
client = HomeAssistantWebSocketClient(
    base_url="http://homeassistant.local:8123",
    token="YOUR_LONG_LIVED_TOKEN",
)
```

---

## Basic Usage

### Create and connect

```python
client = HomeAssistantWebSocketClient()
await client.ensure_connected()
```

> You usually don’t need to call `ensure_connected()` explicitly — it is called automatically when sending commands or creating subscriptions.

---

## Sending Commands

Use `send_command()` for standard Home Assistant WebSocket commands.

```python
response = await client.send_command(
    "get_states",
    {}
)
```

### Behaviour

* Commands are sent with an incrementing `id`
* Responses are awaited asynchronously
* Multiple commands can be in flight concurrently
* Errors are raised as `HomeAssistantWsError`

### Timeouts and retries

```python
await client.send_command(
    "get_states",
    {},
    timeout_s=5,
    retry_read_once=True,
)
```

* Read‑only commands are retried **once** after reconnect by default
* Write commands are **never retried**

---

## Subscriptions

Subscriptions are first‑class objects with lifecycle management.

### Key concepts

| Concept              | Meaning                                      |
| -------------------- | -------------------------------------------- |
| `SubscriptionHandle` | Local representation of a HA subscription    |
| `scope_id`           | Logical lifecycle boundary for cleanup       |
| `persistent`         | Survives scope cleanup and reconnects        |
| `ttl_s`              | Auto‑expiry for non‑persistent subscriptions |
| `logical_name`       | Optional unique lookup name                  |

---

## Subscribing to Events

```python
handle = await client.subscribe_events(
    event_type="state_changed",
    scope_id="agent-loop-1",
    logical_name="state_watch",
)
```

* `event_type=None` subscribes to **all events**
* Automatically re‑subscribed after reconnect

---

## Subscribing to Triggers

```python
handle = await client.subscribe_trigger(
    trigger={
        "platform": "state",
        "entity_id": "light.kitchen",
    },
    scope_id="agent-loop-1",
)
```

Triggers behave the same as event subscriptions, but use Home Assistant’s trigger engine.

---

## Receiving Events

### Registering callbacks

```python
async def on_event(event):
    print(event)

client.register_callback(handle, on_event)
```

Notes:

* Callbacks may be sync or async
* Each callback runs in its own task
* Exceptions are logged but do not stop dispatching

---

### Waiting for a single event (one‑shot)

```python
event = await client.wait_for_event(
    handle,
    predicate=lambda e: e["data"]["entity_id"] == "light.kitchen",
    timeout_s=30,
)
```

Behaviour:

* Waits for the first matching event
* Automatically unsubscribes afterward
* Useful for request/response‑style flows

---

## Subscription Scopes

Scopes provide structured cleanup for agent loops or tasks.

### Closing a scope

```python
await client.close_scope("agent-loop-1")
```

This unsubscribes all **non‑persistent** subscriptions in that scope.

Typical usage pattern:

```python
scope_id = "agent-loop-123"
try:
    ...
finally:
    await client.close_scope(scope_id)
```

---

## Automatic Cleanup & Limits

To protect long‑running processes, the client enforces limits:

### TTL expiry

* Non‑persistent subscriptions expire after `ttl_s`
* Cleaned periodically by a background janitor task

### Subscription caps

| Setting                   | Purpose                         |
| ------------------------- | ------------------------------- |
| `max_subscriptions_total` | Global subscription cap         |
| `max_non_persistent`      | Non‑persistent subscription cap |

Oldest unused subscriptions are evicted first.

---

## Reconnect & Resilience

Handled automatically:

* Exponential backoff with jitter
* Stall detection (no inbound messages)
* Automatic re‑authentication
* Automatic subscription rehydration

Subscriptions are restored if they are:

* Persistent **or**
* Belong to an active scope and not expired

No manual reconnect or resubscribe logic is required.

---

## Shutdown

```python
await client.close()
```

This:

* Cancels background tasks
* Closes the WebSocket
* Fails all pending requests
* Stops reconnect attempts

---

## Error Handling

All operational failures raise `HomeAssistantWsError`.

| Code           | Meaning                          |
| -------------- | -------------------------------- |
| `DISCONNECTED` | Connection lost                  |
| `AUTH_INVALID` | Token missing or rejected        |
| `TIMEOUT`      | Command timeout                  |
| `BUSY`         | Too many in‑flight requests      |
| `HA_ERROR`     | Home Assistant returned an error |
| `CONFIG`       | Invalid client configuration     |

Errors are explicit and structured, making them suitable for agent logic.

---

## Intended Use Cases

This client is ideal for:

* Home Assistant add‑ons
* Local agents and automation services
* Tools mixing commands, events, and triggers
* Long‑running processes that must survive HA restarts

It is **not** intended as a short‑lived request client — it assumes ownership of a durable WebSocket connection.

---

## Example

```python
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
```
