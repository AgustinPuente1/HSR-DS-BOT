import os, discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from ..db.session import SessionLocal
from ..db.models import Player
from ..services.data_loader import load_data
from ..services.equipment_service import EquipmentService
from ..util.equipment_select import CharacterSelectView, UnequipCharacterSelectView

characters, light_cones, _banners = load_data()
CHAR_SET = {c.id for c in characters.characters}
LC_SET   = {l.id for l in light_cones.light_cones}
CHAR_META = {c.id: (c.name, c.rarity, c.path) for c in characters.characters}
LC_META   = {l.id: (l.name, l.rarity, l.path, set(l.favorites)) for l in light_cones.light_cones}

class EquipmentCogs(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="equip_select", description="Elegí personaje y Light Cone con menús.")
    async def equip_select(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

        view = CharacterSelectView(
            user_id=uid,
            char_ids=list(CHAR_SET),
            lc_ids=list(LC_SET),
            char_meta=CHAR_META,
            lc_meta=LC_META
        )
        await interaction.response.send_message("Elegí un personaje:", view=view, ephemeral=True)
    
    @app_commands.command(name="unequip_select", description="Quitá un Light Cone usando un selector.")
    async def unequip_select(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

            pairs = EquipmentService.list_pairs(db, uid)

        if not pairs:
            return await interaction.response.send_message(
                "No tenés Light Cones equipados.", ephemeral=True
            )

        view = UnequipCharacterSelectView(
            user_id=uid,
            char_ids=list(CHAR_SET),
            char_meta=CHAR_META,
            lc_meta=LC_META,
        )
        await interaction.response.send_message(
            "Elegí el personaje al que querés quitarle el Light Cone:",
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="equipment", description="Lista tus emparejamientos Personaje ↔ Light Cone.")
    async def equipment(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            pairs = EquipmentService.list_pairs(db, uid)

        if not pairs:
            return await interaction.response.send_message("No tenés equipamiento asignado.", ephemeral=True)

        lines = []
        for cid, lid in pairs:
            cname, _, c_path = CHAR_META.get(cid, (cid, 0, "?"))
            lname, _, l_path, favs = LC_META.get(lid, (lid, 0, "?", set()))
            fav_tag = " ⭐" if cid in favs else ""
            lines.append(f"**{cname}**  ↔  **{lname}**{fav_tag}")

        msg = "\n".join(lines)
        await interaction.response.send_message(msg if len(msg) < 1900 else msg[:1900])


async def setup(bot):
    await bot.add_cog(EquipmentCogs(bot))