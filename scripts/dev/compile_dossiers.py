#!/usr/bin/env python
"""履歷編譯入口 —— 讓 2026-08-13 產出的 42 篇履歷不會爛掉。

## 為什麼需要這一支

履歷（`dossier.py` 的 ADR 履歷、`feature_dossier.py` 的功能模組履歷）當天是**手動**
產出的。本專案最常見的死法就是這個：一份看起來很有用的東西產出一次之後
沒有人維護它，幾個月後它記載的東西已經不是現實，而**沒有任何訊號會說**
（`entity_relations` 停在 6/16 卻仍被指標讀著、wiki index 停在 04-19 而新頁全成孤兒，
都是同一回事）。

## 為什麼跑在 host 而不是容器

`dossier.py` 要 `git log`、`feature_dossier.py` 要查 DB。實測容器內
**有 psql、但沒有 git 也沒有 docker CLI** —— 與 2026-08-11 那三支 daily 檢核
同一個坑（檢核跑在哪個環境，和它判得對不對一樣重要）。

所以沿用既有分工：**host 產出、容器消費**（同 weekly fitness 於 08-07 的移交）。
排在 **週一 04:50**，容器的 `wiki_compile`（05:00）緊接著 `rebuild_index`，
新頁面同一輪就會進索引、不會變成孤兒。

## 產出

`wiki/memory/integration-health/dossier-compile.json`，由 producer registry 以
`json_result` 納管。**不用 `file_fresh`** —— 2026-08-03 立法：凡產出結果檔者，
`file_fresh` 一律不得單獨使用（它證明的是「跑了」，不是「跑出東西了」）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "wiki" / "memory" / "integration-health" / "dossier-compile.json"


def _run(script: str, args: list[str]) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dev" / script), *args],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=1800,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    print("=" * 70)
    print("履歷編譯（ADR 履歷 + 功能模組履歷）")
    print("=" * 70)

    results: dict[str, object] = {
        "compiled_at": datetime.now().isoformat(timespec="seconds"),
        "fail": 0,
    }

    rc_adr, out_adr = _run("dossier.py", ["--all-adr"])
    adr_pages = out_adr.count("✓")
    print(f"  ADR 履歷      rc={rc_adr}  產出 {adr_pages} 頁")

    rc_feat, out_feat = _run("feature_dossier.py", ["--all", "--emit-wiki"])
    feat_pages = out_feat.count("✓")
    print(f"  功能模組履歷  rc={rc_feat}  產出 {feat_pages} 頁")

    # 知識地圖 —— 2026-08-13 併入本入口。
    #
    # 它本來掛在 `.git/hooks/post-commit` 上，條件是 commit 有動到
    # `.claude/{skills,rules,agents,commands}/` 或 `docs/{adr,diagrams,knowledge-map}/`。
    # 但那個呼叫是 **背景執行 + 輸出丟 /dev/null**：失敗與沒跑長得完全一樣。
    # 實際結果是 owner 回報「知識地圖感覺還是舊的」時，內容停在 **2026-03-19**、
    # 已經五個月 —— 而手動跑一次就正常產出（226 → 281 卡片），生成器毫無問題。
    # 機制在、產出停了，沒有任何訊號。這正是本檔要治的那個形狀，只是換個對象。
    kmap = ROOT / ".claude" / "scripts" / "generate-knowledge-map.cjs"
    if kmap.exists():
        p = subprocess.run(["node", str(kmap)], cwd=str(ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=1800)
        cards = 0
        m = __import__("re").search(r"卡片[:：]\s*(\d+)", p.stdout or "")
        if m:
            cards = int(m.group(1))
        print(f"  知識地圖      rc={p.returncode}  卡片 {cards} 張")
        results["kmap_cards"] = cards
        if p.returncode != 0 or cards == 0:
            results["fail"] = int(results["fail"]) + 1
            results.setdefault("errors", []).append(  # type: ignore[union-attr]
                f"knowledge-map: rc={p.returncode} cards={cards}")
    else:
        results["fail"] = int(results["fail"]) + 1
        results.setdefault("errors", []).append("knowledge-map: 生成器不存在")  # type: ignore[union-attr]

    results["adr_pages"] = adr_pages
    results["feature_pages"] = feat_pages
    results["pages"] = adr_pages + feat_pages

    # 產出 0 頁不是「沒事可做」而是壞了 —— 兩支生成器的輸入（docs/adr、
    # site_navigation_items）都不可能真的變成空的。分開記，才知道是哪一邊斷。
    for label, rc, n in (("dossier", rc_adr, adr_pages), ("feature_dossier", rc_feat, feat_pages)):
        if rc != 0 or n == 0:
            results["fail"] = int(results["fail"]) + 1
            results.setdefault("errors", []).append(  # type: ignore[union-attr]
                f"{label}: rc={rc} pages={n}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  已寫入 {OUT.relative_to(ROOT)}")

    if results["fail"]:
        print(f"\nStatus: [RED] {results['fail']} 個生成器失敗或零產出")
        for e in results.get("errors", []):  # type: ignore[union-attr]
            print(f"  - {e}")
        return 2
    print(f"\nStatus: [GREEN] 共 {results['pages']} 頁履歷已更新")
    print("  註：索引由容器的 wiki_compile（週一 05:00）緊接著 rebuild，故不會變孤兒。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
