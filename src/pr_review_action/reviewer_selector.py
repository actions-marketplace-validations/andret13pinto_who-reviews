from __future__ import annotations

from pr_review_action.config import ReviewConfig, SquadConfig
from pr_review_action.ownership import resolve_ownership
from pr_review_action.strategies.base import SelectionContext, SelectionStrategy


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
        if len(candidates) < 2:
            return candidates

        ctx = SelectionContext(repo=repo, pr_number=pr_number, role="fallback")
        first = self._strategy.select(candidates, ctx)
        remaining = [c for c in candidates if c != first]
        second = self._strategy.select(remaining, ctx)
        return [first, second]

    def _select_with_ownership(
        self,
        affected_squads: list[SquadConfig],
        author: str,
        repo: str,
        pr_number: int,
    ) -> list[str]:
        reviewers: list[str] = []

        for squad in affected_squads:
            candidates = sorted(set(squad.members) - {author} - set(reviewers))
            if not candidates:
                continue
            ctx = SelectionContext(
                repo=repo, pr_number=pr_number, role=f"squad-{squad.name}"
            )
            selected = self._strategy.select(candidates, ctx)
            reviewers.append(selected)

        outsider = self._pick_outsider(
            affected_squads, author, reviewers, repo, pr_number
        )
        if outsider:
            reviewers.append(outsider)

        return reviewers

    def _pick_outsider(
        self,
        affected_squads: list[SquadConfig],
        author: str,
        already_selected: list[str],
        repo: str,
        pr_number: int,
    ) -> str | None:
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
            return None

        ctx = SelectionContext(repo=repo, pr_number=pr_number, role="outsider")
        return self._strategy.select(outsider_candidates, ctx)
