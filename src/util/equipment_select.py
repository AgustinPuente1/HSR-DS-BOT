import discord
from ..db.session import SessionLocal
from ..db.models import Player
from ..services.equipment_service import EquipmentService

# ----------- EquipSelect -------------

class CharacterSelect(discord.ui.Select):
    def __init__(self, user_id: str, char_ids: list[str],
                 char_meta: dict[str, tuple[str,int,str]]):
        self.user_id = user_id
        self.char_meta = char_meta

        opts = []
        with SessionLocal() as db:
            for cid in char_ids:
                if EquipmentService.owns_char(db, user_id, cid):
                    name, rarity, path = char_meta[cid]
                    opts.append(discord.SelectOption(
                        label=f"{name} ({rarity}★)"[:100],
                        value=cid,
                        description=f"Path: {path}"[:100]
                    ))
                if len(opts) >= 25:
                    break

        super().__init__(
            placeholder="Elegí un personaje…",
            min_values=1, max_values=1,
            options=opts,
            custom_id="char_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "No podés usar el menú de otra persona.", ephemeral=True
            )
        chosen_char = self.values[0]
        cname = self.char_meta[chosen_char][0]

        view = LightConeSelectView(
            user_id=self.user_id,
            character_id=chosen_char,
            lc_ids=self.view.lc_ids,
            lc_meta=self.view.lc_meta,
            char_meta=self.view.char_meta
        )

        await interaction.response.edit_message(
            content=f"Personaje elegido: **{cname}**. Ahora elegí el Light Cone compatible:",
            view=view
        )

class LightConeSelect(discord.ui.Select):
    def __init__(self, user_id: str, character_id: str,
                 lc_ids: list[str],
                 lc_meta: dict[str, tuple[str,int,str,set]],
                 char_meta: dict[str, tuple[str,int,str]]):
        self.user_id = user_id
        self.character_id = character_id
        self.lc_meta = lc_meta
        self.char_meta = char_meta

        c_path = char_meta[character_id][2] 

        opts = []
        with SessionLocal() as db:
            for lid in lc_ids:
                if not EquipmentService.owns_lc(db, user_id, lid):
                    continue
                lname, rarity, lpath, favs = lc_meta[lid]
                if lpath != c_path:
                    continue
                equipped = EquipmentService.equipped_for_lc(db, user_id, lid)
                tag = " (equipado)" if equipped else ""
                fav = " ⭐" if character_id in favs else ""
                opts.append(discord.SelectOption(
                    label=f"{lname}{fav}{tag}"[:100],
                    value=lid,
                    description=f"{rarity}★ • Path: {lpath} "[:100]
                ))
                if len(opts) >= 25:
                    break

        if not opts:
            opts = [discord.SelectOption(
                label="No tenés LCs compatibles",
                value="__none__",
                description="Consejo: fijate el Path."
            )]

        super().__init__(
            placeholder="Elegí un Light Cone…",
            min_values=1, max_values=1,
            options=opts,
            custom_id="lc_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "No podés usar el menú de otra persona.", ephemeral=True
            )

        lid = self.values[0]
        if lid == "__none__":
            return await interaction.response.send_message(
                "No hay LCs compatibles para ese personaje.", ephemeral=True
            )

        uid = self.user_id
        cid = self.character_id

        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

            if not EquipmentService.owns_char(db, uid, cid):
                return await interaction.response.send_message("Ya no poseés ese personaje.", ephemeral=True)
            if not EquipmentService.owns_lc(db, uid, lid):
                return await interaction.response.send_message("Ya no poseés ese Light Cone.", ephemeral=True)

            EquipmentService.equip(db, uid, cid, lid)
            db.commit()

        cname = self.char_meta[cid][0]
        lname = self.lc_meta[lid][0]
        await interaction.response.edit_message(
            content=f"Equipado: **{cname}** ⇄ **{lname}** ",
            view=None
        )

