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

from .scraper_base import register_scraper

logger = logging.getLogger(__name__)

# 2026-08-02：`cf.ezbid.tw` 已 301 永久搬到 `ezbid.tw`，且站台改版
# （列表連結由 /tender/{id} 變成 /detail/{unit_id}/{job_number}，欄位移出 <a> 到 <tr>）。
# 舊 code 不跟隨 301 → 每小時抓 0 筆、只記 warning 但 job 仍報 success
# → **ezbid 自 2026-06-15 起 48 天無新資料，兩層監控都沒發現**（見 _parse_html 說明）。
EZBID_BASE = "https://ezbid.tw"
REQUEST_TIMEOUT = 15.0
MAX_RETRIES = 3
BACKOFF_BASE = 2.0
# P1-4 (2026-05-27)：5 → 3 — 縮短 silent window 從 ~5h → ~3h，配合 Prometheus alert
BLOCK_THRESHOLD = 3

# 封鎖頁面的明確特徵。**不要放單字 "block"** —— 它會命中 Bootstrap 的
# `d-inline-block` 等 CSS class，把正常頁面判成封鎖（2026-08-03 修）。
BLOCK_SIGNATURES = (
    "captcha",
    "cf-challenge",
    "checking your browser",
    "access denied",
    "ip has been blocked",
    "您的 ip 已被",
    "請求過於頻繁",
)

# ezbid 分類對照
EZBID_CATEGORIES = {
    "ALL": "全部",
    "WORK": "工程",
    "SERV": "勞務",
    "PPTY": "財物",
}


