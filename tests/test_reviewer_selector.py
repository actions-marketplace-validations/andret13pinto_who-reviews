from __future__ import annotations

import pytest

from pr_review_action.config import ReviewConfig
from pr_review_action.reviewer_selector import ReviewerSelector
from pr_review_action.strategies.base import SelectionStrategy

REPO = "org/repo"
PR = 42


class TestNoOwnership:
    """When no squad owns the changed files → 2 random reviewers."""

    def test_picks_two_reviewers(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["README.md"],
            author="alice",
            repo=REPO,
            pr_number=PR,
        )

        assert len(result) == 2

    def test_excludes_author(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["README.md"],
            author="alice",
            repo=REPO,
            pr_number=PR,
        )

        assert "alice" not in result

    def test_no_duplicates(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["README.md"],
            author="alice",
            repo=REPO,
            pr_number=PR,
        )

        assert len(result) == len(set(result))


class TestSingleSquad:
    """Single squad touched → 1 from squad + 1 outsider."""

    def test_one_from_squad_one_outsider(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["src/payments/stripe.py"],
            author="alice",
            repo=REPO,
            pr_number=PR,
        )

        # 1 from payments squad (bob or charlie, since alice is author)
        # + 1 outsider (not in payments)
        assert len(result) == 2
        payments_members = {"bob", "charlie"}
        outsiders = review_config.all_members - {"alice", "bob", "charlie"}

        assert result[0] in payments_members
        assert result[1] in outsiders

    def test_excludes_author_from_squad(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["src/payments/stripe.py"],
            author="bob",
            repo=REPO,
            pr_number=PR,
        )

        assert "bob" not in result


class TestMultipleSquads:
    """Multiple squads touched → 1 from each + 1 outsider."""

    def test_one_per_squad_plus_outsider(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["src/payments/stripe.py", "src/infra/deploy.py"],
            author="alice",
            repo=REPO,
            pr_number=PR,
        )

        # 1 from payments + 1 from platform + 1 outsider (growth)
        assert len(result) == 3
        assert "alice" not in result

    def test_all_squads_touched(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=[
                "src/payments/stripe.py",
                "src/infra/deploy.py",
                "src/growth/ab.py",
            ],
            author="alice",
            repo=REPO,
            pr_number=PR,
        )

        # 1 from each squad (3), no outsider possible (all squads affected)
        # but outsider pool is empty since all members belong to affected squads
        assert len(result) == 3
        assert "alice" not in result


class TestEdgeCases:
    def test_author_is_sole_squad_member(
        self,
        deterministic_strategy: SelectionStrategy,
    ) -> None:
        config = ReviewConfig(
            strategy="random",
            squads=[
                {"name": "solo", "members": ["alice"], "paths": ["src/**"]},  # type: ignore[list-item]
                {"name": "other", "members": ["bob", "charlie"], "paths": ["lib/**"]},  # type: ignore[list-item]
            ],
        )
        selector = ReviewerSelector(config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["src/foo.py"],
            author="alice",
            repo=REPO,
            pr_number=PR,
        )

        # No one from solo squad, but should get outsider
        assert "alice" not in result
        assert len(result) >= 1

    @pytest.mark.parametrize(
        "author",
        ["alice", "bob", "charlie", "dave", "eve", "frank", "grace", "heidi"],
    )
    def test_author_always_excluded(
        self,
        review_config: ReviewConfig,
        deterministic_strategy: SelectionStrategy,
        author: str,
    ) -> None:
        selector = ReviewerSelector(review_config, deterministic_strategy)

        result = selector.select_reviewers(
            changed_files=["src/payments/stripe.py"],
            author=author,
            repo=REPO,
            pr_number=PR,
        )

        assert author not in result