class CharacterSelectView(discord.ui.View):
    def __init__(self, user_id: str,
                 char_ids, lc_ids,
                 char_meta, lc_meta,
                 *, timeout: float = 180):
        super().__init__(timeout=timeout)
        
        self.char_meta = char_meta
        self.lc_meta = lc_meta
        self.lc_ids = list(lc_ids)

        self.add_item(CharacterSelect(
            user_id=user_id,
            char_ids=list(char_ids),
            char_meta=char_meta
        ))

class LightConeSelectView(discord.ui.View):
    def __init__(self, user_id: str, character_id: str,
                 lc_ids, lc_meta, char_meta,
                 *, timeout: float = 180):
        super().__init__(timeout=timeout)
        
        self.char_meta = char_meta
        self.lc_meta = lc_meta
        self.lc_ids = list(lc_ids)

        self.add_item(LightConeSelect(
            user_id=user_id,
            character_id=character_id,
            lc_ids=list(lc_ids),
            lc_meta=lc_meta,
            char_meta=char_meta
        ))
        
# ----------- UnequipSelect -------------

class UnequipCharacterSelect(discord.ui.Select):
    def __init__(
        self,
        user_id: str,
        char_ids: list[str],
        char_meta: dict[str, tuple[str,int,str]],
        lc_meta: dict[str, tuple[str,int,str,set]],
    ):
        self.user_id = user_id
        self.char_meta = char_meta
        self.lc_meta = lc_meta

        opts = []
        with SessionLocal() as db:
            for cid in char_ids:
                row = EquipmentService.equipped_for_char(db, user_id, cid)
                if row:
                    cname, crarity, cpath = char_meta.get(cid, (cid, 0, "?"))
                    lid = row.light_cone_id
                    lname, lrarity, lpath, _ = lc_meta.get(lid, (lid, 0, "?", set()))

                    label = f"{cname} ({crarity}★) ↔ {lname} ({lrarity}★)"
                    desc  = f"Path PJ: {cpath} • Path LC: {lpath}"

                    opts.append(discord.SelectOption(
                        label=label[:100],
                        value=cid,
                        description=desc[:100]
                    ))
                if len(opts) >= 25:
                    break

        if not opts:
            opts = [discord.SelectOption(
                label="No tenés personajes con LC equipado",
                value="__none__",
                description="Usá /equipment para ver tus emparejamientos."
            )]

        super().__init__(
            placeholder="Elegí el personaje al que querés quitar el LC…",
            min_values=1, max_values=1,
            options=opts,
            custom_id="unequip_char_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "No podés usar el menú de otra persona.", ephemeral=True
            )

        cid = self.values[0]
        if cid == "__none__":
            return await interaction.response.send_message(
                "No hay nada para quitar.", ephemeral=True
            )

        uid = self.user_id
        with SessionLocal() as db:
            p = db.get(Player, uid)
            if not p:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)

            ok = EquipmentService.unequip(db, uid, cid)
            if not ok:
                return await interaction.response.send_message("Ese personaje no tiene LC equipado.", ephemeral=True)
            db.commit()

        cname = self.char_meta.get(cid, (cid, 0, "?"))[0]
        await interaction.response.edit_message(
            content=f"**{cname}** ahora no tiene Light Cone.",
            view=None
        )

class UnequipCharacterSelectView(discord.ui.View):
    def __init__(
        self,
        user_id: str,
        char_ids: list[str],
        char_meta: dict[str, tuple[str,int,str]],
        lc_meta: dict[str, tuple[str,int,str,set]],
        *, timeout: float = 180
    ):
        super().__init__(timeout=timeout)
        self.char_meta = char_meta
        self.lc_meta = lc_meta
        self.add_item(UnequipCharacterSelect(
            user_id=user_id,
            char_ids=list(char_ids),
            char_meta=char_meta,
            lc_meta=lc_meta
        ))