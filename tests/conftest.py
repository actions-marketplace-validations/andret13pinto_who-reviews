from __future__ import annotations

import pytest

from who_reviews.config import ReviewConfig, SquadConfig
from who_reviews.strategies.base import SelectionContext, SelectionStrategy


@pytest.fixture()
def payments_squad() -> SquadConfig:
    return SquadConfig(
        name="payments",
        members=["alice", "bob", "charlie"],
        paths=["src/payments/**", "src/billing/**"],
    )


@pytest.fixture()
def platform_squad() -> SquadConfig:
    return SquadConfig(
        name="platform",
        members=["dave", "eve", "frank"],
        paths=["src/infra/**", "src/auth/**"],
    )


@pytest.fixture()
def growth_squad() -> SquadConfig:
    return SquadConfig(
        name="growth",
        members=["grace", "heidi"],
        paths=["src/growth/**", "src/onboarding/**"],
    )


@pytest.fixture()
def review_config(
    payments_squad: SquadConfig,
    platform_squad: SquadConfig,
    growth_squad: SquadConfig,
) -> ReviewConfig:
    return ReviewConfig(
        strategy="random",
        squads=[payments_squad, platform_squad, growth_squad],
    )


@pytest.fixture()
def selection_context() -> SelectionContext:
    return SelectionContext(repo="org/repo", pr_number=42, role="test")


class DeterministicStrategy:
    """Always picks the first candidate alphabetically."""

    def select(self, candidates: list[str], context: SelectionContext) -> str:
        return sorted(candidates)[0]


@pytest.fixture()
def deterministic_strategy() -> SelectionStrategy:
    return DeterministicStrategy()
