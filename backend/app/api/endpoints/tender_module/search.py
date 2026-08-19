"""
標案搜尋 API — search / detail / detail-full / search-company / recommend / realtime
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tender.search import TenderSearchService
from app.schemas.common import SuccessResponse
from app.schemas.tender_admin import (
    TenderCompanySearchRequest,
    TenderDetailRequest,
    TenderRecommendRequest,
    TenderSearchRequest,
)
from app.db.database import get_async_db as get_db

logger = logging.getLogger(__name__)

router = APIRouter()


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

@router.post("/search")
async def search_tenders(
    req: TenderSearchRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """搜尋標案 — DB 優先 + g0v + ezbid 三軌合併"""
    from datetime import datetime, timedelta

    # Step 0: DB 快速查詢 (毫秒級)
    db_records = []
    try:
        from app.db.database import AsyncSessionLocal
        from app.services.tender.cache import search_from_db
        async with AsyncSessionLocal() as cache_db:
            db_records = await search_from_db(cache_db, req.query, limit=20)
    except Exception:
        pass

    if req.search_type == "org":
        result = await service.search_by_org(req.query, page=req.page)
    elif req.search_type == "company":
        result = await service.search_by_company(req.query, page=req.page)
    else:
        result = await service.search_by_title(
            query=req.query, page=req.page, category=req.category,
        )

    # 合併 ezbid 即時資料 (僅第一頁)
    if req.page in (None, 1):
        try:
            from app.services.tender.ezbid_scraper import EzbidScraper
            from app.core.redis_client import get_redis
            try:
                _redis = await get_redis()
            except Exception:
                _redis = None
            scraper = EzbidScraper(redis_client=_redis)
            category_map = {"工程": "WORK", "勞務": "SERV", "財物": "PPTY"}
            cat = category_map.get(req.category or "", "ALL")
            ezbid = await scraper.fetch_latest(query=req.query, category=cat, pages=1)

            # ⚠️ 去重鍵**兩邊必須取自同一組欄位**。
            #
            # 原本 `seen` 用 `unit_id + title`，而新項目比對時用 `ezbid_id + title`
            # —— 第一段來自不同欄位，於是這個 key **永遠不可能相等**，
            # 每一筆 ezbid 結果都被判成「沒看過」而插入。
            # 症狀就是同一個標案在搜尋頁出現兩三次（2026-08-19 owner 回報
            # 「臺北港鄰近淺水域海陸光達測繪」連出三筆）。
            #
            # 改用「標題＋機關」：跨來源的 unit_id 格式本來就不同
            # （PCC 是 base64 如 `NzEzMDA1NzQ=`，ezbid 是 `A.47.3`），
            # 拿它當同一性判準從一開始就不成立；而 `job_number` 在
            # ezbid 即時抓取時是空字串，也不能用。
            def _dedupe_key(rec: dict) -> str:
                return (rec.get("title") or "")[:30] + "|" + (rec.get("unit_name") or "")

            seen = {_dedupe_key(r) for r in result.get("records", [])}
            ezbid_added = 0
            for r in ezbid.get("records", []):
                key = _dedupe_key(r)
                if key not in seen:
                    seen.add(key)
                    result["records"].insert(0, {
                        "date": r.get("date", ""),
                        "raw_date": int(r.get("date", "0").replace("-", "")) if r.get("date") else 0,
                        "title": r.get("title", ""),
                        "type": r.get("type", ""),
                        "category": r.get("category", ""),
                        "unit_id": r.get("ezbid_id", ""),
                        "unit_name": r.get("unit_name", ""),
                        "job_number": "",
                        "company_names": [], "company_ids": [],
                        "winner_names": [], "bidder_names": [],
                        "tender_api_url": r.get("ezbid_url", ""),
                        "source": "ezbid",
                    })
                    ezbid_added += 1

            if ezbid_added > 0:
                result["records"].sort(key=lambda x: x.get("raw_date", 0), reverse=True)
                result["total_records"] = result.get("total_records", 0) + ezbid_added
        except Exception:
            pass  # ezbid 失敗不影響主搜尋

    # 合併 DB 結果 (補充 API 未覆蓋的歷史資料)
    if db_records:
        seen_titles = {r.get("title", "")[:20] for r in result.get("records", [])}
        for r in db_records:
            if r.get("title", "")[:20] not in seen_titles:
                seen_titles.add(r.get("title", "")[:20])
                r["source"] = "db"
                result["records"].append(r)
        result["total_records"] = len(result["records"])

    # Relevance re-ranking — 合併後按標題相似度重排序
    if result.get("records") and len(req.query) > 5:
        from app.services.tender.search_query import rerank_by_title_similarity
        result["records"] = rerank_by_title_similarity(
            result["records"], req.query, top_k=30,
        )
        result["total_records"] = len(result["records"])

    # ── 最終統一去重（三軌合併之後，回傳之前）──
    #
    # 這一支合併三個來源：DB 快查、g0v/PCC 服務、ezbid 即時抓取。
    # 原本**每一段各自去重**，於是只要有一段沒涵蓋到，重複就會漏出去 ——
    # 2026-08-19 owner 兩次回報同一個標案在搜尋頁連續出現兩筆
    # （臺北港海陸光達、花蓮和平空載光達）。我第一次只修了「ezbid 對既有結果」
    # 那一段，重複照樣出現，因為它來自另一段。
    #
    # 去重放在**唯一的出口**，比在每一段各自維護一份判準可靠：
    # 三段的欄位命名不同（unit_id / ezbid_id / db 的 unit_id），
    # 而「標題＋機關」是三段都有、且跨來源穩定的欄位。
    #
    # 保留策略：同一案取**資訊較完整**的那筆（有預算金額的優先），
    # 因為 PCC 公告幾乎都沒有 budget 而 ezbid 有（實測 13,913/14,105 組）。
    # 鍵優先用 `job_number`（招標案的正式編號）——它才是「同一個案子」的定義。
    # 實測 owner 回報的花蓮案：`B115076` 在 **07-15 與 08-06 各公告一次**
    # （很可能流標重招），另有 `B115077` 是同名但不同招標方式的另一個案子。
    # 只用「標題＋機關」會把 B115076/B115077 併成一筆（錯，那是兩個案），
    # 只用 job_number 又會撞號（不同機關各自編號，實測 1,129 組標題不同）
    # ⇒ 兩者都要。沒有 job_number 的（ezbid 即時抓取）才退回標題＋機關。
    def _merge_key(rec: dict) -> str:
        jn = (rec.get("job_number") or "").strip()
        if jn:
            return "J|" + jn + "|" + (rec.get("title") or "")[:20]
        return "T|" + (rec.get("title") or "")[:30] + "|" + (rec.get("unit_name") or "")

    def _better(a: dict, b: dict) -> dict:
        """同一案的多筆之中留哪一筆：先看公告日新舊，同日再看有沒有金額。"""
        da, db = a.get("date") or "", b.get("date") or ""
        if da != db:
            return a if da > db else b
        if not a.get("budget") and b.get("budget"):
            return b
        return a

    _records = result.get("records") or []
    if _records:
        _by_key: dict[str, dict] = {}
        _order: list[str] = []
        for _r in _records:
            _k = _merge_key(_r)
            if _k not in _by_key:
                _by_key[_k] = _r
                _order.append(_k)
            else:
                _by_key[_k] = _better(_by_key[_k], _r)
        if len(_order) != len(_records):
            result["records"] = [_by_key[k] for k in _order]
            result["total_records"] = len(result["records"])

    # ── 列表層的跨來源補值 ──
    #
    # 詳情頁在 2026-08-19 已經會跨來源補金額，但**列表沒有** ——
    # owner 回報「15 筆紀錄皆無詳細資料」。實測搜尋「測量」34 筆，
    # 有金額的只有 12 筆，而且**全部是 ezbid 來源；pcc 來源一筆都沒有**
    # （PCC 清單頁本身就沒有金額欄位）。
    #
    # 一次 SQL 補完，不逐筆查（那會是 N+1）。配對鍵與詳情頁同一條：
    # job_number + 標題前 20 字（job_number 單獨會撞號）。
    _need = [r for r in (result.get("records") or [])
             if not r.get("budget") and (r.get("job_number") or "").strip()]
    if _need:
        try:
            from sqlalchemy import text as _sa_text2
            from app.db.database import AsyncSessionLocal as _Sess2
            _jns = list({(r.get("job_number") or "").strip() for r in _need})
            async with _Sess2() as _db2:
                _rows = (await _db2.execute(_sa_text2("""
                    SELECT job_number, left(title, 20) AS t, budget, source
                      FROM tender_records
                     WHERE job_number = ANY(:jns) AND budget IS NOT NULL
                """), {"jns": _jns})).all()
            _lookup = {(r[0], r[1]): (r[2], r[3]) for r in _rows}
            _filled = 0
            for _r in _need:
                _hit = _lookup.get(
                    ((_r.get("job_number") or "").strip(), (_r.get("title") or "")[:20])
                )
                if _hit and _hit[0] is not None:
                    _r["budget"] = float(_hit[0])
                    # 標明出處 —— 不讓使用者以為這個數字是該來源公告上寫的
                    _r["budget_source"] = _hit[1]
                    _filled += 1
            if _filled:
                logging.getLogger(__name__).info(
                    "標案列表跨來源補金額：%d/%d 筆", _filled, len(_need)
                )
        except Exception as _e:
            # 補值失敗不該讓整個搜尋掛掉，但要出聲 ——
            # 靜默的話又會變成「金額一直是空的而沒有人知道為什麼」。
            logging.getLogger(__name__).warning("標案列表跨來源補值失敗: %s", _e)

    # 搜尋結果自動入庫 — 2026-04-24 改非同步背景任務，不阻塞 response
    try:
        import asyncio as _aio
        from app.db.database import AsyncSessionLocal
        from app.services.tender.cache import save_search_results

        async def _bg_save(records_snapshot):
            try:
                async with AsyncSessionLocal() as cache_db:
                    await save_search_results(cache_db, records_snapshot, source="pcc")
            except Exception as e:
                import logging as _logging
                _logging.getLogger(__name__).debug(f"bg tender save failed: {e}")

        _aio.create_task(_bg_save(list(result.get("records", []))[:50]))
    except Exception:
        pass

    # L51 task F: page view counter
    try:
        from app.services.tender.metrics import get_tender_metrics
        get_tender_metrics().page_view.labels(page="search").inc()
    except Exception:
        pass

    return SuccessResponse(data=result)


@router.post("/detail")
async def get_tender_detail(
    req: TenderDetailRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """取得標案詳情 (含歷次公告)

    支援兩種 ID：
    - PCC: unit_id + job_number (e.g. "A.19.4.8" + "115-1528-02")
    - ezbid: unit_id = 純數字 ezbid_id, job_number = None
    """
    # ezbid-only: 純數字 + 無 job_number → 查 DB tender_records
    is_ezbid = req.unit_id.isdigit() and not req.job_number
    if is_ezbid:
        # L51 task F: page view counter (ezbid path)
        try:
            from app.services.tender.metrics import get_tender_metrics
            get_tender_metrics().page_view.labels(page="detail").inc()
        except Exception:
            pass
        # 2026-04-24 修復：原 SQL 引用不存在的 ezbid_url 欄位導致 silent fail（ADR-0028）
        import logging as _log
        _logger = _log.getLogger(__name__)
        try:
            from app.db.database import async_session_maker
            from sqlalchemy import text as sa_text
            async with async_session_maker() as db:
                r = await db.execute(sa_text("""
                    SELECT title, unit_name, budget, announce_date, status,
                           unit_id, job_number, source, raw_data,
                           pcc_match_unit_id, pcc_match_job_number,
                           pcc_match_confidence, pcc_match_at,
                           id
                    FROM tender_records
                    WHERE ezbid_id = :eid
                    ORDER BY announce_date DESC LIMIT 1
                """), {"eid": req.unit_id})
                row = r.one_or_none()
                if row:
                    # 從 raw_data 取 ezbid_url；若無則組預設 URL
                    ezbid_url = f"https://cf.ezbid.tw/tender/{req.unit_id}"
                    if row[8]:
                        try:
                            import json as _json
                            raw = _json.loads(row[8])
                            ezbid_url = raw.get("ezbid_url") or ezbid_url
                        except Exception:
                            pass

                    result = {
                        "kind": "ezbid",  # ADR-0032 discriminated union
                        "ezbid_id": req.unit_id,
                        "unit_id": row[5] or req.unit_id,
                        "job_number": row[6] or "",
                        "title": row[0] or "",
                        "unit_name": row[1] or "",
                        "budget": row[2],
                        "announce_date": str(row[3]) if row[3] else "",
                        "status": row[4] or "",
                        "source": "ezbid_db",
                        "ezbid_url": ezbid_url,
                        # 2026-07-31 L3 回指：前端建案/關聯時要帶 tender_records.id，
                        # 否則案件無從記錄「我從哪個標案來」。
                        "tender_id": row[13],
                    }
                    # L51 (2026-05-28) ADR-0046 Phase 3 對應 PCC link 暴露給前端
                    # 233/27286 (0.85%) HIGH-matched ezbid 才有，UI 渲染「對應 PCC」區塊 + 跳轉
                    if row[9] and row[10]:
                        result["pcc_match"] = {
                            "unit_id": row[9],
                            "job_number": row[10],
                            "confidence": float(row[11]) if row[11] is not None else None,
                            "matched_at": str(row[12]) if row[12] else None,
                        }
                    # 如果有 PCC unit_id + job_number，嘗試補充 PCC 詳情
                    if row[5] and row[6] and not row[5].isdigit():
                        pcc_result = await service.get_tender_detail(row[5], row[6])
                        if pcc_result:
                            pcc_result["kind"] = "pcc"
                            pcc_result["ezbid_url"] = result["ezbid_url"]
                            return SuccessResponse(data=pcc_result)
                    return SuccessResponse(data=result)
                # row is None → 真的查無
                _logger.info(f"ezbid detail not found: ezbid_id={req.unit_id}")
        except Exception as e:
            _logger.error(f"ezbid detail query failed for {req.unit_id}: {e}", exc_info=True)
        return SuccessResponse(data=None, message="查無此 ezbid 標案")

    result = await service.get_tender_detail(
        unit_id=req.unit_id, job_number=req.job_number or "",
    )
    # ⚠️ 不能只判 `not result`：`get_tender_detail` 查不到時回的是一個
    # **有 key 但值都是空的 dict**，於是 `not result` 為 False、空殼被當成
    # 有資料送回前端，而前端的「查無此標案」判斷寫的是 `!detail` ——
    # 兩邊對「沒有資料」的定義不一樣，結果是畫面渲染成一片空白，
    # 使用者看到的是「壞掉」而不是「查無」。
    #
    # 2026-08-19 owner 連續回報三個 URL 都空白，實測其中
    # `NzEyODY4Nzk=` 這個 unit_id 在 DB 根本不存在 —— 那是**即時搜尋結果**
    # （搜尋結果入庫是背景非同步，使用者點得比入庫快），
    # 而外部 PCC 詳情頁有反爬限流（L77）所以也取不到。
    # 這種情況要講清楚，不是給一張空白頁。
    if not result or not str(result.get("title") or "").strip():
        return SuccessResponse(
            data=None,
            message="查無此標案內容 —— 可能是即時搜尋結果尚未收錄，或政府採購網詳情頁當下不可取得",
        )
    # ADR-0032: PCC response 明確標記 kind
    result["kind"] = "pcc"

    # 2026-08-16 L3 回指補完：ezbid 分支早在 07-31 就回傳 tender_id，
    # **PCC 分支一直沒有** —— 於是前端建案時送不出 tender_id，
    # `pm_cases.source_tender_id` 在 74 筆裡是 **0 筆有值**，
    # 「這個案件從哪個標案來」完全無從追溯（和美案即此形態）。
    # (unit_id, job_number) 在 60,296 筆 PCC 紀錄中**完全唯一**，可安全定位。
    try:
        from sqlalchemy import text as _sa_text
        from app.db.database import AsyncSessionLocal as _Sess
        async with _Sess() as _db:
            # 2026-08-19：改為**跨來源補值**。
            #
            # 原本這裡只查 `source='pcc'`，而註解自己就寫著「PCC 來源 budget
            # 全為 NULL」—— 也就是它去問一個已知永遠沒有答案的地方，
            # 結果就是詳情頁永遠沒有預算金額，使用者看到的是「找不到資料」。
            #
            # 同一個標案在 ezbid 常常是有金額的。實測（owner 回報的
            # `NAMR115131` 臺北港案）：PCC 那筆 budget 空、status 空；
            # ezbid 那筆 budget = 4,000,000、status =「公告」。
            # 全庫規模：跨來源可靠配對 14,105 組，其中
            # **pcc 缺 budget 而 ezbid 有的佔 13,913 組（98.6%）**，反向為 0。
            #
            # 配對鍵用 `job_number + 標題前 20 字`，**不用 pg_trgm**：
            # ADR-0046 的自動 link 就是用 pg_trgm 相似度計分（HIGH 門檻 0.85），
            # 而 pg_trgm 對中文無效 —— 實測這兩筆標題與機關名**完全相同**，
            # similarity 卻都是 **0.0000**，結構上永遠達不到門檻
            # （這就是 47,232 筆 ezbid 只 link 到 2,033 筆的原因）。
            # job_number 單獨不可靠（不同機關會撞號，實測 1,129 組標題不同），
            # 所以必須加上標題比對。
            _row = (await _db.execute(_sa_text("""
                SELECT p.id,
                       COALESCE(p.budget, x.budget)                  AS budget,
                       CASE WHEN p.budget IS NULL AND x.budget IS NOT NULL
                            THEN x.source END                        AS budget_from,
                       COALESCE(NULLIF(p.status, ''), x.status)      AS status
                  FROM tender_records p
                  LEFT JOIN LATERAL (
                      SELECT e.budget, e.status, e.source
                        FROM tender_records e
                       WHERE p.job_number IS NOT NULL AND p.job_number <> ''
                         AND e.job_number = p.job_number
                         AND left(e.title, 20) = left(p.title, 20)
                         AND e.source <> p.source
                       ORDER BY (e.budget IS NOT NULL) DESC, e.id
                       LIMIT 1
                  ) x ON TRUE
                 WHERE p.source = 'pcc' AND p.unit_id = :u AND p.job_number = :j
                 LIMIT 1
            """), {"u": req.unit_id, "j": req.job_number or ""})).one_or_none()
        if _row:
            result["tender_id"] = _row[0]
            # ⚠️ 不能用 `setdefault` —— `result` 這時**已經有** `budget` 這個 key
            # 而值是 `None`，setdefault 只在 key 不存在時才寫入，於是補到的值
            # 會被靜靜丟掉。2026-08-19 實測就撞到：`budget_source` 標成了 ezbid
            # （代表配對有命中），而 `budget` 仍是 None。
            # 判準要看「值有沒有內容」，不是「key 在不在」。
            if _row[1] is not None and not result.get("budget"):
                result["budget"] = str(_row[1])
                # 值若來自另一個來源就講明白 —— 不讓使用者以為
                # 這個數字是 PCC 公告上寫的。
                if _row[2]:
                    result["budget_source"] = _row[2]
            if _row[3] and not result.get("status"):
                result["status"] = _row[3]
    except Exception as _e:
        logging.getLogger(__name__).warning(
            "PCC 詳情回指查詢失敗 unit_id=%s job_number=%s: %s",
            req.unit_id, req.job_number, _e,
        )

    # ── 還是沒有金額 → 直接去 PCC 詳情頁抓 ──
    #
    # 2026-08-19：既有程式只把 PCC 詳情頁的**網址**組出來給前端，
    # 從來沒有真的去抓那一頁的內容 —— 而 `budget` 取自 DB，
    # PCC 來源 60,296 筆的 budget 全是 NULL，所以永遠是空的。
    #
    # 這推翻了 L77「enrichment 死結」的判斷。那條教訓講的是
    # **採購性質／底價**需要 org_id、而 org_id 只在被限流的頁面上；
    # 但**預算金額**就寫在詳情頁本文，不需要 org_id。
    # 實測三筆全部 HTTP 200、0.2~1.2 秒、無驗證碼，且值可交叉驗證：
    #   NzEzMDA1NzQ= → 4,000,000（與 ezbid 那筆一致）
    #   NzEyODY4Nzk= →   625,000（與該案 PM 合約金額一致）
    #
    # 只在沒有金額時才抓（有值的走 DB，不會多打一次外部）；
    # 抓到就寫回 DB，所以同一筆最多只會抓一次。
    if not result.get("budget"):
        try:
            import re as _re
            from urllib.parse import quote as _q2
            import httpx as _httpx
            # ⚠️ base64 尾端的 `=` 必須原樣送出：編成 %3D 會被 PCC 導向精簡 stub 頁
            _pcc_url = (
                "https://web.pcc.gov.tw/tps/QueryTender/query/searchTenderDetail?pkPmsMain="
                + _q2(str(req.unit_id), safe="=")
            )
            async with _httpx.AsyncClient(
                timeout=8, follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            ) as _c:
                _resp = await _c.get(_pcc_url)
            _m = _re.search(r"預算金額[^0-9]{0,40}([0-9,]{4,})", _resp.text or "")
            if _m:
                _amt = _m.group(1).replace(",", "")
                if _amt.isdigit() and int(_amt) > 0:
                    result["budget"] = _amt
                    result["budget_source"] = "pcc_detail"
                    # 寫回 DB —— 下一次同一筆就不必再打外部
                    try:
                        from sqlalchemy import text as _sa_text3
                        from app.db.database import AsyncSessionLocal as _Sess3
                        async with _Sess3() as _db3:
                            await _db3.execute(_sa_text3("""
                                UPDATE tender_records SET budget = :b, updated_at = NOW()
                                 WHERE source = 'pcc' AND unit_id = :u AND job_number = :j
                                   AND budget IS NULL
                            """), {"b": int(_amt), "u": req.unit_id, "j": req.job_number or ""})
                            await _db3.commit()
                    except Exception as _e3:
                        # 寫不回去不影響這次顯示，但要出聲（否則會變成每次都重抓）
                        logging.getLogger(__name__).warning("PCC 預算回寫失敗: %s", _e3)
        except Exception as _e2:
            # 外部抓取失敗不擋詳情頁 —— 沒有金額仍然要看得到標案本身
            logging.getLogger(__name__).info("PCC 詳情頁預算抓取未成功: %s", _e2)
    # L51 task F: page view counter
    try:
        from app.services.tender.metrics import get_tender_metrics
        get_tender_metrics().page_view.labels(page="detail").inc()
    except Exception:
        pass
    return SuccessResponse(data=result)


@router.post("/detail-full")
async def get_tender_detail_full(
    req: TenderDetailRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """標案完整戰情 — 詳情 + 相似標案 + 機關生態 + 競爭對手 (並行, Redis 快取)"""
    import asyncio
    import json as _json
    from app.services.tender.analytics import TenderAnalyticsService

    # Redis 快取 (整個 detail-full 結果, 2hr)
    try:
        from app.core.redis_client import get_redis
        _redis = await get_redis()
        if _redis:
            cache_key = f"tender:detail-full:{req.unit_id}:{req.job_number}"
            cached = await _redis.get(cache_key)
            if cached:
                return SuccessResponse(data=_json.loads(cached))
    except Exception:
        _redis = None

    analytics = TenderAnalyticsService()

    # Step 1: 取得詳情 (需先知道機關名稱)
    detail = await service.get_tender_detail(req.unit_id, req.job_number)
    if not detail:
        return SuccessResponse(data=None, message="查無此標案")

    agency_name = detail.get("unit_name", "")

    # Step 2: 並行取得戰情+底價+機關生態 (傳入 detail 避免重複查詢)
    from app.services.tender.analytics_battle import battle_room as _battle_room
    battle_task = _battle_room(service, req.unit_id, req.job_number, detail=detail)
    from app.services.tender.analytics_price import price_analysis as _price_analysis
    price_task = _price_analysis(service, req.unit_id, req.job_number, detail=detail)
    async def _empty_org(): return {}
    org_task = analytics.org_ecosystem(agency_name, pages=3) if agency_name else _empty_org()

    results = await asyncio.gather(battle_task, price_task, org_task, return_exceptions=True)

    battle = results[0] if not isinstance(results[0], Exception) else {}
    price = results[1] if not isinstance(results[1], Exception) else {}
    org_eco = results[2] if not isinstance(results[2], Exception) else {}

    # 從相似標案推估決標折率
    estimate = None
    if battle.get("similar_tenders") and price and not price.get("error"):
        budget_val = price.get("prices", {}).get("budget")
        if budget_val and not price.get("prices", {}).get("award_amount"):
            import re
            ratios = []
            for st in battle.get("similar_tenders", []):
                try:
                    st_detail = await service.get_tender_detail(st.get("unit_id", ""), st.get("job_number", ""))
                    if not st_detail:
                        continue
                    for evt in st_detail.get("events", []):
                        ad = evt.get("award_details") or {}
                        ed = evt.get("detail") or {}
                        b_raw = ed.get("budget", "")
                        b = float(re.sub(r'[^\d.]', '', str(b_raw).replace(',', ''))) if b_raw else None
                        a = ad.get("total_award_amount")
                        if b and a and b > 0:
                            ratios.append(a / b)
                            break
                except Exception:
                    continue

            if ratios:
                avg_ratio = sum(ratios) / len(ratios)
                estimate = {
                    "avg_ratio": round(avg_ratio * 100, 1),
                    "sample_count": len(ratios),
                    "estimated_award": round(budget_val * avg_ratio),
                    "budget": budget_val,
                }

    result_data = {
        "detail": detail,
        "battle_room": battle,
        "org_ecosystem": org_eco,
        "price_analysis": price if not price.get("error") else None,
        "price_estimate": estimate,
    }

    # 存入 Redis 快取 (2hr)
    try:
        if _redis:
            await _redis.setex(cache_key, 7200, _json.dumps(result_data, default=str, ensure_ascii=False))
    except Exception:
        pass

    return SuccessResponse(data=result_data)


@router.post("/search-company")
async def search_by_company(
    req: TenderCompanySearchRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """依廠商名稱搜尋得標紀錄"""
    result = await service.search_by_company(
        company_name=req.company_name, page=req.page,
    )
    return SuccessResponse(data=result)


@router.post("/recommend")
async def recommend_tenders(
    req: TenderRecommendRequest,
    service: TenderSearchService = Depends(get_tender_service),
    db: AsyncSession = Depends(get_db),
):
    """智能推薦 v2 (L51.5 統一版, 2026-05-29)

    Owner 反饋：/tender/search 推薦 14 筆與 LINE 推薦 3 筆無關聯，管理混淆。

    修法：兩端統一使用 business_recommendation.find_business_recommendations
          (3 條基本面 AND + 3 重業務信號 OR + 加權排序)

    保留原 response 結構 (keywords/total/today_records/records) 不破壞 frontend，
    新增 match_signals 標籤透明化推薦原因。
    """
    from app.extended.models.tender import TenderSubscription
    from app.services.tender.business_recommendation import find_business_recommendations

    # 取訂閱關鍵字（給 frontend 顯示「依訂閱關鍵字推薦」label）
    subs = await db.execute(
        select(TenderSubscription).where(TenderSubscription.is_active == True)  # noqa: E712
    )
    keywords = [s.keyword for s in subs.scalars().all()]

    # L51.5 統一邏輯：用 LINE 業務推薦同一個 SQL
    # days_back=7 (與 LINE 1 日不同 — UI 場景看更多)
    # budget_min=1_000_000 (與 LINE 同)
    # limit=50 (UI 場景上限，LINE 是 20)
    recs = await find_business_recommendations(
        db, days_back=7, budget_min=1_000_000, limit=50,
    )

    def adapt(r):
        """v2 結果 → frontend TenderRecord shape + 透明化標籤"""
        return {
            "date": r.get("announce_date", ""),
            "raw_date": int(
                str(r.get("announce_date", "0")).replace("-", "")
            ) if r.get("announce_date") else 0,
            "title": r.get("title", ""),
            "type": "",  # v2 SQL 暫無此欄
            "category": "",
            "unit_id": r.get("unit_id", ""),
            "unit_name": r.get("unit_name", ""),
            "job_number": r.get("job_number", "") or "",
            "company_names": [], "company_ids": [],
            "winner_names": [], "bidder_names": [],
            "tender_api_url": "",
            "source": r.get("source", ""),
            "budget": r.get("budget", 0),
            # L51.5 frontend 既有欄位 (gold tag)
            "matched_keyword": (
                r["matched_keywords"][0] if r.get("matched_keywords") else None
            ),
            # L51.5 透明化標籤（前端可用於 tooltip / detail view）
            "match_signals": {
                "matched_keywords": r.get("matched_keywords", []),
                "is_contracted": r.get("is_contracted", False),
                "is_cooperated": r.get("is_cooperated", False),
                "agency_match_count": r.get("agency_match_count", 0),
                "match_score": (
                    (3 if r.get("matched_keywords") else 0)
                    + (2 if r.get("is_contracted") else 0)
                    + (1 if r.get("is_cooperated") else 0)
                ),
            },
        }

    # 業務推薦 = Option B 相關性推薦（關鍵字＝工項含同義詞 / 精準局處工程）；可為 0＝本期無相關（誠實）
    business_records = [adapt(r) for r in recs]

    # 今日最新 = 今日「招標案件」（活動量）。L75 卡片語意（owner 定案 Option A，2026-06-16）：
    #   「今日最新」反映系統活動，不套相關性/預算過濾（否則 PCC budget 多 NULL + Option B 過濾
    #    → 卡片恆 0 看似系統壞）。「業務推薦」維持相關性過濾。兩卡語意分離。
    #   2026-06-16 口徑（owner 定案）：「今日最新」＝今日**完整標案機會**（含報價單/企劃書，排決標，
    #     去重 job_number）。與 dashboard「今日標案」同源同口徑 → 共用 fetch_complete_tenders（SSOT，
    #     杜絕兩頁數字漂移）。完整去重 ≈891。
    from app.services.tender.business_recommendation import (
        fetch_complete_tenders, count_complete_tenders,
    )
    # today_count＝真實去重「筆數」(不受清單上限截斷)，與 dashboard「今日標案」同源；
    #   today_records 清單上限 2000 供表格瀏覽（卡片數字用 today_count，解 1000 截斷 ≠ 1237）。
    today_count = await count_complete_tenders(db, days_back=0)
    today_records = await fetch_complete_tenders(db, days_back=0, limit=2000)

    return SuccessResponse(data={
        "keywords": keywords,
        "total": len(business_records),
        "today_count": today_count,       # 今日最新（活動量，真 count = dashboard 今日標案）
        "today_records": today_records,   # 今日最新清單
        "records": business_records,      # 業務推薦（Option B 相關性）
    })


@router.post("/realtime")
async def realtime_tenders(req: TenderSearchRequest):
    """即時標案 — 爬取 ezbid.tw 最新資料 (補充 PCC API 延遲)"""
    from app.services.tender.ezbid_scraper import EzbidScraper

    category_map = {"工程": "WORK", "勞務": "SERV", "財物": "PPTY"}
    cat = category_map.get(req.category or "", "ALL")

    try:
        from app.core.redis_client import get_redis_client
        redis = get_redis_client()
    except Exception:
        redis = None

    scraper = EzbidScraper(redis_client=redis)
    result = await scraper.fetch_latest(query=req.query, category=cat, pages=1)
    return SuccessResponse(data=result)
