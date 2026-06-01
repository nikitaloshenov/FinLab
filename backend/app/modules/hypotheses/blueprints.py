from __future__ import annotations

from copy import deepcopy
from typing import Any


class UnsupportedHypothesisBlueprintError(Exception):
    pass


BlueprintKey = tuple[str, str, str]
Blueprint = dict[str, Any]


COMMON_LIMITATIONS = [
    "This blueprint is not a forecast for future price movement.",
    "This material is not an investment recommendation.",
    "The event effect may already be priced in by the market.",
    "Without company reports and news analysis, the conclusion is limited.",
    "Historical price reaction, when added, does not prove causality.",
    "A higher-quality result needs comparison with IMOEX, sector dynamics, and macro context.",
]


RATE_CUT_ALERT_TEMPLATES = [
    {
        "id": "breakout_after_confirmation",
        "title": "Breakout after confirmation",
        "description": "Watch for a move above a recent confirmation level after the event reaction settles.",
        "condition_hint": "above",
        "level_source": "recent_high",
    },
    {
        "id": "return_to_event_price",
        "title": "Return to event price",
        "description": "Watch whether the ticker returns above the event reference price.",
        "condition_hint": "above",
        "level_source": "event_price",
    },
    {
        "id": "trend_failure_below_recent_low",
        "title": "Trend failure below recent low",
        "description": "Watch for a move below a recent low if the expected supportive reaction fades.",
        "condition_hint": "below",
        "level_source": "recent_low",
    },
]


RATE_HIKE_ALERT_TEMPLATES = [
    {
        "id": "breakdown_risk_level",
        "title": "Breakdown risk level",
        "description": "Watch for a move below a recent support level after tighter policy signals.",
        "condition_hint": "below",
        "level_source": "recent_low",
    },
    {
        "id": "recovery_above_event_price",
        "title": "Recovery above event price",
        "description": "Watch whether the ticker recovers above the event reference price after the first reaction.",
        "condition_hint": "above",
        "level_source": "event_price",
    },
    {
        "id": "volatility_watch",
        "title": "Volatility watch",
        "description": "Use a user-defined level to track whether post-event volatility expands beyond a chosen range.",
        "condition_hint": "above",
        "level_source": "user_defined",
    },
]


