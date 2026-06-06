from uuid import UUID

from fastapi import Header

from app.shared.errors import raise_api_error


SESSION_HEADER_NAME = "X-FinLab-Session-Id"


def get_demo_session_id(
    session_id: str | None = Header(default=None, alias=SESSION_HEADER_NAME),
) -> str:
    normalized_session_id = (session_id or "").strip()

    if not normalized_session_id:
        raise_api_error(
            status_code=400,
            code="demo_session_required",
            message=f"{SESSION_HEADER_NAME} header is required",
        )

    try:
        return str(UUID(normalized_session_id))
    except ValueError:
        raise_api_error(
            status_code=400,
            code="demo_session_invalid",
            message=f"{SESSION_HEADER_NAME} header must be a valid UUID",
        )
