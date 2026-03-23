"""PM API Endpoints — 全部端點需認證"""
from fastapi import APIRouter, Depends
from app.core.dependencies import require_auth
from . import cases, milestones, staff

router = APIRouter(dependencies=[Depends(require_auth())])
router.include_router(cases.router, prefix="/cases", tags=["PM 案件管理"])
router.include_router(milestones.router, prefix="/milestones", tags=["PM 里程碑"])
router.include_router(staff.router, prefix="/staff", tags=["PM 人員配置"])
