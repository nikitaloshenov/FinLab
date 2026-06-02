from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from app.modules.hypotheses.blueprints import UnsupportedHypothesisBlueprintError
from app.modules.hypotheses.schemas import HypothesisAnalyzeRequest
from app.modules.hypotheses.service import analyze_hypothesis
from app.shared.errors import raise_api_error


router = APIRouter(
    prefix="/hypotheses",
    tags=["Hypotheses"],
)


@router.post("/analyze")
def analyze_hypothesis_endpoint(request: HypothesisAnalyzeRequest):
    try:
        return jsonable_encoder(analyze_hypothesis(request))
    except UnsupportedHypothesisBlueprintError as error:
        raise_api_error(
            status_code=400,
            code="unsupported_hypothesis_blueprint",
            message=str(error),
        )

