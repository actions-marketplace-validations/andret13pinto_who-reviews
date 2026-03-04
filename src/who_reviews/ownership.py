from __future__ import annotations

from fnmatch import fnmatch

from who_reviews.config import ReviewConfig, SquadConfig


def resolve_ownership(
    changed_files: list[str], config: ReviewConfig
) -> list[SquadConfig]:
    affected: list[SquadConfig] = []
    for squad in config.squads:
        if _squad_owns_any(squad, changed_files):
            affected.append(squad)
    return affected


def _squad_owns_any(squad: SquadConfig, changed_files: list[str]) -> bool:
    return any(
        fnmatch(file, pattern) for file in changed_files for pattern in squad.paths
    )
