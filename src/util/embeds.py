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

# ---------- INVENTORY ------------

def make_inventory_embeds(
    owner: discord.abc.User | discord.Member,
    entries: list[dict],
    *,
    title_prefix: str = "Inventario de",
    color: int = 0x90cdf4,
    items_per_page: int = 25,   # 🔹 nuevo parámetro
) -> list[discord.Embed]:
    """
    entries: lista de dicts normalizados:
      {
        "name": str,
        "rarity": int,        # 0..5
        "kind": "char"|"lc",  # para rotular Character / Light Cone
        "count": int
      }
    Devuelve una lista de embeds paginados, con máx. 'items_per_page' por embed.
    """

    # Orden: rareza desc, nombre asc
    items = sorted(entries, key=lambda x: (-x["rarity"], x["name"]))

    # Armamos líneas
    lines: list[str] = []
    for it in items:
        stars = "★" * it["rarity"] if it["rarity"] else ""
        prefix = "[Character]" if it["kind"] == "char" else "[Light Cone]"
        lines.append(f"{prefix}{stars} **{it['name']}** ×{it['count']}")

    # 🔹 Paginación por cantidad de ítems
    pages: list[list[str]] = []
    for i in range(0, len(lines), items_per_page):
        pages.append(lines[i:i + items_per_page])
    if not pages:
        pages = [[]]

    # Crear embeds
    embeds: list[discord.Embed] = []
    total = len(pages)
    for i, page in enumerate(pages, start=1):
        title = f"{title_prefix} {owner.display_name}"
        embed = discord.Embed(title=title, color=color)
        # autor/avatares
        try:
            embed.set_author(name=str(owner), icon_url=owner.display_avatar.url)
        except Exception:
            embed.set_author(name=str(owner))

        # descripción
        embed.description = "\n".join(page) if page else "_(sin objetos)_"
        embed.set_footer(text=f"Página {i}/{total}")
        embeds.append(embed)

    return embeds