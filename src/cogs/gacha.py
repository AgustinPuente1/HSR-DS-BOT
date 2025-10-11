from discord.ext import commands
from ..db.session import SessionLocal
from ..services.data_loader import load_data
from ..services.gacha_service import GachaService
from ..util.embeds import make_pull_embed
from ..db.models import Player, GachaState, InventoryItem, PullHistory


characters, banners = load_data()
GS = GachaService(characters, banners)

class GachaCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="setbanner")
    async def setbanner(self, ctx, banner_id: str):
        if banner_id not in GS.banners:
            return await ctx.reply("Banner inexistente.")
        with SessionLocal() as db:
            gs = db.get(GachaState, str(ctx.author.id))
            if not gs: return await ctx.reply("Usá !register primero.")
            gs.banner_id = banner_id
            db.commit()
            await ctx.reply(f"Banner activo: **{banner_id}**")

    @commands.command(name="pull")
    async def pull(self, ctx): await self._do_pull(ctx, 1)

    @commands.command(name="pull10")
    async def pull10(self, ctx): await self._do_pull(ctx, 10)

    async def _do_pull(self, ctx, count: int):
        with SessionLocal() as db:
            p = db.get(Player, str(ctx.author.id))
            if not p: return await ctx.reply("Usá !register primero.")
            if p.currencies.tickets < count: return await ctx.reply("No te alcanzan los tickets.")

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

                pity4 = 0 if rarity >= 4 else pity4 + 1
                pity5 = 0 if rarity >= 5 else pity5 + 1
                if rarity == 5: last_feat = is_feat

                inv = (db.query(InventoryItem)
                         .filter(InventoryItem.player_id==p.user_id, InventoryItem.character_id==char_id)
                         .first())
                if inv: inv.copies += 1
                else: db.add(InventoryItem(player_id=p.user_id, character_id=char_id))
                
                #actualizo el historial de pulls
                db.add(PullHistory(
                    player_id=p.user_id,
                    banner_id=gs.banner_id,
                    rarity=rarity,
                    character_id=char_id
                ))

            p.currencies.tickets -= count
            gs.pity4, gs.pity5, gs.last_5_was_featured = pity4, pity5, last_feat
            
            
            db.commit()

        embed, files = make_pull_embed(results, characters)
        await ctx.reply(embed=embed, files=files)
        

async def setup(bot): await bot.add_cog(GachaCog(bot))
