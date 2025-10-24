import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, func
from ..db.session import SessionLocal
from ..db.models import Player, InventoryItem
from ..services.data_loader import load_data
from ..util.embeds import make_inventory_embeds
from ..util.pager import Pager  

characters, light_cones, _banners = load_data()

CHAR_MAP = {c.id: (c.name, c.rarity) for c in characters.characters}
LC_MAP   = {l.id: (l.name, l.rarity) for l in light_cones.light_cones}

class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="inventory",
        description="Muestra tu inventario o el de otro usuario."
    )
    @app_commands.describe(user="Usuario (opcional) para ver su inventario")
    async def inventory(self, interaction: discord.Interaction, user: discord.User | None = None):
        owner = user or interaction.user
        target_id = str(owner.id)

        with SessionLocal() as db:
            p = db.get(Player, target_id)
            if not p:
                msg = "Ese usuario no está registrado." if user else "Usá /register primero."
                return await interaction.response.send_message(msg, ephemeral=True)

            rows = db.execute(
                select(
                    InventoryItem.item_id,
                    InventoryItem.item_type,
                    func.sum(InventoryItem.copies)
                )
                .where(InventoryItem.player_id == p.user_id)
                .group_by(InventoryItem.item_id, InventoryItem.item_type)
            ).all()

        if not rows:
            return await interaction.response.send_message(
                f"El inventario de **{owner.display_name}** está vacío.",
                ephemeral=True if not user else False
            )

        # Normalizar a entries para el embed factory
        entries = []
        for item_id, item_type, total in rows:
            total = int(total)
            if item_type == "character":
                name, rarity = CHAR_MAP.get(item_id, (item_id, 0))
                kind = "char"
                e = max(0, min(6, total - 1))
                badge = f"E{e}"
            else:
                name, rarity = LC_MAP.get(item_id, (item_id, 0))
                kind = "lc"
                s = max(1, min(5, total))
                badge = f"S{s}"
            entries.append({
                "name": name,
                "rarity": rarity,
                "kind": kind,
                "count": total,
                "badge": badge,
            })

        embeds = make_inventory_embeds(owner=owner, entries=entries)
        
        view = Pager(user_id=str(interaction.user.id), embeds=embeds)

        await interaction.response.send_message(
            embed=embeds[0],
            view=view,
            ephemeral=False  # cambialo a True si querés que sea privado
        )

async def setup(bot):
    await bot.add_cog(InventoryCog(bot))