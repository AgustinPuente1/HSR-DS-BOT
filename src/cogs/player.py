from discord.ext import commands
from ..db.session import SessionLocal
from ..db.models import Player, Currency, GachaState

WELCOME_TICKETS = 10

class PlayerCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="register")
    async def register(self, ctx):
        with SessionLocal() as db:
            uid = str(ctx.author.id)
            if db.get(Player, uid):
                return await ctx.reply("Ya estás registrado.")
            p = Player(user_id=uid, name=ctx.author.display_name)
            db.add(p)
            db.add(Currency(player=p, tickets=WELCOME_TICKETS, credits=1000))
            db.add(GachaState(player=p))
            db.commit()
        await ctx.reply(f"¡Perfil creado! Tenés {WELCOME_TICKETS} tickets de bienvenida.")

    @commands.command(name="profile")
    async def profile(self, ctx):
        with SessionLocal() as db:
            p = db.get(Player, str(ctx.author.id))
            if not p: return await ctx.reply("Usá !register primero.")
            await ctx.reply(f"Jugador: **{p.name}** — Tickets: {p.currencies.tickets} — Créditos: {p.currencies.credits}")
        
        
async def setup(bot): await bot.add_cog(PlayerCog(bot))
