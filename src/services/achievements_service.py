from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func
from ..db.models import PullHistory, Equipment, AchievementState
from ..services.data_loader import load_data

BASE = Path(__file__).resolve().parents[2]
ACH_PATH = BASE / "data" / "achievements" / "achievements.json"

@dataclass
class Achievement:
    id: str
    name: str
    desc: str
    type: str
    params: Dict[str, Any]
    rewards: Dict[str, int]

@dataclass
class AchCatalog:
    version: int
    achievements: List[Achievement]

def load_catalog() -> AchCatalog:
    with ACH_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    achs = [Achievement(**a) for a in raw["achievements"]]
    return AchCatalog(version=raw["version"], achievements=achs)

# Pre-cargar mapping banner_id -> key desde data_loader (no DB)
_char, _lc, _banners = load_data()
BANNER_KEY = {b.id: b.key for b in _banners.banners}

# -------- Evaluadores por tipo --------
def is_completed(db, player_id: str, a: Achievement) -> Tuple[bool, Optional[str]]:
    """
    Devuelve (completed?, progress_str) para mostrar progreso útil (opcional).
    """
    t = a.type
    p = a.params or {}

    if t == "pulls_by_key":
        key = p.get("key")
        need = int(p.get("count", 0))
        # contar pulls por banner key
        total = 0
        rows = db.execute(
            select(PullHistory.banner_id, func.count(PullHistory.id))
            .where(PullHistory.player_id == player_id)
            .group_by(PullHistory.banner_id)
        ).all()
        for bid, cnt in rows:
            if BANNER_KEY.get(bid) == key:
                total += int(cnt)
        return (total >= need, f"{total}/{need}")

    if t == "has_any_equipment":
        has = db.execute(
            select(func.count(Equipment.id)).where(Equipment.player_id == player_id)
        ).scalar() or 0
        return (has > 0, f"{has}/1")

    if t == "character_level_reached":
        # placeholder: cuando haya tabla de niveles, consultá ahí
        # por ahora siempre False
        lvl = int(p.get("level", 1))
        return (False, f"0/{lvl}")

    if t == "battle_wins":
        # placeholder: cuando haya tabla de batallas, consultá ahí
        need = int(p.get("count", 1))
        return (False, f"0/{need}")

    # tipo desconocido
    return (False, None)

# -------- Recompensas --------
def apply_rewards(db, player, rewards: Dict[str, int]) -> str:
    """
    Aplica recompensas al player.currencies.
    Soportado: tickets_standard, tickets_special, credits
    Devuelve un string resumen.
    """
    parts = []
    if not player.currencies:
        raise RuntimeError("El jugador no tiene fila de Currency creada.")

    ts = int(rewards.get("tickets_standard", 0))
    if ts:
        player.currencies.tickets_standard += ts
        parts.append(f"+{ts} Standard Pass")

    sp = int(rewards.get("tickets_special", 0))
    if sp:
        player.currencies.tickets_special += sp
        parts.append(f"+{sp} Special Pass")

    cr = int(rewards.get("credits", 0))
    if cr:
        player.currencies.credits += cr
        parts.append(f"+{cr} créditos")

    return ", ".join(parts) if parts else "Sin recompensa definida"
