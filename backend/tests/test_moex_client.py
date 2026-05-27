from decimal import Decimal

import httpx
import pytest

from app.modules.market import moex_client as moex_client_module
from app.modules.market.moex_client import MoexClient, MoexClientError


class FakeResponse:
    def __init__(self, payload=None, json_error=None):
        self.payload = payload
        self.json_error = json_error

    def raise_for_status(self):
        return None

    def json(self):
        if self.json_error is not None:
            raise self.json_error

        return self.payload


def make_moex_payload():
    return {
        "securities": {
            "columns": ["SECID", "SHORTNAME", "SECNAME", "BOARDID", "FACEUNIT"],
            "data": [["SBER", "Sber", "Sberbank", "TQBR", "RUB"]],
        },
        "marketdata": {
            "columns": ["SECID", "BOARDID", "LAST", "CURRENCYID"],
            "data": [["SBER", "TQBR", "123.45", "RUB"]],
        },
    }


def make_moex_candles_payload():
    return {
        "candles": {
            "columns": [
                "begin",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "value",
            ],
            "data": [
                [
                    "2026-05-26 10:00:00",
                    390,
                    391,
                    389,
                    390.5,
                    123456,
                    12345678.9,
                ]
            ],
        }
    }


def test_fetch_ticker_retries_after_http_error(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))

        if len(calls) == 1:
            raise httpx.HTTPError("temporary failure")

        return FakeResponse(make_moex_payload())

    monkeypatch.setattr(moex_client_module.httpx, "get", fake_get)
    monkeypatch.setattr(moex_client_module, "sleep", lambda seconds: None)

    client = MoexClient(base_url="https://example.test", engine="stock", market="shares", board="TQBR")

    result = client.fetch_ticker("sber")

    assert len(calls) == 2
    assert result["secid"] == "SBER"
    assert result["short_name"] == "Sber"
    assert result["price"] == Decimal("123.45")


def test_fetch_ticker_raises_moex_client_error_after_http_retries(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        raise httpx.HTTPError("network is down")

    monkeypatch.setattr(moex_client_module.httpx, "get", fake_get)
    monkeypatch.setattr(moex_client_module, "sleep", lambda seconds: None)

    client = MoexClient(base_url="https://example.test", engine="stock", market="shares", board="TQBR")

    with pytest.raises(MoexClientError, match="MOEX request failed after 2 attempts"):
        client.fetch_ticker("SBER")

    assert len(calls) == 2


def test_fetch_ticker_raises_moex_client_error_for_invalid_json(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse(json_error=ValueError("invalid json"))

    monkeypatch.setattr(moex_client_module.httpx, "get", fake_get)
    monkeypatch.setattr(moex_client_module, "sleep", lambda seconds: None)

    client = MoexClient(base_url="https://example.test", engine="stock", market="shares", board="TQBR")

    with pytest.raises(MoexClientError, match="MOEX returned invalid JSON after 2 attempts"):
        client.fetch_ticker("SBER")

    assert len(calls) == 2


def test_fetch_candles_parses_columns_and_data(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse(make_moex_candles_payload())

    monkeypatch.setattr(moex_client_module.httpx, "get", fake_get)

    client = MoexClient(
        base_url="https://example.test",
        engine="stock",
        market="shares",
        board="TQBR",
    )

    result = client.fetch_candles(
        secid="sber",
        interval="10m",
        from_date="2026-05-20",
        till_date="2026-05-27",
    )

    assert len(calls) == 1

    args, kwargs = calls[0]

    assert args[0].endswith("/engines/stock/markets/shares/securities/SBER/candles.json")
    assert kwargs["params"]["interval"] == "10"
    assert kwargs["params"]["from"] == "2026-05-20"
    assert kwargs["params"]["till"] == "2026-05-27"

    assert result == [
        {
            "begin": "2026-05-26 10:00:00",
            "open": Decimal("390"),
            "high": Decimal("391"),
            "low": Decimal("389"),
            "close": Decimal("390.5"),
            "volume": Decimal("123456"),
            "value": Decimal("12345678.9"),
        }
    ]
