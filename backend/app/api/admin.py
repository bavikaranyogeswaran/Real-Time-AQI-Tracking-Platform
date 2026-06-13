from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.rate_limit import limiter
from app.schemas.admin_schema import AdminSummaryOut
from app.services.admin import get_admin_summary

router = APIRouter()


@router.get("/admin/summary", response_model=AdminSummaryOut)
@limiter.limit("10/minute")
async def admin_summary(request: Request, session: AsyncSession = Depends(get_db)):
    return await get_admin_summary(session)
