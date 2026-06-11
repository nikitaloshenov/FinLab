from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.reference.schemas import InstrumentReferenceSummary
from app.modules.reference.service import (
    ReferenceInstrumentNotFoundError,
    get_instrument_reference_summary,
)
from app.shared.errors import raise_api_error


router = APIRouter(
    prefix="/reference",
    tags=["Reference"],
)


@router.get("/instruments/{secid}", response_model=InstrumentReferenceSummary)
def get_reference_instrument(
    secid: str,
    db: Session = Depends(get_db),
):
    try:
        return get_instrument_reference_summary(db, secid)
    except ReferenceInstrumentNotFoundError as error:
        raise_api_error(
            status_code=404,
            code="reference_instrument_not_found",
            message=str(error),
        )
