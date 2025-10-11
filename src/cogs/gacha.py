import discord
from discord import app_commands, File
from discord.ext import commands
from ..db.session import SessionLocal
from ..services.data_loader import load_data
from ..services.gacha_service import GachaService
from ..util.embeds import make_pull_embed
from ..db.models import Player, GachaState, InventoryItem, PullHistory
from datetime import datetime, timezone

characters, banners = load_data()
GS = GachaService(characters, banners)

# -------- View y Select para elegir banner --------

class BannerSelect(discord.ui.Select):
    def __init__(self, user_id: str):
        self.user_id = user_id
        # Construir opciones desde GS.banners (máx 25 por límite de Discord)
        options = []
        for bid, b in list(GS.banners.items())[:25]:
            label = b.name[:100]  # seguridad por longitud
            description = f"ID: {bid}"
            options.append(discord.SelectOption(label=label, value=bid, description=description))
        super().__init__(
            placeholder="Elegí tu banner…",
            min_values=1, max_values=1,
            options=options,
            custom_id="banner_select"
        )

    async def callback(self, interaction: discord.Interaction):
        # Evitar que otros usuarios toquen el menú
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("No podés cambiar el banner de otra persona.", ephemeral=True)

        chosen = self.values[0]
        with SessionLocal() as db:
            gs = db.get(GachaState, self.user_id)
            if not gs:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            gs.banner_id = chosen
            db.commit()

        bname = GS.banners[chosen].name
        await interaction.response.edit_message(content=f"Banner activo: **{bname}** *(ID: `{chosen}`)*", view=None)

class BannerSelectView(discord.ui.View):
    def __init__(self, user_id: str, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.add_item(BannerSelect(user_id=user_id))

# --------------------------------------------------

class GachaCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="setbanner", description="Cambia tu banner activo.")
    async def setbanner(self, interaction: discord.Interaction):
        """Abre un menú para elegir el banner activo."""
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

        view = BannerSelectView(user_id=str(interaction.user.id))
        await interaction.response.send_message("Elegí un banner de la lista:", view=view, ephemeral=True)
    
    """
    @app_commands.command(name="setbanner", description="Cambia tu banner activo.")
    @app_commands.describe(banner_id="Ej: stellar_warp, event_warp_1_seele")
    async def setbanner(self, interaction: discord.Interaction, banner_id: str):
        if banner_id not in GS.banners:
            return await interaction.response.send_message("Banner inexistente.", ephemeral=True)
        with SessionLocal() as db:
            gs = db.get(GachaState, str(interaction.user.id))
            if not gs: return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            gs.banner_id = banner_id
            db.commit()
        await interaction.response.send_message(f"Banner activo: **{banner_id}**", ephemeral=True)
    """

    @app_commands.command(name="pull", description="Tirada x1.")
    async def pull(self, interaction: discord.Interaction):
        await self._do_pull(interaction, 1)

    @app_commands.command(name="pull10", description="Tirada x10.")
    async def pull10(self, interaction: discord.Interaction):
        await self._do_pull(interaction, 10)

    async def _do_pull(self, interaction: discord.Interaction, count: int):
        await interaction.response.defer(ephemeral=False)  # mostramos en canal
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.followup.send("Usá /register primero.")
            if p.currencies.tickets < count:
                return await interaction.followup.send("No te alcanzan los tickets.")

            gs = db.get(GachaState, p.user_id)
            b = GS.banners[gs.banner_id]
            pity4, pity5 = gs.pity4, gs.pity5
            last_feat = gs.last_5_was_featured

            results = []
            for _ in range(count):
                rarity = GS.roll_rarity(pity4, pity5, b.rates)
                char_id, is_feat = GS.choose_character(gs.banner_id, rarity, last_feat)
                ch = GS.characters[char_id]
                results.append((rarity, ch))

                # pity
                pity4 = 0 if rarity >= 4 else pity4 + 1
                pity5 = 0 if rarity >= 5 else pity5 + 1
                if rarity == 5: last_feat = is_feat

                # inventario
                inv = (db.query(InventoryItem)
                         .filter(InventoryItem.player_id==p.user_id, InventoryItem.character_id==char_id)
                         .first())
                if inv: inv.copies += 1
                else: db.add(InventoryItem(player_id=p.user_id, character_id=char_id))

                # historial
                db.add(PullHistory(
                    player_id=p.user_id,
                    banner_id=gs.banner_id,
                    rarity=rarity,
                    character_id=char_id,
                    ts=datetime.now(timezone.utc)
                ))

            # cobrar y guardar
            p.currencies.tickets -= count
            gs.pity4, gs.pity5, gs.last_5_was_featured = pity4, pity5, last_feat
            db.commit()

        embed, files = make_pull_embed(results, characters)
        await interaction.followup.send(embed=embed, files=files)
        

async def setup(bot): await bot.add_cog(GachaCog(bot))
