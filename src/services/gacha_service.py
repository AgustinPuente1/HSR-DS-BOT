import random
from typing import Tuple

class GachaService:
    def __init__(self, characters, banners):
        self.characters = {c.id: c for c in characters.characters}
        self.banners = {b.id: b for b in banners.banners}

    def roll_rarity(self, pity4: int, pity5: int, rates) -> int:
        # Hard pity
        if pity5 + 1 >= rates.hard_pity["five_at"]: return 5
        if pity4 + 1 >= rates.hard_pity["four_at"]:
            # forzamos al menos 4★
            base5 = rates.base["5"]
            r = random.random()
            return 5 if r < base5 else 4

        # Soft pity (5★)
        base5 = rates.base["5"]; base4 = rates.base["4"]
        if rates.soft_pity and pity5 + 1 >= rates.soft_pity["start_5"]:
            inc = rates.soft_pity["inc_5"] * (pity5 + 1 - rates.soft_pity["start_5"])
            base5 = min(1.0, base5 + inc)
        if rates.soft_pity and pity4 + 1 >= rates.soft_pity["start_4"]:
            inc4 = rates.soft_pity["inc_4"] * (pity4 + 1 - rates.soft_pity["start_4"])
            base4 = min(1.0 - base5, base4 + inc4)

        r = random.random()
        if r < base5: return 5
        if r < base5 + base4: return 4
        return 3

    def choose_character(self, banner_id: str, rarity: int, last_5_was_featured: bool) -> Tuple[str, bool]:
        b = self.banners[banner_id]
        pool = b.pool
        featured = b.featured or {}
        is_featured = True

        if rarity == 5:
            # 50/50 para limitado; si perdiste antes, te garantizo ahora
            if "guarantee_5" in featured and featured["guarantee_5"].get("on_fail_next_is_featured") and not last_5_was_featured:
                cid = random.choice(pool.five_star_c)
                return cid, True
            # estándar o 50/50 de limitado (para MVP simplificado usamos featured directo)
            cid = random.choice(pool.five_star_c)
            return cid, True

        if rarity == 4:
            cid = random.choice(pool.four_star_c)
            return cid, False

        # Nota: 3★ ignorado en MVP (si cae 3, devolvemos un 4★ para que no quede vacío)
        cid = random.choice(pool.four_star_c)
        return cid, False
