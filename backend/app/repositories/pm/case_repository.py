"""PM 案件 Repository"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy import Integer, case, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.pm import PMCase
from app.repositories.base_repository import BaseRepository
from app.repositories.sort_utils import order_by_clause

logger = logging.getLogger(__name__)


#: ⚠️ 這裡原本有一份手抄的 `SORTABLE_COLUMNS`（2026-08-31 稍早我自己加的），
#: 已移除 —— 改用 `sort_utils.resolve_sort_column` 直接問 ORM。
#: 理由寫在那支的檔頭：手抄清單會跟著 model 漂移，而我抄的第一版
#: 就已經放了一個不存在的欄位（`quotation_amount`，報價金額其實是聚合來的）。
#: **聚合欄位無法用這條路徑排序，前端也不得對它標 `sorter: true`。**


class PMCaseRepository(BaseRepository[PMCase]):
    """案件主檔資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, PMCase)

    async def get_by_case_code(self, case_code: str) -> Optional[PMCase]:
        """依案號查詢"""
        return await self.find_one_by(case_code=case_code)

    async def get_max_case_code_by_prefix(self, prefix: str) -> Optional[str]:
        """取得指定前綴的最大案號"""
        query = (
            select(func.max(PMCase.case_code))
            .where(PMCase.case_code.like(f"{prefix}%"))
        )
        result = await self.db.execute(query)
        return result.scalar()

    async def exists_by_case_code(self, case_code: str) -> bool:
        """檢查案號是否存在"""
        query = select(func.count(PMCase.id)).where(PMCase.case_code == case_code)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def get_lookup_by_case_code(self, case_code: str) -> Optional[Dict[str, Any]]:
        """跨模組查詢用 — 依 case_code 回傳案號的摘要資訊"""
        return await self._get_lookup(PMCase.case_code == case_code)

    async def get_lookup_by_project_code(
        self, project_code: str
    ) -> Optional[Dict[str, Any]]:
        """跨模組查詢用 — 依 project_code（成案編號）回退查詢（2026-07-29 補，見 ERP 版說明）"""
        return await self._get_lookup(PMCase.project_code == project_code)

    async def _get_lookup(self, where_clause) -> Optional[Dict[str, Any]]:
        """跨模組摘要查詢單一實作（case/project 兩路共用，避免欄位漂移）。"""
        query = select(
            PMCase.id, PMCase.case_name, PMCase.status, PMCase.progress
        ).where(where_clause)
        row = (await self.db.execute(query)).first()
        if not row:
            return None
        return {
            "id": row.id,
            "case_name": row.case_name,
            "status": row.status,
            "progress": row.progress,
        }

    async def filter_cases(
        self,
        year: Optional[int] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        client_name: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "id",
        sort_order: str = "desc",
        include_converted: bool = True,
        staff_user_id: Optional[int] = None,
    ) -> Tuple[List[PMCase], int]:
        """篩選案件列表

        `include_converted=False` 時排除**已成案**的案件（已承攬且有
        `project_code`）—— 那些已移交 `/contract-cases` 列管，
        不該在邀標/報價頁重複出現（owner 2026-08-31 裁示）。

        ⚠️ 條件刻意是「已承攬**且**有成案編號」，不是「已承攬」：
        實測 227 件已承攬裡有 **91 件還沒成案**（沒有 project_code，
        `contract_projects` 裡也沒有）。只看狀態會讓那 91 件從兩邊都消失。
        """
        query = select(PMCase)
        count_query = select(func.count(PMCase.id))

        conditions = []
        if not include_converted:
            conditions.append(
                or_(
                    PMCase.status != "contracted",
                    PMCase.project_code.is_(None),
                    PMCase.project_code == "",
                )
            )
        if year is not None:
            conditions.append(PMCase.year == year)
        if status:
            conditions.append(PMCase.status == status)
        if category:
            conditions.append(PMCase.category == category)
        if client_name:
            conditions.append(PMCase.client_name.ilike(f"%{client_name}%"))
        if staff_user_id is not None:
            # 2026-09-07：個人儀表板的數字要點得進來且已篩好（承辦身分）。
            # 指派有兩條互斥綁法，走 `case_staff` 那一家 —— 只認 case_code 會漏掉
            # 成案後才指派的那些（同族第 N 處，本 repo 已為此付過多次代價）。
            from app.repositories.erp.case_staff import case_codes_of_user
            mine = await case_codes_of_user(self.db, staff_user_id)
            conditions.append(PMCase.case_code.in_(mine or {"__none__"}))
        if search:
            conditions.append(or_(
                PMCase.case_code.ilike(f"%{search}%"),
                PMCase.case_name.ilike(f"%{search}%"),
                PMCase.client_name.ilike(f"%{search}%"),
            ))

        if conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # 排序
        # 空值一律排最後：PostgreSQL 的 DESC 預設 NULLS FIRST ⇒
        # 「由大到小」第一頁會是一整頁空值（見 sort_utils.order_by_clause）。
        query = query.order_by(order_by_clause(
            PMCase, sort_by, PMCase.id, descending=sort_order != "asc"))

        # 分頁
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_summary(
        self, year: Optional[int] = None, include_converted: bool = True,
        status: Optional[str] = None, category: Optional[str] = None,
        staff_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """取得案件統計摘要

        `include_converted` **必須與列表查詢用同一個值** —— 統計卡是列表的
        分母，範圍不同就會出現「卡片說 69 件、列表一件都點不出來」（規範 §2.6 ①）。
        """
        base = select(PMCase)
        if year is not None:
            base = base.where(PMCase.year == year)

        # 2026-09-09 owner：「PM 案件列表與統計兩者無對應，是不合理的統計數據」。
        #
        # 列表帶了 `staff_user_id`（從個人儀表板點進來時就是承辦本人），統計卡沒帶
        # ⇒ 同一個畫面上，列表 6 件而卡片顯示全部。
        # 而這個檔案的 `get_summary` docstring 早就寫著「範圍須與列表一致」——
        # **宣告寫對了、實作少一個參數**，本 repo 反覆付學費的同一個形狀。
        #
        # 身分規則不另寫一份：與列表同樣走 `case_codes_of_user`（`case_staff` 那一家，
        # 指派的兩條互斥綁法都認得），差別只在這裡是在 `_scoped` 裡套，
        # 那是三個子查詢（總計／狀態分組／合約總額）的單一收斂點。
        # 2026-09-09 owner「案件與經費等統計請整合建構中心服務」：範圍從 `services/stats/case_scope` 拿。
        # `include_converted` 是本頁特有的口徑（已成案的移交 /contract-cases），不是通用維度，留在本地。
        from app.services.stats.case_scope import CaseStatsScope, pm_case_columns

        _scope = CaseStatsScope(year=year, staff_user_id=staff_user_id)
        _cols = pm_case_columns()
        _mine = await _scope.resolve_case_codes(self.db)

        def _scoped(q):
            q = _scope.apply_sync(q, _cols, case_codes=_mine)
            if not include_converted:
                q = q.where(
                    or_(
                        PMCase.status != "contracted",
                        PMCase.project_code.is_(None),
                        PMCase.project_code == "",
                    )
                )
            return q

        # 總數
        total = (await self.db.execute(_scoped(select(func.count(PMCase.id))))).scalar() or 0

        # 依狀態分組
        status_q = _scoped(select(PMCase.status, func.count(PMCase.id))).group_by(PMCase.status)
        status_result = await self.db.execute(status_q)
        by_status = {row[0] or "unknown": row[1] for row in status_result.all()}

        # 合約總額
        # 2026-09-04：金額跟著目前點選的狀態卡／類別走（owner「報價總額應僅配合統計卡片動態調整」），
        # 計數不跟——卡片是分母，點了某張卡其他卡的數字不能歸零。
        amt_q = _scoped(select(func.sum(PMCase.contract_amount)))
        if status:
            amt_q = amt_q.where(PMCase.status == status)
        if category:
            amt_q = amt_q.where(PMCase.category == category)
        total_amount = (await self.db.execute(amt_q)).scalar()

        return {
            "total_cases": total,
            "by_status": by_status,
            "total_contract_amount": total_amount,
        }

    async def get_yearly_trend_sql(self) -> List[Dict[str, Any]]:
        """多年度趨勢 — 純 SQL 聚合 (取代 limit=9999 全表載入)"""
        query = (
            select(
                PMCase.year,
                func.count(PMCase.id).label("case_count"),
                func.coalesce(func.sum(PMCase.contract_amount), 0).label("total_contract"),
                func.sum(
                    case((PMCase.status == "closed", 1), else_=0)
                ).label("closed_count"),
                func.sum(
                    case((PMCase.status == "in_progress", 1), else_=0)
                ).label("in_progress_count"),
                func.coalesce(func.avg(PMCase.progress), 0).label("avg_progress"),
            )
            .where(PMCase.year.isnot(None))
            .group_by(PMCase.year)
            .order_by(PMCase.year)
        )
        result = await self.db.execute(query)
        return [
            {
                "year": row.year,
                "case_count": row.case_count,
                "total_contract": Decimal(str(row.total_contract)),
                "closed_count": int(row.closed_count or 0),
                "in_progress_count": int(row.in_progress_count or 0),
                "avg_progress": round(float(row.avg_progress)),
            }
            for row in result.all()
        ]
