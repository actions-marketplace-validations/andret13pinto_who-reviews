from __future__ import annotations

import random

from who_reviews.strategies.base import SelectionContext


class RandomStrategy:
    def select(self, candidates: list[str], context: SelectionContext) -> str:
        return random.choice(candidates)
