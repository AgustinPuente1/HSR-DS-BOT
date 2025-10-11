import discord
from discord import File
from pathlib import Path

def make_pull_embed(results, characters):
    embed = discord.Embed(title="Resultados", color=0x90cdf4)
    files = []
    first_img = None

    for rarity, char in results:
        stars = "★" * rarity
        name = f"{stars} {char.name} ({char.rarity}★)"
        embed.add_field(name=name, value=f"{char.path} • {char.element}", inline=False)
        img = Path(char.image)
        if img.exists():
            files.append(File(img, filename=f"{char.id}.png"))
            if first_img is None:
                first_img = f"attachment://{char.id}.png"

    if first_img:
        embed.set_thumbnail(url=first_img)
    return embed, files
