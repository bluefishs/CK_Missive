"""PM API Endpoints"""
from fastapi import APIRouter
from . import cases, milestones, staff

router = APIRouter()
router.include_router(cases.router, prefix="/cases", tags=["PM 案件管理"])
router.include_router(milestones.router, prefix="/milestones", tags=["PM 里程碑"])
router.include_router(staff.router, prefix="/staff", tags=["PM 人員配置"])
