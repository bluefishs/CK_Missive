"""
標案圖譜 + 建案 API — graph / create-case
"""
from app.core.dependencies import require_auth
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.services.tender.search import TenderSearchService
from app.schemas.common import SuccessResponse
from app.schemas.tender_admin import (
    TenderCreateCaseRequest,
    TenderGraphRequest,
    TenderLinkCaseRequest,
    TenderRelatedCasesRequest,
)

# L2 防重複：候選案件相似度門檻（字元 bigram Jaccard，見 services/tender/name_matching.py）。
#
# 實測規模（2026-07-31，以正規化後**完全同名**計）：
#   標案標題 == 承攬案件名稱 → 8 配對 / 涉及 6 個承攬案件（pcc 6、ezbid 2）
#   標案標題 == 邀標案件名稱 → 4 配對
# ⚠️ 先前用 `pg_trgm similarity()` 量到的「33 筆（38%）」是**假數字**：
#   pg_trgm 對中文不產生 trigram，那 33 筆全因雙方含 ASCII「115」而被判 1.00。
SIMILAR_CASE_THRESHOLD = 0.6
MAX_CANDIDATES = 8

logger = logging.getLogger(__name__)

# 2026-08-21：router 層要求登入。
#
# 公網實測（未帶憑證）本模組端點回 200 並吐出業務資料 ——
# 根因是 TUNNEL_GUARD_ENABLED=false，沒有自帶認證的端點一律對外開放。
# 在 router 層加而不是逐一改端點參數：逐一改會漏，而漏掉的那條沒有人會發現。
#
# 用 require_auth() 不是 require_admin()：這些是一般同仁每天在用的功能。
router = APIRouter(dependencies=[Depends(require_auth())])


# ============================================================================
# Dependencies
# ============================================================================

def get_tender_service() -> TenderSearchService:
    """取得標案搜尋服務 (含 Redis 快取)"""
    try:
        from app.core.redis_client import get_redis_client
        redis = get_redis_client()
    except Exception:
        redis = None
    return TenderSearchService(redis_client=redis)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/graph")
