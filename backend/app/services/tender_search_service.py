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

    def _normalize_record(self, record: dict) -> dict:
        """標準化列表記錄"""
        brief = record.get("brief", {})
        companies = brief.get("companies", {})

        # 解析日期
        raw_date = record.get("date", 0)
        date_str = ""
        if raw_date:
            try:
                d = datetime.strptime(str(raw_date), "%Y%m%d")
                date_str = d.strftime("%Y-%m-%d")
            except ValueError:
                date_str = str(raw_date)

        # 識別得標廠商 vs 投標廠商
        # key 格式: "決標品項:第1品項:得標廠商1:得標廠商" → 得標
        #           "決標品項:第1品項:未得標廠商1:未得標廠商" → 未得標
        name_key = companies.get("name_key", {})
        winner_names = []
        bidder_names = []
        for name, keys in name_key.items():
            is_winner = any(
                "得標廠商" in k and "未得標" not in k
                for k in keys
            )
            if is_winner:
                winner_names.append(name)
            else:
                bidder_names.append(name)

        return {
            "date": date_str,
            "raw_date": raw_date,
            "title": brief.get("title", ""),
            "type": brief.get("type", ""),
            "category": self._clean_category(brief.get("category", "")),
            "unit_id": record.get("unit_id", ""),
            "unit_name": record.get("unit_name", ""),
            "job_number": record.get("job_number", ""),
            "company_names": companies.get("names", []),
            "company_ids": companies.get("ids", []),
            "winner_names": winner_names,
            "bidder_names": bidder_names,
            "tender_api_url": record.get("tender_api_url", ""),
            "matched_keyword": record.get("matched_keyword"),
        }

    def _normalize_detail(self, data: dict) -> dict:
        """標準化詳情資料"""
        unit_name = data.get("unit_name", "")
        records = data.get("records", [])
        if not records:
            return {"unit_name": unit_name, "events": []}

        events = []
        for rec in records:
            detail = rec.get("detail", {})
            events.append({
                "date": rec.get("date"),
                "type": rec.get("brief", {}).get("type", ""),
                "title": rec.get("brief", {}).get("title", ""),
                "category": rec.get("brief", {}).get("category", ""),
                "job_number": rec.get("job_number", ""),
                "detail": {
                    "agency_name": detail.get("機關資料:機關名稱", ""),
                    "agency_unit": detail.get("機關資料:單位名稱", ""),
                    "agency_address": detail.get("機關資料:機關地址", ""),
                    "contact_person": detail.get("機關資料:聯絡人", ""),
                    "contact_phone": detail.get("機關資料:聯絡電話", ""),
                    "contact_email": detail.get("機關資料:電子郵件信箱", ""),
                    "budget": detail.get("採購資料:預算金額", ""),
                    "procurement_type": detail.get("採購資料:標的分類", ""),
                    "method": detail.get("招標資料:招標方式", ""),
                    "award_method": detail.get("招標資料:決標方式", ""),
                    "announce_date": detail.get("招標資料:公告日", ""),
                    "deadline": detail.get("招標資料:截止投標", detail.get("領投開標:截止投標", "")),
                    "open_date": detail.get("領投開標:開標日期", ""),
                    "status": detail.get("招標資料:招標狀態", ""),
                    "pcc_url": detail.get("url", ""),
                },
                "award_details": self._extract_award_details(detail),
                "companies": rec.get("brief", {}).get("companies", {}).get("names", []),
            })

        # 回填 unit_name: 優先 PCC 頂層 → event detail.agency_name
        if not unit_name and events:
            unit_name = events[0].get("detail", {}).get("agency_name", "") or ""

        # 合併所有 events 的 detail — 不同公告類型有不同欄位
        # (決標公告有決標方式, 招標公告有招標方式)
        merged_detail = {}
        for evt in events:
            for k, v in evt.get("detail", {}).items():
                if v and not merged_detail.get(k):  # 取第一個非空值
                    merged_detail[k] = v

        return {
            "unit_name": unit_name,
            "job_number": records[0].get("job_number", ""),
            "title": records[0].get("brief", {}).get("title", ""),
            "events": events,
            "latest": events[0] if events else None,
            "merged_detail": merged_detail,  # 所有事件合併的完整資料
        }

    def _extract_award_details(self, detail: dict) -> dict:
        """從 PCC API 決標資料中提取價格/得標明細

        PCC API 使用中文鍵名，格式如：
          - 決標資料:決標金額, 決標資料:決標日期
          - 採購資料:底價
          - 決標品項:第N品項:得標廠商, 決標品項:第N品項:決標金額
        """
        try:
            award_date = detail.get("決標資料:決標日期") or None
            total_award_amount = self._parse_amount(
                detail.get("決標資料:決標金額")
            )
            floor_price = self._parse_amount(
                detail.get("採購資料:底價")
            )

            # 提取各品項得標資訊
            award_items = []
            for i in range(1, 21):  # 最多掃 20 品項
                item_prefix = f"決標品項:第{i}品項"
                winner_key = f"{item_prefix}:得標廠商"
                amount_key = f"{item_prefix}:決標金額"

                # 得標廠商可能以編號後綴出現: 得標廠商1:得標廠商
                winner_name = detail.get(winner_key)
                if winner_name is None:
                    # 嘗試 "得標廠商1:得標廠商" 格式
                    alt_key = f"{item_prefix}:得標廠商1:得標廠商"
                    winner_name = detail.get(alt_key)

                if winner_name is None and detail.get(amount_key) is None:
                    # 此品項不存在，停止掃描
                    break

                award_items.append({
                    "item_no": i,
                    "winner": winner_name,
                    "amount": self._parse_amount(detail.get(amount_key)),
                })

            return {
                "award_date": award_date,
                "total_award_amount": total_award_amount,
                "floor_price": floor_price,
                "award_items": award_items,
            }
        except Exception as e:
            logger.warning(f"Failed to extract award details: {e}")
            return {
                "award_date": None,
                "total_award_amount": None,
                "floor_price": None,
                "award_items": [],
            }

    @staticmethod
    def _parse_amount(raw: Any) -> Optional[float]:
        """安全解析金額字串為浮點數，支援千分位逗號"""
        if raw is None:
            return None
        try:
            import re
            cleaned = re.sub(r'[^\d.]', '', str(raw).replace(',', ''))
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    def _match_category(self, record: dict, category: str) -> bool:
        """檢查標案是否匹配分類"""
        cat = record.get("brief", {}).get("category", "")
        return category in cat

    @staticmethod
    def _clean_category(raw: str) -> str:
        """Clean category: '482-勞務類' → '勞務類', '2-工程類' → '工程類'"""
        if not raw:
            return "未分類"
        import re
        # Remove leading numbers + dash: "482-勞務類" → "勞務類"
        cleaned = re.sub(r'^[\d.]+-', '', raw).strip()
        # Remove parenthetical codes: "勞務類(482)" → "勞務類"
        cleaned = re.sub(r'\([\d.]+\)', '', cleaned).strip()
        return cleaned or raw

    async def build_tender_graph(
        self, query: str, max_tenders: int = 20
    ) -> Dict[str, Any]:
        """
        建構標案知識圖譜 — 機關→標案→廠商 關係網絡

        Returns:
            {nodes: [{id, name, type, ...}], edges: [{source, target, relation}]}
        """
        result = await self.search_by_title(query, page=1)
        records = result.get("records", [])[:max_tenders]

        nodes: Dict[str, dict] = {}
        edges: list = []

        for r in records:
            # 標案節點
            tender_id = f"tender:{r['job_number']}"
            nodes[tender_id] = {
                "id": tender_id, "name": r["title"][:40],
                "type": "tender", "category": r.get("category", ""),
                "date": r.get("date", ""),
            }

            # 機關節點
            if r.get("unit_name"):
                unit_id = f"agency:{r['unit_id']}"
                if unit_id not in nodes:
                    nodes[unit_id] = {
                        "id": unit_id, "name": r["unit_name"],
                        "type": "agency",
                    }
                edges.append({
                    "source": unit_id, "target": tender_id,
                    "relation": "招標",
                })

            # 廠商節點
            for i, company in enumerate(r.get("company_names", [])):
                comp_id = f"company:{r.get('company_ids', [''])[i] if i < len(r.get('company_ids', [])) else company}"
                if comp_id not in nodes:
                    nodes[comp_id] = {
                        "id": comp_id, "name": company,
                        "type": "company",
                    }
                edges.append({
                    "source": tender_id, "target": comp_id,
                    "relation": "得標",
                })

        return {
            "query": query,
            "nodes": list(nodes.values()),
            "edges": edges,
            "stats": {
                "tenders": len([n for n in nodes.values() if n["type"] == "tender"]),
                "agencies": len([n for n in nodes.values() if n["type"] == "agency"]),
                "companies": len([n for n in nodes.values() if n["type"] == "company"]),
                "edges": len(edges),
            },
        }

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
