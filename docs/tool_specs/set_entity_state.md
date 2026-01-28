# Tool Specification: set_entity_state

- **Tool name**
  - `set_entity_state`

- **Purpose**
  - Invoke Home Assistant services to change the state of one or more entities **by known `entity_id`**
  - Service-first control only; no direct state injection

- **Approval**
  - `needs_approval: true`

- **Assumptions**
  - Caller already resolved and validated `entity_id` values
  - HA API client exists and can call services and read states

---

## Inputs

- `entity_ids`
  - type: `string[]`
  - required: `true`
  - constraints:
    - non-empty
    - unique values
    - `max_items: 20`

- `service`
  - type: `string`
  - required: `true`
  - format: `"<domain>.<service>"`
  - constraints:
    - must match allowlisted domains
    - domain must be compatible with target entities (see Validation)

- `service_data`
  - type: `object`
  - required: `false`
  - default: `{}`
  - constraints:
    - shallow object only (no nested objects beyond 1 level)
    - `max_keys: 20`
    - values must be JSON-serializable primitives or arrays of primitives
    - unknown keys are passed through as-is

- `dry_run`
  - type: `boolean`
  - required: `false`
  - default: `false`
  - behavior:
    - if `true`, do not call HA; return computed payload and expected effects

- `verify`
  - type: `"none" | "basic"`
  - required: `false`
  - default: `"basic"`
  - behavior:
    - `"basic"` performs a single post-call state readback

- `skip_if_already`
  - type: `boolean`
  - required: `false`
  - default: `false`
  - behavior:
    - applies only to clearly idempotent services (e.g., `turn_on`, `turn_off`)
    - entities already in the requested state are skipped

---

## Home Assistant Interaction

- **Pre-read (conditional)**
  - `GET /states/{entity_id}` (or equivalent WS)
  - used when:
    - `skip_if_already = true`
    - or `verify = "basic"`
    - or `dry_run = true`

- **Service call**
  - `POST /services/{domain}/{service}`
  - payload:
    - `target.entity_id: string[]`
    - merged with `service_data`
  - single call when multiple entities are provided

- **Post-read (conditional)**
  - `GET /states/{entity_id}` (single pass)
  - only when `verify = "basic"` and `dry_run = false`

---

## Validation Rules

- **Entity existence**
  - Each `entity_id` must exist
  - Partial execution allowed:
    - missing entities are reported individually
    - valid entities continue processing

- **Service domain compatibility**
  - Default rule:
    - service domain must match entity domain
  - Exceptions:
    - explicitly allowed generic domains (e.g., `homeassistant.turn_on`) if included in allowlist

- **Service allowlist (v1)**
  - Allowed domains:
    - `light`
    - `switch`
    - `climate`
    - `cover`
    - `lock`
    - `fan`
    - `media_player`
    - `scene`
    - `script`
    - `vacuum`
    - `humidifier`
    - `water_heater`
    - `alarm_control_panel`
    - `input_boolean`
    - `input_number`
    - `input_select`
    - `input_text`
    - `counter`
    - `number`
    - `select`
  - Any service outside allowlist → error `DOMAIN_NOT_ALLOWED`

- **Non-idempotent services**
  - Examples: `toggle`, `scene.turn_on`, `script.turn_on`
  - Behavior:
    - `skip_if_already` ignored
    - explicitly marked in response summary

---

## Filtering & Token-Safety Rules

- Hard caps enforced on:
  - `entity_ids` (`max_items`)
  - `service_data` size and depth
- Returned state fields are allowlisted:
  - `state`
  - `last_changed`
- No attributes blobs returned
- Truncation handling:
  - if internal expansion exceeds caps, truncate and report

---

## Return Shape

- Envelope
  - `ok: boolean`
  - `service: string`
  - `requested_count: number`
  - `processed_count: number`
  - `skipped_count: number`
  - `truncated: boolean`
  - `dry_run: boolean`

- `per_entity: []`
  - items:
    - `entity_id: string`
    - `ok: boolean`
    - `skipped: boolean`
    - `error_code?: string`
    - `before_state?: string`
    - `after_state?: string`
    - `changed?: boolean`

- `errors` (optional)
  - list of unique error summaries if any failures occurred

---

## Error Handling

- `ENTITY_NOT_FOUND`
  - one or more `entity_id` values do not exist
  - returned per-entity; does not abort whole call

- `DOMAIN_NOT_ALLOWED`
  - service domain not in allowlist
  - aborts execution; no entities processed

- `DOMAIN_ENTITY_MISMATCH`
  - service domain incompatible with one or more entities
  - mismatched entities skipped with per-entity error

- `SERVICE_CALL_FAILED`
  - HA service call error
  - returned with partial results if applicable

- `INVALID_INPUT`
  - malformed service string or invalid `service_data`

---

## Approval Prompt Requirements

- Must display:
  - service (`domain.service`)
  - count of target entities (and truncated list if needed)
  - top-level keys of `service_data`
- Must describe:
  - intended change
  - impacted entities
  - rollback suggestion when obvious (e.g., `turn_off` for `turn_on`)

---

## Non-Goals

- No entity/area/device/label resolution
- No direct state injection or developer-state overrides
- No configuration changes or reloads
- No streaming updates or long polling
- No attribute-level diffing beyond allowlisted fields

---

## Unit Test Expectations (minimum)

- Single entity, valid service, verified success
- Multiple entities, single service call
- Partial missing entities handled without abort
- Domain not allowlisted → hard failure
- Domain/entity mismatch → per-entity failure
- `dry_run = true` produces no HA service call
- `skip_if_already = true` skips appropriate entities
- `verify = "none"` skips post-read
