"""PM 案件服務

Version: 1.2.0
"""
import csv
import io
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMCase
from app.repositories.pm import PMCaseRepository, PMMilestoneRepository
from app.schemas.pm import (
    PMCaseCreate, PMCaseUpdate, PMCaseResponse, PMCaseListRequest, PMCaseSummary,
    PMYearlyTrendItem,
)
from app.services.contract import CaseCodeService

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
        """建立案件 — case_code 未提供時自動產生，含重複檢查"""
        dump = data.model_dump()

        # 1. 手動 case_code 格式驗證 + 重複檢查
        manual_code = dump.get("case_code")
        if manual_code:
            if not await self.code_service.validate_case_code(manual_code):
                raise ValueError(
                    f"案號格式不合規: {manual_code}，"
                    f"正確格式: CK2025_PM_01_001 (留空可自動產生)"
                )
            if await self.code_service.check_duplicate(manual_code):
                raise ValueError(f"案號 {manual_code} 已存在")

        # 2. 案名重複檢查 (同年度 + 同名 → 疑似重複)
        case_name = dump.get("case_name", "")
        # 2026-08-20：預設值原本是 `114` —— 民國、而且是寫死的過期年份。
        # 規範是統一西元（owner），且寫死的年份每年都會過期而沒有人會發現。
        # schema 的 field_validator 已把送進來的民國值轉成西元，這裡只處理「沒給」。
        year = dump.get("year") or datetime.now().year
        if case_name:
            from sqlalchemy import select, func
            dup_q = await self.db.execute(
                select(func.count())
                .select_from(PMCase)
                .where(PMCase.case_name == case_name)
                .where(PMCase.year == year)
            )
            if (dup_q.scalar() or 0) > 0:
                raise ValueError(
                    f"同年度已有同名案件「{case_name}」({year})，"
                    f"請確認是否重複建案"
                )
            # 2026-09-02 owner：「主要是由標案系統一件建案，但又有同仁由 PM 案管理
            # 重複建置（此應防呆）」——實例 /pm/cases/243 vs /contract-cases/190。
            # 上面那段 04-09 就在了，但**只查 pm_cases**；190 是承攬案（標案系統直接
            # 成案、沒有 PM 案），所以同仁 06-24 從 PM 案管理建 243 時查不到它。
            # 補查 contract_projects：同年同名已成案 ⇒ 擋，並指出該沿用哪個成案編號。
            # ⚠️ 案名不具識別度（「建物第一次測量」有 70 個）：只擋**同年同名同客戶**，
            # 否則同一家建設公司第二次來做同名工作就建不了案。
            from app.extended.models.core import ContractProject
            client = dump.get("client_name")
            ct_q = select(ContractProject.project_code, ContractProject.case_code).where(
                ContractProject.project_name == case_name,
                ContractProject.year == year,
            )
            if client:
                ct_q = ct_q.where(ContractProject.client_agency == client)
            ct = (await self.db.execute(ct_q.limit(1))).first()
            if ct:
                raise ValueError(
                    f"同年度已有同名{'同客戶' if client else ''}的承攬案件「{case_name}」"
                    f"（成案編號 {ct[0] or ct[1]}）。若是同一件工作，請直接在該承攬案下作業，"
                    f"不要重複建 PM 案；若確實是不同的兩案，請把名稱改成能分辨的內容再建。"
                )

        # 3. 自動產生案號 (未手動提供時)
        if not manual_code:
            category = dump.get("category") or "01"
            dump["case_code"] = await self.code_service.generate_case_code(
                "pm", year, category,
            )

        # 2026-08-29：由 FK 回填 `client_name` —— `update` 早就這樣做了
        # （見本檔 update 的同段），而 **create 沒有**。於是「只送 FK 的
        # 建案入口」會產生 client_name 空白的案件，而報價單輸出的客戶抬頭
        # 正是讀它（`quotation_document.gather` 的 COALESCE(cp.client_agency,
        # pm.client_name)）⇒ 文件上的客戶欄會是空的。
        # 同一條規則要在所有寫入路徑上（L83）。
        if dump.get("client_vendor_id") and not dump.get("client_name"):
            from sqlalchemy import select as _sel
            from app.extended.models.core import PartnerVendor as _PV
            vendor_name = await self.db.scalar(
                _sel(_PV.vendor_name).where(_PV.id == dump["client_vendor_id"]))
            if vendor_name:
                dump["client_name"] = vendor_name

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
            include_converted=params.include_converted,
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

    async def get_summary(
        self, year: Optional[int] = None, include_converted: bool = True,
        status: Optional[str] = None, category: Optional[str] = None,
    ) -> PMCaseSummary:
        """案件統計摘要（範圍須與列表一致，見 repo 的說明；status／category 只影響金額）"""
        data = await self.repo.get_summary(year=year, include_converted=include_converted,
                                           status=status, category=category)
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
