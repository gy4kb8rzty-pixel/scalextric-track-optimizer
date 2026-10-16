"""NASCAR ovals cannot use C/D/E: Sport max curve is R4."""
from __future__ import annotations

NASCAR_R4_NOTE = (
    "Scalextric Sport has no curve larger than R4. "
    "This NASCAR oval therefore has no ambition levels C, D or E — "
    "those levels need a tighter fit than R4 can draw. "
    "Use A (manual) or B (R4 stadium / tri-oval)."
)


def nascar_hides_cde(track_id: str | None) -> bool:
    tid = str(track_id or "").strip().lower()
    if not tid or "roval" in tid:
        return False
    try:
        from monza_optimizer.optimize.oval_fit import is_nascar_oval
        return bool(is_nascar_oval(tid))
    except Exception:
        return False


def apply_nascar_level_policy(rows: list[dict], track_id: str | None) -> list[dict]:
    if not nascar_hides_cde(track_id):
        return rows
    out = []
    for row in rows:
        item = dict(row)
        letter = str(item.get("letter") or "").upper()
        if letter in {"C", "D", "E"}:
            item["visible_in_menu"] = False
            item["restricted"] = True
            item["warning"] = NASCAR_R4_NOTE
        elif letter == "B":
            item["warning"] = NASCAR_R4_NOTE
            item["pitch"] = (
                str(item.get("pitch") or "")
                + " NASCAR oval: R4 is the largest Sport curve, so C/D/E are not offered."
            ).strip()
        item["nascar_r4_only"] = True
        item["max_letter"] = "B"
        item["level_notice"] = NASCAR_R4_NOTE
        out.append(item)
    return out
