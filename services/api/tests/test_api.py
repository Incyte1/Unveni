from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_opportunities() -> None:
    response = client.get("/opportunities")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "render-api"
    assert len(body["items"]) >= 3


def test_get_trade_detail() -> None:
    response = client.get("/opportunities/nvda-call-vertical-28d")

    assert response.status_code == 200
    assert response.json()["symbol"] == "NVDA"
