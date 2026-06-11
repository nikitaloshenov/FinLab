from pydantic import BaseModel


class ReferenceIssuerSummary(BaseModel):
    id: int
    name: str
    short_name: str | None = None


class ReferenceSectorSummary(BaseModel):
    code: str
    name: str


class InstrumentReferenceSummary(BaseModel):
    secid: str
    name: str | None = None
    short_name: str | None = None
    asset_type: str
    engine: str
    market: str
    board: str
    currency: str | None = None
    issuer: ReferenceIssuerSummary | None = None
    sector: ReferenceSectorSummary | None = None
