from discord.ext import commands
from ..db.session import SessionLocal
from ..db.models import Player, PullHistory
from sqlalchemy import select, desc

DEFAULT_LIMIT = 10
MAX_LIMIT = 50

class HistoryCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="history")
    async def history(self, ctx, limit: int = DEFAULT_LIMIT):
        """Muestra tus últimas tiradas (por defecto 10, máx 50)."""
        limit = max(1, min(limit, MAX_LIMIT))

        with SessionLocal() as db:
            p = db.get(Player, str(ctx.author.id))
            if not p: return await ctx.reply("Usá !register primero.")

            rows = db.execute(
                select(PullHistory)
                .where(PullHistory.player_id == p.user_id)
                .order_by(desc(PullHistory.id))
                .limit(limit)
            ).scalars().all()

        if not rows:
            return await ctx.reply("Aún no tenés tiradas registradas.")

        from ..cogs.gacha import GS

        lines = []
        for r in rows:
            ch = GS.characters.get(r.character_id)
            name = ch.name if ch else r.character_id
            stars = "★" * r.rarity
            lines.append(f"[{r.banner_id}] {stars} **{name}** — {r.ts}")

        # mandar en uno o más mensajes si excede 2000 chars
        msg = "\n".join(lines)
        if len(msg) <= 2000: 
            return await ctx.reply(msg)

        # segmentar
        chunk = []
        total_len = 0
        for line in lines:
            if total_len + len(line) + 1 > 1900:
                await ctx.reply("\n".join(chunk))
                chunk = [line]; total_len = len(line) + 1
            else:
                chunk.append(line); total_len += len(line) + 1
        if chunk:
            await ctx.reply("\n".join(chunk))

async def setup(bot): await bot.add_cog(HistoryCog(bot))
