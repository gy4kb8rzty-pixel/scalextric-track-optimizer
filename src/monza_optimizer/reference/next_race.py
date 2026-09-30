"""Map calendar rows to track cards and sort by the next race weekend."""
from __future__ import annotations

from datetime import date, datetime, timezone

from monza_optimizer.reference.race_calendar import ALL_EVENTS

VENUE_TO_TRACK = {
    "melbourne": "albert_park",
    "shanghai": "shanghai",
    "suzuka": "suzuka",
    "sakhir": "bahrain",
    "jeddah": "jeddah",
    "miami": "miami",
    "montreal": "montreal",
    "monaco": "monaco",
    "barcelona": "barcelona",
    "madrid": "madring",
    "spielberg": "red_bull_ring",
    "silverstone": "silverstone",
    "spa-francorchamps": "spa",
    "hungaroring": "hungaroring",
    "zandvoort": "zandvoort",
    "monza": "monza",
    "baku": "baku",
    "marina bay": "marina_bay",
    "austin": "cota",
    "mexico city": "mexico",
    "interlagos": "interlagos",
    "las vegas": "las_vegas",
    "lusail": "lusail",
    "yas marina": "yas_marina",
    "bristol": "bristol",
    "kansas": "kansas",
    "darlington": "darlington",
    "phoenix": "phoenix",
    "talladega": "talladega",
    "martinsville": "martinsville",
    "homestead-miami": "homestead",
    "daytona": "daytona",
}

ID_ALIASES = {
    "singapore": "marina_bay",
    "monte_carlo": "monaco",
    "madrid": "madring",
    "spain": "madring",
}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def canonical_track_id(track_id: str | None, venue: str | None = None) -> str | None:
    tid = (track_id or "").strip().lower() or None
    if tid:
        tid = ID_ALIASES.get(tid, tid)
        return tid
    venue_key = (venue or "").strip().lower()
    return VENUE_TO_TRACK.get(venue_key)


def resolve_event_track_id(ev: dict) -> str | None:
    return canonical_track_id(ev.get("track_id"), ev.get("venue"))


def attach_next_race(row: dict, *, as_of: date | None = None) -> dict:
    tid = canonical_track_id(row.get("id"), None)
    series = (row.get("series") or "").lower()
    start = as_of or _today()
    best = None
    for ev in ALL_EVENTS:
        ev_tid = resolve_event_track_id(ev)
        if ev_tid != tid:
            continue
        ev_series = (ev.get("series") or "").lower()
        if series and ev_series and series not in ev_series and ev_series not in series:
            # f1 track should not pick a cup date, and vice versa
            if {"f1", "nascar_cup"} <= {series.replace("nascar", "nascar_cup"), ev_series, series}:
                if ("f1" in series) != ("f1" in ev_series):
                    continue
        if series == "f1" and ev_series != "f1":
            continue
        if series == "nascar_cup" and ev_series != "nascar_cup":
            continue
        race = date.fromisoformat(ev["race_date"])
        if race < start:
            continue
        if best is None or race < date.fromisoformat(best["race_date"]):
            best = ev
    if best:
        race = date.fromisoformat(best["race_date"])
        row["next_race_date"] = best["race_date"]
        row["next_race_name"] = best.get("name")
        row["next_race_venue"] = best.get("venue")
        row["next_race_label"] = race.strftime("%b %-d") if False else race.strftime("%b %d").replace(" 0", " ")
        row["next_race_series"] = best.get("series")
    else:
        row["next_race_date"] = None
    return row
