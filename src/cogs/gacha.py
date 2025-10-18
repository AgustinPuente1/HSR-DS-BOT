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

# --- helpers E/S ---
def eidolons_from_copies(copies: int) -> int:
    # E0 con 1 copia; tope E6
    return max(0, min(6, (copies - 1)))

def superpos_from_copies(copies: int) -> int:
    # S1 con 1 copia; tope S5
    return max(1, min(5, copies))

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
            
            if not GS.is_banner_active(gs.banner_id):
                return await interaction.followup.send(
                    f"El banner **{b.name}** está **inactivo** en este momento. Elegí otro con `/set_banner`.",
                )

            # Tickets por tipo de banner
            if b.key == "star_rail_pass":
                have = p.currencies.tickets_standard
                if have < count:
                    return await interaction.followup.send(f"No te alcanzan los tickets. Tenés {have} **Star Rail Pass**.")
                p.currencies.tickets_standard -= count
            else:
                have = p.currencies.tickets_special
                if have < count:
                    return await interaction.followup.send(f"No te alcanzan los tickets. Tenés {have} **Star Rail Special Pass**.")
                p.currencies.tickets_special -= count

            pity4, pity5 = gs.pity4, gs.pity5
            last_feat = gs.last_5_was_featured

            results = []  # (rarity, item_obj, item_type, note)
            for _ in range(count):
                rarity = GS.roll_rarity(pity4, pity5, b.rates)
                item_id, item_type, is_feat = GS.choose_item(gs.banner_id, rarity, last_feat)
                item = GS.characters[item_id] if item_type == "character" else GS.light_cones[item_id]

                # Buscar inventario actual del item
                inv = (db.query(InventoryItem)
                         .filter(InventoryItem.player_id == p.user_id,
                                 InventoryItem.item_id == item_id,
                                 InventoryItem.item_type == item_type)
                         .first())

                note = ""
                if inv is None:
                    # Primera vez: crear registro y setear nota E0 / S1
                    inv = InventoryItem(player_id=p.user_id, item_id=item_id, item_type=item_type, copies=1)
                    db.add(inv)
                    if item_type == "character":
                        note = "E0 (nuevo)"
                    else:
                        note = "S1 (nuevo)"
                else:
                    # Ya lo tiene: progreso o conversión a tickets si está en tope
                    if item_type == "character":
                        current_e = eidolons_from_copies(inv.copies)
                        if current_e >= 6:
                            if rarity == 5:
                                p.currencies.tickets_special += 5
                                note = "Convertido: +5 Special Pass (E6)"
                            elif rarity == 4:
                                p.currencies.tickets_standard += 2
                                note = "Convertido: +2 Standard Pass (E6)"
                            else :
                                note = "Máximo de copias"
                            
                        else:
                            inv.copies += 1
                            note = f"E{eidolons_from_copies(inv.copies)}"
                    else:
                        current_s = superpos_from_copies(inv.copies)
                        if current_s >= 5:
                            if rarity == 5:
                                p.currencies.tickets_special += 5
                                note = "Convertido: +5 Special Pass (E6)"
                            elif rarity == 4:
                                p.currencies.tickets_standard += 2
                                note = "Convertido: +2 Standard Pass (E6)"
                            else :
                                note = "Máximo de copias"
                        else:
                            inv.copies += 1
                            note = f"S{superpos_from_copies(inv.copies)}"

                # pity / featured
                pity4 = 0 if rarity >= 4 else pity4 + 1
                pity5 = 0 if rarity >= 5 else pity5 + 1
                if rarity == 5:
                    last_feat = is_feat

                # historial
                db.add(PullHistory(
                    player_id=p.user_id,
                    banner_id=gs.banner_id,
                    rarity=rarity,
                    item_id=item_id,
                    item_type=item_type,
                    ts=datetime.now(timezone.utc)
                ))

                results.append((rarity, item, item_type, note))

            gs.pity4, gs.pity5, gs.last_5_was_featured = pity4, pity5, last_feat
            db.commit()

        # ahora el embed acepta 'note'
        embeds, files = make_pull_embed(results, characters, light_cones)
        await interaction.followup.send(embeds=embeds, files=files)

async def setup(bot): await bot.add_cog(GachaCog(bot))
