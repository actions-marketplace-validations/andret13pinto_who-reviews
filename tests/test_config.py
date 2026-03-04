from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pr_review_action.config import ReviewConfig, load_config


class TestReviewConfig:
    def test_valid_config(self, review_config: ReviewConfig) -> None:
        assert len(review_config.squads) == 3
        assert review_config.strategy == "random"

    @pytest.mark.parametrize("strategy", ["random", "round-robin", "least-recent"])
    def test_valid_strategies(self, strategy: str) -> None:
        config = ReviewConfig(
            strategy=strategy,  # type: ignore[arg-type]
            squads=[
                {"name": "a", "members": ["alice"], "paths": ["src/**"]},  # type: ignore[list-item]
            ],
        )
        assert config.strategy == strategy

    def test_rejects_invalid_strategy(self) -> None:
        with pytest.raises(ValueError):
            ReviewConfig(
                strategy="invalid",  # type: ignore[arg-type]
                squads=[
                    {"name": "a", "members": ["alice"], "paths": ["src/**"]},  # type: ignore[list-item]
                ],
            )

    def test_rejects_duplicate_members(self) -> None:
        with pytest.raises(ValueError, match="is in both"):
            ReviewConfig(
                strategy="random",
                squads=[
                    {"name": "a", "members": ["alice", "bob"], "paths": ["src/a/**"]},  # type: ignore[list-item]
                    {"name": "b", "members": ["alice"], "paths": ["src/b/**"]},  # type: ignore[list-item]
                ],
            )

    def test_rejects_empty_members(self) -> None:
        with pytest.raises(ValueError, match="has no members"):
            ReviewConfig(
                strategy="random",
                squads=[
                    {"name": "empty", "members": [], "paths": ["src/**"]},  # type: ignore[list-item]
                ],
            )

    def test_rejects_empty_paths(self) -> None:
        with pytest.raises(ValueError, match="has no paths"):
            ReviewConfig(
                strategy="random",
                squads=[
                    {"name": "no_paths", "members": ["alice"], "paths": []},  # type: ignore[list-item]
                ],
            )

    def test_all_members(self, review_config: ReviewConfig) -> None:
        expected = {"alice", "bob", "charlie", "dave", "eve", "frank", "grace", "heidi"}
        assert review_config.all_members == expected


class TestLoadConfig:
    def test_loads_from_yaml(self, tmp_path: Path) -> None:
        config_data = {
            "strategy": "round-robin",
            "squads": [
                {"name": "team", "members": ["alice", "bob"], "paths": ["src/**"]},
            ],
        }
        config_file = tmp_path / "squads.yml"
        config_file.write_text(yaml.dump(config_data))

        config = load_config(config_file)

        assert config.strategy == "round-robin"
        assert len(config.squads) == 1
        assert config.squads[0].name == "team"
