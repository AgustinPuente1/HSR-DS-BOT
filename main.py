import discord, os, asyncio
from discord.ext import commands
from dotenv import load_dotenv
from src.db.session import init_db

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

EXTENSIONS = [
    "src.cogs.player",
    "src.cogs.economy",
    "src.cogs.gacha",
    "src.cogs.inventory",
    "src.cogs.history",
    "src.cogs.stats",
]

@bot.event
async def on_ready():
    print(f"ENCENDIDO {bot.user}")

async def main():
    init_db()
    for ext in EXTENSIONS:
        await bot.load_extension(ext)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
