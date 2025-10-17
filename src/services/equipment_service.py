from sqlalchemy import select, func
from ..db.models import Player, InventoryItem, Equipment

class EquipmentService:
    """Lógica de negocio para equipamiento 1:1 Personaje ↔ Light Cone."""

    # ---- helpers de consulta ----
    @staticmethod
    def owns_char(db, player_id: str, cid: str) -> bool:
        row = db.execute(
            select(func.sum(InventoryItem.copies)).where(
                InventoryItem.player_id == player_id,
                InventoryItem.item_type == "character",
                InventoryItem.item_id == cid,
            )
        ).scalar()
        return bool(row and int(row) >= 1)

    @staticmethod
    def owns_lc(db, player_id: str, lid: str) -> bool:
        row = db.execute(
            select(func.sum(InventoryItem.copies)).where(
                InventoryItem.player_id == player_id,
                InventoryItem.item_type == "light_cone",
                InventoryItem.item_id == lid,
            )
        ).scalar()
        return int(row or 0) >= 1

    @staticmethod
    def equipped_for_char(db, player_id: str, cid: str) -> Equipment | None:
        return db.execute(
            select(Equipment).where(
                Equipment.player_id == player_id,
                Equipment.character_id == cid,
            )
        ).scalars().first()

    @staticmethod
    def equipped_for_lc(db, player_id: str, lid: str) -> Equipment | None:
        return db.execute(
            select(Equipment).where(
                Equipment.player_id == player_id,
                Equipment.light_cone_id == lid,
            )
        ).scalars().first()

    # ---- acciones ----
    @staticmethod
    def equip(db, player_id: str, character_id: str, light_cone_id: str):
        """
        Reglas:
         - Si el LC está en otro personaje, se mueve.
         - Si el personaje tenía otro LC, se reemplaza.
        """
        row_lc = EquipmentService.equipped_for_lc(db, player_id, light_cone_id)
        row_char = EquipmentService.equipped_for_char(db, player_id, character_id)

        if row_lc and row_lc.character_id != character_id:
            # mover LC al nuevo personaje
            row_lc.character_id = character_id
            # si el nuevo tenía otro LC, lo pierde
            if row_char and row_char.light_cone_id != light_cone_id:
                db.delete(row_char)
        else:
            if row_char:
                row_char.light_cone_id = light_cone_id
            else:
                db.add(Equipment(
                    player_id=player_id,
                    character_id=character_id,
                    light_cone_id=light_cone_id
                ))

    @staticmethod
    def unequip(db, player_id: str, character_id: str) -> bool:
        row = EquipmentService.equipped_for_char(db, player_id, character_id)
        if not row:
            return False
        db.delete(row)
        return True

    @staticmethod
    def list_pairs(db, player_id: str) -> list[tuple[str, str]]:
        rows = db.execute(
            select(Equipment.character_id, Equipment.light_cone_id).where(
                Equipment.player_id == player_id
            )
        ).all()
        return [(cid, lid) for cid, lid in rows]