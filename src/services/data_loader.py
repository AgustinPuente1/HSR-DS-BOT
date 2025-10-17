from pydantic import BaseModel, field_validator
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[2]

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

class LightCone(BaseModel):
    id: str; name: str; rarity: int
    path: str; image: str
    hp: int; atk: int; def_: int
    favorites: list[str] = [] 

    @field_validator("image")
    @classmethod
    def image_exists(cls, v: str):
        p = BASE / v
        if not p.exists():
            raise ValueError(f"Imagen no encontrada: {p}")
        return v

    @classmethod
    def model_validate_json(cls, d: dict):
        d = dict(d)
        if "def" in d and "def_" not in d:
            d["def_"] = d.pop("def")
        # favorites puede no venir; si viene, debe ser lista
        favs = d.get("favorites")
        if favs is not None and not isinstance(favs, list):
            raise ValueError("favorites debe ser una lista de ids de personajes")
        return cls(**d)

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

class LightConesFile(BaseModel):
    version: int
    light_cones: list[LightCone]

def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_data():
    chars_raw = _load_json(BASE / "data/characters/characters.json")
    characters = CharactersFile(**chars_raw)

    lcs_raw = _load_json(BASE / "data/light-cones/light-cones.json")
    lcs_items = [LightCone.model_validate_json(x) for x in lcs_raw["light_cones"]]
    light_cones = LightConesFile(version=lcs_raw["version"], light_cones=lcs_items)

    banners_raw = _load_json(BASE / "data/banners/banners.json")
    banners = BannersFile(**banners_raw)

    # Chequeos de referencias
    char_ids = {c.id for c in characters.characters}
    lc_ids   = {l.id for l in light_cones.light_cones}
    
    # Chequeos para light cones con personajes que no existen
    for lc in light_cones.light_cones:
        missing = [cid for cid in lc.favorites if cid not in char_ids]
        if missing:
            raise ValueError(f"Light Cone '{lc.id}' tiene favorites inválidos: {missing}")

    for b in banners.banners:
        for lst_name in ["five_star_c", "four_star_c"]:
            missing = [x for x in getattr(b.pool, lst_name) if x not in char_ids]
            if missing:
                raise ValueError(f"IDs inexistentes en {b.id}/{lst_name}: {missing}")
        for lst_name in ["five_star_l", "four_star_l", "three_star_l"]:
            missing = [x for x in getattr(b.pool, lst_name) if x not in lc_ids]
            if missing:
                raise ValueError(f"IDs inexistentes en {b.id}/{lst_name}: {missing}")

    return characters, light_cones, banners
