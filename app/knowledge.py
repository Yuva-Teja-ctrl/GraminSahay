"""Scheme knowledge base loader.

Loads the Telangana scheme JSON once at startup and keeps it in memory, exposing lookups.
Equivalent to the Java ``SchemeRepository``.
"""

import json
from pathlib import Path

from app.domain import Scheme


class SchemeRepository:
    """In-memory store of all welfare schemes, keyed by id."""

    def __init__(self, schemes_path: str) -> None:
        raw = Path(schemes_path).read_text(encoding="utf-8")
        records = json.loads(raw)
        # Pydantic validates each JSON object against the Scheme model as we build it.
        schemes = [Scheme.model_validate(record) for record in records]
        self._by_id: dict[str, Scheme] = {s.id: s for s in schemes}

    def all(self) -> list[Scheme]:
        return list(self._by_id.values())

    def by_id(self, scheme_id: str) -> Scheme | None:
        return self._by_id.get(scheme_id)
