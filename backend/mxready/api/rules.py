from fastapi import APIRouter, Request

from mxready.scanning.rule_loader import RuleCatalog

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=RuleCatalog)
def get_rules(request: Request) -> RuleCatalog:
    return request.app.state.rule_catalog
