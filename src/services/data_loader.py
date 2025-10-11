from pydantic import BaseModel, field_validator
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[2]  # carpeta raíz del proyecto

class Character(BaseModel):
    id: str; name: str; rarity: int
    path: str; element: str; image: str
    tags: list[str] = []

    @field_validator("image")
    @classmethod
    def image_exists(cls, v: str):
        p = BASE / v
        if not p.exists():
            raise ValueError(f"Imagen no encontrada: {p}")
        return v

class CharactersFile(BaseModel):
    version: int
    characters: list[Character]

class BannerRates(BaseModel):
    base: dict
    hard_pity: dict
    soft_pity: dict | None = None

class BannerPool(BaseModel):
    five_star_c: list[str] = []
    four_star_c: list[str] = []
    five_star_l: list[str] = []
    four_star_l: list[str] = []
    three_star_l: list[str] = []

class Banner(BaseModel):
    id: str; name: str; key: str
    pool: BannerPool
    rates: BannerRates
    featured: dict | None = None

class BannersFile(BaseModel):
    version: int
    banners: list[Banner]

def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_data():
    chars_raw = _load_json(BASE / "data/characters/characters.json")
    characters = CharactersFile(**chars_raw)

    banners_raw = _load_json(BASE / "data/banners/banners.json")
    banners = BannersFile(**banners_raw)

    # Chequeo de referencias: que IDs existan
    char_ids = {c.id for c in characters.characters}
    for b in banners.banners:
        for lst_name in ["five_star_c", "four_star_c"]:
            missing = [x for x in getattr(b.pool, lst_name) if x not in char_ids]
            if missing:
                raise ValueError(f"IDs inexistentes en {b.id}/{lst_name}: {missing}")

    return characters, banners