BLUEPRINTS: dict[BlueprintKey, Blueprint] = {
    (
        "key_rate",
        "rate_cut",
        "banks",
    ): {
        "event_type": "key_rate",
        "event_direction": "rate_cut",
        "sector": "banks",
        "title": "Key rate cut impact blueprint for banks",
        "summary": (
            "A lower key rate can support banks through cheaper funding, better credit demand, "
            "and improved risk appetite, but the effect depends on margins, expectations, and asset quality."
        ),
        "mechanisms": [
            {
                "id": "funding_cost",
                "name": "Funding cost",
                "direction": "positive",
                "importance": "high",
                "explanation": "Lower policy rates may reduce the cost of liabilities over time.",
                "supports_hypothesis_when": "Deposit and wholesale funding costs decline faster than asset yields.",
                "weakens_hypothesis_when": "Funding costs remain sticky or competition for deposits stays high.",
            },
            {
                "id": "credit_demand",
                "name": "Credit demand",
                "direction": "positive",
                "importance": "medium",
                "explanation": "Lower rates can improve affordability for borrowers and support loan growth.",
                "supports_hypothesis_when": "Retail and corporate loan demand starts to recover.",
                "weakens_hypothesis_when": "Borrowers remain cautious because of income, sanctions, or macro risks.",
            },
            {
                "id": "net_interest_margin",
                "name": "Net interest margin",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Rate cuts can help funding costs, but asset yields may also reprice lower.",
                "supports_hypothesis_when": "Liabilities reprice faster than loan books and securities portfolios.",
                "weakens_hypothesis_when": "Asset yields compress faster than funding costs.",
            },
            {
                "id": "risk_appetite",
                "name": "Risk appetite",
                "direction": "positive",
                "importance": "medium",
                "explanation": "Lower rates can increase demand for equities compared with cash-like instruments.",
                "supports_hypothesis_when": "Market breadth improves and financial stocks outperform IMOEX.",
                "weakens_hypothesis_when": "Liquidity stays defensive and sector flows remain weak.",
            },
            {
                "id": "market_expectations",
                "name": "Market expectations",
                "direction": "mixed",
                "importance": "high",
                "explanation": "The reaction depends on what investors expected before the decision.",
                "supports_hypothesis_when": "The cut is larger or guidance is softer than consensus expected.",
                "weakens_hypothesis_when": "The decision was already expected or guidance stays cautious.",
            },
        ],
        "arguments_for": [
            {
                "type": "fundamental_logic",
                "message": "Banks may benefit if funding costs decline and loan demand improves.",
            },
            {
                "type": "market_context",
                "message": "Lower rates can support equity risk appetite relative to deposits and bonds.",
            },
        ],
        "arguments_against": [
            {
                "type": "risk",
                "message": "Margins can compress if asset yields reprice faster than liabilities.",
            },
            {
                "type": "market_context",
                "message": "If the cut was expected, the market reaction can be muted.",
            },
        ],
        "watch_factors": [
            {
                "id": "central_bank_guidance",
                "name": "Central bank guidance",
                "why_it_matters": "Guidance can matter more than the rate move itself.",
                "signal_positive": "Softer guidance and room for further easing.",
                "signal_negative": "Cautious guidance and inflation concerns.",
            },
            {
                "id": "credit_growth",
                "name": "Credit growth",
                "why_it_matters": "Loan growth is a direct driver of bank earnings.",
                "signal_positive": "Retail and corporate portfolios start expanding.",
                "signal_negative": "Loan growth remains weak or turns lower.",
            },
            {
                "id": "sector_relative_strength",
                "name": "Sector relative strength",
                "why_it_matters": "Relative performance helps separate sector effects from broad market movement.",
                "signal_positive": "Banks outperform IMOEX after the event.",
                "signal_negative": "Banks lag IMOEX despite the rate cut.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_CUT_ALERT_TEMPLATES,
        "disclaimer": "Use this as a research checklist, not as a trading instruction.",
    },
    (
        "key_rate",
        "rate_hike",
        "banks",
    ): {
        "event_type": "key_rate",
        "event_direction": "rate_hike",
        "sector": "banks",
        "title": "Key rate hike impact blueprint for banks",
        "summary": (
            "A higher key rate can pressure banks through slower credit growth and asset-quality risks, "
            "while margin impact can be mixed depending on liability and asset repricing."
        ),
        "mechanisms": [
            {
                "id": "funding_cost_pressure",
                "name": "Funding cost pressure",
                "direction": "negative",
                "importance": "high",
                "explanation": "Higher rates can increase deposit and market funding costs.",
                "supports_hypothesis_when": "Deposit costs rise quickly and competition for funding intensifies.",
                "weakens_hypothesis_when": "Banks reprice assets faster than liabilities.",
            },
            {
                "id": "credit_slowdown",
                "name": "Credit slowdown",
                "direction": "negative",
                "importance": "high",
                "explanation": "Higher borrowing costs can reduce new loan demand.",
                "supports_hypothesis_when": "Retail and corporate origination slows after the decision.",
                "weakens_hypothesis_when": "Loan demand stays resilient in priority segments.",
            },
            {
                "id": "asset_quality_risk",
                "name": "Asset quality risk",
                "direction": "negative",
                "importance": "high",
                "explanation": "Higher debt service costs may increase pressure on weaker borrowers.",
                "supports_hypothesis_when": "Delinquencies, restructurings, or provisioning risks increase.",
                "weakens_hypothesis_when": "Credit quality remains stable and provisions stay controlled.",
            },
            {
                "id": "net_interest_margin_mixed_effect",
                "name": "Net interest margin mixed effect",
                "direction": "mixed",
                "importance": "medium",
                "explanation": "Rate hikes may lift asset yields, but can also raise funding costs.",
                "supports_hypothesis_when": "Funding cost pressure dominates asset repricing benefits.",
                "weakens_hypothesis_when": "Asset repricing offsets higher funding costs.",
            },
            {
                "id": "market_expectations",
                "name": "Market expectations",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Reaction depends on whether the hike and guidance were expected.",
                "supports_hypothesis_when": "The hike or hawkish guidance is stronger than expected.",
                "weakens_hypothesis_when": "The decision was expected and commentary is less restrictive.",
            },
        ],
        "arguments_for": [
            {
                "type": "fundamental_logic",
                "message": "Higher rates can slow lending activity and increase pressure on borrowers.",
            },
            {
                "type": "risk",
                "message": "Asset-quality concerns can weigh on bank valuation multiples.",
            },
        ],
        "arguments_against": [
            {
                "type": "fundamental_logic",
                "message": "Some banks may protect margins if assets reprice faster than liabilities.",
            },
            {
                "type": "market_context",
                "message": "If the hike was expected, the reaction may be limited.",
            },
        ],
        "watch_factors": [
            {
                "id": "deposit_rates",
                "name": "Deposit rates",
                "why_it_matters": "Deposit competition affects funding costs.",
                "signal_positive": "Deposit costs remain controlled.",
                "signal_negative": "Deposit rates rise quickly across the sector.",
            },
            {
                "id": "asset_quality",
                "name": "Asset quality",
                "why_it_matters": "Credit losses can offset revenue benefits.",
                "signal_positive": "Delinquency metrics remain stable.",
                "signal_negative": "Provisioning or overdue loan metrics worsen.",
            },
            {
                "id": "sector_relative_strength",
                "name": "Sector relative strength",
                "why_it_matters": "Relative weakness can confirm sector-specific pressure.",
                "signal_positive": "Banks hold up better than IMOEX.",
                "signal_negative": "Banks underperform IMOEX after the decision.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_HIKE_ALERT_TEMPLATES,
        "disclaimer": "Use this as a research checklist, not as a trading instruction.",
    },
    (
        "key_rate",
        "rate_cut",
        "broad_market",
    ): {
        "event_type": "key_rate",
        "event_direction": "rate_cut",
        "sector": "broad_market",
        "title": "Key rate cut impact blueprint for broad market",
        "summary": (
            "A rate cut can support broad equity valuations through a lower discount rate, stronger risk appetite, "
            "and weaker competition from cash-like instruments."
        ),
        "mechanisms": [
            {
                "id": "discount_rate",
                "name": "Discount rate",
                "direction": "positive",
                "importance": "high",
                "explanation": "Lower rates can increase the present value of future cash flows.",
                "supports_hypothesis_when": "Long-duration sectors and broad indices improve after the event.",
                "weakens_hypothesis_when": "Inflation risk keeps required returns elevated.",
            },
            {
                "id": "risk_appetite",
                "name": "Risk appetite",
                "direction": "positive",
                "importance": "high",
                "explanation": "Easing policy can make equity risk more attractive.",
                "supports_hypothesis_when": "Market breadth and turnover improve.",
                "weakens_hypothesis_when": "Defensive flows dominate despite the cut.",
            },
            {
                "id": "bond_yield_competition",
                "name": "Bond yield competition",
                "direction": "positive",
                "importance": "medium",
                "explanation": "Lower yields can reduce the relative appeal of fixed-income alternatives.",
                "supports_hypothesis_when": "Bond yields decline and equities gain relative appeal.",
                "weakens_hypothesis_when": "Yields remain elevated because of inflation or fiscal concerns.",
            },
            {
                "id": "earnings_expectations",
                "name": "Earnings expectations",
                "direction": "mixed",
                "importance": "medium",
                "explanation": "Lower rates can help demand, but earnings still depend on sector fundamentals.",
                "supports_hypothesis_when": "Cyclical expectations improve with easier financial conditions.",
                "weakens_hypothesis_when": "Earnings revisions stay weak.",
            },
            {
                "id": "market_expectations",
                "name": "Market expectations",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Broad market reaction depends on how much easing was expected.",
                "supports_hypothesis_when": "The decision or guidance is softer than consensus expected.",
                "weakens_hypothesis_when": "The cut was already reflected in prices.",
            },
        ],
        "arguments_for": [
            {
                "type": "market_context",
                "message": "Lower rates can improve equity demand relative to deposits and bonds.",
            },
            {
                "type": "fundamental_logic",
                "message": "Easier financial conditions can support valuation multiples.",
            },
        ],
        "arguments_against": [
            {
                "type": "risk",
                "message": "Inflation, currency pressure, or weak earnings can offset valuation support.",
            },
            {
                "type": "market_context",
                "message": "A widely expected cut may have limited incremental impact.",
            },
        ],
        "watch_factors": [
            {
                "id": "imoex_trend",
                "name": "IMOEX trend",
                "why_it_matters": "The index shows whether the reaction is broad or isolated.",
                "signal_positive": "IMOEX holds above the event reference level.",
                "signal_negative": "IMOEX loses the event reference level after the decision.",
            },
            {
                "id": "bond_yields",
                "name": "Bond yields",
                "why_it_matters": "Yields influence equity alternatives and discount rates.",
                "signal_positive": "Yields decline after the decision.",
                "signal_negative": "Yields stay high or rebound.",
            },
            {
                "id": "market_breadth",
                "name": "Market breadth",
                "why_it_matters": "Breadth helps identify whether the move is broad-based.",
                "signal_positive": "More sectors participate in the move.",
                "signal_negative": "The move is concentrated in a few large names.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_CUT_ALERT_TEMPLATES,
        "disclaimer": "Use this as a research checklist, not as a trading instruction.",
    },
    (
        "key_rate",
        "rate_hike",
        "broad_market",
    ): {
        "event_type": "key_rate",
        "event_direction": "rate_hike",
        "sector": "broad_market",
        "title": "Key rate hike impact blueprint for broad market",
        "summary": (
            "A rate hike can pressure broad equities through higher discount rates, tighter financial conditions, "
            "and stronger competition from fixed-income alternatives."
        ),
        "mechanisms": [
            {
                "id": "discount_rate_pressure",
                "name": "Discount rate pressure",
                "direction": "negative",
                "importance": "high",
                "explanation": "Higher rates can lower the present value of future cash flows.",
                "supports_hypothesis_when": "Valuation-sensitive sectors underperform after the event.",
                "weakens_hypothesis_when": "Earnings upgrades offset the discount-rate pressure.",
            },
            {
                "id": "risk_appetite_decline",
                "name": "Risk appetite decline",
                "direction": "negative",
                "importance": "high",
                "explanation": "Tighter policy can reduce appetite for equity risk.",
                "supports_hypothesis_when": "Market breadth weakens and cash-like alternatives attract flows.",
                "weakens_hypothesis_when": "Equity demand remains broad and resilient.",
            },
            {
                "id": "bond_yield_competition",
                "name": "Bond yield competition",
                "direction": "negative",
                "importance": "medium",
                "explanation": "Higher yields can make fixed-income alternatives more attractive.",
                "supports_hypothesis_when": "Bond yields rise after the decision.",
                "weakens_hypothesis_when": "Bond yields fall because the hike was expected or guidance softens.",
            },
            {
                "id": "earnings_pressure",
                "name": "Earnings pressure",
                "direction": "negative",
                "importance": "medium",
                "explanation": "Higher financing costs can affect demand and corporate profitability.",
                "supports_hypothesis_when": "Analysts reduce earnings assumptions for rate-sensitive sectors.",
                "weakens_hypothesis_when": "Commodity, FX, or pricing factors support earnings.",
            },
            {
                "id": "market_expectations",
                "name": "Market expectations",
                "direction": "mixed",
                "importance": "high",
                "explanation": "The reaction depends on whether the hike and guidance surprised investors.",
                "supports_hypothesis_when": "The decision or guidance is more restrictive than expected.",
                "weakens_hypothesis_when": "The hike was expected and commentary is less restrictive.",
            },
        ],
        "arguments_for": [
            {
                "type": "market_context",
                "message": "Higher rates can increase competition from deposits and bonds.",
            },
            {
                "type": "risk",
                "message": "Tighter financial conditions can pressure valuation multiples.",
            },
        ],
        "arguments_against": [
            {
                "type": "fundamental_logic",
                "message": "Some sectors can offset rate pressure with earnings growth or commodity support.",
            },
            {
                "type": "market_context",
                "message": "If the hike was expected, the index reaction can be moderate.",
            },
        ],
        "watch_factors": [
            {
                "id": "imoex_trend",
                "name": "IMOEX trend",
                "why_it_matters": "The index confirms whether pressure is broad-based.",
                "signal_positive": "IMOEX recovers above the event reference level.",
                "signal_negative": "IMOEX stays below the event reference level.",
            },
            {
                "id": "bond_yields",
                "name": "Bond yields",
                "why_it_matters": "Rising yields can compete with equity returns.",
                "signal_positive": "Yields stabilize after the decision.",
                "signal_negative": "Yields continue rising after the decision.",
            },
            {
                "id": "ruble_pressure",
                "name": "Ruble and inflation pressure",
                "why_it_matters": "Currency and inflation context can shape further policy expectations.",
                "signal_positive": "Ruble and inflation expectations stabilize.",
                "signal_negative": "Currency pressure or inflation expectations rise.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_HIKE_ALERT_TEMPLATES,
        "disclaimer": "Use this as a research checklist, not as a trading instruction.",
    },
}


def list_supported_blueprints() -> list[dict[str, str]]:
    return [
        {
            "event_type": blueprint["event_type"],
            "event_direction": blueprint["event_direction"],
            "sector": blueprint["sector"],
            "title": blueprint["title"],
        }
        for blueprint in BLUEPRINTS.values()
    ]


def get_hypothesis_blueprint(
    event_type: str,
    event_direction: str,
    sector: str,
) -> Blueprint:
    key = (
        _normalize(event_type),
        _normalize(event_direction),
        _normalize(sector),
    )

    blueprint = BLUEPRINTS.get(key)

    if blueprint is None:
        raise UnsupportedHypothesisBlueprintError(
            "Unsupported hypothesis blueprint: "
            f"event_type={event_type}, event_direction={event_direction}, sector={sector}"
        )

    return deepcopy(blueprint)


def build_hypothesis_blueprint_report(
    event_type: str,
    event_direction: str,
    sector: str,
    tickers: list[str] | None = None,
    user_hypothesis_text: str | None = None,
) -> dict[str, Any]:
    blueprint = get_hypothesis_blueprint(
        event_type=event_type,
        event_direction=event_direction,
        sector=sector,
    )

    return {
        "blueprint": blueprint,
        "selected_tickers": _normalize_tickers(tickers),
        "user_hypothesis_text": user_hypothesis_text,
        "metadata": {
            "source": "rule_based_blueprint",
            "is_prediction": False,
            "requires_price_validation": True,
        },
    }


def _normalize(value: str) -> str:
    return value.strip().lower()


def _normalize_tickers(tickers: list[str] | None) -> list[str]:
    if tickers is None:
        return []

    return [
        ticker.strip().upper()
        for ticker in tickers
        if ticker and ticker.strip()
    ]

