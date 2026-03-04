from __future__ import annotations

from who_reviews.config import ReviewConfig, SquadConfig
from who_reviews.ownership import resolve_ownership
from who_reviews.strategies.base import SelectionContext, SelectionStrategy


class ReviewerSelector:
    def __init__(self, config: ReviewConfig, strategy: SelectionStrategy) -> None:
        self._config = config
        self._strategy = strategy

    def select_reviewers(
        self,
        changed_files: list[str],
        author: str,
        repo: str,
        pr_number: int,
    ) -> list[str]:
        affected_squads = resolve_ownership(changed_files, self._config)

        if not affected_squads:
            return self._select_no_ownership(author, repo, pr_number)

        return self._select_with_ownership(affected_squads, author, repo, pr_number)

    def _select_no_ownership(self, author: str, repo: str, pr_number: int) -> list[str]:
        candidates = sorted(self._config.all_members - {author})
        total = self._config.squad_reviewers + self._config.outsider_reviewers
        if not candidates or total == 0:
            return []

        reviewers: list[str] = []
        ctx = SelectionContext(repo=repo, pr_number=pr_number, role="fallback")
        for _ in range(min(total, len(candidates))):
            remaining = [c for c in candidates if c not in reviewers]
            if not remaining:
                break
            selected = self._strategy.select(remaining, ctx)
            reviewers.append(selected)

        return reviewers

    def _select_with_ownership(
        self,
        affected_squads: list[SquadConfig],
        author: str,
        repo: str,
        pr_number: int,
    ) -> list[str]:
        reviewers: list[str] = []

        for squad in affected_squads:
            ctx = SelectionContext(
                repo=repo, pr_number=pr_number, role=f"squad-{squad.name}"
            )
            for _ in range(self._config.squad_reviewers):
                candidates = sorted(set(squad.members) - {author} - set(reviewers))
                if not candidates:
                    break
                selected = self._strategy.select(candidates, ctx)
                reviewers.append(selected)

        outsiders = self._pick_outsiders(
            affected_squads, author, reviewers, repo, pr_number
        )
        reviewers.extend(outsiders)

        return reviewers

    def _pick_outsiders(
        self,
        affected_squads: list[SquadConfig],
        author: str,
        already_selected: list[str],
        repo: str,
        pr_number: int,
    ) -> list[str]:
        affected_members: set[str] = set()
        for squad in affected_squads:
            affected_members.update(squad.members)

        outsider_candidates = sorted(
            self._config.all_members
            - affected_members
            - {author}
            - set(already_selected)
        )
        if not outsider_candidates:
            return []

        ctx = SelectionContext(repo=repo, pr_number=pr_number, role="outsider")
        result: list[str] = []
        for _ in range(self._config.outsider_reviewers):
            remaining = [c for c in outsider_candidates if c not in result]
            if not remaining:
                break
            selected = self._strategy.select(remaining, ctx)
            result.append(selected)

        return result
