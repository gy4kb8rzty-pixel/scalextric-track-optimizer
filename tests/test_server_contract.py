"""Contract tests for the Lovable HTTP surface."""

from fastapi.testclient import TestClient

from monza_optimizer.server import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_tracks_and_levels():
    tracks = client.get("/tracks").json()
    ids = {t["id"] for t in tracks}
    assert "monza" in ids
    assert "monaco" in ids
    letters = {lv["letter"] for lv in client.get("/levels").json()}
    assert letters >= {"0", "A", "B", "C", "D"}
    assert "E" not in letters


def test_empty_inventory_is_empty_box():
    r = client.post(
        "/optimize",
        json={"track_id": "monza", "inventory": {}, "accuracy_level": "0"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sequence"], body.get("metrics")
    assert body["shopping"]["missing_piece_count"] == len(body["sequence"])
    assert body["metrics"].get("collapsed") is not True
    if body["metrics"].get("closed") and body["profile"].get("letter") == "0":
        talk = body["shopping"].get("join_dialogue") or {}
        assert talk.get("kind") in {"click", "pinch_or_short", "open"}
