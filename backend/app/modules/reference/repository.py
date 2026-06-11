from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.reference.models import Instrument, IssuerSectorHistory, Sector


def get_preferred_instrument_by_secid(db: Session, secid: str) -> Instrument | None:
    normalized_secid = secid.strip().upper()

    instruments = db.scalars(
        select(Instrument).where(func.upper(Instrument.secid) == normalized_secid),
    ).all()

    if not instruments:
        return None

    return sorted(
        instruments,
        key=lambda instrument: (
            not instrument.is_active,
            instrument.board != "TQBR",
            instrument.id,
        ),
    )[0]


def get_current_sector_for_issuer(
    db: Session,
    issuer_id: int,
    *,
    as_of: date | None = None,
) -> Sector | None:
    effective_date = as_of or date.today()

    return db.scalar(
        select(Sector)
        .join(IssuerSectorHistory, IssuerSectorHistory.sector_id == Sector.id)
        .where(IssuerSectorHistory.issuer_id == issuer_id)
        .where(IssuerSectorHistory.valid_from <= effective_date)
        .where(
            or_(
                IssuerSectorHistory.valid_to.is_(None),
                IssuerSectorHistory.valid_to >= effective_date,
            ),
        )
        .order_by(IssuerSectorHistory.valid_from.desc())
        .limit(1),
    )
