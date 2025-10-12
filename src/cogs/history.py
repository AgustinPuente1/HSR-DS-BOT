import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, desc
from ..db.session import SessionLocal
from ..db.models import Player, PullHistory
from ..services.data_loader import load_data

# Para obtener nombres de items
characters, light_cones, _banners = load_data()

PAGE_SIZE = 10

def fmt_item_name(item_id: str, item_type: str):
    if item_type == "character":
        c = next((x for x in characters.characters if x.id == item_id), None)
        return c.name if c else item_id
    l = next((x for x in light_cones.light_cones if x.id == item_id), None)
    return (l.name + " (LC)") if l else item_id

class HistoryPager(discord.ui.View):
    def __init__(self, user_id: str, pages: list[str], timeout: float = 180):
        super().__init__(timeout=timeout); self.user_id=user_id; self.pages=pages; self.index=0
        self._update()

    def _update(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "prev": child.disabled = (self.index<=0)
                if child.custom_id == "next": child.disabled = (self.index>=len(self.pages)-1)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("No podés navegar el historial de otra persona.", ephemeral=True); return False
        return True

    async def _show(self, interaction: discord.Interaction):
        self._update()
        await interaction.response.edit_message(content=self.pages[self.index], view=self)

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index>0: self.index-=1
        await self._show(interaction)

    @discord.ui.button(label="Siguiente ➡️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index<len(self.pages)-1: self.index+=1
        await self._show(interaction)

class HistoryCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="history", description="Muestra tu historial de tiradas con paginación (10 por página).")
    async def history(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p: return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            rows = db.execute(
                select(PullHistory)
                .where(PullHistory.player_id == p.user_id)
                .order_by(desc(PullHistory.id))
            ).scalars().all()

        if not rows:
            return await interaction.response.send_message("Aún no tenés tiradas registradas.", ephemeral=True)

        lines = []
        for r in rows:
            name = fmt_item_name(r.item_id, r.item_type)
            stars = "★" * r.rarity
            lines.append(f"[{r.banner_id}] {stars} **{name}** — {r.ts}")

        pages, buf = [], []
        for i, line in enumerate(lines, start=1):
            buf.append(line)
            if i % PAGE_SIZE == 0:
                pages.append("\n".join(buf)); buf=[]
        if buf: pages.append("\n".join(buf))

        view = HistoryPager(user_id=str(interaction.user.id), pages=pages)
        await interaction.response.send_message(pages[0], view=view, ephemeral=True)

async def setup(bot): await bot.add_cog(HistoryCog(bot))
