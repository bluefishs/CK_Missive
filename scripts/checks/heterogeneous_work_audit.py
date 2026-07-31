#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
異質同工防增量審計（Heterogeneous-Same-Work Anti-Regrowth Audit）

登記表：docs/architecture/HETEROGENEOUS_WORK_REGISTRY.md
立法觸發：2026-07-16 整體覆盤——兩大反覆回歸 bug 家族（SSO L74/L78、KG L79）
         根源皆為異質同工（不同實作各自做同一件事）。收斂後須防其重新長出來。

偵測（皆對照 baseline，成長即 RED）：
  A. 前端 axios.create 實例數（H1）——SSO 反覆回歸根源。baseline=2
     （api/interceptors.ts 主 client + services/authService.ts；收斂後應降為 1）
  B. scripts 內直呼 ollama /api/embed 繞過 ai_connector 的檔案（H2）。
     baseline whitelist=2 host 緊急腳本；新增未登記者即 RED。
  C. 後端 services 頂層 stub 轉發檔數（H3）——只增不減即 RED（Q3 應遞減）。baseline<=81

host 側執行（read-only，不動 runtime）。cp950 韌性（L49.8）。
用法：
    python scripts/checks/heterogeneous_work_audit.py           # 觀察
    python scripts/checks/heterogeneous_work_audit.py --strict  # 超 baseline exit 1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# cp950 host 韌性（L49.8 同族）
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]

# ---- Baselines（收斂後應下降；此為「不得超過」上限）----
BASE_AXIOS_INSTANCES = 2          # H1: 目標收斂到 1
BASE_DUP_BASENAMES = 5            # H4: 同名元件跨目錄組數上限（現況 5，逐步收斂）
BASE_STUB_FILES = 5               # H3: 顯式 stub 標記檔（re-export/向後相容/已遷移）；目標 Q3 遞減到 0
                                  #     註：舊記憶「81」為廣義 grep 高估（含註解僅提及「遷移」者）
# H4: 同名元件跨目錄 —— 已人工核實為「合理」者（2026-07-31 逐一開檔確認）
#     判定原則：re-export shim / 語意刻意不同 / 測試鏡像目錄
DUP_BASENAME_LEGIT = {
    # 頂層檔為子目錄的 re-export shim（模組化良好，非重複）
    "ReportsPage.tsx",
    "TaoyuanProjectDetailPage.tsx",
    "UnifiedFormDemoPage.tsx",
    # CLAUDE.md / ADR-0031 已載明語意不同：健康進化 vs 結晶進化
    "EvolutionTab.tsx",
    # 測試鏡像目錄（__tests__ 與元件旁各一份）
    "AgentStepsDisplay.test.tsx", "GraphNodeSettings.test.tsx",
    "GraphToolbar.test.tsx", "MessageBubble.test.tsx",
    "SelectedNodeInfoCard.test.tsx", "MermaidBlock.test.tsx",
    "index.tsx",
}

EMBED_BYPASS_WHITELIST = {        # H2: 已登記的 host 緊急腳本
    "backfill_dispatch_embeddings.py",
    "backfill_kg_embeddings_all.py",
}


def audit_axios_instances() -> tuple[int, list[str]]:
    """H1: 前端 axios.create 實例數。"""
    hits = []
    fe = ROOT / "frontend" / "src"
    if not fe.exists():
        return 0, []
    for p in fe.rglob("*.ts"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"axios\.create\s*\(", txt):
            hits.append(str(p.relative_to(ROOT)))
    for p in fe.rglob("*.tsx"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"axios\.create\s*\(", txt):
            hits.append(str(p.relative_to(ROOT)))
    return len(hits), sorted(hits)


