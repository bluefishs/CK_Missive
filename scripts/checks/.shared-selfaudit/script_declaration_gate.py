# -*- coding: utf-8 -*-
"""腳本強制表態閘門（canonical: shared-modules/selfaudit/src/）— 2026-08-09。

## 這支解決什麼

**寫下一支腳本，卻沒有任何人會跑它** —— 這在本專案是反覆形態：

    lvrland  6 支檢核腳本沒有 runner（2026-08-01 發現）
    pile     6 支同樣狀況（2026-08-09 發現，至此才建 runner）
    Missive  `sso_ttl_ssot_audit.py` 寫好兩週沒接線；另有 6 支孤兒
    DT       新建的 `asset_integrity_audit.py` 我自己就忘了接線

而**既有的三層都抓不到**（2026-08-09 查證）：

| 層 | 為什麼抓不到 |
|---|---|
| 程式圖譜 | 掃 `backend/app`，**不含 `scripts/`**；且完全不解析 `.sh` —— runner 對腳本的引用是 shell 裡的一個字串，Python AST 圖譜沒有那條邊 |
| `code_graph_orphan_audit` | 它問的是「圖裡還留著但程式碼已刪」，不是「檔案還在但沒人跑」。同名反義 |
| 覆盤 | 靠人想到要問。孤兒的症狀是**一片安靜**，不在任何問題清單上 |

## 為什麼是「寫入當下」而不是事後掃描

2026-08-09 逐一查證 CK_Missive 那 6 支孤兒，**其中 3 支不是「一次性工具」而是壞掉被拿掉的**
（cp950 崩潰、需容器模組、印 12 個 issue 卻 exit 0）。

事後掃描只能告訴你「沒人跑」，**分不出是刻意還是壞掉**；
而寫入當下，作者就是知道答案的那個人。兩者互補，缺一不可。

原型來自 `CK_PileMgmt/backend/tests/integration/test_active_ssot_indexed.py`
（2026-04-28 建立、實戰驗證過），其 docstring 寫得最好：
**「沒有『我忘了』這個 failure mode」**。本檔把判定邏輯抽出共用，
scope 與索引檔位置由各 repo 的設定提供 —— 直接複製那支就是製造第五份會漂移的副本。

## 使用（各 repo 寫一支薄包裝）

    from script_declaration_gate import check_declarations
    code, msgs = check_declarations(
        repo_root=Path(__file__).resolve().parents[2],
        index_files=["CLAUDE.md"],
        scopes=[("scripts/checks", "*.py"), ("scripts/checks", "*.sh")],
        peripheral={"jwt_debug.py": "除錯工具，非檢核"},
    )

## 判準

  scope 內的每個檔案，必須滿足其一：
    (a) 檔名（或含它的 brace 縮寫路徑）出現在任一索引文件
    (b) 列在 peripheral 且**附理由**（只有名字沒有理由 → 視為未表態）

  兩者皆無 → 未表態 → 閘門失敗。
"""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _indexed(name: str, rel: str, blobs: list[str]) -> bool:
    """檔名或相對路徑出現在任一索引文件即算表態。

    同時比對 basename 與 relative path —— pile 的原型只比對這兩者，
    因為索引文件常用 brace 縮寫（`scripts/dr/{backup,restore}.sh`），
    完整路徑比對會漏掉。寧可寬鬆：這道閘門要擋的是「完全沒提過」。
    """
    return any(name in b or rel in b for b in blobs)


