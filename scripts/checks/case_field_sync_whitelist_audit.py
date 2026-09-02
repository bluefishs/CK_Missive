#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三表（pm_cases／contract_projects／erp_quotations）共有欄位必須在同步白名單裡，
且同步的目標欄位必須真的存在於模型（weekly 101）。

## 這條在防什麼

2026-09-02 一天踩兩次同型：
- 上午 `status` 不在 `SYNC_FIELDS` ⇒ 48 筆承攬案已結案而 PM 案仍 contracted；
- 晚上 `case_name` 不在 ⇒ owner 的「完整案名」109 筆要三表各改一次。
兩者都是「三表都有這個欄位、只有一份在管同步、而白名單漏了它」。

同日還查到第三種形狀：`sync_from_pm` 對 `ERPQuotation` 設 `client_name`，
而那個模型**沒有這個欄位** —— `setattr` 只設了一個 Python 屬性，不寫 DB、不報錯。
「同步做了」與「同步寫進資料庫」在程式碼裡長得一樣。

## 判準（全部靜態、不連 DB）

① 三表共有的業務欄位（下表）每一個都要在 `SYNC_FIELDS`（PM 側名）或
   `CONTRACT_SYNC_FIELDS`（承攬側別名）—— 缺一個 RED。
② `sync_from_pm` / `sync_from_contract` 寫到目標模型的每個欄位名，必須出現在
   該模型的 `Column(` 宣告裡 —— 不存在 RED（那就是靜默不落地）。
③ 端點（`projects/crud.py`、`pm/cases.py`）過濾 changed 時不得自己寫一份欄位清單，
   必須從 `field_sync` import —— 自抄 RED（09-02 上午的 crud.py 就是這樣讓修法失效）。

刻意不判「白名單裡的欄位有沒有真的被同步到每一表」——ERP 沒有 case_nature 是合理的，
那要人判斷，不是機械式規則。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import backend_dir  # noqa: E402

B = backend_dir()
FIELD_SYNC = B / "app/services/contract/field_sync.py"
MODELS = {
    "PMCase": B / "app/extended/models/pm.py",
    "ContractProject": B / "app/extended/models/core.py",
    "ERPQuotation": B / "app/extended/models/erp.py",
}
ENDPOINTS = [B / "app/api/endpoints/projects/crud.py", B / "app/api/endpoints/pm/cases.py"]

# 三表共有的業務語意欄位：(PM 側名, 承攬側名或 None)
SHARED = [
    ("case_name", "project_name"),
    ("client_name", "client_agency"),
    ("contract_amount", None),
    ("status", None),
    ("category", None),
    ("case_nature", None),
]


def _strip(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"(?m)^\s*#.*$", "", src)


def _list_literal(src: str, name: str) -> list[str]:
    m = re.search(rf"^{name}\s*=\s*(\[[^\]]*\])", src, re.M)
    if not m:
        return []
    return re.findall(r'"([a-z_]+)"', m.group(1))


def _model_columns(cls: str, path: Path) -> set[str]:
    src = path.read_text(encoding="utf-8")
    m = re.search(rf"^class {cls}\(Base\):[\s\S]*?(?=^class |\Z)", src, re.M)
    body = m.group(0) if m else ""
    return set(re.findall(r"^\s+([a-z_]+)\s*=\s*Column\(", body, re.M))


def _targets(src: str, func: str) -> dict[str, set[str]]:
    """回傳 {模型: {寫入的欄位}}。cp_update["x"] / pm_update["x"] / erp_update["x"] / erp.x = / setattr 不追。"""
    m = re.search(rf"async def {func}\([\s\S]*?(?=\n    async def |\Z)", src)
    body = m.group(0) if m else ""
    out = {"ContractProject": set(), "PMCase": set(), "ERPQuotation": set()}
    out["ContractProject"] |= set(re.findall(r'cp_update\["([a-z_]+)"\]\s*=', body))
    out["PMCase"] |= set(re.findall(r'pm_update\["([a-z_]+)"\]\s*=', body))
    out["ERPQuotation"] |= set(re.findall(r'erp_update\["([a-z_]+)"\]\s*=', body))
    out["ERPQuotation"] |= set(re.findall(r"\berp\.([a-z_]+)\s*=", body))
    return out


def main() -> int:
    print("=== 三表共有欄位同步白名單（weekly 101）===")
    src = _strip(FIELD_SYNC.read_text(encoding="utf-8"))
    sync = _list_literal(src, "SYNC_FIELDS")
    extra = re.search(r"^CONTRACT_SYNC_FIELDS\s*=\s*SYNC_FIELDS\s*\+\s*(\[[^\]]*\])", src, re.M)
    contract = sync + (re.findall(r'"([a-z_]+)"', extra.group(1)) if extra else [])
    print(f"  SYNC_FIELDS={sync}")
    print(f"  CONTRACT_SYNC_FIELDS 追加={sorted(set(contract) - set(sync))}")
    reds: list[str] = []

    # ① 共有欄位覆蓋
    for pm_name, ct_name in SHARED:
        if pm_name not in sync:
            reds.append(f"① 共有欄位 `{pm_name}` 不在 SYNC_FIELDS")
        if ct_name and ct_name not in contract:
            reds.append(f"① 承攬側別名 `{ct_name}` 不在 CONTRACT_SYNC_FIELDS")

    # ② 目標欄位存在於模型
    cols = {k: _model_columns(k, p) for k, p in MODELS.items()}
    for func in ("sync_from_pm", "sync_from_contract"):
        for model, fields in _targets(src, func).items():
            for f in sorted(fields):
                if f not in cols[model]:
                    reds.append(f"② {func} 寫 {model}.{f}，但模型沒有這個欄位 ⇒ setattr 靜默不落地")

    # ③ 端點不得自抄清單
    for ep in ENDPOINTS:
        s = _strip(ep.read_text(encoding="utf-8"))
        if "sync_from_" not in s:
            continue
        # 自抄的兩種寫法：`sync_fields = [...]`（crud.py 09-02 上午）與
        # `if k in ("category", "case_nature", ...)`（pm/cases.py，09-02 晚端到端 probe 抓到：
        # PM 側改案名不同步、承攬側會 —— 因為這份 inline tuple 連 status 都沒有）。
        # 首版只認第一種寫法，於是對第二種完全是盲的、印 GREEN；判準改成
        # 「任何用字面清單過濾 changed、且清單裡有兩個以上共有欄位名」。
        shared_names = {n for pair in SHARED for n in pair if n}
        for m in re.finditer(r"\bk in \(([^)]*)\)|\bk in \[([^\]]*)\]|sync_fields\s*=\s*\[([^\]]*)\]", s):
            names = set(re.findall(r'"([a-z_]+)"', m.group(1) or m.group(2) or m.group(3) or ""))
            if len(names & shared_names) >= 2:
                reds.append(f"③ {ep.relative_to(B)} 自己寫了一份同步欄位清單 {sorted(names)}，不是 import field_sync 的 SYNC_FIELDS")

    print()
    for r in reds:
        print(f"  🔴 {r}")
    if reds:
        print(f"\nStatus: [RED] {len(reds)} 項")
        return 2
    print("Status: [GREEN] 共有欄位全在白名單、目標欄位全存在於模型、端點未自抄清單")
    return 0


if __name__ == "__main__":
    sys.exit(main())
