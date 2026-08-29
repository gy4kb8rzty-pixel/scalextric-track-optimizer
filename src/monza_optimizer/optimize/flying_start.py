"""Flying Start — smallest official 1:32 box you can clip together tonight.

Source (Aug 2026): Scalextric C1446M START Grand Prix Race Set,
https://uk.scalextric.com/products/scalextric-start-grand-prix-race-set-c1446m

Hornby lists it as the 1:32 START introduction set. What's Inside:
  3 × Straight Track
  16 × R2 45º Curved Track
  2 × START Conversion Track
  1 × START Powerbase

START plastic is not a second geometry family in this optimiser. After the
included converters the centreline matches Sport:
  powerbase + 3 straights  →  4 × C8205  (350 mm standard straight)
  16 × R2 45º            →  8 × C8206L + 8 × C8206R
Converters (C8222 family) are join adapters only, so they stay off the BOM.
No unofficial SKUs.
"""

from __future__ import annotations

FLYING_START_SET_ID = "C1446M"
FLYING_START_LABEL = "Flying Start"
FLYING_START_URL = (
    "https://uk.scalextric.com/products/scalextric-start-grand-prix-race-set-c1446m"
)

# Sport-SKU map of the official START Grand Prix track pack.
FLYING_START_INVENTORY: dict[str, int] = {
    "C8205": 4,
    "C8206L": 8,
    "C8206R": 8,
}

FLYING_START_NOTE = (
    "Flying Start stock is the official C1446M START Grand Prix race set "
    "mapped onto Sport SKUs (4×C8205, 8×C8206L, 8×C8206R)."
)


def flying_start_inventory() -> dict[str, int]:
    return dict(FLYING_START_INVENTORY)
