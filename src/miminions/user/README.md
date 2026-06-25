# MiMinions User Module

A minimal user module. The `User` data model is implemented; the
`UserController` persistence layer is **not yet implemented**.

## `User` model

A simple dataclass with JSON serialization (`miminions.user.model`):

```python
from datetime import datetime, timezone
from miminions.user.model import User

user = User(
    id="user_123",
    name="Jane Doe",
    api_key="...",
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)

data = user.to_dict()          # datetimes serialized to ISO strings
restored = User.from_dict(data)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Display name |
| `api_key` | `str` | API key |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last-update timestamp |

## `UserController` — not implemented

> [!WARNING]
> `UserController` (`miminions.user.controller`) is a **stub**. Every method —
> including `__init__` — raises `NotImplementedError`, so it cannot be
> instantiated. CRUD and API-key methods (`create_user`, `get_user`,
> `update_user`, `delete_user`, `list_users`, `generate_api_key`,
> `validate_api_key`) are placeholders for a future release. Do not rely on
> them yet.

If you need per-user persistence today, use the `User` dataclass with your own
storage, or model identities at the workspace/agent layer (see the
[CLI](https://miminions.ai/modules/cli/) `auth` and `agent` commands).
