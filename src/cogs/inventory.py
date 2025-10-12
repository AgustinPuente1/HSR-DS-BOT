import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, func
from ..db.session import SessionLocal
from ..db.models import Player, InventoryItem
from ..services.data_loader import load_data

characters, light_cones, _banners = load_data()

class InventoryCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="inventory", description="Muestra tu inventario o el de otro usuario.")
    @app_commands.describe(user="Usuario (opcional) para ver su inventario")
    async def inventory(self, interaction: discord.Interaction, user: discord.User | None = None):
        target_id = str((user or interaction.user).id)
        with SessionLocal() as db:
            p = db.get(Player, target_id)
            if not p:
                msg = "Ese usuario no está registrado." if user else "Usá /register primero."
                return await interaction.response.send_message(msg, ephemeral=True)

            items = db.execute(
                select(InventoryItem.item_id, InventoryItem.item_type, func.sum(InventoryItem.copies))
                .where(InventoryItem.player_id == p.user_id)
                .group_by(InventoryItem.item_id, InventoryItem.item_type)
            ).all()

        if not items: return await interaction.response.send_message("Inventario vacío.", ephemeral=True)

        def to_meta(item_id, item_type):
            if item_type == "character":
                ch = next((x for x in characters.characters if x.id == item_id), None)
                return (ch.rarity if ch else 0, ch.name if ch else item_id, "char")
            lc = next((x for x in light_cones.light_cones if x.id == item_id), None)
            return (lc.rarity if lc else 0, (lc.name) if lc else item_id, "lc")

        # ordenar por rareza desc y nombre
        sorted_items = sorted(
            [(*to_meta(iid, itype), cnt, iid, itype) for iid, itype, cnt in items],
            key=lambda x: (-x[0], x[1])
        )

        lines = []
        for rarity, name, kind, cnt, iid, itype in sorted_items:
            stars = "★"*rarity if rarity else ""
            prefix = "[Character]" if kind=="char" else "[Light Cone]"
            lines.append(f"{prefix}{stars} **{name}** ×{cnt}")

        # enviar chunked
        chunks, buf = [], ""
        for line in lines:
            if len(buf) + len(line) + 1 > 1900:
                chunks.append(buf); buf = line+"\n"
            else:
                buf += line+"\n"
        if buf: chunks.append(buf)

        await interaction.response.send_message(chunks[0])
        for extra in chunks[1:]:
            await interaction.followup.send(extra)

async def setup(bot): await bot.add_cog(InventoryCog(bot))
