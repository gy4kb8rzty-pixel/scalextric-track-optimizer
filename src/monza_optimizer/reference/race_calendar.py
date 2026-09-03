"""F1 and NASCAR Cup calendars. Banner shows today through +28 days."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

# race_date = Sunday (or Saturday night) of the event weekend.
# 2027 F1 rows are provisional until the FIA publishes the official calendar.
F1_EVENTS: list[dict[str, Any]] = [
    {"season": 2026, "series": "f1", "name": "Australian Grand Prix", "venue": "Melbourne", "race_date": "2026-03-08", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Chinese Grand Prix", "venue": "Shanghai", "race_date": "2026-03-15", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Japanese Grand Prix", "venue": "Suzuka", "race_date": "2026-03-29", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Bahrain Grand Prix", "venue": "Sakhir", "race_date": "2026-04-12", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Saudi Arabian Grand Prix", "venue": "Jeddah", "race_date": "2026-04-19", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Miami Grand Prix", "venue": "Miami", "race_date": "2026-05-03", "track_id": "miami", "status": "official"},
    {"season": 2026, "series": "f1", "name": "Canadian Grand Prix", "venue": "Montreal", "race_date": "2026-05-24", "track_id": "montreal", "status": "official"},
    {"season": 2026, "series": "f1", "name": "Monaco Grand Prix", "venue": "Monaco", "race_date": "2026-06-07", "track_id": "monaco", "status": "official"},
    {"season": 2026, "series": "f1", "name": "Spanish Grand Prix", "venue": "Barcelona", "race_date": "2026-06-14", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Austrian Grand Prix", "venue": "Spielberg", "race_date": "2026-06-28", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "British Grand Prix", "venue": "Silverstone", "race_date": "2026-07-05", "track_id": "silverstone", "status": "official"},
    {"season": 2026, "series": "f1", "name": "Belgian Grand Prix", "venue": "Spa-Francorchamps", "race_date": "2026-07-19", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Hungarian Grand Prix", "venue": "Hungaroring", "race_date": "2026-07-26", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Dutch Grand Prix", "venue": "Zandvoort", "race_date": "2026-08-23", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Italian Grand Prix", "venue": "Monza", "race_date": "2026-09-06", "track_id": "monza", "status": "official"},
    {"season": 2026, "series": "f1", "name": "Spanish Grand Prix", "venue": "Madrid", "race_date": "2026-09-13", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Azerbaijan Grand Prix", "venue": "Baku", "race_date": "2026-09-26", "track_id": "baku", "status": "official"},
    {"season": 2026, "series": "f1", "name": "Singapore Grand Prix", "venue": "Marina Bay", "race_date": "2026-10-11", "track_id": "singapore", "status": "official"},
    {"season": 2026, "series": "f1", "name": "United States Grand Prix", "venue": "Austin", "race_date": "2026-10-25", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Mexico City Grand Prix", "venue": "Mexico City", "race_date": "2026-11-01", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "São Paulo Grand Prix", "venue": "Interlagos", "race_date": "2026-11-08", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Las Vegas Grand Prix", "venue": "Las Vegas", "race_date": "2026-11-21", "track_id": "las_vegas", "status": "official"},
    {"season": 2026, "series": "f1", "name": "Qatar Grand Prix", "venue": "Lusail", "race_date": "2026-11-29", "track_id": None, "status": "official"},
    {"season": 2026, "series": "f1", "name": "Abu Dhabi Grand Prix", "venue": "Yas Marina", "race_date": "2026-12-06", "track_id": None, "status": "official"},
    {"season": 2027, "series": "f1", "name": "Bahrain Grand Prix", "venue": "Sakhir", "race_date": "2027-03-14", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Saudi Arabian Grand Prix", "venue": "Jeddah", "race_date": "2027-03-21", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Australian Grand Prix", "venue": "Melbourne", "race_date": "2027-04-04", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Japanese Grand Prix", "venue": "Suzuka", "race_date": "2027-04-11", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Chinese Grand Prix", "venue": "Shanghai", "race_date": "2027-04-18", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Miami Grand Prix", "venue": "Miami", "race_date": "2027-05-02", "track_id": "miami", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Canadian Grand Prix", "venue": "Montreal", "race_date": "2027-05-23", "track_id": "montreal", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Monaco Grand Prix", "venue": "Monaco", "race_date": "2027-06-06", "track_id": "monaco", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Portuguese Grand Prix", "venue": "Portimão", "race_date": "2027-06-20", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "British Grand Prix", "venue": "Silverstone", "race_date": "2027-07-04", "track_id": "silverstone", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Austrian Grand Prix", "venue": "Spielberg", "race_date": "2027-07-11", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Belgian Grand Prix", "venue": "Spa-Francorchamps", "race_date": "2027-07-25", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Hungarian Grand Prix", "venue": "Hungaroring", "race_date": "2027-08-01", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Italian Grand Prix", "venue": "Monza", "race_date": "2027-09-05", "track_id": "monza", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Spanish Grand Prix", "venue": "Madrid", "race_date": "2027-09-12", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Azerbaijan Grand Prix", "venue": "Baku", "race_date": "2027-09-26", "track_id": "baku", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Turkish Grand Prix", "venue": "Istanbul", "race_date": "2027-10-03", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Singapore Grand Prix", "venue": "Marina Bay", "race_date": "2027-10-10", "track_id": "singapore", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "United States Grand Prix", "venue": "Austin", "race_date": "2027-10-24", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Mexico City Grand Prix", "venue": "Mexico City", "race_date": "2027-10-31", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "São Paulo Grand Prix", "venue": "Interlagos", "race_date": "2027-11-14", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Las Vegas Grand Prix", "venue": "Las Vegas", "race_date": "2027-11-21", "track_id": "las_vegas", "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Qatar Grand Prix", "venue": "Lusail", "race_date": "2027-12-05", "track_id": None, "status": "provisional"},
    {"season": 2027, "series": "f1", "name": "Abu Dhabi Grand Prix", "venue": "Yas Marina", "race_date": "2027-12-12", "track_id": None, "status": "provisional"},
]

CUP_EVENTS: list[dict[str, Any]] = [
    {"season": 2026, "series": "nascar_cup", "name": "Cook Out Southern 500", "venue": "Darlington", "race_date": "2026-09-06", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "Enjoy Illinois 300", "venue": "Gateway", "race_date": "2026-09-13", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "Bass Pro Shops Night Race", "venue": "Bristol", "race_date": "2026-09-19", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "Hollywood Casino 400", "venue": "Kansas", "race_date": "2026-09-27", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "South Point 400", "venue": "Las Vegas", "race_date": "2026-10-04", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "Bank of America 400", "venue": "Charlotte", "race_date": "2026-10-11", "track_id": "charlotte_roval", "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "Freeway Insurance 500", "venue": "Phoenix", "race_date": "2026-10-18", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "YellaWood 500", "venue": "Talladega", "race_date": "2026-10-25", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "Xfinity 500", "venue": "Martinsville", "race_date": "2026-11-01", "track_id": None, "status": "official"},
    {"season": 2026, "series": "nascar_cup", "name": "Cup Series Championship", "venue": "Homestead-Miami", "race_date": "2026-11-08", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Daytona 500", "venue": "Daytona", "race_date": "2027-02-21", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Autotrader 400", "venue": "EchoPark / Atlanta", "race_date": "2027-02-28", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "DuraMAX Grand Prix", "venue": "COTA", "race_date": "2027-03-07", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Phoenix", "venue": "Phoenix", "race_date": "2027-03-14", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Las Vegas", "venue": "Las Vegas", "race_date": "2027-03-21", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Southern 500", "venue": "Darlington", "race_date": "2027-09-05", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Richmond", "venue": "Richmond", "race_date": "2027-09-11", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Watkins Glen", "venue": "Watkins Glen", "race_date": "2027-09-19", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "New Hampshire", "venue": "Loudon", "race_date": "2027-09-26", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Las Vegas", "venue": "Las Vegas", "race_date": "2027-10-10", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Charlotte", "venue": "Charlotte", "race_date": "2027-10-17", "track_id": "charlotte_roval", "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Phoenix", "venue": "Phoenix", "race_date": "2027-10-24", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "YellaWood 500", "venue": "Talladega", "race_date": "2027-10-31", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Xfinity 500", "venue": "Martinsville", "race_date": "2027-11-07", "track_id": None, "status": "official"},
    {"season": 2027, "series": "nascar_cup", "name": "Championship", "venue": "Homestead-Miami", "race_date": "2027-11-14", "track_id": None, "status": "official"},
]

ALL_EVENTS = F1_EVENTS + CUP_EVENTS
WINDOW_DAYS = 28
HIDDEN_FROM_BANNER_TRACK = {"charlotte_roval", "gateway"}
HIDDEN_FROM_BANNER_VENUE = {"gateway", "charlotte"}


def _parse(iso: str) -> date:
    return date.fromisoformat(iso)


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def upcoming_events(*, as_of: date | None = None, days: int = WINDOW_DAYS) -> dict[str, Any]:
    start = as_of or today_utc()
    end = start + timedelta(days=int(days))
    rows = []
    for ev in ALL_EVENTS:
        if (ev.get("track_id") or "") in HIDDEN_FROM_BANNER_TRACK:
            continue
        if str(ev.get("venue") or "").strip().lower() in HIDDEN_FROM_BANNER_VENUE:
            continue
        race = _parse(ev["race_date"])
        weekend_start = race - timedelta(days=3)
        if race < start:
            continue
        if weekend_start > end:
            continue
        rows.append(
            {
                **ev,
                "weekend_start": weekend_start.isoformat(),
                "label": f"{ev['name']} · {ev['venue']} · {race.strftime('%d %b')}",
            }
        )
    rows.sort(key=lambda r: (r["race_date"], 0 if r["series"] == "f1" else 1))
    f1 = [r for r in rows if r["series"] == "f1"]
    cup = [r for r in rows if r["series"] == "nascar_cup"]
    return {
        "enabled": True,
        "as_of": start.isoformat(),
        "window_days": int(days),
        "window_end": end.isoformat(),
        "f1": f1,
        "nascar_cup": cup,
        "banner": {
            "f1": "  ·  ".join(r["label"] for r in f1) or "No F1 races in the next 4 weeks",
            "nascar_cup": "  ·  ".join(r["label"] for r in cup) or "No Cup races in the next 4 weeks",
        },
        "note": "2026 F1 dates follow the published FIA calendar. 2027 F1 dates are provisional.",
    }
