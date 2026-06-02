import logging
from datetime import timedelta
from typing import Any

from app.modules.hypotheses.report_composer import compose_hypothesis_report
from app.modules.hypotheses.schemas import HypothesisAnalyzeRequest
from app.modules.market.moex_client import MoexClient, MoexClientError


logger = logging.getLogger(__name__)


def analyze_hypothesis(request: HypothesisAnalyzeRequest) -> dict[str, Any]:
    normalized_main_ticker = request.main_ticker.strip().upper()
    normalized_benchmark_ticker = (
        request.benchmark_ticker.strip().upper()
        if request.benchmark_ticker
        else None
    )
    tickers_to_fetch = [normalized_main_ticker]

    if normalized_benchmark_ticker is not None:
        tickers_to_fetch.append(normalized_benchmark_ticker)

    from_date = request.event_date - timedelta(days=request.window_before_days)
    till_date = request.event_date + timedelta(days=request.window_after_days)
    candles_by_ticker = _fetch_candles_by_ticker(
        tickers=tickers_to_fetch,
        interval=request.interval,
        from_date=from_date.isoformat(),
        till_date=till_date.isoformat(),
    )

    return compose_hypothesis_report(
        event_type=request.event_type,
        event_direction=request.event_direction,
        sector=request.sector,
        main_ticker=normalized_main_ticker,
        benchmark_ticker=normalized_benchmark_ticker,
        user_hypothesis_text=request.user_hypothesis_text,
        event_date=request.event_date,
        candles_by_ticker=candles_by_ticker,
        expected_direction=request.expected_direction,
    )


def _fetch_candles_by_ticker(
    tickers: list[str],
    interval: str,
    from_date: str,
    till_date: str,
) -> dict[str, list[dict[str, Any]]]:
    moex_client = MoexClient()
    candles_by_ticker = {}

    for secid in tickers:
        try:
            candles_by_ticker[secid] = moex_client.fetch_candles(
                secid=secid,
                interval=interval,
                from_date=from_date,
                till_date=till_date,
            )
        except MoexClientError as error:
            logger.warning(
                "Hypothesis candles fetch failed: secid=%s error=%s",
                secid,
                error,
            )
            candles_by_ticker[secid] = []

    return candles_by_ticker
