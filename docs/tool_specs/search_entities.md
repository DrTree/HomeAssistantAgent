# Tool Spec: search_entities

## Summary
Provide a Home Assistant tool that fuzzy-searches entities by a user-provided query (e.g., "bedroom ceiling") and returns the top matches ranked by similarity.

## Inputs
- `query` (string, required): Search phrase to match against entity names/ids.
- `limit` (integer, optional, default 10): Max number of matches to return.

## Behavior
- Fetch entity states from Home Assistant.
- Build a searchable string for each entity using `entity_id` and friendly name (when available).
- Use fuzzy matching (rapidfuzz or equivalent) to score candidates.
- Return the top `limit` matches sorted by score.
- Handle empty/invalid input gracefully with an error response.

## Output
Return a JSON object with:
- `ok` (bool)
- `query` (string)
- `count` (int)
- `matches` (list of objects)
  - `entity_id` (string)
  - `name` (string | null)
  - `domain` (string)
  - `state` (string | null)
  - `score` (float)
- `error` (object, optional) with `code`, `message`, `details` when not ok.
