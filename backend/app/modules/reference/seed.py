from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.market.models import Ticker
from app.modules.reference.constants import (
    BENCHMARK_SEEDS,
    CURATED_ISSUER_MAPPINGS,
    DATA_SOURCE_SEEDS,
    DEFAULT_SHARE_ASSET_TYPE,
    REFERENCE_VALID_FROM,
    SECTOR_SEEDS,
)
from app.modules.reference.models import (
    Benchmark,
    DataSource,
    Instrument,
    Issuer,
    IssuerSectorHistory,
    Sector,
)


@dataclass
class SeedCounter:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    conflicts: int = 0


@dataclass
class ReferenceSeedSummary:
    data_sources: SeedCounter = field(default_factory=SeedCounter)
    sectors: SeedCounter = field(default_factory=SeedCounter)
    instruments: SeedCounter = field(default_factory=SeedCounter)
    issuers: SeedCounter = field(default_factory=SeedCounter)
    issuer_sector_history: SeedCounter = field(default_factory=SeedCounter)
    benchmarks: SeedCounter = field(default_factory=SeedCounter)


def seed_reference_layer(db: Session) -> ReferenceSeedSummary:
    summary = ReferenceSeedSummary()

    seed_data_sources(db, summary.data_sources)
    seed_sectors(db, summary.sectors)
    backfill_instruments_from_tickers(db, summary.instruments)
    seed_curated_instruments(db, summary.instruments)
    apply_curated_issuer_sector_mapping(
        db,
        issuers_counter=summary.issuers,
        history_counter=summary.issuer_sector_history,
    )
    seed_benchmarks(db, summary.benchmarks)

    db.commit()
    return summary


def seed_data_sources(db: Session, counter: SeedCounter) -> dict[str, DataSource]:
    sources: dict[str, DataSource] = {}

    for seed in DATA_SOURCE_SEEDS:
        source = db.scalar(select(DataSource).where(DataSource.code == seed["code"]))

        if source is None:
            source = DataSource(**seed)
            db.add(source)
            counter.created += 1
        else:
            changed = _update_fields(
                source,
                {
                    "name": seed["name"],
                    "source_type": seed["source_type"],
                    "url": seed["url"],
                    "license_note": seed["license_note"],
                },
            )
            if changed:
                counter.updated += 1
            else:
                counter.skipped += 1

        sources[seed["code"]] = source

    db.flush()
    return sources


def seed_sectors(db: Session, counter: SeedCounter) -> dict[str, Sector]:
    sectors: dict[str, Sector] = {}

    for seed in SECTOR_SEEDS:
        sector = db.scalar(select(Sector).where(Sector.code == seed["code"]))

        if sector is None:
            sector = Sector(**seed)
            db.add(sector)
            counter.created += 1
        else:
            changed = _update_fields(
                sector,
                {
                    "name": seed["name"],
                    "description": seed["description"],
                    "is_active": True,
                },
            )
            if changed:
                counter.updated += 1
            else:
                counter.skipped += 1

        sectors[seed["code"]] = sector

    db.flush()
    return sectors


def backfill_instruments_from_tickers(db: Session, counter: SeedCounter) -> dict[str, Instrument]:
    instruments: dict[str, Instrument] = {}
    tickers = db.scalars(select(Ticker).order_by(Ticker.secid)).all()

    for ticker in tickers:
        instrument = db.scalar(
            select(Instrument).where(
                Instrument.engine == ticker.engine,
                Instrument.market == ticker.market,
                Instrument.board == ticker.board,
                Instrument.secid == ticker.secid,
            ),
        )

        values = {
            "name": ticker.name,
            "short_name": ticker.short_name or ticker.name or ticker.secid,
            "asset_type": DEFAULT_SHARE_ASSET_TYPE,
            "currency": ticker.currency,
            "is_active": True,
        }

        if instrument is None:
            instrument = Instrument(
                secid=ticker.secid,
                board=ticker.board,
                market=ticker.market,
                engine=ticker.engine,
                **values,
            )
            db.add(instrument)
            counter.created += 1
        else:
            changed = _update_fields(instrument, values)
            if changed:
                counter.updated += 1
            else:
                counter.skipped += 1

        instruments[ticker.secid] = instrument

    db.flush()
    return instruments


