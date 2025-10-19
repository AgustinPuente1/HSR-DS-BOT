from typing import Callable, Optional, Tuple, Dict
from .catalog import Achievement
from .repository import pulls_count_by_banner, has_any_equipment
from .banner_map import BANNER_KEY

# firma de evaluador
Evaluator = Callable[[any, str, Achievement], Tuple[bool, Optional[str]]]
_REGISTRY: Dict[str, Evaluator] = {}

def evaluator(kind: str):
    def deco(fn: Evaluator):
        _REGISTRY[kind] = fn
        return fn
    return deco

@evaluator("pulls_by_key")
def _pulls_by_key(db, player_id: str, a: Achievement):
    key = a.params.get("key")
    need = int(a.params.get("count", 0))
    total = 0
    for bid, cnt in pulls_count_by_banner(db, player_id):
        if BANNER_KEY.get(bid) == key:
            total += int(cnt)
    return (total >= need, f"{total}/{need}")

@evaluator("has_any_equipment")
def _has_any_equipment(db, player_id: str, a: Achievement):
    has = has_any_equipment(db, player_id)
    return (has > 0, f"{has}/1")

@evaluator("character_level_reached")
def _character_level_reached(db, player_id: str, a: Achievement):
    lvl = int(a.params.get("level", 1))
    return (False, f"0/{lvl}")  # placeholder

@evaluator("battle_wins")
def _battle_wins(db, player_id: str, a: Achievement):
    need = int(a.params.get("count", 1))
    return (False, f"0/{need}")  # placeholder

def is_completed(db, player_id: str, a: Achievement):
    fn = _REGISTRY.get(a.type)
    if not fn:
        return (False, None)
    return fn(db, player_id, a)