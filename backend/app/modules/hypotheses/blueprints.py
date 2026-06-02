from __future__ import annotations

from copy import deepcopy
from typing import Any


class UnsupportedHypothesisBlueprintError(Exception):
    pass


BlueprintKey = tuple[str, str, str]
Blueprint = dict[str, Any]


COMMON_LIMITATIONS = [
    "Этот сценарий не является прогнозом движения цены.",
    "Материал не является инвестиционной рекомендацией.",
    "Эффект события уже мог быть заложен рынком в цену.",
    "Без анализа отчетности и новостей вывод ограничен.",
    "Историческая реакция цены не доказывает причинно-следственную связь.",
    "Для более качественного вывода нужно сравнение с IMOEX, секторной динамикой и макроконтекстом.",
]


RATE_CUT_ALERT_TEMPLATES = [
    {
        "id": "breakout_after_confirmation",
        "title": "Пробой после подтверждения",
        "description": "Отслеживать движение выше недавнего уровня подтверждения после стабилизации реакции на событие.",
        "condition_hint": "above",
        "level_source": "recent_high",
    },
    {
        "id": "return_to_event_price",
        "title": "Возврат к цене события",
        "description": "Отслеживать, вернется ли тикер выше цены события.",
        "condition_hint": "above",
        "level_source": "event_price",
    },
    {
        "id": "trend_failure_below_recent_low",
        "title": "Срыв тренда ниже недавнего минимума",
        "description": "Отслеживать движение ниже недавнего минимума, если ожидаемая поддерживающая реакция ослабевает.",
        "condition_hint": "below",
        "level_source": "recent_low",
    },
]


