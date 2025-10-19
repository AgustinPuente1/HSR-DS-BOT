from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Dict, List

BASE = Path(__file__).resolve().parents[3]
ACH_PATH = BASE / "data/achievements/achievements.json"

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