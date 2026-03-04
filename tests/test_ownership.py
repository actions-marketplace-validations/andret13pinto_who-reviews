from __future__ import annotations

import pytest

from pr_review_action.config import ReviewConfig
from pr_review_action.ownership import resolve_ownership


class TestResolveOwnership:
    @pytest.mark.parametrize(
        "changed_files,expected_squad_names",
        [
            (["src/payments/stripe.py"], ["payments"]),
            (["src/billing/invoice.py"], ["payments"]),
            (["src/infra/deploy.py"], ["platform"]),
            (["src/auth/login.py"], ["platform"]),
            (["src/growth/experiment.py"], ["growth"]),
            (["src/onboarding/wizard.py"], ["growth"]),
        ],
        ids=[
            "payments-direct",
            "billing-maps-to-payments",
            "infra-maps-to-platform",
            "auth-maps-to-platform",
            "growth-direct",
            "onboarding-maps-to-growth",
        ],
    )
    def test_single_squad_ownership(
        self,
        review_config: ReviewConfig,
        changed_files: list[str],
        expected_squad_names: list[str],
    ) -> None:
        result = resolve_ownership(changed_files, review_config)
        assert [s.name for s in result] == expected_squad_names

    def test_multiple_squads_touched(self, review_config: ReviewConfig) -> None:
        files = ["src/payments/stripe.py", "src/infra/deploy.py"]
        result = resolve_ownership(files, review_config)
        names = {s.name for s in result}
        assert names == {"payments", "platform"}

    def test_all_squads_touched(self, review_config: ReviewConfig) -> None:
        files = [
            "src/payments/stripe.py",
            "src/infra/deploy.py",
            "src/growth/ab.py",
        ]
        result = resolve_ownership(files, review_config)
        assert len(result) == 3

    def test_no_ownership(self, review_config: ReviewConfig) -> None:
        files = ["README.md", "docs/guide.md"]
        result = resolve_ownership(files, review_config)
        assert result == []

    def test_mixed_owned_and_unowned(self, review_config: ReviewConfig) -> None:
        files = ["src/payments/stripe.py", "README.md"]
        result = resolve_ownership(files, review_config)
        assert len(result) == 1
        assert result[0].name == "payments"
