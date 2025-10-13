import discord
from ..db.session import SessionLocal
from ..db.models import GachaState

class BannerSelect(discord.ui.Select):
    def __init__(self, user_id: str, gs, *, max_options: int = 25):
        """
        user_id: dueño del selector
        gs: instancia de GachaService (para leer banners)
        """
        self.user_id = user_id
        self.gs = gs

        options = []
        # 25 max, limite de ds
        for bid, b in list(self.gs.banners.items())[:max_options]:
            label = b.name[:100]
            description = f"ID: {bid} • {('PASS' if b.key=='star_rail_pass' else 'SPECIAL')}"
            options.append(discord.SelectOption(label=label, value=bid, description=description))

        super().__init__(
            placeholder="Elegí tu banner…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="banner_select"
        )

    async def callback(self, interaction: discord.Interaction):
        # seguridad: sólo el dueño puede interactuar
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "No podés cambiar el banner de otra persona.", ephemeral=True
            )

        chosen = self.values[0]
        # persistimos elección
        with SessionLocal() as db:
            gs = db.get(GachaState, self.user_id)
            if not gs:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            gs.banner_id = chosen
            db.commit()

        b = self.gs.banners[chosen]
        kind = "Star Rail Pass" if b.key == "star_rail_pass" else "Star Rail Special Pass"
        await interaction.response.edit_message(
            content=f"Banner activo: **{b.name}** *(ID: `{chosen}`)* — Requiere **{kind}**",
            view=None
        )

class BannerSelectView(discord.ui.View):
    def __init__(self, user_id: str, gs, *, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.add_item(BannerSelect(user_id=user_id, gs=gs))