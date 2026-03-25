"""PM 案件服務

Version: 1.2.0
"""
import csv
import io
import logging
from typing import Optional, Dict, Any, Tuple, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMCase
from app.repositories.pm import PMCaseRepository, PMMilestoneRepository
from app.schemas.pm import (
    PMCaseCreate, PMCaseUpdate, PMCaseResponse, PMCaseListRequest, PMCaseSummary,
    PMYearlyTrendItem,
)
from app.services.case_code_service import CaseCodeService

logger = logging.getLogger(__name__)


class PMCaseService:
    """案件管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PMCaseRepository(db)
        self.milestone_repo = PMMilestoneRepository(db)
        self.code_service = CaseCodeService(db)

    async def generate_case_code(self, year: int, category: str = "01") -> str:
        """產生 PM 案號"""
        return await self.code_service.generate_case_code("pm", year, category)

    async def create(self, data: PMCaseCreate, user_id: Optional[int] = None) -> PMCaseResponse:
        """建立案件 — case_code 未提供時自動產生"""
        dump = data.model_dump()

        # 自動產生案號
        if not dump.get("case_code"):
            year = dump.get("year") or 114
            category = dump.get("category") or "01"
            dump["case_code"] = await self.code_service.generate_case_code(
                "pm", year, category,
            )

        pm_case = PMCase(
            **dump,
            created_by=user_id,
        )
        self.db.add(pm_case)
        await self.db.flush()
        await self.db.refresh(pm_case)
        await self.db.commit()
        return await self._to_response(pm_case)

    async def get_detail(self, case_id: int) -> Optional[PMCaseResponse]:
        """取得案件詳情"""
        pm_case = await self.repo.get_by_id(case_id)
        if not pm_case:
            return None
        return await self._to_response(pm_case)

    async def update(self, case_id: int, data: PMCaseUpdate) -> Optional[PMCaseResponse]:
        """更新案件（含 client_name auto-sync）"""
        pm_case = await self.repo.get_by_id(case_id)
        if not pm_case:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Auto-sync client_name from client_vendor_id
        if 'client_vendor_id' in update_data and update_data['client_vendor_id']:
            from sqlalchemy import select
            from app.extended.models.core import PartnerVendor
            result = await self.db.execute(
                select(PartnerVendor.vendor_name).where(
                    PartnerVendor.id == update_data['client_vendor_id']
                )
            )
            vendor_name = result.scalar()
            if vendor_name:
                update_data['client_name'] = vendor_name

        for key, value in update_data.items():
            setattr(pm_case, key, value)

        await self.db.flush()
        await self.db.refresh(pm_case)
        await self.db.commit()
        return await self._to_response(pm_case)

    async def delete(self, case_id: int) -> bool:
        """刪除案件"""
        pm_case = await self.repo.get_by_id(case_id)
        if not pm_case:
            return False
        await self.db.delete(pm_case)
        await self.db.commit()
        return True

    async def list_cases(self, params: PMCaseListRequest) -> Tuple[List[PMCaseResponse], int]:
        """案件列表 — 使用批次聚合消除 N+1 查詢"""
        items, total = await self.repo.filter_cases(
            year=params.year,
            status=params.status,
            category=params.category,
            client_name=params.client_name,
            search=params.search,
            skip=params.skip,
            limit=params.limit,
            sort_by=params.sort_by or "id",
            sort_order=params.sort_order.value if params.sort_order else "desc",
        )

        if not items:
            return [], total

        # 批次取得聚合 (2 queries instead of N*2)
        ids = [c.id for c in items]
        milestone_counts = await self.milestone_repo.get_counts_batch(ids)

        responses = [
            PMCaseResponse(
                **{c.name: getattr(item, c.name) for c in item.__table__.columns},
                milestone_count=milestone_counts.get(item.id, 0),
                staff_count=0,  # staff moved to unified table
            )
            for item in items
        ]
        return responses, total

    async def get_summary(self, year: Optional[int] = None) -> PMCaseSummary:
        """案件統計摘要"""
        data = await self.repo.get_summary(year=year)
        return PMCaseSummary(**data)

    async def get_yearly_trend(self) -> List[PMYearlyTrendItem]:
        """多年度案件趨勢 — SQL 聚合 (取代全表載入)"""
        rows = await self.repo.get_yearly_trend_sql()
        return [PMYearlyTrendItem(**row) for row in rows]

    async def recalculate_progress(self, case_id: int) -> Optional[int]:
        """根據里程碑完成率自動計算進度百分比"""
        milestones: list = await self.milestone_repo.get_by_case_id(case_id)
        if not milestones:
            return None

        total = len(milestones)
        completed = sum(1 for m in milestones if m.status == "completed")
        progress = round(completed / total * 100)

        pm_case = await self.repo.get_by_id(case_id)
        if pm_case and pm_case.progress != progress:
            pm_case.progress = progress
            await self.db.flush()
            await self.db.commit()

        return progress

    async def generate_gantt(self, case_id: int) -> Optional[str]:
        """產生 Mermaid Gantt 語法

        根據案件里程碑資料生成甘特圖，status 對應:
        - completed → done
        - in_progress → active
        - overdue → crit
        - pending/skipped → 無標記
        """
        pm_case = await self.repo.get_by_id(case_id)
        if not pm_case:
            return None

        milestones = await self.milestone_repo.get_by_case_id(case_id)

        title = pm_case.case_code or f"案件 #{case_id}"
        lines = [
            "gantt",
            f"    title 案件里程碑 — {title}",
            "    dateFormat YYYY-MM-DD",
            "    section 里程碑",
        ]

        status_map = {
            "completed": "done",
            "in_progress": "active",
            "overdue": "crit",
        }

        idx = 0
        for m in sorted(milestones, key=lambda x: x.sort_order or 0):
            if not m.planned_date:
                continue

            idx += 1
            tag = status_map.get(m.status, "")
            tag_part = f"{tag}, " if tag else ""
            name = m.milestone_name or f"里程碑{idx}"

            if m.actual_date and m.planned_date:
                # 有實際日期 → 使用 planned_date 到 actual_date 區間
                start = m.planned_date.isoformat()
                end = m.actual_date.isoformat()
                lines.append(f"    {name}    :{tag_part}m{idx}, {start}, {end}")
            else:
                # 僅有 planned_date → 1 天
                start = m.planned_date.isoformat()
                lines.append(f"    {name}    :{tag_part}m{idx}, {start}, 1d")

        return "\n".join(lines)

    async def export_csv(self, year: Optional[int] = None) -> str:
        """匯出案件為 CSV 字串"""
        items, _ = await self.repo.filter_cases(
            year=year, skip=0, limit=9999,
        )

        output = io.StringIO()
        output.write("\ufeff")  # BOM for Excel
        writer = csv.writer(output)
        writer.writerow([
            "案號", "案名", "年度", "類別", "業主",
            "合約金額", "進度(%)", "狀態", "開始日期", "結束日期",
        ])

        for item in items:
            writer.writerow([
                item.case_code or "",
                item.case_name or "",
                item.year or "",
                item.category or "",
                item.client_name or "",
                item.contract_amount or "",
                item.progress or 0,
                item.status or "",
                item.start_date.isoformat() if item.start_date else "",
                item.end_date.isoformat() if item.end_date else "",
            ])

        return output.getvalue()

    async def _to_response(self, pm_case: PMCase) -> PMCaseResponse:
        """轉換為回應格式 (含聚合欄位)"""
        milestones = await self.milestone_repo.get_by_case_id(pm_case.id)

        return PMCaseResponse(
            **{c.name: getattr(pm_case, c.name) for c in pm_case.__table__.columns},
            milestone_count=len(milestones),
            staff_count=0,  # staff moved to unified table
        )
