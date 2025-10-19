from typing import Dict

def apply_rewards(db, player, rewards: Dict[str, int]) -> str:
    parts = []
    if not player.currencies:
        raise RuntimeError("El jugador no tiene fila de Currency creada.")

    ts = int(rewards.get("tickets_standard", 0))
    if ts:
        player.currencies.tickets_standard += ts
        parts.append(f"+{ts} Standard Pass")

    sp = int(rewards.get("tickets_special", 0))
    if sp:
        player.currencies.tickets_special += sp
        parts.append(f"+{sp} Special Pass")

    cr = int(rewards.get("credits", 0))
    if cr:
        player.currencies.credits += cr
        parts.append(f"+{cr} créditos")

    return ", ".join(parts) if parts else "Sin recompensa definida"