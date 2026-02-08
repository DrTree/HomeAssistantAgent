# Tool Spec: ha_search_services

Search Home Assistant services (domain + service) with optional filters, returning compact matches suitable for downstream call-service actions.

## Inputs
- `query` (string, default: ""): case-insensitive substring match against domain, service, description, and fields.
- `domain` (string|null, default: null): optional domain filter (case-insensitive exact match; when match != exact, may resolve ambiguity).
- `include_fields` (boolean, default: false): include a compact field schema per service (allowlisted).
- `include_targets` (boolean, default: false): include boolean target support flags when present.
- `limit` (integer, default: 25, range 1..50): result cap (values > 50 clamp to 50).
- `offset` (integer, default: 0, range 0..10_000): pagination offset.
- `sort` (string enum, default: "relevance"): `relevance` | `domain` | `service`.
- `match` (string enum, default: "contains"): `contains` | `prefix` | `exact` (applies to domain/service tokens).
- `return_raw` (boolean, default: false): must remain false by default; still apply allowlists if true.

## Home Assistant interaction
- Primary call (WS): `{"type":"get_services"}`
- REST fallback: `GET /api/services`

## Output (success)
```
{
  "ok": true,
  "count": <int>,
  "total_available": <int|null>,
  "offset": <int>,
  "limit": <int>,
  "truncated": <bool>,
  "truncated_scan": <bool>,
  "services": [
    {
      "domain": <string>,
      "service": <string>,
      "name": <string|null>,
      "description": <string|null>,
      "score": <int|null>,
      "targets": {
        "supports_entity_target": <bool>,
        "supports_device_target": <bool>,
        "supports_area_target": <bool>
      }|null,
      "fields": [
        {
          "field": <string>,
          "required": <bool|null>,
          "selector_type": <string|null>,
          "description": <string|null>,
          "example": <string|number|boolean|null>
        }
      ]|null,
      "fields_truncated": <bool|null>
    }
  ]
}
```

## Output (error)
```
{
  "ok": false,
  "code": "HA_UNAVAILABLE"|"HA_AUTH_FAILED"|"INVALID_ARGUMENT"|"DOMAIN_NOT_FOUND"|"AMBIGUOUS_DOMAIN"|"INTERNAL_ERROR",
  "message": <string>,
  "details": <object|null>,
  "candidates": <array|null>
}
```

## Notes
- Empty query + no domain returns the first `limit` services sorted by domain/service, plus a note.
- Hard caps: scan up to 10,000 services, max 25 fields per service.
- Descriptions are truncated (service 200 chars, field 120 chars).
