import discord

def status_emoji(state: str) -> str:
    return {"locked":"🔒", "ready":"🏁", "claimed":"✅"}.get(state, "❔")

def make_achievements_embed(
    user: discord.abc.User,
    items: list[dict],
    page_idx: int,
    total_pages: int
) -> discord.Embed:
    lines = []
    for it in items:
        em = status_emoji(it["state"])
        prog_txt = f" — *{it['progress']}*" if it["progress"] else ""
        lines.append(f"{em} **{it['name']}** (`{it['id']}`)\n{it['desc']}{prog_txt}")

    desc = "\n\n".join(lines) if lines else "_sin logros_"
    embed = discord.Embed(title="Logros", color=0x90cdf4, description=desc)
    try:
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    except Exception:
        embed.set_author(name=str(user))
    embed.set_footer(text=f"Página {page_idx+1}/{total_pages} • Mostrando {len(items)}")
    return embed