import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from ..db.session import SessionLocal
from ..db.models import Player, AchievementState
from ..services.achievements_service import load_catalog, is_completed, apply_rewards

CATALOG = load_catalog()

def _status_emoji(state: str) -> str:
    return {"locked":"🔒", "ready":"🏁", "claimed":"✅"}.get(state, "❔")

class AchievementsSlash(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="achievements", description="Lista tus logros y su estado.")
    async def achievements(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

            # logros ya reclamados
            claimed_ids = set(
                r[0] for r in db.execute(
                    select(AchievementState.achievement_id).where(
                        AchievementState.player_id == uid,
                        AchievementState.claimed_at.is_not(None)
                    )
                ).all()
            )

            lines = []
            for a in CATALOG.achievements:
                if a.id in claimed_ids:
                    state = "claimed"
                    progress = None
                else:
                    done, progress = is_completed(db, uid, a)
                    state = "ready" if done else "locked"
                em = _status_emoji(state)
                prog_txt = f" — *{progress}*" if progress else ""
                lines.append(f"{em} **{a.name}** (`{a.id}`)\n{a.desc}{prog_txt}")

        # enviar en embed
        embed = discord.Embed(title="Logros", color=0x90cdf4, description="\n\n".join(lines) if lines else "_sin logros_")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="claim_all", description="Reclama todas las recompensas disponibles.")
    async def claim_all(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        claimed = 0
        summaries = []

        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)

            for a in CATALOG.achievements:
                row = db.execute(
                    select(AchievementState).where(
                        AchievementState.player_id == uid,
                        AchievementState.achievement_id == a.id
                    )
                ).scalars().first()

                if row and row.claimed_at is not None:
                    continue

                done, _ = is_completed(db, uid, a)
                if not done:
                    continue

                summary = apply_rewards(db, p, a.rewards)
                if row is None:
                    db.add(AchievementState(player_id=uid, achievement_id=a.id, claimed_at=now))
                else:
                    row.claimed_at = now
                summaries.append(f"• {a.name}: {summary}")
                claimed += 1

            db.commit()

        if claimed == 0:
            return await interaction.response.send_message("No tenés recompensas pendientes.", ephemeral=True)

        embed = discord.Embed(title="Recompensas reclamadas", color=0x48bb78, description="\n".join(summaries))
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot):
    await bot.add_cog(AchievementsSlash(bot))
