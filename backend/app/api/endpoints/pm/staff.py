"""PM 案件人員 API — 已遷移至統一人員表 (v5.2.0)

原 PM staff endpoints 已遷移至 /project-staff/case/{case_code}/list。
保留空 router 確保 PM __init__.py 的 include_router 不報錯。
"""
from fastapi import APIRouter

router = APIRouter()
