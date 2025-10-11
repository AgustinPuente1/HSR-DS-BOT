import discord
from discord import File
from pathlib import Path
from datetime import datetime, timezone

# ----------- GACHA -----------

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

# ---------- HISTORY ------------

def _fmt_discord_relative(dt: datetime | None) -> str:
    if not dt:
        return ""
    try:
        # Normalizamos por si viene naive o en otra tz
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return f"<t:{int(dt.timestamp())}:R>"
    except Exception:
        return str(dt)

def make_history_embed(
    user: discord.abc.User | discord.Member,
    page_items: list[dict],
    page_index: int,
    total_pages: int,
    total_rows: int
) -> discord.Embed:
    """
    page_items: lista de dicts con claves: banner (str), rarity (int), name (str), ts (datetime|None)
    """
    embed = discord.Embed(
        title="Historial de tiradas",
        color=0x90cdf4,
        description=""
    )

    # Autor = el usuario dueño del historial
    try:
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    except Exception:
        embed.set_author(name=str(user))

    # Cuerpo: una línea por item
    if page_items:
        lines = []
        for it in page_items:
            stars = "★" * int(it["rarity"])
            when = _fmt_discord_relative(it.get("ts"))
            lines.append(f"[{it['banner']}] {stars} **{it['name']}** — {when}")
        embed.description = "\n".join(lines)
    else:
        embed.description = "_(sin registros en esta página)_"

    # Footer con paginación
    embed.set_footer(text=f"Página {page_index+1}/{total_pages} • Total: {total_rows}")

    return embed