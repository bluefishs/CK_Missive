"""客戶回簽報價單匯入 —— 依檔名的舊案號自動掛回對應案件。

owner 2026-08-19：
  ①「產生報價單只是步驟一，其需將客戶回簽檔案上傳確認才正式完成邀標報價承攬」
  ②「客戶回簽上傳的實際素材，請規劃匯入對應 pm/cases 案件以利檢視複查」

# 檔名就是對應關係

    Z:\\03.專案管控專區\\01.報價單紀錄\\2026報價紀錄\\
    回簽報價單_B115-C013-0_朱冠綸_太平區洪厝段360地號_建物標示圖.pdf
    回簽報價單_B115-C017a-0_林淑慧_后里區文德段888地號_建物地籍測繪資料.pdf
                 ↑ 舊案號

第 2 段就是 `legacy_quotation_no`，而那正是 2026-08-19 新增的欄位 ——
**這個功能之所以做得起來，是因為那個欄位存在**；在它之前，
這批檔案沒有任何辦法對回系統（案名會被改寫、客戶名有簡稱）。

# 為什麼走上傳而不是掃描 Z 槽

Z 槽是 host 的網路磁碟，**容器內看不到**。寫成「後端去掃某個路徑」
會得到一個在開發機能跑、在容器裡永遠掃到 0 筆的功能 ——
那是本專案記錄過的「跑在哪個環境同樣重要」。

# 預覽先於寫入

與彙整表匯入同一個原則：先回報「幾個對得上、幾個對不上」，確認才寫。
對不上的**列出檔名與原因**，不靜靜跳過 —— 使用者要知道哪幾份沒掛上。
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation
from app.extended.models.pm import PMCaseAttachment

logger = logging.getLogger(__name__)

#: 與既有附件上傳同一個落點（不另立第二個設定）
ARCHIVE_ROOT_ENV = "PM_ATTACHMENT_DIR"
ARCHIVE_ROOT_DEFAULT = "uploads/pm_attachments"

#: 檔名前綴。目前只有這一種，但寫成集合是因為日後可能有「回簽合約」等。
_SIGNED_PREFIXES = ("回簽報價單", "回簽")


def parse_legacy_no(filename: str) -> Optional[str]:
    """從檔名取出舊案號。

    `回簽報價單_B115-C017b-0_林淑慧_豐原區鳳山段151_建物標示圖.pdf`
                 ^^^^^^^^^^^^ 第 2 段

    ⚠️ 用 `split('_')[1]` 而不是正則抓「B開頭」：標的名稱裡也可能出現
    看起來像編號的字串（`豐原區鳳山段151`），而位置是穩定的。
    """
    base = os.path.basename(filename or "")
    stem = os.path.splitext(base)[0]
    parts = stem.split("_")
    if len(parts) < 2:
        return None
    if not any(parts[0].startswith(p) for p in _SIGNED_PREFIXES):
        return None
    no = parts[1].strip()
    # 舊案號長這樣：B115-C013-0 / B114-B001-1 / B115-022a-0
    return no if re.match(r"^[A-Za-z]?\d{3}[-_]", no) else None


_QT_RE = re.compile(r"QT\d{4}_\d{3,}")
# 兩種形狀：新制 CK2026_PM_02_083／CK2026_02_083；舊制成案編號 CK2025_02_01_027（年_類_性_序）
_CK_RE = re.compile(r"CK\d{4}(?:_(?:PM|GN|FN))?(?:_\d{2}){1,2}_\d{3,}[a-z]?")


def parse_keys(filename: str) -> dict[str, Optional[str]]:
    """檔名裡能當鑰匙的三種編號（2026-09-04 晚 owner「如無法對應所有案件機制則刪除」）。

    舊案號只有 246/277 張有、QT 號只有 139 張有，唯獨 case_code 每張都有 ⇒ 三把任一即可，
    案件無論新舊都對得到。QT／CK 在檔名任何位置都認（它們的形狀不會與標的名稱混淆）。
    """
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    qt = _QT_RE.search(stem)
    ck = _CK_RE.search(stem)
    return {
        "legacy_no": parse_legacy_no(filename),
        "quotation_no": qt.group(0) if qt else None,
        "case_code": ck.group(0) if ck else None,
    }


def normalize_legacy_no(no: str) -> str:
    """把舊案號正規化成可比對的形式。

    ⚠️ **同一張報價單在兩個地方寫法不同**（2026-08-19 實測）：

        回簽 PDF 檔名   B115-C017a-0     子號字母黏在序號後
        彙整表 Excel    B115-C017-a      子號字母用連字號分開

    直接字串比對會對不上 —— 5 個回簽檔裡有 3 個因此掛不上。
    這不是誰填錯，是兩份紀錄各自演化出的寫法；
    要求人先統一，等於把工作推回去給填表的人。

    ⚠️ **本 repo 對同一個舊案號有兩種正規化政策，兩種都是對的**（2026-08-27 登記）：

        本檔（附檔比對）           **忽略尾碼** —— 掛不上的代價高於掛錯
        quotation_legacy_import    **保留完整案號** —— 併錯案子的代價高於分開

    去尾碼會讓 `B114-B026`（平鎮區土地協議市價查估）與 `B114-B026-0`
    （永翠76透地雷達測量）被硬掛成同一件 —— 那在建案那一側是不可接受的。
    **不要把兩邊統一。** 先問「這一側改用另一側的政策，錯的時候會發生什麼」。
    見 `docs/architecture/TIER3_INTENTIONAL_DIVERGENCE_REGISTRY.md` §10。

    正規化取「年 + 類別 + 序號 + 子號」四段，忽略連字號與尾碼：

        B115-C017a-0 → 115|C|17|A
        B115-C017-a  → 115|C|17|A
        B115-C013-0  → 115|C|13|
        B114-B001-1  → 114|B|1|

    ⚠️ 刻意**丟掉最後的 `-0`/`-1`**：那是版次，同一張報價單改版後仍是同一張
    （彙整表的 `B115-C009-1` 與回簽檔可能寫 `-0`）。若把版次納入比對，
    改過價的案子就掛不上回簽檔。
    """
    s = (no or "").strip().upper().replace("_", "-")
    m = re.match(r"^[A-Z]?(\d{3})-([A-Z]*)(\d+)([A-Z]?)(?:-([A-Z0-9]+))?$", s)
    if not m:
        return s  # 認不得就原樣回傳，不猜
    year, cat, seq, suffix_inline, tail = m.groups()
    # 子號可能在序號後（C017a）或在尾段（C017-a）；尾段若是純數字則是版次，丟掉
    suffix = suffix_inline or (tail if tail and not tail.isdigit() else "")
    return f"{year}|{cat}|{int(seq)}|{suffix}"


class SignedQuotationImportService:
    """把客戶回簽檔掛回對應案件；一個入口，先預覽再寫入。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, files: list[tuple[str, bytes]], *, dry_run: bool = True,
                  user_id: Optional[int] = None) -> dict[str, Any]:
        parsed: list[dict[str, Any]] = []
        unmatched: list[dict[str, str]] = []

        for filename, content in files:
            keys = parse_keys(filename)
            if not any(keys.values()):
                unmatched.append({
                    "file_name": os.path.basename(filename),
                    "reason": "檔名看不出任何編號——請含舊案號（B115-C017-0）、報價單編號（QT2026_063）或案號（CK2026_PM_02_083）之一",
                })
                continue
            parsed.append({"file_name": os.path.basename(filename), **keys,
                           "legacy_no": keys["legacy_no"], "content": content})

        found: dict[str, Any] = {}
        by_qt: dict[str, Any] = {}
        by_case: dict[str, Any] = {}
        if parsed:
            for q in (await self.db.execute(
                select(ERPQuotation).where(ERPQuotation.deleted_at.is_(None))
            )).scalars().all():
                if q.legacy_quotation_no:
                    key = normalize_legacy_no(q.legacy_quotation_no)
                    prev = found.get(key)
                    if prev is None or (q.id or 0) > (prev.id or 0):
                        found[key] = q
                if q.quotation_no:
                    by_qt[q.quotation_no.upper()] = q
                # 同一案多張報價單取最新一張（id 最大）
                for code in (q.case_code, q.project_code):
                    if code:
                        prev = by_case.get(code.upper())
                        if prev is None or (q.id or 0) > (prev.id or 0):
                            by_case[code.upper()] = q

        matched: list[dict[str, Any]] = []
        for p in parsed:
            q = None
            if p.get("legacy_no"):
                q = found.get(normalize_legacy_no(p["legacy_no"]))
            if q is None and p.get("quotation_no"):
                q = by_qt.get(p["quotation_no"].upper())
            if q is None and p.get("case_code"):
                q = by_case.get(p["case_code"].upper())
            if q is None:
                tried = "／".join(v for v in (p.get("legacy_no"), p.get("quotation_no"), p.get("case_code")) if v)
                unmatched.append({
                    "file_name": p["file_name"],
                    "reason": f"系統裡找不到 {tried} 對應的報價單（舊案號可能彙整表還沒匯入）",
                })
                continue
            p["legacy_no"] = p.get("legacy_no") or p.get("quotation_no") or p.get("case_code")
            if not q.case_code:
                unmatched.append({
                    "file_name": p["file_name"],
                    "reason": f"{p['legacy_no']} 對應的報價單沒有案號，附件無處可掛",
                })
                continue
            matched.append({**p, "quotation": q})

        preview = {
            "success": True,
            "dry_run": dry_run,
            "total_files": len(files),
            "will_attach": len(matched),
            "unmatched": len(unmatched),
            "unmatched_detail": unmatched[:20],
            "sample_match": [
                {"file_name": m["file_name"], "legacy_no": m["legacy_no"],
                 "case_code": m["quotation"].case_code,
                 "case_name": m["quotation"].case_name}
                for m in matched[:10]
            ],
        }
        if dry_run:
            return preview

        attached = replaced = 0
        root = os.environ.get(ARCHIVE_ROOT_ENV, ARCHIVE_ROOT_DEFAULT)
        for m in matched:
            q = m["quotation"]
            dir_path = os.path.join(root, str(q.case_code), datetime.now().strftime("%Y%m"))
            os.makedirs(dir_path, exist_ok=True)
            # 正斜線寫入（L49.3：Windows 反斜線進 Linux 容器後 os.path.exists 一律 false）
            full_path = os.path.join(dir_path, m["file_name"]).replace("\\", "/")

            # 同一份回簽重傳就覆蓋（同案號＋同檔名）
            olds = (await self.db.execute(
                select(PMCaseAttachment).where(
                    PMCaseAttachment.case_code == q.case_code,
                    PMCaseAttachment.file_name == m["file_name"],
                )
            )).scalars().all()
            for old in olds:
                prev = (old.file_path or "").replace("\\", os.sep)
                if prev and os.path.exists(prev) and \
                        os.path.abspath(prev) != os.path.abspath(full_path):
                    try:
                        os.remove(prev)
                    except OSError:
                        logger.warning("回簽檔舊檔刪除失敗 path=%s", prev)
                await self.db.delete(old)
                replaced += 1

            with open(full_path, "wb") as f:
                f.write(m["content"])

            self.db.add(PMCaseAttachment(
                case_code=q.case_code,
                file_name=m["file_name"],
                file_path=full_path,
                file_size=len(m["content"]),
                mime_type="application/pdf",
                original_name=m["file_name"],
                checksum=hashlib.sha256(m["content"]).hexdigest(),
                uploaded_by=user_id,
                # 這一行是整個功能的重點：讓「有沒有客戶回簽」查得出來，
                # 而不是靠檔名猜（檔名一改判定就靜靜失效）。
                doc_type="signed_quotation",
                notes=f"客戶回簽（舊案號 {m['legacy_no']}）",
            ))
            attached += 1

        await self.db.commit()
        logger.info("回簽報價單匯入：掛上 %d／覆蓋 %d／未對應 %d",
                    attached, replaced, len(unmatched))
        return {**preview, "dry_run": False, "attached": attached, "replaced": replaced}
