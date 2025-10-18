import discord, os, asyncio
from discord.ext import commands
from dotenv import load_dotenv
from src.db.session import init_db

load_dotenv()
TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("GUILD_ID") 

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=None, intents=intents)

EXTENSIONS = [
    "src.cogs.player",
    "src.cogs.economy",
    "src.cogs.gacha",
    "src.cogs.inventory",
    "src.cogs.history",
    "src.cogs.stats",
    "src.cogs.equipment",
    "src.cogs.achievements",
]

@bot.event
async def on_ready():
    who = f"{bot.user} ({bot.user.id})"
    print(f"ENCENDIDO {who}")
    # Sync de comandos
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Slash sincronizados en guild {GUILD_ID}: {len(synced)}")
        else:
            synced = await bot.tree.sync()
            print(f"Slash globales sincronizados: {len(synced)} (pueden tardar unos minutos en verse)")
    except Exception as e:
        print("Error sync:", e)

async def main():
    init_db()
    for ext in EXTENSIONS:
        await bot.load_extension(ext)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
