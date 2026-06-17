"""
標案檢索查詢服務

封裝 pcc-api.openfun.app 政府電子採購網開放資料 API，
提供標案搜尋、詳情查詢、廠商比對、智能推薦等功能。

資料來源: g0v 開放標案資料 (https://pcc-api.openfun.app)

Version: 1.0.0
Created: 2026-04-01
"""
import logging
import json
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

import httpx

from .data_transformer import (
    normalize_record,
    normalize_detail,
    clean_category,
    match_category,
    parse_amount,
    build_tender_graph,
)

logger = logging.getLogger(__name__)

PCC_API_BASE = "https://pcc-api.openfun.app/api"
REQUEST_TIMEOUT = 15.0

# 乾坤測繪核心業務關鍵字 (用於智能推薦)
CK_BUSINESS_KEYWORDS = [
    "測量", "空拍", "無人機", "UAV", "光達", "LiDAR", "3D掃描",
    "透地雷達", "GPR", "地形", "地籍", "航測", "正射影像",
    "水深測量", "建築線", "土地複丈", "土方", "施工放樣",
    "GIS", "圖資", "地理資訊",
]

# 標案分類對照
TENDER_CATEGORIES = {
    "工程": "engineering",
    "勞務": "service",
    "財物": "property",
}


class TenderSearchService:
    """政府標案檢索服務"""

    def __init__(self, redis_client=None):
        self._redis = redis_client

    async def search_by_title(
        self,
        query: str,
        page: int = 1,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        依標題搜尋標案

        Args:
            query: 搜尋關鍵字
            page: 頁碼 (1-based)
            category: 分類篩選 (工程/勞務/財物)

        Returns:
            {query, page, total_records, total_pages, records: [...]}
        """
        cache_key = f"tender:search:{query}:{page}:{category or 'all'}"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        # DB-first: 先查本地 tender_records (毫秒級)
        # L49.13 (2026-05-28): 放寬 short-circuit 條件 — 原本要 >=3 筆才 return，
        # 不熱門關鍵字（如「劉銘傳」DB 只 1-2 筆）跳外部 PCC API 5-15s 拖慢。
        # 改為 DB 有任何資料即 return（外部 API 由 scheduler 每日 3 次同步背景補）。
        # 修前：owner 「今日最新」24s / 修後：預期 < 200ms（DB GIN trigram index）。
        try:
            from app.db.database import async_session_maker
            from .cache import search_from_db
            async with async_session_maker() as db:
                db_results = await search_from_db(db, query, limit=50)
                if db_results:  # 放寬：原 >=3，改為 >=1
                    from .data_transformer import dedup_records
                    db_result = {
                        "query": query, "page": 1,
                        "total_records": len(db_results),
                        "total_pages": 1,
                        "records": dedup_records(db_results),
                        "source": "db",
                    }
                    await self._set_cache(cache_key, db_result, ttl=600)
                    # 背景更新外部 API (不阻塞)
                    return db_result
        except Exception:
            pass

        url = f"{PCC_API_BASE}/searchbytitle"
        params = {"query": query, "page": page}

        data = await self._fetch(url, params)
        if not data:
            return {"query": query, "page": page, "total_records": 0, "total_pages": 0, "records": []}

        # 後處理: 分類篩選 + 欄位標準化
        records = data.get("records", [])
        if category:
            records = [r for r in records if self._match_category(r, category)]

        from .data_transformer import dedup_records
        normalized = [self._normalize_record(r) for r in records]
        result = {
            "query": query,
            "page": data.get("page", page),
            "total_records": data.get("total_records", 0),
            "total_pages": data.get("total_pages", 0),
            "records": dedup_records(normalized),
        }

        await self._set_cache(cache_key, result, ttl=7200)  # 2 hr
        return result

    async def get_tender_detail(
        self, unit_id: str, job_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        取得標案詳情

        Args:
            unit_id: 機關代碼 (e.g. "3.87.16")
            job_number: 標案案號

        Returns:
            標案完整資訊 (含機關/採購/招標/決標)
        """
        cache_key = f"tender:detail:{unit_id}:{job_number}"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        # DB 快取優先：精確查 tender_records（毫秒級）
        # L49.12 (2026-05-28) 修兩個 bug：
        # 1. 原 search_from_db 是 trigram 模糊查詢，對 "unit_id job_number" 串接
        #    無命中（unit_id base64 + job_number 16 字元短 query 過 threshold）
        #    → 改精確 SQL: WHERE unit_id = :uid AND job_number = :jn
        # 2. 原 DB 有資料但 set_cache 後沒 return，落到外部 API fallback 失敗 → None
        #    → DB 有資料即 return；外部 API 只在 DB 無時 fallback
        db_quick_result = None
        try:
            from app.db.database import async_session_maker
            from sqlalchemy import text as sa_text
            async with async_session_maker() as db:
                r = await db.execute(sa_text("""
                    SELECT title, unit_name, budget, award_amount,
                           announce_date, status, source, raw_data
                    FROM tender_records
                    WHERE unit_id = :uid AND job_number = :jn
                    ORDER BY announce_date DESC NULLS LAST
                    LIMIT 1
                """), {"uid": unit_id, "jn": job_number})
                row = r.one_or_none()
                if row:
                    # L49.12.1 (2026-05-28): 補 frontend 期望的 latest.detail + events
                    # 結構，讓 isPccDetail+pccDetail.latest.detail 渲染條件成立。
                    # 否則 frontend 走到 `: <Empty />` 顯示「無此資料」 —
                    # 雖然 DB 有 record 但用戶感受是「壞了」。
                    # 2026-06-17：PCC 已不支援 atmAwardAction deep-link（404）；且我們的 unit_id 為
                    #   base64、無 PCC tender pk → 無法可靠直連。改 Google 精準搜尋（案號必中 PCC 頁）。
                    from urllib.parse import quote as _q
                    pcc_url = (
                        "https://www.google.com/search?q="
                        + _q(f'"{job_number}" {row[0] or ""} 政府電子採購網')
                    )
                    announce_str = str(row[4]) if row[4] else ""
                    db_quick_result = {
                        "unit_id": unit_id,
                        "job_number": job_number,
                        "title": row[0] or "",
                        "unit_name": row[1] or "",
                        "budget": row[2],
                        "award_amount": row[3],
                        "announce_date": announce_str,
                        "status": row[5] or "",
                        "source": row[6] or "db_cache",
                        # frontend 期望結構（避免渲染為 Empty）
                        "latest": {
                            "detail": {
                                "agency_name": row[1] or "",
                                "agency_unit": "",
                                "contact_person": "",
                                "contact_phone": "",
                                "contact_email": "",
                                "agency_address": "",
                                "announce_date": announce_str,
                                "deadline": "",
                                "open_date": "",
                                "budget": str(row[2]) if row[2] else "",
                                "method": "",
                                "award_method": "",
                                "status": row[5] or "",
                                "procurement_type": "",
                                "pcc_url": pcc_url,
                            }
                        },
                        "events": [],  # 空陣列讓 tab「尚無投標/得標紀錄」正常
                        "merged_detail": {},
                    }
                    await self._set_cache(cache_key, db_quick_result, ttl=300)
        except Exception:
            pass  # DB 不可用時 fallback 到外部 API

        # 嘗試外部 API 取得「完整」詳情（含歷次公告 / 決標明細等）
        url = f"{PCC_API_BASE}/tender"
        params = {"unit_id": unit_id, "job_number": job_number}

        data = await self._fetch(url, params)
        if not data or not data.get("records"):
            # L49.12: 外部 API 失敗 → 若 DB 有快資料就用（業務優先於完整性）
            if db_quick_result:
                return db_quick_result
            return None

        result = self._normalize_detail(data)
        await self._set_cache(cache_key, result, ttl=14400)  # 4 hr
        return result

    async def search_by_org(
        self, org_name: str, page: int = 1
    ) -> Dict[str, Any]:
        """依機關名稱搜尋標案"""
        cache_key = f"tender:org:{org_name}:{page}"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        url = f"{PCC_API_BASE}/searchbyorgname"
        params = {"query": org_name, "page": page}

        data = await self._fetch(url, params)
        if not data:
            # Fallback: 用標題搜尋
            return await self.search_by_title(query=org_name, page=page)

        result = {
            "query": org_name,
            "page": data.get("page", page),
            "total_records": data.get("total_records", 0),
            "total_pages": data.get("total_pages", 0),
            "records": [self._normalize_record(r) for r in data.get("records", [])],
        }

        await self._set_cache(cache_key, result, ttl=1800)
        return result

    async def search_by_company(
        self, company_name: str, page: int = 1
    ) -> Dict[str, Any]:
        """依廠商名稱搜尋得標紀錄"""
        cache_key = f"tender:company:{company_name}:{page}"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        url = f"{PCC_API_BASE}/searchbycompanyname"
        params = {"query": company_name, "page": page}

        data = await self._fetch(url, params)
        if not data:
            return {"query": company_name, "page": page, "total_records": 0, "records": []}

        from .data_transformer import dedup_records
        result = {
            "query": company_name,
            "page": data.get("page", page),
            "total_records": data.get("total_records", 0),
            "total_pages": data.get("total_pages", 0),
            "records": dedup_records([self._normalize_record(r) for r in data.get("records", [])]),
        }

        await self._set_cache(cache_key, result, ttl=1800)
        return result

    async def recommend_tenders(
        self, keywords: Optional[List[str]] = None, page: int = 1
    ) -> Dict[str, Any]:
        """
        智能推薦 — 業務推薦 + 今日最新標案

        Returns:
            {keywords, total, records (業務推薦), today_records (今日全量)}
        """
        import asyncio
        kw_list = keywords or CK_BUSINESS_KEYWORDS[:5]

        # === 並行: 業務推薦 + ezbid 今日全量 ===
        async def fetch_kw(kw):
            return kw, await self.search_by_title(kw, page=1)

        async def fetch_today():
            """ezbid 今日全量 — 統一服務層 (與 dashboard 共享快取)"""
            from .ezbid_scraper import EzbidScraper
            scraper = EzbidScraper()
            result = await scraper.get_today_all()
            return result.get("records", [])

        tasks = [fetch_kw(kw) for kw in kw_list[:5]]
        tasks.append(fetch_today())
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 分離結果: 前 N 個是關鍵字搜尋，最後一個是 ezbid
        kw_results = results[:-1]
        ezbid_result = results[-1] if not isinstance(results[-1], Exception) else []

        # 業務推薦
        all_records = []
        seen_jobs = set()
        for item in kw_results:
            if isinstance(item, Exception):
                continue
            kw, result = item
            for r in result.get("records", [])[:10]:
                if r["job_number"] not in seen_jobs:
                    seen_jobs.add(r["job_number"])
                    r["matched_keyword"] = kw
                    all_records.append(r)
        all_records.sort(key=lambda r: r.get("date", 0), reverse=True)

        # 今日最新 (ezbid 全量轉統一格式)
        today_records = []
        seen_today = set()
        for r in ezbid_result:
            key = r.get("ezbid_id", "")
            if key and key not in seen_today:
                seen_today.add(key)
                today_records.append({
                    "date": r.get("date", ""),
                    "title": r.get("title", ""),
                    "type": r.get("type", ""),
                    "category": r.get("category", ""),
                    "unit_id": r.get("ezbid_id", ""),
                    "unit_name": r.get("unit_name", ""),
                    "job_number": "",
                    "winner_names": [],
                    "source": "ezbid",
                    "budget": r.get("budget"),
                    "days_left": r.get("days_left"),
                })

        return {
            "keywords": kw_list[:5],
            "total": len(all_records),
            "records": all_records[:50],
            "today_records": today_records,
            "today_total": len(today_records),
        }

    # =========================================================================
    # 內部方法
    # =========================================================================

    async def _fetch(self, url: str, params: dict) -> Optional[dict]:
        """HTTP GET with timeout and error handling

        PCC API 偶爾以 Big5 編碼回傳，需嘗試多種 charset 解碼。
        """
        import json as _json
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"PCC API {resp.status_code}: {url} {params}")
                    return None

                # 嘗試按 response charset 解碼，回退 utf-8 → big5
                content = resp.content
                for encoding in ("utf-8", "big5", "latin-1"):
                    try:
                        text = content.decode(encoding)
                        return _json.loads(text)
                    except (UnicodeDecodeError, _json.JSONDecodeError):
                        continue

                logger.warning(f"PCC API all decode attempts failed: {url}")
                return None
        except Exception as e:
            logger.error(f"PCC API error: {e}")
            return None

    # ── Data transformation (delegated to tender_data_transformer.py) ──

    def _normalize_record(self, record: dict) -> dict:
        return normalize_record(record)

    def _normalize_detail(self, data: dict) -> dict:
        return normalize_detail(data)

    def _extract_award_details(self, detail: dict) -> dict:
        from .data_transformer import extract_award_details
        return extract_award_details(detail)

    @staticmethod
    def _parse_amount(raw: Any) -> Optional[float]:
        return parse_amount(raw)

    def _match_category(self, record: dict, category: str) -> bool:
        return match_category(record, category)

    @staticmethod
    def _clean_category(raw: str) -> str:
        return clean_category(raw)

    async def build_tender_graph(
        self, query: str, max_tenders: int = 20
    ) -> Dict[str, Any]:
        """建構標案知識圖譜 — 機關→標案→廠商 關係網絡"""
        result = await self.search_by_title(query, page=1)
        records = result.get("records", [])[:max_tenders]
        return build_tender_graph(records, query)

    async def _get_cache(self, key: str) -> Optional[dict]:
        if not self._redis:
            return None
        try:
            val = await self._redis.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None

    async def _set_cache(self, key: str, data: dict, ttl: int = 1800):
        if not self._redis:
            return
        try:
            await self._redis.set(key, json.dumps(data, ensure_ascii=False, default=str), ex=ttl)
        except Exception:
            pass
