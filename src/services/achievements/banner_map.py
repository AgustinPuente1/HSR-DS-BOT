from ..data_loader import load_data

_char, _lc, _banners = load_data()
BANNER_KEY = {b.id: b.key for b in _banners.banners}

__all__ = ["BANNER_KEY"]