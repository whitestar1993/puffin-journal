"""Storage layer: the ONLY place that reads or writes the database.

Every public function takes ``user_id`` and scopes its queries to it. Routers
must not build queries themselves. If app-level field encryption is ever added,
it belongs here (encrypt on write / decrypt on read), invisible to the API.
"""

from app.storage import entries, prompts, tags, users
from app.storage.errors import Conflict, Invalid, NotFound

__all__ = ["entries", "prompts", "tags", "users", "Conflict", "Invalid", "NotFound"]
