import random
from typing import Tuple, Literal

ItemType = Literal["character", "light_cone"]

class GachaService:
    def __init__(self, characters, light_cones, banners):
        self.characters = {c.id: c for c in characters.characters}
        self.light_cones = {l.id: l for l in light_cones.light_cones}
        self.banners = {b.id: b for b in banners.banners}

    def is_banner_active(self, banner_id: str) -> bool:
        b = self.banners.get(banner_id)
        if not b:
            return False
        return getattr(b, "active", True)

    def roll_rarity(self, pity4: int, pity5: int, rates) -> int:
        if pity5 + 1 >= rates.hard_pity["five_at"]:
            return 5
        if pity4 + 1 >= rates.hard_pity["four_at"]:
            base5 = rates.base["5"]
            r = random.random()
            return 5 if r < base5 else 4

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

    def choose_item(self, banner_id: str, rarity: int, last_5_was_featured: bool) -> Tuple[str, ItemType, bool]:
        """
        Devuelve (item_id, item_type, is_featured).

        Reglas:
        - En banners de SPECIAL PASS (limitados de personaje):
          * Para 5★: 50% personaje featured del banner, 50% personaje 5★ del pool de 'stellar_warp'.
          * Si perdiste el 50/50 en el último 5★ (last_5_was_featured = False), el próximo 5★ es garantizado featured.
          * SOLO personajes para 5★ (no LCs) en estos banners.
        - En 'stellar_warp' (STANDARD PASS): se mantiene el comportamiento original (mezcla según pool).
        - 4★ y 3★: igual que antes (según pools del banner actual).
        """
        b = self.banners[banner_id]
        pool = b.pool
        is_featured = False

        # --- 5 ESTRELLAS ---
        if rarity == 5:
            # STANDARD banner: comportamiento original (puede mezclar personaje/LC según datos)
            if b.key == "star_rail_pass":
                chars = list(pool.five_star_c)
                lcones = list(pool.five_star_l)
                combined = [(cid, "character") for cid in chars] + [(lid, "light_cone") for lid in lcones]
                if not combined and chars:
                    combined = [(cid, "character") for cid in chars]
                elif not combined and lcones:
                    combined = [(lid, "light_cone") for lid in lcones]
                item_id, itype = random.choice(combined)
                # En estándar no afecta guarantee; marcamos featured=True para no “romper” tu flag
                return item_id, itype, True

            # SPECIAL banner (limitado de personaje): aplicar 50/50 contra 'stellar_warp'
            # 1) featured del banner actual (personajes 5★ del pool del banner)
            featured_chars = list(pool.five_star_c)

            # 2) personajes 5★ del pool de stellar_warp (para "perder" el 50/50)
            std_banner = self.banners.get("stellar_warp")
            std_chars = list(std_banner.pool.five_star_c) if std_banner and std_banner.pool else []

            # Si por configuración no hay featured o std, hacemos fallbacks razonables
            if not featured_chars and std_chars:
                # sin featured definidos -> cae del estándar
                return random.choice(std_chars), "character", False
            if featured_chars and not std_chars:
                # no hay estándar -> siempre featured
                return random.choice(featured_chars), "character", True
            if not featured_chars and not std_chars:
                # nada definido (datos incompletos): devolvemos cualquier 4★ como salvavidas
                fallback = pool.four_star_c or pool.four_star_l or []
                pick = random.choice(list(fallback)) if fallback else None
                if pick:
                    return pick, ("character" if pick in pool.four_star_c else "light_cone"), False
                # último fallback imposible
                raise RuntimeError("No hay pools configurados para 5★ ni fallback en el banner.")

            # Guarantee: si la anterior NO fue featured, este 5★ es garantizado featured
            if not last_5_was_featured:
                return random.choice(featured_chars), "character", True

            # 50/50 normal: 50% featured, 50% estándar
            if random.random() < 0.5:
                return random.choice(featured_chars), "character", True
            else:
                return random.choice(std_chars), "character", False

        # --- 4 ESTRELLAS ---
        if rarity == 4:
            combined = [(cid, "character") for cid in pool.four_star_c] + \
                       [(lid, "light_cone") for lid in pool.four_star_l]
            if combined:
                item_id, itype = random.choice(combined)
            else:
                # fallback mínimo
                item_id, itype = (random.choice(pool.four_star_c), "character")
            return item_id, itype, False

        # --- 3 ESTRELLAS ---
        if pool.three_star_l:
            return random.choice(pool.three_star_l), "light_cone", False

        # Fallback por si no hay 3★: tirar un 4★ del pool
        return random.choice(pool.four_star_c), "character", False