RATE_HIKE_ALERT_TEMPLATES = [
    {
        "id": "breakdown_risk_level",
        "title": "Риск пробоя уровня поддержки",
        "description": "Отслеживать движение ниже недавнего уровня поддержки после более жестких сигналов политики.",
        "condition_hint": "below",
        "level_source": "recent_low",
    },
    {
        "id": "recovery_above_event_price",
        "title": "Восстановление выше цены события",
        "description": "Отслеживать, восстановится ли тикер выше цены события после первой реакции.",
        "condition_hint": "above",
        "level_source": "event_price",
    },
    {
        "id": "volatility_watch",
        "title": "Наблюдение за волатильностью",
        "description": "Использовать пользовательский уровень, чтобы отслеживать выход волатильности за выбранный диапазон.",
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
        "title": "Снижение ключевой ставки: влияние на банки",
        "summary": (
            "Снижение ключевой ставки может поддержать банки через более дешевое фондирование, "
            "оживление спроса на кредиты и рост аппетита к риску. Эффект зависит от маржи, "
            "ожиданий рынка и качества кредитного портфеля."
        ),
        "mechanisms": [
            {
                "id": "funding_cost",
                "name": "Стоимость фондирования",
                "direction": "positive",
                "importance": "high",
                "explanation": "Более низкая ставка со временем может снизить стоимость обязательств банка.",
                "supports_hypothesis_when": "Стоимость депозитов и рыночного фондирования снижается быстрее доходности активов.",
                "weakens_hypothesis_when": "Стоимость фондирования остается высокой или конкуренция за депозиты усиливается.",
            },
            {
                "id": "credit_demand",
                "name": "Спрос на кредиты",
                "direction": "positive",
                "importance": "medium",
                "explanation": "Более низкие ставки могут повысить доступность кредитов для заемщиков.",
                "supports_hypothesis_when": "Розничный и корпоративный спрос на кредиты начинает восстанавливаться.",
                "weakens_hypothesis_when": "Заемщики остаются осторожными из-за доходов, санкций или макрорисков.",
            },
            {
                "id": "net_interest_margin",
                "name": "Чистая процентная маржа",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Снижение ставки помогает со стоимостью фондирования, но доходность активов тоже может снижаться.",
                "supports_hypothesis_when": "Обязательства переоцениваются быстрее кредитного портфеля и портфеля ценных бумаг.",
                "weakens_hypothesis_when": "Доходность активов снижается быстрее стоимости фондирования.",
            },
            {
                "id": "risk_appetite",
                "name": "Аппетит к риску",
                "direction": "positive",
                "importance": "medium",
                "explanation": "Более низкие ставки могут повысить интерес к акциям относительно депозитов и облигаций.",
                "supports_hypothesis_when": "Рыночная ширина улучшается, а финансовый сектор выглядит сильнее IMOEX.",
                "weakens_hypothesis_when": "Деньги остаются в защитных инструментах, а приток в сектор слабый.",
            },
            {
                "id": "market_expectations",
                "name": "Ожидания рынка",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Реакция зависит от того, чего инвесторы ожидали до решения.",
                "supports_hypothesis_when": "Снижение сильнее ожиданий или сигнал регулятора мягче консенсуса.",
                "weakens_hypothesis_when": "Решение уже было учтено рынком или комментарий остается осторожным.",
            },
        ],
        "arguments_for": [
            {
                "type": "fundamental_logic",
                "message": "Банки могут получить поддержку, если стоимость фондирования снижается, а спрос на кредиты улучшается.",
            },
            {
                "type": "market_context",
                "message": "Более низкие ставки могут поддержать спрос на акции относительно депозитов и облигаций.",
            },
        ],
        "arguments_against": [
            {
                "type": "risk",
                "message": "Маржа может сжаться, если доходность активов снижается быстрее стоимости обязательств.",
            },
            {
                "type": "market_context",
                "message": "Если снижение ставки ожидалось заранее, реакция рынка может быть умеренной.",
            },
        ],
        "watch_factors": [
            {
                "id": "central_bank_guidance",
                "name": "Сигнал регулятора",
                "why_it_matters": "Комментарий регулятора может быть важнее самого изменения ставки.",
                "signal_positive": "Более мягкий сигнал и пространство для дальнейшего смягчения.",
                "signal_negative": "Осторожный тон и акцент на инфляционных рисках.",
            },
            {
                "id": "credit_growth",
                "name": "Рост кредитного портфеля",
                "why_it_matters": "Рост кредитов напрямую влияет на прибыль банков.",
                "signal_positive": "Розничный и корпоративный портфели начинают расти.",
                "signal_negative": "Рост кредитов остается слабым или замедляется.",
            },
            {
                "id": "sector_relative_strength",
                "name": "Относительная сила сектора",
                "why_it_matters": "Относительная динамика помогает отделить секторный эффект от общего движения рынка.",
                "signal_positive": "Банки выглядят сильнее IMOEX после события.",
                "signal_negative": "Банки отстают от IMOEX несмотря на снижение ставки.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_CUT_ALERT_TEMPLATES,
        "disclaimer": "Используйте это как исследовательский чеклист, а не как торговую инструкцию.",
    },
    (
        "key_rate",
        "rate_hike",
        "banks",
    ): {
        "event_type": "key_rate",
        "event_direction": "rate_hike",
        "sector": "banks",
        "title": "Повышение ключевой ставки: влияние на банки",
        "summary": (
            "Повышение ключевой ставки может давить на банки через замедление кредитования "
            "и риски качества активов. Влияние на маржу может быть смешанным и зависит "
            "от переоценки активов и обязательств."
        ),
        "mechanisms": [
            {
                "id": "funding_cost_pressure",
                "name": "Давление на стоимость фондирования",
                "direction": "negative",
                "importance": "high",
                "explanation": "Более высокие ставки могут повысить стоимость депозитов и рыночного фондирования.",
                "supports_hypothesis_when": "Стоимость депозитов быстро растет, а конкуренция за фондирование усиливается.",
                "weakens_hypothesis_when": "Банки переоценивают активы быстрее обязательств.",
            },
            {
                "id": "credit_slowdown",
                "name": "Замедление кредитования",
                "direction": "negative",
                "importance": "high",
                "explanation": "Более дорогие кредиты могут снизить спрос на новые займы.",
                "supports_hypothesis_when": "Выдачи розничных и корпоративных кредитов замедляются после решения.",
                "weakens_hypothesis_when": "Спрос на кредиты остается устойчивым в приоритетных сегментах.",
            },
            {
                "id": "asset_quality_risk",
                "name": "Риск качества активов",
                "direction": "negative",
                "importance": "high",
                "explanation": "Более высокая стоимость обслуживания долга может усилить давление на слабых заемщиков.",
                "supports_hypothesis_when": "Растут просрочки, реструктуризации или риски резервирования.",
                "weakens_hypothesis_when": "Качество кредитов остается стабильным, а резервы контролируемыми.",
            },
            {
                "id": "net_interest_margin_mixed_effect",
                "name": "Смешанный эффект для процентной маржи",
                "direction": "mixed",
                "importance": "medium",
                "explanation": "Повышение ставки может увеличить доходность активов, но также повышает стоимость фондирования.",
                "supports_hypothesis_when": "Давление стоимости фондирования сильнее выгоды от переоценки активов.",
                "weakens_hypothesis_when": "Переоценка активов компенсирует рост стоимости фондирования.",
            },
            {
                "id": "market_expectations",
                "name": "Ожидания рынка",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Реакция зависит от того, ожидались ли повышение ставки и тон комментария.",
                "supports_hypothesis_when": "Повышение или жесткий сигнал сильнее ожиданий рынка.",
                "weakens_hypothesis_when": "Решение ожидалось, а комментарий менее жесткий.",
            },
        ],
        "arguments_for": [
            {
                "type": "fundamental_logic",
                "message": "Более высокие ставки могут замедлить кредитование и усилить давление на заемщиков.",
            },
            {
                "type": "risk",
                "message": "Риски качества активов могут давить на оценку банковского сектора.",
            },
        ],
        "arguments_against": [
            {
                "type": "fundamental_logic",
                "message": "Часть банков может защитить маржу, если активы переоцениваются быстрее обязательств.",
            },
            {
                "type": "market_context",
                "message": "Если повышение ожидалось заранее, реакция может быть ограниченной.",
            },
        ],
        "watch_factors": [
            {
                "id": "deposit_rates",
                "name": "Ставки по депозитам",
                "why_it_matters": "Конкуренция за депозиты влияет на стоимость фондирования.",
                "signal_positive": "Стоимость депозитов остается контролируемой.",
                "signal_negative": "Ставки по депозитам быстро растут по сектору.",
            },
            {
                "id": "asset_quality",
                "name": "Качество активов",
                "why_it_matters": "Кредитные потери могут перекрыть выгоду по доходам.",
                "signal_positive": "Показатели просрочки остаются стабильными.",
                "signal_negative": "Показатели резервов или просроченной задолженности ухудшаются.",
            },
            {
                "id": "sector_relative_strength",
                "name": "Относительная сила сектора",
                "why_it_matters": "Относительная слабость может подтвердить секторное давление.",
                "signal_positive": "Банки держатся лучше IMOEX.",
                "signal_negative": "Банки отстают от IMOEX после решения.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_HIKE_ALERT_TEMPLATES,
        "disclaimer": "Используйте это как исследовательский чеклист, а не как торговую инструкцию.",
    },
    (
        "key_rate",
        "rate_cut",
        "broad_market",
    ): {
        "event_type": "key_rate",
        "event_direction": "rate_cut",
        "sector": "broad_market",
        "title": "Снижение ключевой ставки: влияние на широкий рынок",
        "summary": (
            "Снижение ставки может поддержать оценку рынка акций через более низкую ставку дисконтирования, "
            "рост аппетита к риску и меньшую конкуренцию со стороны денежных инструментов."
        ),
        "mechanisms": [
            {
                "id": "discount_rate",
                "name": "Ставка дисконтирования",
                "direction": "positive",
                "importance": "high",
                "explanation": "Более низкие ставки могут повысить текущую стоимость будущих денежных потоков.",
                "supports_hypothesis_when": "Сектора с длинным горизонтом и широкие индексы улучшают динамику после события.",
                "weakens_hypothesis_when": "Инфляционные риски удерживают требуемую доходность на высоком уровне.",
            },
            {
                "id": "risk_appetite",
                "name": "Аппетит к риску",
                "direction": "positive",
                "importance": "high",
                "explanation": "Смягчение политики может сделать риск акций более привлекательным.",
                "supports_hypothesis_when": "Рыночная ширина и обороты улучшаются.",
                "weakens_hypothesis_when": "Защитные потоки доминируют несмотря на снижение ставки.",
            },
            {
                "id": "bond_yield_competition",
                "name": "Конкуренция доходности облигаций",
                "direction": "positive",
                "importance": "medium",
                "explanation": "Более низкая доходность облигаций может снизить привлекательность альтернатив с фиксированным доходом.",
                "supports_hypothesis_when": "Доходности облигаций снижаются, а акции становятся относительно привлекательнее.",
                "weakens_hypothesis_when": "Доходности остаются высокими из-за инфляции или бюджетных рисков.",
            },
            {
                "id": "earnings_expectations",
                "name": "Ожидания по прибыли",
                "direction": "mixed",
                "importance": "medium",
                "explanation": "Более низкие ставки могут поддержать спрос, но прибыль зависит от фундаментальных факторов секторов.",
                "supports_hypothesis_when": "Ожидания по циклическим секторам улучшаются на фоне более мягких финансовых условий.",
                "weakens_hypothesis_when": "Пересмотры ожиданий по прибыли остаются слабыми.",
            },
            {
                "id": "market_expectations",
                "name": "Ожидания рынка",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Реакция широкого рынка зависит от того, насколько смягчение уже ожидалось.",
                "supports_hypothesis_when": "Решение или сигнал мягче консенсуса.",
                "weakens_hypothesis_when": "Снижение ставки уже было учтено в ценах.",
            },
        ],
        "arguments_for": [
            {
                "type": "market_context",
                "message": "Более низкие ставки могут улучшить спрос на акции относительно депозитов и облигаций.",
            },
            {
                "type": "fundamental_logic",
                "message": "Более мягкие финансовые условия могут поддержать оценочные мультипликаторы.",
            },
        ],
        "arguments_against": [
            {
                "type": "risk",
                "message": "Инфляция, валютное давление или слабая прибыль могут компенсировать поддержку оценки.",
            },
            {
                "type": "market_context",
                "message": "Широко ожидаемое снижение может иметь ограниченный дополнительный эффект.",
            },
        ],
        "watch_factors": [
            {
                "id": "imoex_trend",
                "name": "Тренд IMOEX",
                "why_it_matters": "Индекс показывает, реакция широкая или локальная.",
                "signal_positive": "IMOEX удерживается выше уровня события.",
                "signal_negative": "IMOEX теряет уровень события после решения.",
            },
            {
                "id": "bond_yields",
                "name": "Доходности облигаций",
                "why_it_matters": "Доходности влияют на альтернативы акциям и ставку дисконтирования.",
                "signal_positive": "Доходности снижаются после решения.",
                "signal_negative": "Доходности остаются высокими или отскакивают.",
            },
            {
                "id": "market_breadth",
                "name": "Рыночная ширина",
                "why_it_matters": "Ширина рынка помогает понять, насколько движение распространено.",
                "signal_positive": "В движении участвует больше секторов.",
                "signal_negative": "Движение сосредоточено в нескольких крупных бумагах.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_CUT_ALERT_TEMPLATES,
        "disclaimer": "Используйте это как исследовательский чеклист, а не как торговую инструкцию.",
    },
    (
        "key_rate",
        "rate_hike",
        "broad_market",
    ): {
        "event_type": "key_rate",
        "event_direction": "rate_hike",
        "sector": "broad_market",
        "title": "Повышение ключевой ставки: влияние на широкий рынок",
        "summary": (
            "Повышение ставки может давить на широкий рынок акций через более высокую ставку дисконтирования, "
            "ужесточение финансовых условий и рост конкуренции со стороны инструментов с фиксированным доходом."
        ),
        "mechanisms": [
            {
                "id": "discount_rate_pressure",
                "name": "Давление ставки дисконтирования",
                "direction": "negative",
                "importance": "high",
                "explanation": "Более высокие ставки могут снижать текущую стоимость будущих денежных потоков.",
                "supports_hypothesis_when": "Сектора, чувствительные к оценке, отстают после события.",
                "weakens_hypothesis_when": "Улучшение ожиданий по прибыли компенсирует давление ставки дисконтирования.",
            },
            {
                "id": "risk_appetite_decline",
                "name": "Снижение аппетита к риску",
                "direction": "negative",
                "importance": "high",
                "explanation": "Более жесткая политика может снижать интерес к риску акций.",
                "supports_hypothesis_when": "Рыночная ширина ухудшается, а денежные инструменты притягивают потоки.",
                "weakens_hypothesis_when": "Спрос на акции остается широким и устойчивым.",
            },
            {
                "id": "bond_yield_competition",
                "name": "Конкуренция доходности облигаций",
                "direction": "negative",
                "importance": "medium",
                "explanation": "Более высокие доходности могут сделать инструменты с фиксированным доходом привлекательнее.",
                "supports_hypothesis_when": "Доходности облигаций растут после решения.",
                "weakens_hypothesis_when": "Доходности снижаются, потому что повышение ожидалось или сигнал смягчился.",
            },
            {
                "id": "earnings_pressure",
                "name": "Давление на прибыль",
                "direction": "negative",
                "importance": "medium",
                "explanation": "Более высокая стоимость финансирования может влиять на спрос и прибыль компаний.",
                "supports_hypothesis_when": "Аналитики снижают ожидания по прибыли для чувствительных к ставке секторов.",
                "weakens_hypothesis_when": "Сырьевые, валютные или ценовые факторы поддерживают прибыль.",
            },
            {
                "id": "market_expectations",
                "name": "Ожидания рынка",
                "direction": "mixed",
                "importance": "high",
                "explanation": "Реакция зависит от того, стало ли повышение ставки и комментарий неожиданностью для инвесторов.",
                "supports_hypothesis_when": "Решение или сигнал жестче ожиданий.",
                "weakens_hypothesis_when": "Повышение ожидалось, а комментарий менее жесткий.",
            },
        ],
        "arguments_for": [
            {
                "type": "market_context",
                "message": "Более высокие ставки могут усилить конкуренцию со стороны депозитов и облигаций.",
            },
            {
                "type": "risk",
                "message": "Более жесткие финансовые условия могут давить на оценочные мультипликаторы.",
            },
        ],
        "arguments_against": [
            {
                "type": "fundamental_logic",
                "message": "Некоторые сектора могут компенсировать давление ставки ростом прибыли или сырьевой поддержкой.",
            },
            {
                "type": "market_context",
                "message": "Если повышение ожидалось заранее, реакция индекса может быть умеренной.",
            },
        ],
        "watch_factors": [
            {
                "id": "imoex_trend",
                "name": "Тренд IMOEX",
                "why_it_matters": "Индекс помогает понять, насколько давление распространено по рынку.",
                "signal_positive": "IMOEX восстанавливается выше уровня события.",
                "signal_negative": "IMOEX остается ниже уровня события.",
            },
            {
                "id": "bond_yields",
                "name": "Доходности облигаций",
                "why_it_matters": "Растущие доходности могут конкурировать с ожидаемой доходностью акций.",
                "signal_positive": "Доходности стабилизируются после решения.",
                "signal_negative": "Доходности продолжают расти после решения.",
            },
            {
                "id": "ruble_pressure",
                "name": "Рубль и инфляционное давление",
                "why_it_matters": "Валютный и инфляционный контекст влияет на ожидания по дальнейшей политике.",
                "signal_positive": "Рубль и инфляционные ожидания стабилизируются.",
                "signal_negative": "Валютное давление или инфляционные ожидания растут.",
            },
        ],
        "limitations": COMMON_LIMITATIONS,
        "suggested_alert_templates": RATE_HIKE_ALERT_TEMPLATES,
        "disclaimer": "Используйте это как исследовательский чеклист, а не как торговую инструкцию.",
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
