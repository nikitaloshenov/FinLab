from decimal import Decimal, InvalidOperation
from time import sleep
from typing import Any

import httpx

from app.core.config import settings


class MoexClientError(Exception):
    pass


class MoexTickerNotFoundError(MoexClientError):
    pass


class MoexClient:
    def __init__(
        self,
        base_url: str = settings.moex_base_url,
        engine: str = settings.moex_default_engine,
        market: str = settings.moex_default_market,
        board: str = settings.moex_default_board,
    ):
        self.base_url = base_url.rstrip("/")
        self.engine = engine
        self.market = market
        self.board = board

    def fetch_ticker(self, secid: str) -> dict[str, Any]:
        normalized_secid = secid.upper().strip()

        url = (
            f"{self.base_url}"
            f"/engines/{self.engine}"
            f"/markets/{self.market}"
            f"/boards/{self.board}"
            f"/securities/{normalized_secid}.json"
        )

        params = {
            "iss.meta": "off",
            "iss.only": "securities,marketdata",
            "lang": "ru",
        }

        payload = self._get_json_with_retries(url=url, params=params)

        securities = self._table_to_dicts(payload.get("securities", {}))
        marketdata = self._table_to_dicts(payload.get("marketdata", {}))

        if not securities:
            raise MoexTickerNotFoundError(
                f"Ticker {normalized_secid} not found on MOEX"
            )

        security = securities[0]
        market_row = self._find_market_row(marketdata, normalized_secid)

        return {
            "secid": security.get("SECID") or normalized_secid,
            "short_name": security.get("SHORTNAME"),
            "name": security.get("SECNAME"),
            "board": security.get("BOARDID") or self.board,
            "market": self.market,
            "engine": self.engine,
            "currency": self._extract_currency(security, market_row),
            "price": self._extract_price(market_row),
        }

    def _get_json_with_retries(
        self,
        url: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        attempts = 2

        for attempt in range(1, attempts + 1):
            try:
                response = httpx.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as error:
                if attempt == attempts:
                    raise MoexClientError(
                        f"MOEX request failed after {attempts} attempts: {error}"
                    ) from error

                sleep(0.5)
            except ValueError as error:
                if attempt == attempts:
                    raise MoexClientError(
                        "MOEX returned invalid JSON after "
                        f"{attempts} attempts: {error}"
                    ) from error

                sleep(0.5)

        raise MoexClientError(
            f"MOEX request failed after {attempts} attempts: unknown error"
        )

    def _table_to_dicts(self, table: dict[str, Any]) -> list[dict[str, Any]]:
        columns = table.get("columns") or []
        rows = table.get("data") or []

        return [dict(zip(columns, row)) for row in rows]

    def _find_market_row(
        self,
        rows: list[dict[str, Any]],
        secid: str,
    ) -> dict[str, Any] | None:
        for row in rows:
            if row.get("SECID") == secid and row.get("BOARDID") == self.board:
                return row

        for row in rows:
            if row.get("SECID") == secid:
                return row

        return rows[0] if rows else None

    def _extract_price(self, market_row: dict[str, Any] | None) -> Decimal | None:
        if not market_row:
            return None

        for field_name in ("LAST", "MARKETPRICE", "LCLOSE", "PREVPRICE"):
            value = market_row.get(field_name)
            decimal_value = self._to_decimal(value)

            if decimal_value is not None:
                return decimal_value

        return None

    def _extract_currency(
        self,
        security: dict[str, Any],
        market_row: dict[str, Any] | None,
    ) -> str | None:
        if market_row and market_row.get("CURRENCYID"):
            return market_row.get("CURRENCYID")

        if security.get("FACEUNIT"):
            return security.get("FACEUNIT")

        return None

    def _to_decimal(self, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
