import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from ..db.session import SessionLocal
from ..db.models import Player, Currency 

DAILY_TICKETS_STANDARD = 5
DAILY_TICKETS_SPECIAL = 2
COOLDOWN = timedelta(hours=24)

def to_utc_aware(dt: datetime | None) -> datetime | None:
    #Normaliza a UTC. Si viene naive, ASUMIMOS que es UTC.
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class EconomyCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="daily", description="Reclamá tus tickets diarios.")
    async def daily(self, interaction: discord.Interaction):
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

            last = to_utc_aware(p.last_daily_at)
            if last is not None:
                delta = now - last 
                if delta < COOLDOWN:
                    restante = COOLDOWN - delta
                    h = int(restante.total_seconds() // 3600)
                    m = int((restante.total_seconds() % 3600) // 60)
                    return await interaction.response.send_message(f"Aún no pasaron 24h. Te faltan ~{h}h {m}m.", ephemeral=True)

            if p.currencies is None:
                p.currencies = Currency(tickets_standard=0,tickets_special=0 ,credits=0)

            p.currencies.tickets_standard += DAILY_TICKETS_STANDARD
            p.currencies.tickets_special += DAILY_TICKETS_SPECIAL
            p.last_daily_at = now
            db.commit()

            await interaction.response.send_message(f"¡Reclamaste {DAILY_TICKETS_STANDARD} tickets standard y {DAILY_TICKETS_SPECIAL} tickets especiales!", ephemeral=True)

    @app_commands.command(name="add100", description="Agrega 100 tickets a tu cuenta.")
    async def add100(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá !register primero.", ephemeral=True)
            if p.currencies is None:
                p.currencies = Currency(tickets=0, credits=0)
            p.currencies.tickets_standard += 100
            p.currencies.tickets_special += 100
            db.commit()
            return await interaction.response.send_message(f"¡Te di 100 tickets! Ahora tenés {p.currencies.tickets_standard} tickets standard y {p.currencies.tickets_special} tickets especiales.", ephemeral=True)

    @app_commands.command(name="balance", description="Tu balance actual.")
    async def balance(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            #if p.currencies is None:
            #    return await interaction.reply("Sin billetera aún. Usá `!daily` primero.")
            return await interaction.response.send_message(f"Tickets standard: {p.currencies.tickets_standard} — Tickets especiales: {p.currencies.tickets_special} — Créditos: {p.currencies.credits}", ephemeral=True)
        
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
