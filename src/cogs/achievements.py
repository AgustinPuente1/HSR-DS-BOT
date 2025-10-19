import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from ..db.session import SessionLocal
from ..db.models import Player, AchievementState
from ..services.achievements_service import load_catalog, is_completed, apply_rewards

CATALOG = load_catalog()
PER_PAGE = 20

def _status_emoji(state: str) -> str:
    # Mantengo tu mapping: locked=🔒, ready=🏁, claimed=✅
    return {"locked":"🔒", "ready":"🏁", "claimed":"✅"}.get(state, "❔")

def _compute_status(db, uid: str):
    """
    Devuelve lista de dicts:
      { "id", "name", "desc", "state": "locked|ready|claimed", "progress": str|None }
    """
    # Recolectar ya reclamados
    claimed_ids = set(
        r[0] for r in db.execute(
            select(AchievementState.achievement_id).where(
                AchievementState.player_id == uid,
                AchievementState.claimed_at.is_not(None)
            )
        ).all()
    )

    items = []
    for a in CATALOG.achievements:
        if a.id in claimed_ids:
            items.append({
                "id": a.id,
                "name": a.name,
                "desc": a.desc,
                "state": "claimed",
                "progress": None
            })
        else:
            done, progress = is_completed(db, uid, a)
            items.append({
                "id": a.id,
                "name": a.name,
                "desc": a.desc,
                "state": "ready" if done else "locked",
                "progress": progress
            })
    return items

def _page_count(n: int, per_page: int = PER_PAGE) -> int:
    return max(1, (n + per_page - 1) // per_page)

def _slice(items, page_idx: int, per_page: int = PER_PAGE):
    start = page_idx * per_page
    end = start + per_page
    return items[start:end]

def _build_embed(user: discord.abc.User, items, page_idx: int, total_pages: int) -> discord.Embed:
    lines = []
    for it in items:
        em = _status_emoji(it["state"])
        prog_txt = f" — *{it['progress']}*" if it["progress"] else ""
        lines.append(f"{em} **{it['name']}** (`{it['id']}`)\n{it['desc']}{prog_txt}")

    desc = "\n\n".join(lines) if lines else "_sin logros_"
    embed = discord.Embed(title="Logros", color=0x90cdf4, description=desc)
    try:
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    except Exception:
        embed.set_author(name=str(user))
    embed.set_footer(text=f"Página {page_idx+1}/{total_pages} • Mostrando {len(items)}")
    return embed

class AchievementsView(discord.ui.View):
    def __init__(self, user_id: str, page_idx: int = 0, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.page_idx = page_idx

    # --- helpers internos ---
    def _guard(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            # Bloquear a otros usuarios
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
        # Corregir page_idx si quedó fuera de rango
        self.page_idx = max(0, min(self.page_idx, total_pages - 1))

        page_items = _slice(items, self.page_idx, PER_PAGE)
        has_ready = any(it["state"] == "ready" for it in items)

        self._refresh_buttons_state(total_pages, has_ready)
        embed = _build_embed(interaction.user, page_items, self.page_idx, total_pages)

        await interaction.response.edit_message(embed=embed, view=self)

    # --- botones ---
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

        # 1) Acknowledge la interacción
        await interaction.response.defer(ephemeral=True)

        uid = self.user_id
        claimed = 0
        summaries = []

        try:
            from datetime import datetime, timezone
            with SessionLocal() as db:
                p = db.get(Player, uid)
                if not p:
                    return await interaction.followup.send("Usá /register primero.", ephemeral=True)

                now = datetime.now(timezone.utc)

                for a in CATALOG.achievements:
                    row = db.execute(
                        select(AchievementState).where(
                            AchievementState.player_id == uid,
                            AchievementState.achievement_id == a.id
                        )
                    ).scalars().first()

                    # Ya reclamado -> skip
                    if row and row.claimed_at is not None:
                        continue

                    done, _ = is_completed(db, uid, a)
                    if not done:
                        continue

                    # Aplico recompensas
                    summary = apply_rewards(db, p, a.rewards)

                    if row is None:
                        db.add(AchievementState(player_id=uid, achievement_id=a.id, claimed_at=now))
                    else:
                        row.claimed_at = now

                    summaries.append(f"• {a.name}: {summary}")
                    claimed += 1

                db.commit()

            # 3) Mensaje resumen (followup)
            if claimed == 0:
                await interaction.followup.send("No tenés recompensas pendientes.", ephemeral=True)
            else:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="Recompensas reclamadas",
                        color=0x48bb78,
                        description="\n".join(summaries)
                    ),
                    ephemeral=True
                )

            # 4) Refrescar el embed original
            with SessionLocal() as db:
                items = _compute_status(db, uid)
            total = len(items)
            total_pages = _page_count(total, PER_PAGE)
            self.page_idx = max(0, min(self.page_idx, total_pages - 1))
            page_items = _slice(items, self.page_idx, PER_PAGE)
            has_ready = any(it["state"] == "ready" for it in items)
            self._refresh_buttons_state(total_pages, has_ready)
            embed = _build_embed(interaction.user, page_items, self.page_idx, total_pages)
            await interaction.edit_original_response(embed=embed, view=self)

        except Exception as e:
            # Para que no explote en silencio
            await interaction.followup.send(f"Ocurrió un error al reclamar: `{e}`", ephemeral=True)
            
            
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

            # armar primera página
            items = _compute_status(db, uid)

        total = len(items)
        total_pages = _page_count(total, PER_PAGE)
        page_idx = 0
        page_items = _slice(items, page_idx, PER_PAGE)

        view = AchievementsView(user_id=uid, page_idx=page_idx)
        # habilitar/deshabilitar botones inicialmente
        has_ready = any(it["state"] == "ready" for it in items)
        view.prev_button.disabled = True
        view.next_button.disabled = (total_pages <= 1)
        view.claim_button.disabled = (not has_ready)

        embed = _build_embed(interaction.user, page_items, page_idx, total_pages)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AchievementsSlash(bot))