@register_scraper("ezbid")
class EzbidScraper:
    """ezbid.tw 標案爬蟲。

    Step 5A (2026-05-28): @register_scraper 註冊進 ScraperRegistry，
    subscription_scheduler / freshness_audit / Grafana 可自動 enumerate。
    Inherit base 是漸進式 — 既有測試保留，只加 registry。
    """
    # ScraperRegistry 需要的 attributes（與 base class 對齊）
    source_name = "ezbid"
    cache_prefix = "ezbid"
    cache_ttl = 600

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
                # follow_redirects：對端換網域時不要靜默抓 0 筆（2026-08-02 實際踩到）
                async with httpx.AsyncClient(
                    timeout=REQUEST_TIMEOUT, follow_redirects=True
                ) as client:
                    resp = await client.get(EZBID_BASE, params=params)

                    # 封鎖偵測: 403 或回應含 captcha/block 關鍵字
                    if resp.status_code == 403:
                        logger.warning("ezbid 可能已封鎖 IP (HTTP 403)")
                        self._record_failure("http_403")
                        return []

                    # 2026-08-03：原本判斷是 `"block" in body_lower`，會被 Bootstrap 的
                    # `d-inline-block` / `d-md-block` 等 CSS class 命中 → 正常頁面被當成
                    # 封鎖、直接放棄整批抓取。之所以沒天天爆，只因為它只看前 2000 字元，
                    # 而那段剛好落在 <head>；CSS class 往前挪一點就會誤觸發 ——
                    # 也就是「目前正常」純屬運氣。改為比對明確的封鎖語句。
                    body_lower = resp.text[:2000].lower()
                    hit = next((s for s in BLOCK_SIGNATURES if s in body_lower), None)
                    if hit:
                        logger.warning(f"ezbid 可能已封鎖 IP（偵測到 '{hit}'）")
                        self._record_failure("captcha")
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
                        self._record_failure(f"http_{resp.status_code}")
                        return []

                    # 成功
                    self._record_success()
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
        self._record_failure("network_error")
        logger.error(f"ezbid fetch failed after {MAX_RETRIES} retries: {last_error}")
        if self._consecutive_failures >= BLOCK_THRESHOLD:
            logger.error(
                f"ezbid 爬蟲連續失敗 {self._consecutive_failures} 次，可能需要人工介入"
            )
        return []

    # ────────── P1-4 (2026-05-27) Prometheus 計數輔助 ──────────

    def _record_failure(self, reason: str) -> None:
        """單一失敗記錄入口 — 同步 self._consecutive_failures + Prometheus counter"""
        self._consecutive_failures += 1
        try:
            from .metrics import get_tender_metrics
            m = get_tender_metrics()
            m.failures.labels(source="ezbid", reason=reason).inc()
            m.consecutive.labels(source="ezbid").set(self._consecutive_failures)
        except Exception:
            # metric 失敗不阻 scraper 主路徑
            pass

    def _record_success(self) -> None:
        """單一成功記錄入口 — 重置 consecutive + 觸發 Prometheus runs ok"""
        self._consecutive_failures = 0
        try:
            from .metrics import get_tender_metrics
            m = get_tender_metrics()
            m.runs.labels(source="ezbid", status="ok").inc()
            m.consecutive.labels(source="ezbid").set(0)
        except Exception:
            pass

    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        """解析 ezbid HTML，提取標案列表。

        2026-08-02 重寫（站台改版）：
        - 舊版：整列資訊塞在 `<a href="/tender/{id}">` 的文字裡，用位置索引切 8 段。
        - 新版：`<a href="/detail/{unit_id}/{job_number}">` 只剩標題，其餘欄位在同一 `<tr>`。
          新版反而更好——它直接給 PCC 的 unit_id/job_number，可直接與 PCC 對應（ADR-0046）。

        欄位改用**特徵定位**而非固定索引：實測列可能有押標金也可能沒有，
        寫死索引會在部分列上整排錯位（舊版就是這樣寫的）。
        """
        soup = BeautifulSoup(html, "html.parser")
        records: List[Dict[str, Any]] = []

        for row in soup.find_all("tr"):
            try:
                link = row.find("a", href=lambda h: h and "/detail/" in h)
                if not link:
                    continue
                m = re.search(r"/detail/([^/]+)/([^/?#\"]+)", link.get("href", ""))
                if not m:
                    continue

                unit_id, job_number = m.group(1), m.group(2)
                title = link.get_text(strip=True)
                if not title:
                    continue

                parts = [
                    p.strip()
                    for p in row.get_text(separator="|||", strip=True).split("|||")
                    if p.strip()
                ]

                # 特徵定位（缺欄位時只影響該欄，不會整排位移）
                status = parts[0] if parts else ""
                roc_date = next((p for p in parts if re.match(r"^\d{2,3}/\d{2}/\d{2}$", p)), "")
                deadline_text = next((p for p in parts if "天" in p or "截止" in p), "")
                category = next((p for p in parts if p.endswith("類")), "")

                # 機關：標題的前一段（該列由「機關上層 → 機關 → 標題」排列）
                unit_name = ""
                if title in parts:
                    idx = parts.index(title)
                    if idx > 0:
                        unit_name = parts[idx - 1]

                # 預算：'$' 之後那一段（舊版靠 parts[7]，改版後必錯）
                budget_str = ""
                if "$" in parts:
                    bidx = parts.index("$")
                    if bidx + 1 < len(parts):
                        budget_str = parts[bidx + 1]

                records.append({
                    # 複合鍵當 ezbid_id（欄位為 varchar(50)，PCC key 遠短於此）
                    "ezbid_id": f"{unit_id}/{job_number}"[:50],
                    "unit_id": unit_id,
                    "job_number": job_number,
                    "title": title,
                    "date": self._roc_to_date(roc_date),
                    "unit_name": unit_name,
                    "category": category.replace("類", ""),
                    "type": "公開招標公告" if status == "公告" else status,
                    "status": status,
                    "budget": self._parse_budget(budget_str),
                    "days_left": self._parse_deadline(deadline_text),
                    "deadline_text": deadline_text,
                    "ezbid_url": f"{EZBID_BASE}/detail/{unit_id}/{job_number}",
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
        # 2026-04-24: 改 async redis（前版是 sync API，注入 async client 時會 coroutine leak 導致 cache 永遠 miss）
        redis = self._redis
        if redis is None:
            try:
                from app.core.redis_client import get_redis
                redis = await get_redis()
            except Exception:
                return None
        if redis is None:
            return None
        try:
            import json
            data = await redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cache(self, key: str, value, ttl: int = 600):
        redis = self._redis
        if redis is None:
            try:
                from app.core.redis_client import get_redis
                redis = await get_redis()
            except Exception:
                return
        if redis is None:
            return
        try:
            import json
            await redis.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
        except Exception:
            pass
