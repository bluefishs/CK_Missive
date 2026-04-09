"""
ezbid.tw 標案爬蟲 — 即時資料補充源

爬取 cf.ezbid.tw 最新標案列表，補充 g0v PCC API 1-5 天的資料延遲。
資料來源: https://cf.ezbid.tw (每日 3 次與 PCC 同步)

用法:
    scraper = EzbidScraper(redis_client)
    records = await scraper.fetch_latest(category='WORK', pages=2)

Version: 1.0.0
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EZBID_BASE = "https://cf.ezbid.tw"
REQUEST_TIMEOUT = 15.0
MAX_RETRIES = 3
BACKOFF_BASE = 2.0
BLOCK_THRESHOLD = 5

# ezbid 分類對照
EZBID_CATEGORIES = {
    "ALL": "全部",
    "WORK": "工程",
    "SERV": "勞務",
    "PPTY": "財物",
}


class EzbidScraper:
    """ezbid.tw 標案爬蟲"""

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._consecutive_failures: int = 0

    async def fetch_latest(
        self,
        query: Optional[str] = None,
        category: str = "ALL",
        pages: int = 1,
        per_page: int = 15,
    ) -> Dict[str, Any]:
        """
        爬取最新標案列表

        Args:
            query: 搜尋關鍵字 (None = 全部最新)
            category: 分類 (ALL/WORK/SERV/PPTY)
            pages: 爬取頁數
            per_page: 每頁筆數 (15/30/50/100)

        Returns:
            {total: int, records: [...], source: 'ezbid', fetched_at: str}
        """
        cache_key = f"ezbid:{query or 'latest'}:{category}:{pages}"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        all_records = []
        for page in range(1, pages + 1):
            records = await self._fetch_page(query, category, page, per_page)
            all_records.extend(records)

        result = {
            "total": len(all_records),
            "records": all_records,
            "source": "ezbid",
            "fetched_at": datetime.utcnow().isoformat(),
        }

        await self._set_cache(cache_key, result, ttl=600)  # 10 min
        return result

    async def get_today_all(self) -> Dict[str, Any]:
        """
        今日全量標案 — 統一服務入口 (dashboard/search/recommend 共用)。

        使用全域 Redis (get_redis) 確保跨實例快取共享。
        cache key: 'ezbid:today:all'，TTL 15 分鐘。

        Returns:
            {total, records: [...], source: 'ezbid', fetched_at}
        """
        import json as _json

        # 使用全域 async Redis (不依賴 self._redis)
        redis = None
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
        except Exception:
            pass

        cache_key = "ezbid:today:all"
        if redis:
            try:
                cached_raw = await redis.get(cache_key)
                if cached_raw:
                    cached = _json.loads(cached_raw)
                    logger.debug("ezbid today cache hit: %d records", cached.get("total", 0))
                    return cached
            except Exception:
                pass

        # 全量爬取: 10 頁 × 100 筆 (並行 + 節流，避免被封鎖)
        import asyncio as _aio

        async def _fetch_batch(pages):
            """批次並行抓取，每批 3 頁"""
            return await _aio.gather(
                *[self._fetch_page(None, "ALL", p, 100) for p in pages],
                return_exceptions=True,
            )

        all_records = []
        # 分 4 批：[1,2,3], [4,5,6], [7,8,9], [10]
        for batch_start in range(1, 11, 3):
            batch_pages = list(range(batch_start, min(batch_start + 3, 11)))
            batch_results = await _fetch_batch(batch_pages)
            batch_empty = True
            for result in batch_results:
                if isinstance(result, Exception):
                    continue
                if result:
                    all_records.extend(result)
                    batch_empty = False
            if batch_empty:
                break  # No more data
            await _aio.sleep(0.3)  # 節流間隔

        result = {
            "total": len(all_records),
            "records": all_records,
            "source": "ezbid",
            "fetched_at": datetime.utcnow().isoformat(),
        }

        # 寫入全域 Redis 快取 (15 min)
        if redis:
            try:
                await redis.set(
                    cache_key,
                    _json.dumps(result, ensure_ascii=False, default=str),
                    ex=900,
                )
            except Exception:
                pass

        logger.info("ezbid today fetched: %d records (cached 15min)", len(all_records))
        return result

    async def fetch_for_keywords(
        self, keywords: List[str], category: str = "ALL",
    ) -> Dict[str, Any]:
        """多關鍵字爬取 (用於訂閱/儀表板即時補充)"""
        all_records = []
        seen_ids = set()

        for kw in keywords[:5]:
            result = await self.fetch_latest(query=kw, category=category, pages=1)
            for r in result.get("records", []):
                if r["ezbid_id"] not in seen_ids:
                    seen_ids.add(r["ezbid_id"])
                    r["matched_keyword"] = kw
                    all_records.append(r)

        all_records.sort(key=lambda r: r.get("date", ""), reverse=True)

        return {
            "total": len(all_records),
            "records": all_records,
            "source": "ezbid",
            "keywords": keywords[:5],
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """回傳爬蟲健康狀態"""
        return {
            "healthy": self._consecutive_failures < BLOCK_THRESHOLD,
            "consecutive_failures": self._consecutive_failures,
        }

    async def _fetch_page(
        self, query: Optional[str], category: str, page: int, per_page: int,
    ) -> List[Dict[str, Any]]:
        """爬取單頁 (含重試/退避/封鎖偵測)"""
        # 連續失敗過多，跳過以避免洪水請求
        if self._consecutive_failures >= BLOCK_THRESHOLD:
            logger.error(
                f"ezbid 爬蟲連續失敗 {self._consecutive_failures} 次，可能需要人工介入"
            )
            return []

        params = {
            "cat": category,
            "per_page": per_page,
            "sort": "date_new",
        }
        if query:
            params["q"] = query
        if page > 1:
            params["page"] = page

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.get(EZBID_BASE, params=params)

                    # 封鎖偵測: 403 或回應含 captcha/block 關鍵字
                    if resp.status_code == 403:
                        logger.warning("ezbid 可能已封鎖 IP (HTTP 403)")
                        self._consecutive_failures += 1
                        return []

                    body_lower = resp.text[:2000].lower()
                    if "captcha" in body_lower or "block" in body_lower:
                        logger.warning("ezbid 可能已封鎖 IP (captcha/block detected)")
                        self._consecutive_failures += 1
                        return []

                    # 可重試的 HTTP 狀態碼
                    if resp.status_code in (429, 503):
                        wait = BACKOFF_BASE ** attempt
                        logger.warning(
                            f"ezbid HTTP {resp.status_code}, 重試 {attempt + 1}/{MAX_RETRIES} "
                            f"(等待 {wait:.1f}s)"
                        )
                        await asyncio.sleep(wait)
                        continue

                    if resp.status_code != 200:
                        logger.warning(f"ezbid HTTP {resp.status_code}")
                        self._consecutive_failures += 1
                        return []

                    # 成功
                    self._consecutive_failures = 0
                    return self._parse_html(resp.text)

            except Exception as e:
                last_error = e
                wait = BACKOFF_BASE ** attempt
                logger.warning(
                    f"ezbid fetch error (attempt {attempt + 1}/{MAX_RETRIES}): {e}, "
                    f"等待 {wait:.1f}s"
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(wait)

        # 所有重試用盡
        self._consecutive_failures += 1
        logger.error(f"ezbid fetch failed after {MAX_RETRIES} retries: {last_error}")
        if self._consecutive_failures >= BLOCK_THRESHOLD:
            logger.error(
                f"ezbid 爬蟲連續失敗 {self._consecutive_failures} 次，可能需要人工介入"
            )
        return []

    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        """解析 ezbid HTML，提取標案列表"""
        soup = BeautifulSoup(html, "html.parser")
        records = []

        links = soup.find_all("a", href=lambda h: h and "/tender/" in h)

        for link in links:
            try:
                href = link.get("href", "")
                tid_match = re.search(r"/tender/(\d+)", href)
                if not tid_match:
                    continue

                ezbid_id = tid_match.group(1)
                parts = [
                    p.strip()
                    for p in link.get_text(separator="|||", strip=True).split("|||")
                    if p.strip()
                ]

                if len(parts) < 5:
                    continue

                # 結構: [狀態, 截止天數, 標案名稱, 分類, 日期(ROC), 機關, $, 預算]
                status = parts[0] if len(parts) > 0 else ""
                deadline_text = parts[1] if len(parts) > 1 else ""
                title = parts[2] if len(parts) > 2 else ""
                category = parts[3] if len(parts) > 3 else ""
                roc_date = parts[4] if len(parts) > 4 else ""
                unit_name = parts[5] if len(parts) > 5 else ""
                budget_str = parts[7] if len(parts) > 7 else ""

                # ROC 日期轉西元
                date_str = self._roc_to_date(roc_date)

                # 預算
                budget = self._parse_budget(budget_str)

                # 截止天數
                days_left = self._parse_deadline(deadline_text)

                # 分類對照
                tender_type = "公開招標公告" if status == "公告" else status
                cat_label = category.replace("類", "")

                records.append({
                    "ezbid_id": ezbid_id,
                    "title": title,
                    "date": date_str,
                    "unit_name": unit_name,
                    "category": cat_label,
                    "type": tender_type,
                    "status": status,
                    "budget": budget,
                    "days_left": days_left,
                    "deadline_text": deadline_text,
                    "ezbid_url": f"{EZBID_BASE}/tender/{ezbid_id}",
                    "source": "ezbid",
                })

            except Exception as e:
                logger.debug(f"Parse tender failed: {e}")
                continue

        return records

    @staticmethod
    def _roc_to_date(roc_str: str) -> str:
        """ROC 日期 (115/04/07) → 西元 (2026-04-07)"""
        match = re.match(r"(\d{2,3})/(\d{2})/(\d{2})", roc_str)
        if not match:
            return ""
        year = int(match.group(1)) + 1911
        return f"{year}-{match.group(2)}-{match.group(3)}"

    @staticmethod
    def _parse_budget(budget_str: str) -> Optional[int]:
        """解析預算金額"""
        cleaned = budget_str.replace(",", "").strip()
        try:
            return int(cleaned) if cleaned.isdigit() else None
        except ValueError:
            return None

    @staticmethod
    def _parse_deadline(text: str) -> Optional[int]:
        """解析截止天數"""
        match = re.search(r"剩\s*(\d+)\s*天", text)
        if match:
            return int(match.group(1))
        if "已截止" in text:
            return 0
        if "今日截止" in text:
            return 0
        return None

    # =========================================================================
    # Redis 快取
    # =========================================================================

    async def _get_cache(self, key: str):
        if not self._redis:
            return None
        try:
            import json
            data = self._redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cache(self, key: str, value, ttl: int = 600):
        if not self._redis:
            return
        try:
            import json
            self._redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception:
            pass
