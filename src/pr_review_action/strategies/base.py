from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SelectionContext:
    repo: str
    pr_number: int
    role: str


class SelectionStrategy(Protocol):
    def select(self, candidates: list[str], context: SelectionContext) -> str: ...
