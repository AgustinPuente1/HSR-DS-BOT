from typing import Iterable, Tuple, Set
from sqlalchemy import select, func
from ...db.models import PullHistory, Equipment, AchievementState

def claimed_ids(db, player_id: str) -> Set[str]:
    rows = db.execute(
        select(AchievementState.achievement_id)
        .where(
            AchievementState.player_id == player_id,
            AchievementState.claimed_at.is_not(None)
        )
    ).all()
    return {r[0] for r in rows}

def pulls_count_by_banner(db, player_id: str) -> Iterable[Tuple[str, int]]:
    return db.execute(
        select(PullHistory.banner_id, func.count(PullHistory.id))
        .where(PullHistory.player_id == player_id)
        .group_by(PullHistory.banner_id)
    ).all()

def has_any_equipment(db, player_id: str) -> int:
    return int(db.execute(
        select(func.count(Equipment.id)).where(Equipment.player_id == player_id)
    ).scalar() or 0)

def get_achievement_row(db, player_id: str, achievement_id: str) -> AchievementState | None:
    return db.execute(
        select(AchievementState).where(
            AchievementState.player_id == player_id,
            AchievementState.achievement_id == achievement_id
        )
    ).scalars().first()