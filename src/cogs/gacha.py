import discord
from discord import app_commands
from discord.ext import commands
from ..db.session import SessionLocal
from ..services.data_loader import load_data
from ..services.gacha_service import GachaService
from ..util.embeds import make_pull_embed
from ..db.models import Player, GachaState, InventoryItem, PullHistory
from ..util.banner_select import BannerSelectView
from datetime import datetime, timezone

characters, light_cones, banners = load_data()
GS = GachaService(characters, light_cones, banners)

class GachaCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="setbanner", description="Cambia tu banner activo.")
    async def setbanner(self, interaction: discord.Interaction):
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
        # pasamos la instancia GS a la view
        view = BannerSelectView(user_id=str(interaction.user.id), gs=GS)
        await interaction.response.send_message("Elegí un banner de la lista:", view=view, ephemeral=True)

    @app_commands.command(name="pull", description="Tirada x1.")
    async def pull(self, interaction: discord.Interaction):
        await self._do_pull(interaction, 1)

    @app_commands.command(name="pull10", description="Tirada x10.")
    async def pull10(self, interaction: discord.Interaction):
        await self._do_pull(interaction, 10)

    async def _do_pull(self, interaction: discord.Interaction, count: int):
        await interaction.response.defer(ephemeral=False)
        with SessionLocal() as db:
            p = db.get(Player, str(interaction.user.id))
            if not p:
                return await interaction.followup.send("Usá /register primero.")

            gs = db.get(GachaState, p.user_id)
            b = GS.banners[gs.banner_id]

            # Tickets por tipo de banner
            if b.key == "star_rail_pass":
                have = p.currencies.tickets_standard
                need_name = "Star Rail Pass"
                if have < count:
                    return await interaction.followup.send(f"No te alcanzan los tickets. Tenés {have} **{need_name}**.")
                p.currencies.tickets_standard -= count
            else:
                have = p.currencies.tickets_special
                need_name = "Star Rail Special Pass"
                if have < count:
                    return await interaction.followup.send(f"No te alcanzan los tickets. Tenés {have} **{need_name}**.")
                p.currencies.tickets_special -= count

            pity4, pity5 = gs.pity4, gs.pity5
            last_feat = gs.last_5_was_featured

            results = []
            for _ in range(count):
                rarity = GS.roll_rarity(pity4, pity5, b.rates)
                item_id, item_type, is_feat = GS.choose_item(gs.banner_id, rarity, last_feat)
                item = GS.characters[item_id] if item_type == "character" else GS.light_cones[item_id]
                results.append((rarity, item, item_type))

                pity4 = 0 if rarity >= 4 else pity4 + 1
                pity5 = 0 if rarity >= 5 else pity5 + 1
                if rarity == 5: 
                    last_feat = is_feat

                # inventario
                inv = (db.query(InventoryItem)
                         .filter(InventoryItem.player_id == p.user_id,
                                 InventoryItem.item_id == item_id,
                                 InventoryItem.item_type == item_type)
                         .first())
                if inv: inv.copies += 1
                else: db.add(InventoryItem(player_id=p.user_id, item_id=item_id, item_type=item_type))

                # historial
                db.add(PullHistory(
                    player_id=p.user_id,
                    banner_id=gs.banner_id,
                    rarity=rarity,
                    item_id=item_id,
                    item_type=item_type,
                    ts=datetime.now(timezone.utc)
                ))

            gs.pity4, gs.pity5, gs.last_5_was_featured = pity4, pity5, last_feat
            db.commit()

        embeds, files = make_pull_embed(results, characters, light_cones)
        await interaction.followup.send(embeds=embeds, files=files)

async def setup(bot): await bot.add_cog(GachaCog(bot))
