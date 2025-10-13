import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, desc
from ..db.session import SessionLocal
from ..db.models import Player, PullHistory
from ..services.data_loader import load_data
from ..util.history_pager import HistoryPager
from ..util.embeds import make_history_embed

# Para resolver nombres sin acoplar a GS
characters, light_cones, _banners = load_data()
CHAR_MAP = {c.id: c.name for c in characters.characters}
LC_MAP   = {l.id: l.name for l in light_cones.light_cones}

PAGE_SIZE = 10

def _resolve_name(item_id: str, item_type: str) -> str:
    if item_type == "character":
        return CHAR_MAP.get(item_id, item_id)
    return LC_MAP.get(item_id, item_id) + " (LC)"

class HistoryCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @app_commands.command(
        name="history",
        description="Muestra tu historial de tiradas con paginación (10 por página)."
    )
    async def history(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

            rows = (
                db.execute(
                    select(PullHistory)
                    .where(PullHistory.player_id == p.user_id)
                    .order_by(desc(PullHistory.id))
                )
                .scalars()
                .all()
            )

        if not rows:
            return await interaction.response.send_message("Aún no tenés tiradas registradas.", ephemeral=True)

        # Mapear a items simples
        items = [{
            "banner": r.banner_id,
            "rarity": r.rarity,
            "name": _resolve_name(r.item_id, r.item_type),
            "ts": r.ts
        } for r in rows]

        # Paginado
        pages_items: list[list[dict]] = []
        for i in range(0, len(items), PAGE_SIZE):
            pages_items.append(items[i:i + PAGE_SIZE])

        # Embeds por página
        embeds = [
            make_history_embed(
                user=interaction.user,
                page_items=pi,
                page_index=idx,
                total_pages=len(pages_items),
                total_rows=len(items)
            )
            for idx, pi in enumerate(pages_items)
        ]

        view = HistoryPager(user_id=str(interaction.user.id), embeds=embeds)
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

async def setup(bot): 
    await bot.add_cog(HistoryCog(bot))