def seed_curated_instruments(db: Session, counter: SeedCounter) -> dict[str, Instrument]:
    instruments: dict[str, Instrument] = {}

    for mapping in CURATED_ISSUER_MAPPINGS:
        for secid in mapping["secids"]:
            instrument = db.scalar(
                select(Instrument).where(
                    Instrument.engine == "stock",
                    Instrument.market == "shares",
                    Instrument.board == "TQBR",
                    Instrument.secid == secid,
                ),
            )

            if instrument is None:
                values = {
                    "name": mapping["issuer_name"],
                    "short_name": secid,
                    "asset_type": DEFAULT_SHARE_ASSET_TYPE,
                    "currency": "RUB",
                    "is_active": True,
                }
                instrument = Instrument(
                    secid=secid,
                    board="TQBR",
                    market="shares",
                    engine="stock",
                    **values,
                )
                db.add(instrument)
                counter.created += 1
            else:
                values = {
                    "name": instrument.name or mapping["issuer_name"],
                    "short_name": instrument.short_name or secid,
                    "asset_type": instrument.asset_type or DEFAULT_SHARE_ASSET_TYPE,
                    "currency": instrument.currency or "RUB",
                    "is_active": True,
                }
                changed = _update_fields(instrument, values)
                if changed:
                    counter.updated += 1
                else:
                    counter.skipped += 1

            instruments[secid] = instrument

    db.flush()
    return instruments


def apply_curated_issuer_sector_mapping(
    db: Session,
    *,
    issuers_counter: SeedCounter,
    history_counter: SeedCounter,
) -> None:
    manual_seed_source = db.scalar(select(DataSource).where(DataSource.code == "manual_seed"))
    sector_by_code = {sector.code: sector for sector in db.scalars(select(Sector)).all()}
    seen_history_keys = {
        (history.issuer_id, history.sector_id, history.valid_from)
        for history in db.scalars(select(IssuerSectorHistory)).all()
    }

    for mapping in CURATED_ISSUER_MAPPINGS:
        sector = sector_by_code.get(mapping["sector_code"])
        if sector is None:
            continue

        instruments = db.scalars(
            select(Instrument).where(Instrument.secid.in_(mapping["secids"])),
        ).all()
        if not instruments:
            continue

        issuer = _resolve_mapping_issuer(
            db,
            instruments=instruments,
            issuer_name=mapping["issuer_name"],
            counter=issuers_counter,
        )

        for instrument in instruments:
            if instrument.issuer_id != issuer.id:
                instrument.issuer = issuer

        current_history = _get_current_sector_history(db, issuer_id=issuer.id)
        if current_history is not None:
            if current_history.sector_id == sector.id:
                history_counter.skipped += 1
            else:
                history_counter.conflicts += 1
            continue

        history_key = (issuer.id, sector.id, REFERENCE_VALID_FROM)
        if history_key in seen_history_keys:
            history_counter.skipped += 1
            continue

        db.add(
            IssuerSectorHistory(
                issuer=issuer,
                sector=sector,
                valid_from=REFERENCE_VALID_FROM,
                valid_to=None,
                source=manual_seed_source,
            )
        )
        seen_history_keys.add(history_key)
        history_counter.created += 1

    db.flush()


