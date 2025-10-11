from discord.ext import commands
from datetime import datetime, timedelta, timezone
from ..db.session import SessionLocal
from ..db.models import Player, Currency  # <-- importá Currency

DAILY_TICKETS = 2
COOLDOWN = timedelta(hours=24)

def to_utc_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    # Si vino naive (sin tz) asumimos que estaba guardado en UTC
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    # Normalizamos a UTC
    return dt.astimezone(timezone.utc)

class EconomyCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @commands.command(name="daily")
    async def daily(self, ctx):
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            p = db.get(Player, str(ctx.author.id))
            if not p:
                return await ctx.reply("Usá !register primero.")

            last = to_utc_aware(p.last_daily_at)
            if last is not None:
                delta = now - last  # <- ahora nunca rompe
                if delta < COOLDOWN:
                    restante = COOLDOWN - delta
                    h = int(restante.total_seconds() // 3600)
                    m = int((restante.total_seconds() % 3600) // 60)
                    return await ctx.reply(f"Aún no pasaron 24h. Te faltan ~{h}h {m}m.")

            # Asegurar que exista currencies
            if p.currencies is None:
                p.currencies = Currency(tickets=0, credits=0)

            p.currencies.tickets += DAILY_TICKETS
            p.last_daily_at = now
            db.commit()

            # Responder dentro del contexto para evitar DetachedInstanceError
            return await ctx.reply(
                f"¡Reclamaste {DAILY_TICKETS} tickets! Ahora tenés {p.currencies.tickets}."
            )

    @commands.command(name="add100")
    async def add100(self, ctx):
        with SessionLocal() as db:
            p = db.get(Player, str(ctx.author.id))
            if not p:
                return await ctx.reply("Usá !register primero.")
            if p.currencies is None:
                p.currencies = Currency(tickets=0, credits=0)
            p.currencies.tickets += 100
            db.commit()
            return await ctx.reply(f"¡Te di 100 tickets! Ahora tenés {p.currencies.tickets}.")

    @commands.command(name="balance")
    async def balance(self, ctx):
        with SessionLocal() as db:
            p = db.get(Player, str(ctx.author.id))
            if not p:
                return await ctx.reply("Usá !register primero.")
            if p.currencies is None:
                return await ctx.reply("Sin billetera aún. Usá `!daily` primero.")
            return await ctx.reply(f"Tickets: {p.currencies.tickets} — Créditos: {p.currencies.credits}")
        
    # Handler error
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Error al ds
        if isinstance(error, commands.CommandInvokeError):
            original = error.original
            await ctx.reply(f"⚠️ Error en comando: {original.__class__.__name__} — {original}")
        else:
            await ctx.reply(f"⚠️ Error: {error.__class__.__name__} — {error}")

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
