from datetime import datetime, timezone
from ..db.models import Player, GachaState, InventoryItem, PullHistory
from ..util.gacha.gacha_helpers import eidolons_from_copies, superpos_from_copies

def run_pull_transaction(db, GS, player_id: str, count: int):
    """
    Ejecuta una tirada (o x10) dentro de una transacción abierta por el caller.
    Devuelve: (results, banner_obj, final_state_dict)
      - results: list[(rarity:int, item_obj, item_type:str, note:str)]
      - banner_obj: banner actual
      - final_state_dict: {'pity4':int, 'pity5':int, 'last_feat':bool}
    Lanza excepciones si faltan cosas (no registrado, sin tickets, banner inactivo, etc.).
    """
    p = db.get(Player, player_id)
    if not p:
        raise RuntimeError("Usá /register primero.")

    gs = db.get(GachaState, p.user_id)
    b = GS.banners[gs.banner_id]

    # Validez banner
    if not GS.is_banner_active(gs.banner_id):
        raise RuntimeError(f"El banner {b.name} está inactivo. Elegí otro con /set_banner.")

    # Tickets según tipo
    if b.key == "star_rail_pass":
        have = p.currencies.tickets_standard
        if have < count:
            raise RuntimeError(f"No te alcanzan los tickets. Tenés {have} Star Rail Pass.")
        p.currencies.tickets_standard -= count
    else:
        have = p.currencies.tickets_special
        if have < count:
            raise RuntimeError(f"No te alcanzan los tickets. Tenés {have} Star Rail Special Pass.")
        p.currencies.tickets_special -= count

    pity4, pity5 = gs.pity4, gs.pity5
    last_feat = gs.last_5_was_featured

    results = []
    for _ in range(count):
        rarity = GS.roll_rarity(pity4, pity5, b.rates)
        item_id, item_type, is_feat = GS.choose_item(gs.banner_id, rarity, last_feat)
        item = GS.characters[item_id] if item_type == "character" else GS.light_cones[item_id]

        inv = (db.query(InventoryItem)
                 .filter(InventoryItem.player_id == p.user_id,
                         InventoryItem.item_id == item_id,
                         InventoryItem.item_type == item_type)
                 .first())

        note = ""
        if inv is None:
            inv = InventoryItem(player_id=p.user_id, item_id=item_id, item_type=item_type, copies=1)
            db.add(inv)
            note = "E0 (nuevo)" if item_type == "character" else "S1 (nuevo)"
        else:
            if item_type == "character":
                current_e = eidolons_from_copies(inv.copies)
                if current_e >= 6:
                    if rarity == 5:
                        p.currencies.tickets_special += 5
                        note = "Convertido: +5 Special Pass (E6)"
                    elif rarity == 4:
                        p.currencies.tickets_standard += 2
                        note = "Convertido: +2 Standard Pass (E6)"
                    else:
                        note = "Máximo de copias"
                else:
                    inv.copies += 1
                    note = f"E{eidolons_from_copies(inv.copies)}"
            else:
                current_s = superpos_from_copies(inv.copies)
                if current_s >= 5:
                    if rarity == 5:
                        p.currencies.tickets_special += 5
                        note = "Convertido: +5 Special Pass (E6)"
                    elif rarity == 4:
                        p.currencies.tickets_standard += 2
                        note = "Convertido: +2 Standard Pass (E6)"
                    else:
                        note = "Máximo de copias"
                else:
                    inv.copies += 1
                    note = f"S{superpos_from_copies(inv.copies)}"

        # pity / featured
        pity4 = 0 if rarity >= 4 else pity4 + 1
        pity5 = 0 if rarity >= 5 else pity5 + 1
        if rarity == 5:
            last_feat = is_feat

        db.add(PullHistory(
            player_id=p.user_id,
            banner_id=gs.banner_id,
            rarity=rarity,
            item_id=item_id,
            item_type=item_type,
            ts=datetime.now(timezone.utc)
        ))

        results.append((rarity, item, item_type, note))

    gs.pity4, gs.pity5, gs.last_5_was_featured = pity4, pity5, last_feat
    return results, b, {"pity4": pity4, "pity5": pity5, "last_feat": last_feat}