# -*- coding: utf-8 -*-
"""往來對象（協力廠商／委託單位）的名稱解析器 —— 填報當下就把名字變成鍵。

## 為什麼要有這一層

2026-09-06 逐筆查證得到的事實：

* 應付 #51 的廠商名是 `銢欣有限公司乃耳企業社` —— **兩家併寫在同一格**（銢欣 80321095、
  司乃耳 82349892）。414,750 全記在其中一家名下，另一家在系統裡查無支出；
  而事後要拆時，**系統裡已經沒有任何憑證能決定怎麼分**。
* 另有 `楊長燁加李雅倫`（同一批匯入）、`林晉廷` vs 主檔 `林宥廷測量技師事務所`（疑似打錯字）。
* 快照漂移 12 筆：`張啟良建築師` vs 主檔 `張啟良建築師事務所` 這類簡稱。

共同形狀：**名字進得來、鍵沒有跟上**。事後稽核（weekly 107）看得到，但那時錢已經記在錯的地方。
⇒ 這一層的職責是「填報當下就回答：這個名字是主檔裡的哪一筆」，答不出來就**出聲**，
不要靜靜地留一個沒有鍵的名字。

## 判準（由強到弱，先命中先用）

1. **統一編號**（`tax_id` / `vendor_code` 有 8 碼數字）—— 唯一且不會因改名而變
2. **精確名稱**
3. **正規化名稱**（去空白／全形半形／常見後綴差異，例如「張啟良建築師」↔「張啟良建築師事務所」）
4. **唯一前綴**（只有一家以它開頭時才算，兩家以上視為不明確）

任何一步都可能回「不明確」（多個候選），那時**不猜** —— 回候選讓呼叫端請人選。

## 併寫偵測

一個字串裡出現兩個以上的「機構型後綴」（有限公司／股份有限公司／企業社／事務所／工程行……），
或含有 `加`／`及`／`與`／`、`／`+` 這類連接詞時，判為併寫並回兩段候選。
**併寫不是解析失敗，是資料本身錯了** —— 一筆金額不能同時屬於兩家。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.core import PartnerVendor

#: 機構型後綴 —— 用來偵測「一格兩家」
_ORG_SUFFIX = (
    "股份有限公司", "有限公司", "企業社", "事務所", "工程行", "工作室",
    "合夥", "商行", "社", "行號",
)
#: 併寫連接詞（`、` 與 `+` 也算）
_JOINERS = ("加", "及", "與", "、", "+", "／")
_BAN = re.compile(r"\b\d{8}\b")


def normalize_name(name: str) -> str:
    """正規化：全形→半形、去空白與括號內容、去掉常見機構後綴。

    只用於**比對**，不用於顯示 —— 顯示一律用主檔的現行名稱（名稱是快照、鍵才是關聯）。
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name)).strip()
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = re.sub(r"[\s　]+", "", s)
    for suf in _ORG_SUFFIX:
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s


def split_candidates(name: str) -> list[str]:
    """若像「兩家併寫」，回各段名稱；否則回空 list。"""
    if not name:
        return []
    s = unicodedata.normalize("NFKC", str(name)).strip()

    for j in _JOINERS:
        if j in s:
            parts = [p.strip() for p in s.split(j) if p.strip()]
            if len(parts) >= 2:
                return parts

    # 沒有連接詞時：看有沒有兩個機構後綴（`銢欣有限公司乃耳企業社`）
    hits: list[int] = []
    for suf in _ORG_SUFFIX:
        start = 0
        while True:
            i = s.find(suf, start)
            if i < 0:
                break
            hits.append(i + len(suf))
            start = i + len(suf)
    hits = sorted(set(hits))
    if len(hits) >= 2 and hits[-1] >= len(s) - 1:
        cut = hits[0]
        left, right = s[:cut].strip(), s[cut:].strip()
        if left and right:
            return [left, right]
    return []


@dataclass
class ResolveResult:
    """解析結果。`vendor_id` 有值代表確定；否則看 `reason` 與 `candidates`。"""

    vendor_id: Optional[int] = None
    matched_by: str = ""                      # tax_id / exact / normalized / prefix
    reason: str = ""                          # 沒解出來時的原因（給人看）
    candidates: list[tuple[int, str]] = field(default_factory=list)
    split_into: list[str] = field(default_factory=list)   # 併寫時的各段


class PartyResolver:
    """把「名字」解析成 partner_vendors 的鍵。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(
        self,
        name: Optional[str],
        *,
        tax_id: Optional[str] = None,
        vendor_type: Optional[str] = None,
    ) -> ResolveResult:
        if not (name or tax_id):
            return ResolveResult(reason="沒有給名稱也沒有統編")

        rows = await self._all(vendor_type)

        # ① 統編
        ban = _BAN.search(str(tax_id or "")) or _BAN.search(str(name or ""))
        if ban:
            code = ban.group(0)
            hit = [(v.id, v.vendor_name) for v in rows
                   if code in {str(v.tax_id or ""), str(getattr(v, "vendor_code", "") or "")}]
            if len(hit) == 1:
                return ResolveResult(vendor_id=hit[0][0], matched_by="tax_id")
            if len(hit) > 1:
                return ResolveResult(reason=f"統編 {code} 對到 {len(hit)} 家，主檔本身有重複", candidates=hit)

        if not name:
            return ResolveResult(reason=f"統編 {ban.group(0) if ban else ''} 在主檔查無此家")

        # ② 併寫：先擋下來，不要讓一筆金額掛在兩家的名字上
        parts = split_candidates(name)
        if parts:
            resolved = []
            for p in parts:
                r = await self._by_name(p, rows)
                if r.vendor_id:
                    resolved.append((r.vendor_id, p))
            return ResolveResult(
                reason=f"「{name}」看起來是 {len(parts)} 家併寫（{'／'.join(parts)}）"
                       "—— 一筆金額不能同時屬於兩家，請拆成多筆分別填報",
                candidates=resolved,
                split_into=parts,
            )

        return await self._by_name(name, rows)

    async def _by_name(self, name: str, rows: Sequence[PartnerVendor]) -> ResolveResult:
        exact = [(v.id, v.vendor_name) for v in rows if str(v.vendor_name or "").strip() == name.strip()]
        if len(exact) == 1:
            return ResolveResult(vendor_id=exact[0][0], matched_by="exact")
        if len(exact) > 1:
            return ResolveResult(reason=f"主檔有 {len(exact)} 家同名「{name}」", candidates=exact)

        key = normalize_name(name)
        if key:
            norm = [(v.id, v.vendor_name) for v in rows if normalize_name(v.vendor_name) == key]
            if len(norm) == 1:
                return ResolveResult(vendor_id=norm[0][0], matched_by="normalized")
            if len(norm) > 1:
                return ResolveResult(reason=f"「{name}」正規化後對到 {len(norm)} 家", candidates=norm)

            pref = [(v.id, v.vendor_name) for v in rows
                    if normalize_name(v.vendor_name).startswith(key) or key.startswith(normalize_name(v.vendor_name))]
            if len(pref) == 1:
                return ResolveResult(vendor_id=pref[0][0], matched_by="prefix")
            if len(pref) > 1:
                return ResolveResult(reason=f"「{name}」是 {len(pref)} 家的前綴，不明確", candidates=pref)

        return ResolveResult(reason=f"主檔沒有「{name}」")

    async def _all(self, vendor_type: Optional[str]) -> Sequence[PartnerVendor]:
        stmt = select(PartnerVendor)
        if vendor_type:
            stmt = stmt.where(PartnerVendor.vendor_type == vendor_type)
        return (await self.db.execute(stmt)).scalars().all()
