"""Cross-repository migration progress aggregation for a single trusted deployment."""

from fastapi import APIRouter, Query, Request

from mxready.models import ProgressPage

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=ProgressPage)
def get_dashboard(
    request: Request,
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=1_000_000),
) -> ProgressPage:
    return request.app.state.store.list_scan_progress(query=q.strip(), limit=limit, offset=offset)
