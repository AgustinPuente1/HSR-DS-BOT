import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, func, desc
from ..db.session import SessionLocal
from ..db.models import Player, PullHistory

TOP_N = 20

class StatsCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="users", description="Ranking de usuarios por cantidad de tiradas.")
    @app_commands.describe(top="Cuántos mostrar (1-100)")
    async def users(self, interaction: discord.Interaction, top: app_commands.Range[int, 1, 100] = TOP_N):
        with SessionLocal() as db:
            q = (
                select(Player.name, Player.user_id, func.count(PullHistory.id))
                .join(PullHistory, PullHistory.player_id == Player.user_id, isouter=True)
                .group_by(Player.user_id, Player.name)
                .order_by(desc(func.count(PullHistory.id)))
                .limit(top)
            )
            rows = db.execute(q).all()

        if not rows:
            return await interaction.response.send_message("No hay usuarios registrados.", ephemeral=True)

        lines = []
        for i, (name, uid, cnt) in enumerate(rows, start=1):
            mention = f"<@{uid}>"
            lines.append(f"**{i}.** {name} {mention} — **{cnt}** tiradas")

        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="global_stats", description="Métricas globales básicas.")
    async def global_stats(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            total_users = db.execute(select(func.count(Player.user_id))).scalar()
            total_pulls = db.execute(select(func.count(PullHistory.id))).scalar()
            five_count = db.execute(select(func.count()).where(PullHistory.rarity == 5)).scalar()
            four_count = db.execute(select(func.count()).where(PullHistory.rarity == 4)).scalar()

        msg = (
            f"**Usuarios:** {total_users}\n"
            f"**Tiradas totales:** {total_pulls}\n"
            f"**5★:** {five_count} • **4★:** {four_count}\n"
        )
        await interaction.response.send_message(msg)

async def setup(bot): await bot.add_cog(StatsCog(bot))
