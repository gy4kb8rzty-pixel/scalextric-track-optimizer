"""Retired official numbers → current Sport SKU."""

CURRENT_SKU = {
    "C156": "C8201",
    "C156L": "C8201L",
    "C156R": "C8201R",
}


def modern_id(sku: str) -> str:
    key = str(sku or "").strip().upper()
    return CURRENT_SKU.get(key, key)
