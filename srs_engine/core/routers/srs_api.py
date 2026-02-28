from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from srs_engine.core.auth.deps import require_user
from srs_engine.core.services.srs_service import (
    auto_generate_section as auto_generate_section_service,
    enhance_problem_statement as enhance_problem_statement_service,
    generate_srs as generate_srs_service,
)
from srs_engine.schemas.home_page_schemas.auto_generate_input_schema import AutoGenerateInput
from srs_engine.schemas.home_page_schemas.problem_statement_enhance_schema import EnhanceProblemStatementInput
from srs_engine.schemas.home_page_schemas.srs_input_schema import SRSRequest


router = APIRouter()


@router.post("/enhance-problem-statement")
async def enhance_problem_statement(
    request: Request,
    input_data: EnhanceProblemStatementInput,
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    return await enhance_problem_statement_service(request.app, input_data, user_id=user_id)


@router.post("/auto-generate-section")
async def auto_generate_section(
    request: Request,
    input_data: AutoGenerateInput,
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    return await auto_generate_section_service(request.app, input_data, user_id=user_id)


@router.post("/generate_srs")
async def generate_srs(
    request: Request,
    srs_data: SRSRequest,
    user=Depends(require_user),
):
    user_id = str(user.get("_id"))
    return await generate_srs_service(request.app, srs_data, user_id=user_id)