def seed_benchmarks(db: Session, counter: SeedCounter) -> dict[str, Benchmark]:
    benchmarks: dict[str, Benchmark] = {}
    sector_by_code = {sector.code: sector for sector in db.scalars(select(Sector)).all()}

    for seed in BENCHMARK_SEEDS:
        benchmark = db.scalar(select(Benchmark).where(Benchmark.code == seed["code"]))
        sector = sector_by_code.get(seed["sector_code"]) if seed["sector_code"] else None

        values = {
            "name": seed["name"],
            "benchmark_type": seed["benchmark_type"],
            "sector": sector,
            "description": seed["description"],
            "is_active": True,
        }

        if benchmark is None:
            benchmark = Benchmark(code=seed["code"], instrument_id=None, **values)
            db.add(benchmark)
            counter.created += 1
        else:
            changed = _update_fields(
                benchmark,
                {
                    "name": seed["name"],
                    "benchmark_type": seed["benchmark_type"],
                    "sector_id": sector.id if sector is not None else None,
                    "description": seed["description"],
                    "is_active": True,
                },
            )
            if changed:
                counter.updated += 1
            else:
                counter.skipped += 1

        benchmarks[seed["code"]] = benchmark

    db.flush()
    return benchmarks


def _get_or_create_issuer(db: Session, *, issuer_name: str, counter: SeedCounter) -> Issuer:
    issuer = db.scalar(select(Issuer).where(Issuer.name == issuer_name))

    if issuer is None:
        issuer = Issuer(name=issuer_name, short_name=issuer_name, country="RU", is_active=True)
        db.add(issuer)
        db.flush()
        counter.created += 1
        return issuer

    changed = _update_fields(
        issuer,
        {
            "short_name": issuer.short_name or issuer_name,
            "country": issuer.country or "RU",
            "is_active": True,
        },
    )
    if changed:
        counter.updated += 1
    else:
        counter.skipped += 1

    return issuer


def _resolve_mapping_issuer(
    db: Session,
    *,
    instruments: list[Instrument],
    issuer_name: str,
    counter: SeedCounter,
) -> Issuer:
    issuer = next((instrument.issuer for instrument in instruments if instrument.issuer), None)
    if issuer is None:
        return _get_or_create_issuer(db, issuer_name=issuer_name, counter=counter)

    _update_existing_issuer_defaults(
        issuer,
        issuer_name=issuer_name,
        counter=counter,
    )
    return issuer


def _update_existing_issuer_defaults(
    issuer: Issuer,
    *,
    issuer_name: str,
    counter: SeedCounter,
) -> None:
    changed = _update_fields(
        issuer,
        {
            "short_name": issuer.short_name or issuer_name,
            "country": issuer.country or "RU",
            "is_active": True,
        },
    )
    if changed:
        counter.updated += 1
    else:
        counter.skipped += 1


def _get_current_sector_history(
    db: Session,
    *,
    issuer_id: int,
) -> IssuerSectorHistory | None:
    return db.scalar(
        select(IssuerSectorHistory)
        .where(IssuerSectorHistory.issuer_id == issuer_id)
        .where(IssuerSectorHistory.valid_to.is_(None))
        .order_by(IssuerSectorHistory.valid_from.desc(), IssuerSectorHistory.id.desc())
        .limit(1),
    )


def _update_fields(instance: object, values: dict[str, object]) -> bool:
    changed = False

    for field_name, value in values.items():
        if getattr(instance, field_name) != value:
            setattr(instance, field_name, value)
            changed = True

    return changed


def format_seed_summary(summary: ReferenceSeedSummary) -> str:
    lines = ["Reference seed/backfill summary"]
    for label, counter in (
        ("data_sources", summary.data_sources),
        ("sectors", summary.sectors),
        ("instruments", summary.instruments),
        ("issuers", summary.issuers),
        ("issuer_sector_history", summary.issuer_sector_history),
        ("benchmarks", summary.benchmarks),
    ):
        lines.append(
            (
                f"{label}: created={counter.created} updated={counter.updated} "
                f"skipped={counter.skipped} conflicts={counter.conflicts}"
            ),
        )

    return "\n".join(lines)


def main() -> int:
    db = SessionLocal()
    try:
        summary = seed_reference_layer(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(format_seed_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
