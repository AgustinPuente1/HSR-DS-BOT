import discord
from ...db.session import SessionLocal
from ...db.models import GachaState

class BannerSelect(discord.ui.Select):
    def __init__(self, user_id: str, gs, *, max_options: int = 25):
        """
        user_id: dueño del selector
        gs: instancia de GachaService (para leer banners)
        """
        self.user_id = user_id
        self.gs = gs

        options = []
        for bid, b in list(self.gs.banners.items()):
            # si el banner tiene atributo active=False, lo ignoramos
            is_active = getattr(b, "active", True)
            if not is_active:
                continue

            label = b.name[:100]
            description = f"ID: {bid} • {('PASS' if b.key == 'star_rail_pass' else 'SPECIAL')}"
            options.append(discord.SelectOption(label=label, value=bid, description=description))

            if len(options) >= max_options:
                break

        # si no hay banners activos
        if not options:
            options = [
                discord.SelectOption(
                    label="(Sin banners activos)",
                    value="__none__",
                    description="No hay banners disponibles actualmente."
                )
            ]
            
        super().__init__(
            placeholder="Elegí tu banner…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="banner_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "No podés cambiar el banner de otra persona.", ephemeral=True
            )

        chosen = self.values[0]
        if chosen == "__none__":
            return await interaction.response.send_message(
                "No hay banners activos para seleccionar.", ephemeral=True
            )

        b = self.gs.banners[chosen]
        with SessionLocal() as db:
            gs = db.get(GachaState, self.user_id)
            if not gs:
                return await interaction.response.send_message("Usá /register primero.", ephemeral=True)
            gs.banner_id = chosen
            db.commit()

        kind = "Star Rail Pass" if b.key == "star_rail_pass" else "Star Rail Special Pass"
        await interaction.response.edit_message(
            content=f"Banner activo: **{b.name}** *(ID: `{chosen}`)* — Requiere **{kind}**",
            view=None
        )

class BannerSelectView(discord.ui.View):
    def __init__(self, user_id: str, gs, *, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.add_item(BannerSelect(user_id=user_id, gs=gs))