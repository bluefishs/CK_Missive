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

from app.services.tender_data_transformer import (
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

        url = f"{PCC_API_BASE}/searchbytitle"
        params = {"query": query, "page": page}

        data = await self._fetch(url, params)
        if not data:
            return {"query": query, "page": page, "total_records": 0, "total_pages": 0, "records": []}

        # 後處理: 分類篩選 + 欄位標準化
        records = data.get("records", [])
        if category:
            records = [r for r in records if self._match_category(r, category)]

        result = {
            "query": query,
            "page": data.get("page", page),
            "total_records": data.get("total_records", 0),
            "total_pages": data.get("total_pages", 0),
            "records": [self._normalize_record(r) for r in records],
        }

        await self._set_cache(cache_key, result, ttl=1800)  # 30 min
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

        url = f"{PCC_API_BASE}/tender"
        params = {"unit_id": unit_id, "job_number": job_number}

        data = await self._fetch(url, params)
        if not data or not data.get("records"):
            return None

        result = self._normalize_detail(data)
        await self._set_cache(cache_key, result, ttl=3600)  # 1 hr
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

        result = {
            "query": company_name,
            "page": data.get("page", page),
            "total_records": data.get("total_records", 0),
            "total_pages": data.get("total_pages", 0),
            "records": [self._normalize_record(r) for r in data.get("records", [])],
        }

        await self._set_cache(cache_key, result, ttl=1800)
        return result

    async def recommend_tenders(
        self, keywords: Optional[List[str]] = None, page: int = 1
    ) -> Dict[str, Any]:
        """
        智能推薦 — 依乾坤核心業務關鍵字搜尋相關標案

        Args:
            keywords: 自訂關鍵字 (None = 使用預設業務關鍵字)
            page: 頁碼
        """
        import asyncio
        kw_list = keywords or CK_BUSINESS_KEYWORDS[:5]

        # 並行搜尋 (加速 3 倍)
        async def fetch_kw(kw):
            return kw, await self.search_by_title(kw, page=1)

        results = await asyncio.gather(*[fetch_kw(kw) for kw in kw_list[:3]], return_exceptions=True)

        all_records = []
        seen_jobs = set()
        for item in results:
            if isinstance(item, Exception):
                continue
            kw, result = item
            for r in result.get("records", [])[:10]:
                if r["job_number"] not in seen_jobs:
                    seen_jobs.add(r["job_number"])
                    r["matched_keyword"] = kw
                    all_records.append(r)

        # 依日期排序 (最新優先)
        all_records.sort(key=lambda r: r.get("date", 0), reverse=True)

        return {
            "keywords": kw_list[:3],
            "total": len(all_records),
            "records": all_records[:20],
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
        from app.services.tender_data_transformer import extract_award_details
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