def audit_embed_bypass() -> tuple[list[str], list[str]]:
    """H2: scripts/sync 直呼 ollama /api/embed 繞過 ai_connector。回 (未登記新增, 全部)。
    僅掃 scripts/sync（真正的 backfill 工具區）；scripts/checks（審計本身會提及 pattern）不掃。"""
    all_hits, unregistered = [], []
    sync_dir = ROOT / "scripts" / "sync"
    if not sync_dir.exists():
        return [], []
    for p in sync_dir.rglob("*.py"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # 真的有 httpx/requests 打 /api/embed（非僅註解提及）
        if re.search(r"(OLLAMA_URL|httpx|requests)\b", txt) and re.search(r"/api/embed", txt):
            rel = str(p.relative_to(ROOT))
            all_hits.append(rel)
            if p.name not in EMBED_BYPASS_WHITELIST:
                unregistered.append(rel)
    return sorted(unregistered), sorted(all_hits)


def audit_stub_files() -> int:
    """H3: backend/app/services/ 頂層顯式 stub 標記檔（可辯護信號）。"""
    svc = ROOT / "backend" / "app" / "services"
    if not svc.exists():
        return 0
    marker = re.compile(r"re-export|向後相容|backward[- ]?compat|已遷移")
    count = 0
    for p in svc.glob("*.py"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if marker.search(txt):
            count += 1
    return count


def audit_duplicate_basenames() -> list[tuple[str, list[str]]]:
    """H4: 同一元件檔名出現在不同目錄（2026-07-31 立法）

    為何要這條：既有 H1-H3 只監控三個歷史個案（axios / embed / stub），
    不是「同一功能有兩份實作」的通則。2026-07-31 當日三起缺陷
    （ExpensesTab 兩份能力不一致、一鍵建案兩分支各寫一套、
    PCC/ezbid 設計不一致）全部在雷達之外，審計照樣報 GREEN。

    為何用確定性檔名比對而非語意相似度：
    同日實測把語意（嵌入）審計指向前端 → 719 個候選且明顯噪音
    （ContractCaseDetailPage ⇄ StatusTags 相似度 0.905），
    因為 React 元件/hook 的命名嵌入天然相近，無鑑別力。
    檔名重複是零誤判設計的訊號：每一筆都是真的同名，由人判定是否合理。
    """
    fe = ROOT / "frontend" / "src"
    if not fe.exists():
        return []
    seen: dict[str, list[str]] = {}
    for p in fe.rglob("*.tsx"):
        seen.setdefault(p.name, []).append(str(p.relative_to(ROOT)).replace("\\", "/"))
    dups = []
    for name, paths in sorted(seen.items()):
        if len(paths) > 1 and name not in DUP_BASENAME_LEGIT:
            dups.append((name, sorted(paths)))
    return dups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    fails = []
    print("=" * 60)
    print("異質同工防增量審計（H1 axios / H2 embed-bypass / H3 stub / H4 同名元件）")
    print("=" * 60)

    # H1
    n_axios, axios_hits = audit_axios_instances()
    tag = "RED" if n_axios > BASE_AXIOS_INSTANCES else ("GREEN" if n_axios <= 1 else "WATCH")
    print(f"\n[H1] 前端 axios.create 實例：{n_axios} (baseline<= {BASE_AXIOS_INSTANCES}) [{tag}]")
    for h in axios_hits:
        print(f"     - {h}")
    if n_axios > BASE_AXIOS_INSTANCES:
        fails.append(f"H1 axios 實例 {n_axios} > baseline {BASE_AXIOS_INSTANCES}（新異質同工）")

    # H2
    unreg, all_embed = audit_embed_bypass()
    tag = "RED" if unreg else "GREEN"
    print(f"\n[H2] scripts 直呼 /api/embed 繞過 SSOT：{len(all_embed)} (已登記 {len(EMBED_BYPASS_WHITELIST)}) [{tag}]")
    for h in all_embed:
        mark = "  <-- 未登記!" if h in unreg else ""
        print(f"     - {h}{mark}")
    if unreg:
        fails.append(f"H2 新增未登記 embed-bypass：{unreg}（應走 ai_connector/EmbeddingManager）")

    # H3
    n_stub = audit_stub_files()
    tag = "RED" if n_stub > BASE_STUB_FILES else "GREEN"
    print(f"\n[H3] 後端 services stub 轉發檔：{n_stub} (baseline<= {BASE_STUB_FILES}, Q3 應遞減) [{tag}]")
    if n_stub > BASE_STUB_FILES:
        fails.append(f"H3 stub {n_stub} > baseline {BASE_STUB_FILES}（新異質同工路徑）")

    # H4
    dups = audit_duplicate_basenames()
    tag = "RED" if len(dups) > BASE_DUP_BASENAMES else "GREEN"
    print(f"\n[H4] 同名元件跨目錄：{len(dups)} 組 (baseline<= {BASE_DUP_BASENAMES}) [{tag}]")
    for name, paths in dups:
        print(f"     - {name}")
        for pp in paths:
            print(f"         {pp}")
    if len(dups) > BASE_DUP_BASENAMES:
        fails.append(
            f"H4 同名元件 {len(dups)} 組 > baseline {BASE_DUP_BASENAMES}"
            "（新的『同一功能兩份實作』；核實後若屬合理請加入 DUP_BASENAME_LEGIT）"
        )

    print("\n" + "=" * 60)
    if not fails:
        print("GREEN: 無異質同工增量")
        return 0
    print(f"{len(fails)} 項超 baseline：")
    for f in fails:
        print(f"  - {f}")
    if args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
