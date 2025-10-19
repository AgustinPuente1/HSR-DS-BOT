def eidolons_from_copies(copies: int) -> int:
    # E0 con 1 copia; tope E6
    return max(0, min(6, copies - 1))

def superpos_from_copies(copies: int) -> int:
    # S1 con 1 copia; tope S5
    return max(1, min(5, copies))