def check_declarations(
    repo_root: Path,
    index_files: list[str],
    scopes: list[tuple[str, str]],
    peripheral: dict[str, str] | None = None,
) -> tuple[int, list[str]]:
    """回傳 (退出碼, 訊息)。0=全部表態 / 2=有未表態。

    抽成純函式才驗得了鑑別力 —— 各 repo 的包裝只負責提供設定。
    """
    peripheral = peripheral or {}
    msgs: list[str] = []

    blobs: list[str] = []
    for f in index_files:
        p = repo_root / f
        if not p.exists():
            # 索引檔不存在＝設定寫錯，不是「全部通過」
            return 2, [f"✗ 索引文件不存在：{f} —— 無法判定，不視為通過"]
        blobs.append(p.read_text(encoding="utf-8", errors="replace"))

    discovered: list[tuple[str, str]] = []
    for scope_dir, pattern in scopes:
        d = repo_root / scope_dir
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and fnmatch.fnmatch(p.name, pattern):
                discovered.append((p.name, f"{scope_dir}/{p.name}"))

    if not discovered:
        # 掃到 0 個檔案幾乎必然是 scope 設定錯 —— 不可判綠
        return 2, ["✗ scope 內掃到 0 個檔案 —— 設定可能寫錯（0 個不等於全部表態）"]

    undeclared: list[str] = []
    declared_peripheral = 0
    for name, rel in discovered:
        if _indexed(name, rel, blobs):
            continue
        reason = peripheral.get(name) or peripheral.get(rel)
        if reason and reason.strip():
            declared_peripheral += 1
            continue
        if (name in peripheral or rel in peripheral) and not (reason or "").strip():
            # 只放名字沒寫理由 —— 三個月後沒人知道當初為什麼，等於沒表態
            undeclared.append(f"{rel}（在 peripheral 但**沒寫理由**）")
            continue
        undeclared.append(rel)

    msgs.append(f"  掃描 {len(discovered)} 個檔案｜索引 {len(discovered) - len(undeclared) - declared_peripheral}"
                f"｜明列周邊 {declared_peripheral}｜未表態 {len(undeclared)}")
    if undeclared:
        msgs.append(f"✗ {len(undeclared)} 個檔案未表態（既不在索引，也不在 peripheral）：")
        msgs += [f"    · {u}" for u in undeclared[:10]]
        if len(undeclared) > 10:
            msgs.append(f"    …另 {len(undeclared) - 10} 個")
        msgs.append("  → 二選一：在索引文件說明它做什麼，或加進 peripheral 並**寫明理由**")
        return 2, msgs
    return 0, msgs


def self_test() -> int:
    """證明判準會動 —— 用暫存目錄造出四種情境。"""
    import shutil
    import tempfile

    root = Path(tempfile.mkdtemp())
    (root / "scripts" / "checks").mkdir(parents=True)
    for n in ("indexed.py", "peripheral.py", "orphan.py", "noreason.py"):
        (root / "scripts" / "checks" / n).write_text("x", encoding="utf-8")
    (root / "CLAUDE.md").write_text("見 scripts/checks/indexed.py 說明", encoding="utf-8")

    scopes = [("scripts/checks", "*.py")]
    cases = [
        ("全部表態", {"peripheral.py": "一次性", "orphan.py": "另一個一次性",
                   "noreason.py": "也有理由"}, 0),
        ("有未表態", {"peripheral.py": "一次性", "noreason.py": "有理由"}, 2),
        ("只放名字沒理由", {"peripheral.py": "一次性", "orphan.py": "", "noreason.py": "有理由"}, 2),
    ]
    bad = []
    for name, periph, expect in cases:
        code, _ = check_declarations(root, ["CLAUDE.md"], scopes, periph)
        ok = code == expect
        print(f"  {'✓' if ok else '✗'} {name:16s} 預期 exit={expect} 實際={code}")
        if not ok:
            bad.append(name)

    # 負向：索引檔不存在
    code, _ = check_declarations(root, ["NOPE.md"], scopes, {})
    ok = code == 2
    print(f"  {'✓' if ok else '✗'} {'索引檔不存在':16s} 預期 exit=2 實際={code}")
    if not ok:
        bad.append("索引檔不存在")

    # 負向：scope 掃到 0 個
    code, _ = check_declarations(root, ["CLAUDE.md"], [("nowhere", "*.py")], {})
    ok = code == 2
    print(f"  {'✓' if ok else '✗'} {'scope 掃到 0 個':16s} 預期 exit=2 實際={code}")
    if not ok:
        bad.append("scope 0 個")

    shutil.rmtree(root, ignore_errors=True)
    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 1 例、負向 4 例）")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
