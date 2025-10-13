import discord

class HistoryPager(discord.ui.View):
    """
    Paginador genérico para listas de embeds.
    """
    def __init__(self, user_id: str, embeds: list[discord.Embed], timeout: float = 180):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.embeds = embeds
        self.index = 0
        self._update()

    def _update(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "prev":
                    child.disabled = self.index <= 0
                elif child.custom_id == "next":
                    child.disabled = self.index >= len(self.embeds) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "No podés navegar el historial de otra persona.",
                ephemeral=True
            )
            return False
        return True

    async def _show(self, interaction: discord.Interaction):
        self._update()
        await interaction.response.edit_message(
            embed=self.embeds[self.index],
            view=self
        )

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        await self._show(interaction)

    @discord.ui.button(label="Siguiente ➡️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.embeds) - 1:
            self.index += 1
        await self._show(interaction)
