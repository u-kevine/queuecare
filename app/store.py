"""In-memory data store. No database setup required."""

from itertools import count

users: dict[str, dict] = {}
appointments: dict[int, dict] = {}
tokens: dict[str, str] = {}

_appointment_ids = count(1)


def next_appointment_id() -> int:
    return next(_appointment_ids)


def reset() -> None:
    """Clear all data. Used by tests to guarantee a clean state."""
    global _appointment_ids
    users.clear()
    appointments.clear()
    tokens.clear()
    _appointment_ids = count(1)
