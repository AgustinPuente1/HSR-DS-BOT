import discord
from discord import File
from pathlib import Path
from datetime import datetime, timezone

# ----------- GACHA -----------

def make_pull_embed(results, characters, light_cones):
    """
    results: lista de (rarity:int, item:obj, item_type:str)
    Devuelve: (embeds: list[discord.Embed], files: list[discord.File])
    En pull10 -> 10 embeds (cada uno con su thumbnail).
    En pull1  -> 1 embed.
    """
    embeds: list[discord.Embed] = []
    files: list[File] = []

    for idx, (rarity, item, item_type) in enumerate(results, start=1):
        stars = "★" * rarity
        if item_type == "character":
            title = f"{stars} {item.name} ({item.rarity}★) — Character"
            desc  = f"{item.path} • {item.element}"
            img_path = Path(item.image)
        else:
            title = f"{stars} {item.name} ({item.rarity}★) — Light Cone"
            desc  = f"{item.path}"
            img_path = Path(item.image)

        embed = discord.Embed(title=title, description=desc, color=0x90cdf4)
        embed.set_footer(text=f"Resultado {idx}/{len(results)}")

        # === CLAVE: nombre de archivo ÚNICO por resultado ===
        if img_path.exists():
            unique_fname = f"{idx}-{item.id}.png"   # <- evita colisiones en el mismo mensaje
            files.append(File(img_path, filename=unique_fname))
            embed.set_thumbnail(url=f"attachment://{unique_fname}")

        embeds.append(embed)

    return embeds, files

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