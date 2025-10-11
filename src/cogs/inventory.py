import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, func
from ..db.session import SessionLocal
from ..db.models import Player, InventoryItem
from .gacha import GS  # para leer metadata de personajes

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
                select(InventoryItem.character_id, func.sum(InventoryItem.copies))
                .where(InventoryItem.player_id == p.user_id)
                .group_by(InventoryItem.character_id)
            ).all()

        if not items:
            return await interaction.response.send_message("Inventario vacío.", ephemeral=True)

        def sort_key(row):
            cid, copies = row
            ch = GS.characters.get(cid)
            return (-ch.rarity if ch else 0, ch.name if ch else cid)

        items_sorted = sorted(items, key=sort_key)

        lines = []
        for cid, copies in items_sorted:
            ch = GS.characters.get(cid)
            if ch:
                stars = "★" * ch.rarity
                lines.append(f"{stars} **{ch.name}** ×{copies}")
            else:
                lines.append(f"?? **{cid}** ×{copies}")

        # arma respuesta cuidando límite
        chunks, buf = [], ""
        for line in lines:
            if len(buf) + len(line) + 1 > 1900:
                chunks.append(buf); buf = line + "\n"
            else:
                buf += line + "\n"
        if buf: chunks.append(buf)

        # primera parte: pública; resto, followups
        await interaction.response.send_message(chunks[0])
        for extra in chunks[1:]:
            await interaction.followup.send(extra)

async def setup(bot): await bot.add_cog(InventoryCog(bot))