async def get_tender_graph(
    req: TenderGraphRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """標案知識圖譜 — DB 優先 + API 補充"""
    # 先從 DB 建圖
    db_graph = None
    try:
        from app.db.database import AsyncSessionFromDB
        from app.services.tender.cache import build_graph_from_db
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            db_graph = await build_graph_from_db(db, req.query, req.max_tenders)
    except Exception:
        pass

    if db_graph and db_graph.get("stats", {}).get("tenders", 0) >= 5:
        return SuccessResponse(data=db_graph)

    # DB 不足 → 回退 API
    result = await service.build_tender_graph(
        query=req.query, max_tenders=req.max_tenders,
    )
    return SuccessResponse(data=result)


@router.post("/related-cases")
async def find_related_cases(req: TenderRelatedCasesRequest):
    """建案前先找出「可能已經是同一案」的既有案件（L2 防重複）

    設計取捨（2026-07-31，owner 決策採「不自動判定」）：
    **本端點不替使用者決定**，只把候選攤開。理由：案名常有「第二期」「(開口契約)」
    等差異，自動判定誤擋的代價高於多按一次。前端據此提供「關聯既有 / 仍要新建」。
    """
    from sqlalchemy import text
    from app.db.database import AsyncSessionLocal

    title = (req.title or "").strip()
    if not title:
        return SuccessResponse(data={"candidates": [], "linked": None})

    async with AsyncSessionLocal() as db:
        # 已關聯者優先回報（L3 回指：避免重複關聯／讓前端直接導向）
        linked = None
        if req.tender_id:
            row = (await db.execute(text(
                "SELECT id, project_code, project_name, status FROM contract_projects "
                "WHERE source_tender_id = :tid LIMIT 1"
            ), {"tid": req.tender_id})).first()
            if row:
                linked = {"type": "contract_project", "id": row[0], "code": row[1],
                          "name": row[2], "status": row[3]}
            else:
                row = (await db.execute(text(
                    "SELECT id, case_code, case_name, status FROM pm_cases "
                    "WHERE source_tender_id = :tid LIMIT 1"
                ), {"tid": req.tender_id})).first()
                if row:
                    linked = {"type": "pm_case", "id": row[0], "code": row[1],
                              "name": row[2], "status": row[3]}

        # ⚠️ 不可用 pg_trgm similarity()：對中文恆為 0 且會因 ASCII 年度數字產生
        # 100% 的假性命中（見 services/tender/name_matching.py 說明）。
        # 案件總量僅約 160 筆，全量拉出在 Python 端比對即可。
        from app.services.tender.name_matching import name_similarity

        cp_rows = (await db.execute(text(
            "SELECT id, project_code, project_name, status, source_tender_id "
            "FROM contract_projects"
        ))).fetchall()
        pm_rows = (await db.execute(text(
            "SELECT id, case_code, case_name, status, source_tender_id FROM pm_cases"
        ))).fetchall()

        def pack(rows, kind):
            out = []
            for r in rows:
                sim = name_similarity(r[2], title)
                if sim < SIMILAR_CASE_THRESHOLD:
                    continue
                out.append({
                    "type": kind,
                    "id": r[0],
                    "code": r[1],
                    "name": r[2],
                    "status": r[3],
                    "already_linked_tender_id": r[4],
                    "similarity": round(sim, 3),
                    "exact": sim >= 1.0,
                })
            return out

        candidates = pack(cp_rows, "contract_project") + pack(pm_rows, "pm_case")
        candidates.sort(key=lambda c: (not c["exact"], -c["similarity"]))

        return SuccessResponse(data={
            "candidates": candidates[:MAX_CANDIDATES],
            "linked": linked,
            "threshold": SIMILAR_CASE_THRESHOLD,
        })


@router.post("/by-id")
async def get_tender_by_id(req: dict):
    """以 tender_records.id 取最小資訊（L3 回指顯示 + L4 報價預填共用）

    案件端只存 `source_tender_id`，要顯示連結或預填預算還需要標案的
    來源別 / ezbid_id / unit_id / job_number / 預算，故提供此輕量查詢。
    """
    from sqlalchemy import text
    from app.db.database import AsyncSessionLocal

    tid = req.get("tender_id")
    if not tid:
        raise HTTPException(status_code=400, detail="缺少 tender_id")

    async with AsyncSessionLocal() as db:
        row = (await db.execute(text(
            "SELECT id, title, unit_name, budget, source, ezbid_id, unit_id, job_number "
            "FROM tender_records WHERE id = :id"
        ), {"id": tid})).first()
        if not row:
            raise HTTPException(status_code=404, detail="標案不存在")
        return SuccessResponse(data={
            "id": row[0], "title": row[1], "unit_name": row[2],
            "budget": str(row[3]) if row[3] is not None else None,
            "source": row[4], "ezbid_id": row[5],
            "unit_id": row[6], "job_number": row[7],
        })


@router.post("/link-case")
async def link_tender_to_case(req: TenderLinkCaseRequest):
    """把標案關聯到既有案件（L2「關聯既有」而非重複新建 + L3 回指落地）"""
    from sqlalchemy import text
    from app.db.database import AsyncSessionLocal

    if req.target_type not in ("pm_case", "contract_project"):
        raise HTTPException(status_code=400, detail="target_type 必須為 pm_case 或 contract_project")

    table, code_col, name_col = (
        ("pm_cases", "case_code", "case_name") if req.target_type == "pm_case"
        else ("contract_projects", "project_code", "project_name")
    )

    async with AsyncSessionLocal() as db:
        row = (await db.execute(text(
            f"SELECT id, {code_col}, {name_col}, source_tender_id FROM {table} WHERE id = :id"
        ), {"id": req.target_id})).first()
        if not row:
            raise HTTPException(status_code=404, detail="目標案件不存在")
        if row[3] and row[3] != req.tender_id:
            raise HTTPException(
                status_code=409,
                detail=f"此案件已關聯其他標案 (tender_id={row[3]})，請先解除再重新關聯",
            )

        await db.execute(text(
            f"UPDATE {table} SET source_tender_id = :tid WHERE id = :id"
        ), {"tid": req.tender_id, "id": req.target_id})
        await db.commit()

        logger.info("標案 %s 關聯至 %s#%s (%s)", req.tender_id, table, row[0], row[1])
        return SuccessResponse(
            data={"type": req.target_type, "id": row[0], "code": row[1], "name": row[2]},
            message=f"已關聯至 {row[1]}",
        )


@router.post("/create-case")
async def create_case_from_tender(
    req: TenderCreateCaseRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """從標案一鍵建立 PM Case。

    2026-08-16：實作已抽到 `services/tender/case_creation.py`。
    這裡只剩「HTTP 進、HTTP 出」—— 因為同一件事還有第二個入口
    （AI 工具 `auto_tender_to_case`），而它原本自己寫了一份查重只有一道、
    金額不帶、且對「邀標階段要不要建報價單」的答案相反的版本。
    """
    from app.db.database import AsyncSessionLocal
    from app.services.tender.case_creation import (
        TenderCaseCreationService,
        TenderCaseDuplicateError,
    )

    async with AsyncSessionLocal() as db:
        try:
            result = await TenderCaseCreationService(db).create_from_tender(
                title=req.title,
                unit_id=req.unit_id,
                unit_name=req.unit_name,
                job_number=req.job_number,
                budget=req.budget,
                tender_id=req.tender_id,
                category=req.category or "01",
            )
        except TenderCaseDuplicateError as e:
            raise HTTPException(status_code=409, detail=str(e))

        await db.commit()

        msg = f"已建立案件 {result['case_code']}"
        if result["contract_amount"] is None:
            # 來源標案沒有金額（PCC 來源 60,296 筆全部沒有）。
            # 不擋建案，但要在當下就說 —— 否則會一路帶到成案才發現空白。
            msg += "（來源標案無預算金額，請於案件內補填合約金額後才能成案）"

        return SuccessResponse(data={
            "case_code": result["case_code"],
            "pm_case_id": result["pm_case_id"],
            "contract_amount": result["contract_amount"],
            "message": msg,
        })
