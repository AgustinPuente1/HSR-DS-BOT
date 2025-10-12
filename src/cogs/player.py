import discord
from discord import app_commands
from discord.ext import commands
from ..db.session import SessionLocal
from ..db.models import Player, Currency, GachaState

WELCOME_TICKETS = 10

class PlayerCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="register", description="Crea tu perfil.")
    async def register(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            uid = str(interaction.user.id)
            if db.get(Player, uid):
                return await interaction.response.send_message("Ya estás registrado.", ephemeral=True)
            p = Player(user_id=uid, name=interaction.user.display_name)
            db.add(p)
            db.add(Currency(player=p, tickets_standard=WELCOME_TICKETS, tickets_special=WELCOME_TICKETS, credits=1000))
            db.add(GachaState(player=p))
            db.commit()
        await interaction.response.send_message(f"¡Perfil creado! Tenés {WELCOME_TICKETS} tickets standard y {WELCOME_TICKETS} tickets especiales.", ephemeral=True)

    @app_commands.command(name="profile", description="Muestra tu perfil.")
    async def profile(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            await interaction.response.send_message(
                f"Jugador: **{p.name}** — Tickets standard: {p.currencies.tickets_standard} — Tickets especiales: {p.currencies.tickets_special} — Créditos: {p.currencies.credits}",
                ephemeral=True
            )   
        
async def setup(bot): await bot.add_cog(PlayerCog(bot))
