#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基礎設施事實漂移（weekly 122，2026-09-08）。

owner 09-08 從舊附件讀到三個「兩套」：sqlite `documents.db` vs PostgreSQL、後端 8001 vs 8003
「優化版」、行事曆服務帳號 vs OAuth2。逐項實查**都不存在** —— 出處是 2026-03 遷移前的附件
與 2026-05 歸檔 wiki。這是同一個病（兩份宣告互不牽動）的文件版：**文件說的東西已經不在了，
而沒有任何機制會告訴讀的人。**

對過期宣告的正確處置是**刪除**，不是「同步」成第二份。這支只做一件事：
**活文件**（非 `archived/`）裡不得再出現這些已不存在的基礎設施字樣。RED 即代表有人把舊附件抄回來了。

刻意排除：`docs/archived/`、`backups/`、`.git/`、`node_modules/`、CHANGELOG（歷史紀錄本來就會提到），
以及本檔與 LESSONS／CONSOLIDATION（它們在描述這個判準）。
"""
from __future__ import annotations
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT = repo_root()
PATTERNS = {
    "sqlite 資料庫（實際只有 PostgreSQL）": re.compile(r"sqlite:///\./(ck_)?documents\.db|ck_documents\.db\b"),
    "後端 8003（不存在的『優化版』）": re.compile(r"(?<![\d.])8003(?![\d])"),
    "Adminer/pgAdmin 8080（已退場）": re.compile(r"localhost:8080|pgadmin", re.I),
    "遷移前路徑 C:/GeminiCli": re.compile(r"GeminiCli"),
    "相對路徑憑證／資料庫教學（./credentials.json、./documents.db）": re.compile(r"\./(credentials\.json|documents\.db)"),
}
SKIP_DIRS = ("archived", "backups", ".git", "node_modules", "__pycache__", "dist", ".claude/code_graph")
SKIP_FILES = ("CHANGELOG.md", "scripts/checks/README.md", "LESSONS_REGISTRY.md", "CONSOLIDATION_20260907.md", "infra_facts_drift_audit.py",
              "code_graph_mtime.json", "quick-fix.md", "mandatory-checklist.md",
              "README.md" if False else "scripts_checks_README_placeholder")
EXT = {".md", ".txt", ".yml", ".yaml", ".example", ".ini", ".toml", ".cfg"}

def main() -> int:
    print("=== 基礎設施事實漂移（weekly 122）===")
    hits = []
    # os.walk 並**剪枝**：rglob 會走進 node_modules／backups（數萬檔），首版因此逾時 —— 剪枝在進目錄前做
    import os
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d == ".claude"]
        for name in filenames:
            f = Path(dirpath) / name
            rel = f.relative_to(ROOT).as_posix()
            if (f.suffix not in EXT and not name.startswith(".env")) or name in SKIP_FILES or rel in SKIP_FILES or name == ".env":
                continue
            if any(f"/{d}/" in f"/{rel}/" for d in SKIP_DIRS):
                continue
            # ⚠️ 首版把這一段縮排到 `continue` 底下（死碼）⇒ 永遠 GREEN。負向控制抓到的。
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for label, pat in PATTERNS.items():
                for i, line in enumerate(text.splitlines(), 1):
                    # 判準的掃描範圍不得包含描述它的文字（L110 家族）：
                    # 「⛔ 沒有的東西」那一行在列舉這些字樣；「~~…~~」是已結案的歷史紀錄
                    # 也豁免「作廢／已不存在／退場」這類**在宣告它不存在**的句子——那正是要留下的更正
                    if "沒有的東西" in line or "~~" in line or any(k in line for k in ("作廢", "已不存在", "已退場", "不存在")):
                        continue
                    if pat.search(line):
                        hits.append((label, rel, i, line.strip()[:80]))
    if hits:
        print(f"[RED] {len(hits)} 處活文件仍描述已不存在的基礎設施（舊附件回流）：")
        for label, rel, i, s in hits[:15]:
            print(f"    {label} ← {rel}:{i}  {s}")
        print("      處置：刪除或改為現況（PostgreSQL 5434／後端 8001／行事曆服務帳號），不要另存一份。")
        return 2
    print("[GREEN] 活文件裡沒有 sqlite／8003／8080／GeminiCli 這些已不存在的宣告")
    return 0

if __name__ == "__main__":
    sys.exit(main())
