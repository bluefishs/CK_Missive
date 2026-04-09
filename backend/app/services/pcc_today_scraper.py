"""
PCC 政府電子採購網今日標案爬蟲 — 主要資料來源

直接爬取 web.pcc.gov.tw 今日標案頁面，取得全量標案資料。
PCC 為權威來源 (633+ 筆/日)，ezbid 退為補充/備援。

資料來源: https://web.pcc.gov.tw/prkms/today/common/todayTender
每日公告分類:
  - 公開招標公告 (~633)
  - 限制性招標 (~111)
  - 選擇性招標(個案) (~10)
  - 選擇性招標(後續邀標) (~677)
  - 公開取得報價單/企劃書 (~406)
  - 更正公告 (~84)

Version: 1.0.0
Created: 2026-04-09
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PCC_BASE = "https://web.pcc.gov.tw"
PCC_TODAY_URL = f"{PCC_BASE}/prkms/today/common/todayTender"
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 2
BACKOFF_BASE = 2.0


class PccTodayScraper:
    """PCC 今日標案爬蟲 — 權威來源"""

    def __init__(self, redis_client=None):
        self._redis = redis_client

    async def fetch_today_tenders(
        self,
        include_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        抓取 PCC 今日全部標案。

        Args:
            include_types: 要抓取的公告類型 (None = 全部)
                可選值: ['open_bid', 'restricted', 'selective', 'rfp']

        Returns:
            {total, records: [...], by_type: {...}, source: 'pcc', fetched_at}
        """
        cache_key = "pcc:today:all"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        all_records: List[Dict[str, Any]] = []
        by_type: Dict[str, int] = {}

        html = await self._fetch_page(PCC_TODAY_URL)
        if not html:
            return {
                "total": 0, "records": [], "by_type": {},
                "source": "pcc", "fetched_at": datetime.utcnow().isoformat(),
                "error": "PCC 網站無回應",
            }

        records, type_counts = self._parse_today_page(html)
        all_records.extend(records)
        by_type = type_counts

        result = {
            "total": len(all_records),
            "records": all_records,
            "by_type": by_type,
            "source": "pcc",
            "fetched_at": datetime.utcnow().isoformat(),
        }

        # 快取 15 分鐘 (PCC 每日更新)
        await self._set_cache(cache_key, result, ttl=900)
        return result

    def _parse_today_page(self, html: str) -> tuple:
        """解析 PCC 今日標案 HTML"""
        soup = BeautifulSoup(html, "html.parser")
        records: List[Dict[str, Any]] = []
        type_counts: Dict[str, int] = {}
        seen_ids = set()

        # PCC 使用 <table> 結構，每個標案在 <tr> 中
        # 結構: 項次 | 機關名稱 | 標案名稱 | 標案案號 | 截止投標
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            current_type = ""

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                # 嘗試提取標案資料
                try:
                    # 尋找含連結的欄位 (標案案號)
                    link = row.find("a", href=lambda h: h and "pkPmsMain" in str(h))
                    if not link:
                        continue

                    href = link.get("href", "")
                    pk_match = re.search(r"pkPmsMain=([A-Za-z0-9=+/]+)", href)
                    tender_id = pk_match.group(1) if pk_match else ""

                    if tender_id in seen_ids:
                        continue
                    seen_ids.add(tender_id)

                    # 解析各欄位
                    cell_texts = [c.get_text(strip=True) for c in cells]

                    # 判斷欄位位置 (PCC 表格: 項次/機關名稱/標案名稱/標案案號/截止投標)
                    unit_name = ""
                    title = ""
                    job_number = ""
                    deadline = ""

                    if len(cell_texts) >= 5:
                        unit_name = cell_texts[1]
                        title = cell_texts[2]
                        job_number = cell_texts[3]
                        deadline = cell_texts[4]
                    elif len(cell_texts) >= 4:
                        unit_name = cell_texts[0]
                        title = cell_texts[1]
                        job_number = cell_texts[2]
                        deadline = cell_texts[3]

                    # ROC 日期轉換
                    deadline_date = self._roc_to_date(deadline)

                    records.append({
                        "title": title,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "raw_date": int(datetime.now().strftime("%Y%m%d")),
                        "type": "公開招標公告",
                        "category": "",
                        "unit_id": tender_id,
                        "unit_name": unit_name,
                        "job_number": job_number,
                        "deadline": deadline_date,
                        "winner_names": [],
                        "source": "pcc",
                        "pcc_url": f"{PCC_BASE}{href}" if href.startswith("/") else href,
                    })

                except Exception as e:
                    logger.debug(f"Parse PCC row failed: {e}")
                    continue

        # 嘗試從頁面摘要提取類型統計
        summary_texts = soup.find_all(string=re.compile(r"總筆數"))
        for t in summary_texts:
            match = re.search(r"總筆數[：:]\s*(\d+)", t)
            if match:
                type_counts["total_announced"] = int(match.group(1))

        # 從 section headers 提取各類型筆數
        headers = soup.find_all(string=re.compile(r"(\d+)\s*筆"))
        for h in headers:
            text = str(h).strip()
            count_match = re.search(r"(\d+)\s*筆", text)
            if count_match:
                count = int(count_match.group(1))
                if "公開招標" in text:
                    type_counts["open_bid"] = count
                elif "限制性" in text:
                    type_counts["restricted"] = count
                elif "選擇性" in text and "後續" in text:
                    type_counts["selective_followup"] = count
                elif "選擇性" in text:
                    type_counts["selective"] = count
                elif "公開取得" in text:
                    type_counts["rfp"] = count
                elif "更正" in text:
                    type_counts["correction"] = count

        logger.info(
            "PCC today scrape: %d records parsed, types=%s",
            len(records), type_counts,
        )
        return records, type_counts

    async def _fetch_page(self, url: str) -> Optional[str]:
        """HTTP GET with retry"""
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=REQUEST_TIMEOUT,
                    follow_redirects=True,
                    verify=False,  # PCC SSL cert issue (Missing Subject Key Identifier)
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"PCC HTTP {resp.status_code}: {url}")
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(BACKOFF_BASE ** attempt)
                        continue

                    # PCC 使用 Big5 編碼
                    content = resp.content
                    for encoding in ("utf-8", "big5", "latin-1"):
                        try:
                            return content.decode(encoding)
                        except UnicodeDecodeError:
                            continue

                    return content.decode("utf-8", errors="replace")
            except Exception as e:
                logger.warning(f"PCC fetch error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_BASE ** attempt)

        logger.error(f"PCC fetch failed after {MAX_RETRIES} retries: {url}")
        return None

    @staticmethod
    def _roc_to_date(roc_str: str) -> str:
        """ROC 日期 (115/04/07) → 西元 (2026-04-07)"""
        match = re.match(r"(\d{2,3})/(\d{2})/(\d{2})", roc_str.strip())
        if not match:
            return ""
        year = int(match.group(1)) + 1911
        return f"{year}-{match.group(2)}-{match.group(3)}"

    async def _get_cache(self, key: str):
        if not self._redis:
            return None
        try:
            import json
            data = await self._redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cache(self, key: str, value, ttl: int = 900):
        if not self._redis:
            return
        try:
            import json
            await self._redis.set(
                key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl,
            )
        except Exception:
            pass
