from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    """Backward-compatible pagination for list endpoints.

    Responses remain arrays/objects so existing mobile and web clients keep
    working. Clients can request subsequent pages with ``limit`` and ``offset``.
    """

    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Query(0, ge=0)

    @property
    def sql(self) -> dict[str, int]:
        return {"limit": self.limit, "offset": self.offset}
