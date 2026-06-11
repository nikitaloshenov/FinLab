from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.reference.repository import (
    get_current_sector_for_issuer,
    get_preferred_instrument_by_secid,
)
from app.modules.reference.schemas import (
    InstrumentReferenceSummary,
    ReferenceIssuerSummary,
    ReferenceSectorSummary,
)


class ReferenceInstrumentNotFoundError(Exception):
    pass


def get_instrument_reference_summary(
    db: Session,
    secid: str,
) -> InstrumentReferenceSummary:
    instrument = get_preferred_instrument_by_secid(db, secid)

    if instrument is None:
        raise ReferenceInstrumentNotFoundError(
            f"Reference instrument {secid.strip().upper()} was not found.",
        )

    issuer = instrument.issuer
    sector = get_current_sector_for_issuer(db, issuer.id) if issuer is not None else None

    return InstrumentReferenceSummary(
        secid=instrument.secid,
        name=instrument.name,
        short_name=instrument.short_name,
        asset_type=instrument.asset_type,
        engine=instrument.engine,
        market=instrument.market,
        board=instrument.board,
        currency=instrument.currency,
        issuer=(
            ReferenceIssuerSummary(
                id=issuer.id,
                name=issuer.name,
                short_name=issuer.short_name,
            )
            if issuer is not None
            else None
        ),
        sector=(
            ReferenceSectorSummary(
                code=sector.code,
                name=sector.name,
            )
            if sector is not None
            else None
        ),
    )
