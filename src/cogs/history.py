import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, desc
from ..db.session import SessionLocal
from ..db.models import Player, PullHistory
from .gacha import GS
from ..util.embeds import make_history_embed

PAGE_SIZE = 10

# -------- View history (con embeds) --------

class HistoryPager(discord.ui.View):
    def __init__(
        self,
        user_id: str,
        user_obj: discord.abc.User | discord.Member,
        pages: list[list[dict]],
        total_rows: int,
        timeout: float = 180
    ):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.user_obj = user_obj
        self.pages = pages              # lista de páginas, cada una es lista de items (dict)
        self.total_rows = total_rows
        self.index = 0
        self._update_buttons()

    def _update_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "prev":
                    child.disabled = self.index <= 0
                elif child.custom_id == "next":
                    child.disabled = self.index >= len(self.pages) - 1

    async def _show(self, interaction: discord.Interaction):
        self._update_buttons()
        embed = make_history_embed(
            user=self.user_obj,
            page_items=self.pages[self.index],
            page_index=self.index,
            total_pages=len(self.pages),
            total_rows=self.total_rows
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Solo el dueño puede paginar
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("No podés navegar el historial de otra persona.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        await self._show(interaction)

    @discord.ui.button(label="Siguiente ➡️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
        await self._show(interaction)

# ------------------------------

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

        # Mapear a items simples para el embed factory
        items: list[dict] = []
        for r in rows:
            ch = GS.characters.get(r.character_id)
            name = ch.name if ch else r.character_id
            items.append({
                "banner": r.banner_id,
                "rarity": r.rarity,
                "name": name,
                "ts": r.ts
            })

        # Partir en páginas de PAGE_SIZE
        pages: list[list[dict]] = []
        for i in range(0, len(items), PAGE_SIZE):
            pages.append(items[i:i + PAGE_SIZE])

        # Embed inicial
        first_embed = make_history_embed(
            user=interaction.user,
            page_items=pages[0],
            page_index=0,
            total_pages=len(pages),
            total_rows=len(items)
        )

        view = HistoryPager(
            user_id=str(interaction.user.id),
            user_obj=interaction.user,
            pages=pages,
            total_rows=len(items)
        )
        await interaction.response.send_message(embed=first_embed, view=view, ephemeral=True)

async def setup(bot): await bot.add_cog(HistoryCog(bot))
