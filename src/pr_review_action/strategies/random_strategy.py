from __future__ import annotations

import random

from pr_review_action.strategies.base import SelectionContext


class RandomStrategy:
    def select(self, candidates: list[str], context: SelectionContext) -> str:
        return random.choice(candidates)
