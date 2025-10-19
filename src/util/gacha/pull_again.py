import discord

class PullAgainView(discord.ui.View):
    def __init__(self, owner_id: str, count: int, cog: "GachaCog", *, timeout: float = 180): # type: ignore
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.count = count
        self.cog = cog
        label = "Tirar otra x10" if count == 10 else "Tirar otra x1"
        self.add_item(PullAgainButton(label=label, style=discord.ButtonStyle.primary))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("No podés reutilizar la tirada de otra persona.", ephemeral=True)
            return False
        return True

class PullAgainButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        view: PullAgainView = self.view  # type: ignore
        # Acknowledge sin editar el mensaje original
        await interaction.response.defer(ephemeral=False)
        # Enviar SIEMPRE un mensaje nuevo:
        await view.cog._send_pull(interaction, view.count)