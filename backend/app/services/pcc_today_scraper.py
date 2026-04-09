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

    # PCC todayTender 頁面的 table 順序 → 類型映射
    # 只有含 pkPmsMain links 的 table 才是資料 table
    _TABLE_TYPE_ORDER = [
        "公開招標公告",
        "限制性招標",
        "選擇性招標(名單)",
        "選擇性招標(個案)",
        "選擇性招標(後續邀標)",
        "公開取得報價單或企劃書",
        # 以下為更正公告
        "公開招標更正公告",
        "限制性招標更正公告",
        "選擇性招標(名單)更正公告",
        "選擇性招標(個案)更正公告",
        "選擇性招標(後續邀標)更正公告",
        "公開取得報價單更正公告",
    ]

    def _parse_today_page(self, html: str) -> tuple:
        """
        解析 PCC 今日標案 HTML — 依 table 順序判斷公告類型。

        PCC 頁面結構: 每個類型有一對 table (header + data)
        data table 含 pkPmsMain links，按出現順序對應 _TABLE_TYPE_ORDER。
        """
        soup = BeautifulSoup(html, "html.parser")
        records: List[Dict[str, Any]] = []
        type_counts: Dict[str, int] = {}
        seen_ids = set()
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_int = int(datetime.now().strftime("%Y%m%d"))

        # PCC 頁面結構: 每個 section 由 header_table (id=label_typeN_M) + data_table 配對
        # header_table id 規則: label_type1_0~5 = 招標 6 類, label_type2_0~5 = 更正 6 類
        _SECTION_TYPE_MAP = {
            "label_type1_0": "公開招標公告",
            "label_type1_1": "限制性招標",
            "label_type1_2": "選擇性招標(名單)",
            "label_type1_3": "選擇性招標(個案)",
            "label_type1_4": "選擇性招標(後續邀標)",
            "label_type1_5": "公開取得報價單或企劃書",
            "label_type2_0": "公開招標更正公告",
            "label_type2_1": "限制性招標更正公告",
            "label_type2_2": "選擇性招標(名單)更正公告",
            "label_type2_3": "選擇性招標(個案)更正公告",
            "label_type2_4": "選擇性招標(後續邀標)更正公告",
            "label_type2_5": "公開取得報價單更正公告",
        }

        # 定位每個 header → 下一個 sibling table = data table
        data_tables = []
        for label_id, tender_type in _SECTION_TYPE_MAP.items():
            header = soup.find("table", id=label_id)
            if not header:
                continue
            # 找 header 之後的下一個 table (data table)
            next_table = header.find_next_sibling("table")
            if not next_table:
                continue
            links = next_table.find_all("a", href=lambda h: h and "pkPmsMain" in str(h))
            data_tables.append((next_table, links, tender_type))

        for table, _links, tender_type in data_tables:
            table_count = 0

            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                try:
                    link = row.find("a", href=lambda h: h and "pkPmsMain" in str(h))
                    if not link:
                        continue

                    href = link.get("href", "")
                    pk_match = re.search(r"pkPmsMain=([A-Za-z0-9=+/]+)", href)
                    tender_id = pk_match.group(1) if pk_match else ""
                    if not tender_id or tender_id in seen_ids:
                        continue
                    seen_ids.add(tender_id)

                    cell_texts = [c.get_text(strip=True) for c in cells]
                    if len(cell_texts) >= 5:
                        unit_name, title, job_number, deadline = (
                            cell_texts[1], cell_texts[2], cell_texts[3], cell_texts[4],
                        )
                    elif len(cell_texts) >= 4:
                        unit_name, title, job_number, deadline = (
                            cell_texts[0], cell_texts[1], cell_texts[2], cell_texts[3],
                        )
                    else:
                        continue

                    records.append({
                        "title": title,
                        "date": today_str,
                        "raw_date": today_int,
                        "type": tender_type,
                        "category": "",
                        "unit_id": tender_id,
                        "unit_name": unit_name,
                        "job_number": job_number,
                        "deadline": self._roc_to_date(deadline),
                        "winner_names": [],
                        "source": "pcc",
                        "pcc_url": f"{PCC_BASE}{href}" if href.startswith("/") else href,
                    })
                    table_count += 1
                except Exception as e:
                    logger.debug(f"Parse PCC row failed: {e}")
                    continue

            type_counts[tender_type] = table_count

        logger.info(
            "PCC today scrape: %d records, types=%s",
            len(records), {k: v for k, v in type_counts.items() if v > 0},
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
