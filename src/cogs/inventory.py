from discord.ext import commands
from ..db.session import SessionLocal
from ..db.models import Player, InventoryItem
from sqlalchemy import select, func

class InventoryCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="inventory")
    async def inventory(self, ctx, member_mention: str = None):
        """Muestra tu inventario o el de otro usuario (mención opcional)."""
        target_id = None
        if member_mention and member_mention.startswith("<@") and member_mention.endswith(">"):
            # admite <@123> y <@!123>
            target_id = member_mention.strip("<@!>")
        else:
            target_id = str(ctx.author.id)

        with SessionLocal() as db:
            p = db.get(Player, target_id)
            if not p:
                return await ctx.reply("Ese usuario no está registrado." if target_id != str(ctx.author.id)
                                       else "Usá !register primero.")

            # Traer items y agrupar por rareza y nombre (opcionalmente podrías join con characters.json en memoria)
            items = db.execute(
                select(InventoryItem.character_id, func.sum(InventoryItem.copies))
                .where(InventoryItem.player_id == p.user_id)
                .group_by(InventoryItem.character_id)
            ).all()

        if not items:
            return await ctx.reply("Inventario vacío.")

        # Para mostrar rareza, necesitás mirar el JSON en memoria. Reutilizamos el loader del cog gacha:
        from ..cogs.gacha import GS  # tiene GS.characters ya cargado

        # ordenar por rareza DESC y luego nombre
        def sort_key(row):
            cid, copies = row
            ch = GS.characters.get(cid)
            return (-ch.rarity if ch else 0, ch.name if ch else cid)

        items_sorted = sorted(items, key=sort_key)

        lines = []
        for cid, copies in items_sorted:
            ch = GS.characters.get(cid)
            if ch:
                stars = "★" * ch.rarity
                lines.append(f"{stars} **{ch.name}** ×{copies}")
            else:
                lines.append(f"?? **{cid}** ×{copies}")

        # Discord limita 2000 chars, segmentamos si fuera necesario
        chunk = []
        total_len = 0
        for line in lines:
            if total_len + len(line) + 1 > 1900:
                await ctx.reply("\n".join(chunk))
                chunk = [line]; total_len = len(line) + 1
            else:
                chunk.append(line); total_len += len(line) + 1
        if chunk:
            await ctx.reply("\n".join(chunk))

async def setup(bot): await bot.add_cog(InventoryCog(bot))
