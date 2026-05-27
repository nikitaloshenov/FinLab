import logging
from decimal import Decimal, InvalidOperation
from time import sleep
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class MoexClientError(Exception):
    pass


class MoexTickerNotFoundError(MoexClientError):
    pass


class MoexClient:
    CANDLE_INTERVALS = {
        "10m": 10,
        "1h": 60,
        "1d": 24,
    }

    def __init__(
        self,
        base_url: str = settings.moex_base_url,
        engine: str = settings.moex_default_engine,
        market: str = settings.moex_default_market,
        board: str = settings.moex_default_board,
        timeout_seconds: float = settings.moex_timeout_seconds,
        retry_attempts: int = settings.moex_retry_attempts,
        retry_delay_seconds: float = settings.moex_retry_delay_seconds,
    ):
        self.base_url = base_url.rstrip("/")
        self.engine = engine
        self.market = market
        self.board = board
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

    def fetch_ticker(self, secid: str) -> dict[str, Any]:
        normalized_secid = secid.upper().strip()

        logger.info(
            "Fetching MOEX ticker: secid=%s board=%s market=%s engine=%s",
            normalized_secid,
            self.board,
            self.market,
            self.engine,
        )

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

        price = self._extract_price(market_row)

        logger.info(
            "MOEX ticker fetched: secid=%s price=%s",
            normalized_secid,
            price,
        )

        return {
            "secid": security.get("SECID") or normalized_secid,
            "short_name": security.get("SHORTNAME"),
            "name": security.get("SECNAME"),
            "board": security.get("BOARDID") or self.board,
            "market": self.market,
            "engine": self.engine,
            "currency": self._extract_currency(security, market_row),
            "price": price,
        }

    def fetch_candles(
        self,
        secid: str,
        interval: str,
        from_date: str,
        till_date: str,
    ) -> list[dict[str, Any]]:
        normalized_secid = secid.upper().strip()
        moex_interval = self.CANDLE_INTERVALS[interval]

        logger.info(
            "Fetching MOEX candles: secid=%s interval=%s from=%s till=%s",
            normalized_secid,
            interval,
            from_date,
            till_date,
        )

        url = (
            f"{self.base_url}"
            f"/engines/{self.engine}"
            f"/markets/{self.market}"
            f"/securities/{normalized_secid}"
            f"/candles.json"
        )

        params = {
            "iss.meta": "off",
            "interval": str(moex_interval),
            "from": from_date,
            "till": till_date,
        }

        payload = self._get_json_with_retries(url=url, params=params)
        candle_rows = self._table_to_dicts(payload.get("candles", {}))

        candles = [
            candle
            for candle in (self._normalize_candle_row(row) for row in candle_rows)
            if candle is not None
        ]

        logger.info(
            "MOEX candles fetched: secid=%s interval=%s candles=%s",
            normalized_secid,
            interval,
            len(candles),
        )

        return candles

    def _get_json_with_retries(
        self,
        url: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = httpx.get(url, params=params, timeout=self.timeout_seconds)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as error:
                if attempt == self.retry_attempts:
                    logger.error(
                        "MOEX request failed after retries: attempts=%s error=%s",
                        self.retry_attempts,
                        error,
                    )
                    raise MoexClientError(
                        "MOEX request failed after "
                        f"{self.retry_attempts} attempts: {error}"
                    ) from error

                logger.warning(
                    "MOEX request failed, retrying: attempt=%s/%s error=%s",
                    attempt,
                    self.retry_attempts,
                    error,
                )
                sleep(self.retry_delay_seconds)
            except ValueError as error:
                if attempt == self.retry_attempts:
                    logger.error(
                        "MOEX returned invalid JSON after retries: attempts=%s error=%s",
                        self.retry_attempts,
                        error,
                    )
                    raise MoexClientError(
                        "MOEX returned invalid JSON after "
                        f"{self.retry_attempts} attempts: {error}"
                    ) from error

                logger.warning(
                    "MOEX returned invalid JSON, retrying: attempt=%s/%s error=%s",
                    attempt,
                    self.retry_attempts,
                    error,
                )
                sleep(self.retry_delay_seconds)

        logger.error(
            "MOEX request failed after retries: attempts=%s error=%s",
            self.retry_attempts,
            "unknown error",
        )
        raise MoexClientError(
            "MOEX request failed after "
            f"{self.retry_attempts} attempts: unknown error"
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

    def _normalize_candle_row(self, row: dict[str, Any]) -> dict[str, Any] | None:
        begin = row.get("begin") or row.get("BEGIN")
        open_price = self._to_decimal(row.get("open") or row.get("OPEN"))
        high_price = self._to_decimal(row.get("high") or row.get("HIGH"))
        low_price = self._to_decimal(row.get("low") or row.get("LOW"))
        close_price = self._to_decimal(row.get("close") or row.get("CLOSE"))

        if not begin or any(
            value is None
            for value in (open_price, high_price, low_price, close_price)
        ):
            return None

        return {
            "begin": begin,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": self._to_decimal(row.get("volume") or row.get("VOLUME"))
            or Decimal("0"),
            "value": self._to_decimal(row.get("value") or row.get("VALUE"))
            or Decimal("0"),
        }

    def _to_decimal(self, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
