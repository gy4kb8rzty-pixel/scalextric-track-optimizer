"""Flying Start — official C1446M START Grand Prix mapped to Sport SKUs."""

from __future__ import annotations

FLYING_START_SET_ID = "C1446M"
FLYING_START_LABEL = "Flying Start"
FLYING_START_URL = (
    "https://uk.scalextric.com/products/scalextric-start-grand-prix-race-set-c1446m"
)

# One moulding per curve. 16 identical R2 45° pieces, not 8L+8R products.
FLYING_START_INVENTORY: dict[str, int] = {
    "C8205": 4,
    "C8206": 16,
}

FLYING_START_NOTE = (
    "Flying Start is C1446M: 4×C8205 and 16×C8206. "
    "C8206 is one piece; L/R is only how you clip it in the lay-list."
)


def flying_start_inventory() -> dict[str, int]:
    return dict(FLYING_START_INVENTORY)
