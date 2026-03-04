from __future__ import annotations

import json
from pathlib import Path

import pytest

from pr_review_action.strategies import (
    LeastRecentStrategy,
    RandomStrategy,
    RoundRobinStrategy,
    SelectionContext,
)


@pytest.fixture()
def ctx() -> SelectionContext:
    return SelectionContext(repo="org/repo", pr_number=1, role="test")


@pytest.fixture()
def candidates() -> list[str]:
    return ["alice", "bob", "charlie"]


class TestRandomStrategy:
    def test_selects_from_candidates(
        self, candidates: list[str], ctx: SelectionContext
    ) -> None:
        strategy = RandomStrategy()
        result = strategy.select(candidates, ctx)
        assert result in candidates

    def test_single_candidate(self, ctx: SelectionContext) -> None:
        result = RandomStrategy().select(["alice"], ctx)
        assert result == "alice"


class TestRoundRobinStrategy:
    def test_distributes_evenly(self, tmp_path: Path, ctx: SelectionContext) -> None:
        state_path = tmp_path / "state.json"
        strategy = RoundRobinStrategy(state_path=state_path)
        candidates = ["alice", "bob"]

        picks = [strategy.select(candidates, ctx) for _ in range(4)]

        assert picks.count("alice") == 2
        assert picks.count("bob") == 2

    def test_picks_least_assigned(self, tmp_path: Path, ctx: SelectionContext) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"assignment_counts": {"alice": 5, "bob": 1}}))
        strategy = RoundRobinStrategy(state_path=state_path)

        result = strategy.select(["alice", "bob"], ctx)
        assert result == "bob"

    def test_persists_state(self, tmp_path: Path, ctx: SelectionContext) -> None:
        state_path = tmp_path / "state.json"
        strategy = RoundRobinStrategy(state_path=state_path)

        strategy.select(["alice", "bob"], ctx)

        data = json.loads(state_path.read_text())
        assert "assignment_counts" in data


class TestLeastRecentStrategy:
    def test_picks_never_assigned(self, tmp_path: Path, ctx: SelectionContext) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"last_assigned": {"alice": 1000.0}}))
        strategy = LeastRecentStrategy(state_path=state_path)

        result = strategy.select(["alice", "bob"], ctx)
        assert result == "bob"

    def test_picks_oldest_assignment(
        self, tmp_path: Path, ctx: SelectionContext
    ) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text(
            json.dumps({"last_assigned": {"alice": 200.0, "bob": 100.0}})
        )
        strategy = LeastRecentStrategy(state_path=state_path)

        result = strategy.select(["alice", "bob"], ctx)
        assert result == "bob"

    def test_persists_timestamp(self, tmp_path: Path, ctx: SelectionContext) -> None:
        state_path = tmp_path / "state.json"
        strategy = LeastRecentStrategy(state_path=state_path)

        strategy.select(["alice"], ctx)

        data = json.loads(state_path.read_text())
        assert "last_assigned" in data
        assert data["last_assigned"]["alice"] > 0
