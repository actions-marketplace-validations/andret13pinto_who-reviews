from __future__ import annotations

import json
from pathlib import Path

from pr_review_action.strategies.base import SelectionContext


class RoundRobinStrategy:
    def __init__(self, state_path: Path = Path(".pr-review-state.json")) -> None:
        self._state_path = state_path

    def select(self, candidates: list[str], context: SelectionContext) -> str:
        counts = self._load_counts()
        candidate_counts = {c: counts.get(c, 0) for c in candidates}
        selected = min(candidate_counts, key=candidate_counts.__getitem__)
        counts[selected] = counts.get(selected, 0) + 1
        self._save_counts(counts)
        return selected

    def _load_counts(self) -> dict[str, int]:
        if not self._state_path.exists():
            return {}
        data: dict[str, object] = json.loads(self._state_path.read_text())
        counts: dict[str, int] = data.get("assignment_counts", {})  # type: ignore[assignment]
        return counts

    def _save_counts(self, counts: dict[str, int]) -> None:
        data: dict[str, object] = {}
        if self._state_path.exists():
            data = json.loads(self._state_path.read_text())
        data["assignment_counts"] = counts
        self._state_path.write_text(json.dumps(data, indent=2))
