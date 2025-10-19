import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from ..db.session import SessionLocal
from ..db.models import Player, AchievementState
from ..services.achievements.catalog import load_catalog
from ..services.achievements.repository import claimed_ids, get_achievement_row
from ..services.achievements.evaluators import is_completed
from ..services.achievements.rewards import apply_rewards
from ..util.embeds_achievements import make_achievements_embed

CATALOG = load_catalog()
PER_PAGE = 20

def _page_count(n: int, per_page: int = PER_PAGE) -> int:
    return max(1, (n + per_page - 1) // per_page)

def _slice(items, page_idx: int, per_page: int = PER_PAGE):
    s = page_idx * per_page
    return items[s:s+per_page]

def _compute_status(db, uid: str):
    already = claimed_ids(db, uid)
    items = []
    for a in CATALOG.achievements:
        if a.id in already:
            items.append({"id": a.id, "name": a.name, "desc": a.desc, "state": "claimed", "progress": None})
        else:
            done, prog = is_completed(db, uid, a)
            items.append({"id": a.id, "name": a.name, "desc": a.desc, "state": "ready" if done else "locked", "progress": prog})
    return items

class AchievementsView(discord.ui.View):
    def __init__(self, user_id: str, page_idx: int = 0, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.page_idx = page_idx

    def _guard(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            self.stop()
            return False
        return True

    def _refresh_buttons_state(self, total_pages: int, has_ready: bool):
        self.prev_button.disabled = (self.page_idx <= 0)
        self.next_button.disabled = (self.page_idx >= total_pages - 1)
        self.claim_button.disabled = (not has_ready)

    async def _render(self, interaction: discord.Interaction):
        uid = self.user_id
        with SessionLocal() as db:
            items = _compute_status(db, uid)

        total = len(items)
        total_pages = _page_count(total, PER_PAGE)
        self.page_idx = max(0, min(self.page_idx, total_pages - 1))
        page_items = _slice(items, self.page_idx, PER_PAGE)
        has_ready = any(it["state"] == "ready" for it in items)
        self._refresh_buttons_state(total_pages, has_ready)

        embed = make_achievements_embed(interaction.user, page_items, self.page_idx, total_pages)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._guard(interaction):
            return await interaction.response.send_message("No podés usar los logros de otra persona.", ephemeral=True)
        self.page_idx -= 1
        await self._render(interaction)

    @discord.ui.button(label="Reclamar disponibles", style=discord.ButtonStyle.success, disabled=True)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._guard(interaction):
            return await interaction.response.send_message("No podés usar los logros de otra persona.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        uid = self.user_id
        from datetime import datetime, timezone
        summaries = []
        claimed = 0

        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.followup.send("Usá /register primero.", ephemeral=True)

            now = datetime.now(timezone.utc)
            for a in CATALOG.achievements:
                row = get_achievement_row(db, uid, a.id)
                if row and row.claimed_at is not None:
                    continue
                done, _ = is_completed(db, uid, a)
                if not done:
                    continue

                summaries.append(f"• {a.name}: {apply_rewards(db, p, a.rewards)}")
                if row is None:
                    db.add(AchievementState(player_id=uid, achievement_id=a.id, claimed_at=now))
                else:
                    row.claimed_at = now
                claimed += 1
            db.commit()

        if claimed == 0:
            await interaction.followup.send("No tenés recompensas pendientes.", ephemeral=True)
        else:
            await interaction.followup.send(
                embed=discord.Embed(title="Recompensas reclamadas", color=0x48bb78, description="\n".join(summaries)),
                ephemeral=True
            )

        # refrescar original
        with SessionLocal() as db:
            items = _compute_status(db, uid)
        total = len(items)
        total_pages = _page_count(total, PER_PAGE)
        self.page_idx = max(0, min(self.page_idx, total_pages - 1))
        page_items = _slice(items, self.page_idx, PER_PAGE)
        has_ready = any(it["state"] == "ready" for it in items)
        self._refresh_buttons_state(total_pages, has_ready)
        embed = make_achievements_embed(interaction.user, page_items, self.page_idx, total_pages)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Siguiente ▶️", style=discord.ButtonStyle.secondary, disabled=True)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._guard(interaction):
            return await interaction.response.send_message("No podés usar los logros de otra persona.", ephemeral=True)
        self.page_idx += 1
        await self._render(interaction)

class AchievementsSlash(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="achievements", description="Lista tus logros, con paginado y botón para reclamar.")
    async def achievements(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            items = _compute_status(db, uid)

        total = len(items)
        total_pages = _page_count(total, PER_PAGE)
        page_idx = 0
        page_items = _slice(items, page_idx, PER_PAGE)

        view = AchievementsView(user_id=uid, page_idx=page_idx)
        has_ready = any(it["state"] == "ready" for it in items)
        view.prev_button.disabled = True
        view.next_button.disabled = (total_pages <= 1)
        view.claim_button.disabled = (not has_ready)

        embed = make_achievements_embed(interaction.user, page_items, page_idx, total_pages)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AchievementsSlash(bot))