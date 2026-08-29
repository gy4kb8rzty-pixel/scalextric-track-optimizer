from fastapi.testclient import TestClient

from monza_optimizer.export.lay_list import hand_of, lay_rows
from monza_optimizer.export.outputs import normalize_wanted
from monza_optimizer.server import app

client = TestClient(app)


def test_hand_and_lay_rows():
    assert hand_of("C8206L") == "L"
    assert hand_of("C8206R") == "R"
    assert hand_of("C8205") is None
    rows = lay_rows(["C8205", "C8206L", "C8206R"])
    assert rows[1]["hand"] == "L" and rows[2]["sku"] == "C8206R"


def test_normalize_wanted_keeps_shopping_default():
    assert normalize_wanted(None) == ["shopping", "lay"]
    assert "shopping" in normalize_wanted(["png", "3mf"])


def test_outputs_menu_and_export_svg():
    menu = client.get("/outputs").json()
    ids = {f["id"] for f in menu["formats"]}
    assert ids >= {"shopping", "lay", "png", "pdf", "3mf"}
    r = client.post(
        "/export",
        json={
            "sequence": ["C8205", "C8206L", "C8206R", "C8205"],
            "track_id": "demo",
            "outputs": ["lay", "svg", "png", "pdf"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lay"]["rows"][1]["hand"] == "L"
    assert "<svg" in body["files"]["svg"]["text"]
    assert body["files"]["png"]["base64"]
    assert body["files"]["pdf"]["base64"].startswith("JVBER")
