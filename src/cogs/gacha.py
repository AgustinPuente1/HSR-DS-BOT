import discord
from discord import app_commands
from discord.ext import commands
from ..db.session import SessionLocal
from ..services.data_loader import load_data
from ..services.gacha_service import GachaService
from ..services.gacha_draw import run_pull_transaction
from ..util.embeds import make_pull_embed
from ..db.models import Player, GachaState
from ..util.gacha.banner_select import BannerSelectView
from ..util.gacha.pull_again import PullAgainView

characters, light_cones, banners = load_data()
GS = GachaService(characters, light_cones, banners)

class GachaCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="set_banner", description="Cambia tu banner activo.")
    async def setbanner(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
        view = BannerSelectView(user_id=str(interaction.user.id), gs=GS)
        await interaction.response.send_message("Elegí un banner de la lista:", view=view, ephemeral=True)

    @app_commands.command(name="pull", description="Tirada x1.")
    async def pull(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await self._send_pull(interaction, 1)

    @app_commands.command(name="pull10", description="Tirada x10.")
    async def pull10(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await self._send_pull(interaction, 10)

    async def _send_pull(self, interaction: discord.Interaction, count: int):
        # Corre la tirada, arma embeds y SIEMPRE manda un mensaje nuevo con followup.send
        try:
            with SessionLocal() as db:
                results, banner, state = run_pull_transaction(db, GS, str(interaction.user.id), count)
                db.commit()
        except Exception as e:
            # error de validación, tickets, banner inactivo, etc.
            return await interaction.followup.send(str(e))

        embeds, files = make_pull_embed(results, characters, light_cones)
        again_view = PullAgainView(owner_id=str(interaction.user.id), count=count, cog=self)
        await interaction.followup.send(embeds=embeds, files=files, view=again_view)

async def setup(bot): await bot.add_cog(GachaCog(bot))