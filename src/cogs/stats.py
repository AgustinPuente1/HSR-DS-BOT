from discord.ext import commands
from ..db.session import SessionLocal
from ..db.models import Player, PullHistory
from sqlalchemy import select, func, desc

TOP_N = 20

class StatsCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="users")
    async def users(self, ctx, top: int = TOP_N):
        """Lista usuarios por cantidad de tiradas (TOP 20 por defecto)."""
        top = max(1, min(top, 100))
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
            return await ctx.reply("No hay usuarios registrados.")

        lines = []
        for i, (name, uid, cnt) in enumerate(rows, start=1):
            mention = f"<@{uid}>"
            lines.append(f"**{i}.** {name} {mention} — **{cnt}** tiradas")

        await ctx.reply("\n".join(lines))

    @commands.command(name="global_stats")
    async def global_stats(self, ctx):
        """Muestra totales globales básicos."""
        with SessionLocal() as db:
            total_users = db.execute(select(func.count())).scalar()  # cuidado: default count() sin tabla
            # mejor: count players
            total_users = db.execute(select(func.count(Player.user_id))).scalar()
            total_pulls = db.execute(select(func.count(PullHistory.id))).scalar()
            five_count = db.execute(select(func.count()).where(PullHistory.rarity == 5)).scalar()
            four_count = db.execute(select(func.count()).where(PullHistory.rarity == 4)).scalar()

        msg = (
            f"**Usuarios:** {total_users}\n"
            f"**Tiradas totales:** {total_pulls}\n"
            f"**5★:** {five_count} • **4★:** {four_count}\n"
        )
        await ctx.reply(msg)

async def setup(bot): await bot.add_cog(StatsCog(bot))
