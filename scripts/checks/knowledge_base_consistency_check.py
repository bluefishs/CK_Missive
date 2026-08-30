#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""四位一體一致性稽核：ADR × 知識地圖 × 架構圖 × 向量庫。

## 為什麼有這一支

owner 2026-08-30 的「四位一體同步規範書」指出的漂移：
「改了代碼、忘了改 ADR」「改了 ADR、忘了改架構圖」「檔案改了、向量庫沒跟上」。

第三種在同日已有實證：`kb_chunks` 在加排程之前**只能手動觸發**，
實測 289 個檔裡 **96 個內容已變（向量是舊的）＋37 個來源已刪除（索引裡的垃圾）
＝ 133/289（46%）是錯的**，而畫面上看不出來。

## 判準（三條，都用實測校準過）

### ① ADR ↔ 知識地圖　→ RED
`docs/adr/*.md` 每一篇都應該在 `docs/knowledge-map/` 裡被提及。
⚠️ 排除 `README` 與 `TEMPLATE` —— 它們不是 ADR。
沒排除的話首次執行就報 2 個假陽性（2026-08-30 實測）。

### ② 架構圖 node ↔ 原始碼　→ YELLOW
⚠️ **文件原本說「比對 `code_graph` 資料表」，而那張表不存在**
（實查 `information_schema`：沒有任何 `code_graph*` 表）。改為掃原始碼。

⚠️ 而且**不能拿所有 Mermaid node 去比對**：真實架構圖用的是標籤與縮寫
（`AI_SVC`／`AUTH`／`BYPASS`），85 個候選裡只有 4 個像類別名。
判準收窄成「CamelCase 且至少兩個大小寫轉折」，再扣掉技術名詞白名單。
收窄後 3 個候選，其中 **1 個真的不存在**（`IntentParsedResult`）——
**收窄之後才有訊號，不收窄只有噪音。**

判 YELLOW 不判 RED：架構圖可以畫「計畫中的元件」，那不是錯誤。

### ③ 向量庫 ↔ 檔案雜湊　→ RED
`kb_chunks.file_hash`（2026-08-30 新增）對照 docs/ 現檔的 MD5。
不符＝向量是舊的；DB 有而檔案沒有＝索引裡的垃圾；
檔案有而 DB 沒有＝從未進過向量庫。**這一條是精確的，不是啟發式。**

⚠️ 連不到 DB 時回「不可判定」（exit 2），**不是 GREEN** ——
「查不到」與「沒問題」在輸出上長得一樣，正是本檢核要防的東西。

## 誰跑它

weekly step 92（`run_fitness_weekly.sh`）。
⚠️ 規範書寫的是「Weekly Step 88」，而 88 已被 `pg_tuning_ssot_audit` 佔用
（87／89／90／91 亦然）—— 編號要 grep 過再用。
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

# 不是 ADR 的檔名
NOT_ADR = {"README", "TEMPLATE", "index"}

# 「像類別名」＝ CamelCase 且至少兩個大小寫轉折
CLASSLIKE = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)\b")
# 技術名詞白名單 —— 它們長得像類別名但不是本專案的符號
TECH_WORDS = {
    "TypeScript", "JavaScript", "PostgreSQL", "FastAPI", "AsyncIO",
    "OpenAPI", "WebSocket", "GitHub", "CloudFlare", "Cloudflare",
    "DockerFile", "Dockerfile", "NodeJS", "PyTest", "SqlAlchemy",
    "SQLAlchemy", "React", "AntDesign", "Redis", "Nginx",
}
# 掃描原始碼的範圍
#
# ⚠️ **刻意不含 `scripts/`**：本檔的 docstring 裡就寫著
# 「`IntentParsedResult` 在程式碼裡找不到」這個發現 —— 首版把 `scripts/`
# 納入掃描範圍，於是它**找到自己的註解**、判定該符號存在，
# 把唯一的真陽性沖成 0。**檢核把自己證偽了。**
#
# 通則：**判準的掃描範圍不得包含描述該判準的文字**。
# 同族＝L97（判準命中字串／註解）。
SRC_DIRS = ["backend/app", "frontend/src"]

# docs 下會進向量庫的子目錄（與 kb_embedding.SCAN_DIRS 對齊）
SCAN_DIRS = ["knowledge-map", "adr", "diagrams", "reports", "specifications"]


def check_adr_vs_map() -> list[str]:
    adr_dir = DOCS / "adr"
    km_dir = DOCS / "knowledge-map"
    if not adr_dir.is_dir() or not km_dir.is_dir():
        return []
    adrs = [f.stem for f in sorted(adr_dir.glob("*.md")) if f.stem not in NOT_ADR]
    blob = "\n".join(
        f.read_text(encoding="utf-8", errors="replace") for f in km_dir.rglob("*.md")
    )
    names = {f.stem for f in km_dir.rglob("*.md")}
    return [a for a in adrs if a not in blob and a not in names]


def check_diagram_symbols() -> list[tuple[str, str]]:
    dg = DOCS / "diagrams"
    if not dg.is_dir():
        return []
    candidates: dict[str, str] = {}
    for f in sorted(dg.rglob("*.md")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        for blk in re.findall(r"```mermaid(.*?)```", txt, re.S):
            for name in CLASSLIKE.findall(blk):
                if name not in TECH_WORDS:
                    candidates.setdefault(name, f.name)
    if not candidates:
        return []

    # 一次把原始碼讀進來比對（比逐個 grep 快，且不依賴外部工具）
    src_blob: list[str] = []
    for d in SRC_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.suffix not in (".py", ".ts", ".tsx", ".js", ".cjs"):
                continue
            if "__pycache__" in p.as_posix() or "node_modules" in p.as_posix():
                continue
            try:
                src_blob.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    joined = "\n".join(src_blob)
    return [(n, f) for n, f in sorted(candidates.items()) if n not in joined]


def check_vector_freshness() -> tuple[str, dict]:
    """回 (status, detail)。status ∈ {'ok', 'drift', 'unavailable'}"""
    try:
        import asyncio

        sys.path.insert(0, str(ROOT / "backend"))
        os.environ.setdefault(
            "DATABASE_URL",
            "postgresql+asyncpg://ck_user:ck_password_2024@127.0.0.1:5434/ck_documents",
        )
        from sqlalchemy import text  # noqa: E402

        from app.db.database import async_session_maker  # noqa: E402

        async def _run():
            async with async_session_maker() as db:
                rows = (await db.execute(
                    text("SELECT DISTINCT file_path, file_hash FROM kb_chunks")
                )).all()
            return {fp: fh for fp, fh in rows}

        db_state = asyncio.run(_run())
    except Exception as e:  # noqa: BLE001
        return "unavailable", {"error": f"{type(e).__name__}: {e}"}

    sources: dict[str, str] = {}
    for sub in SCAN_DIRS:
        base = DOCS / sub
        if not base.is_dir():
            continue
        for md in base.rglob("*.md"):
            try:
                content = md.read_text(encoding="utf-8")
            except Exception:
                continue
            if not content.strip():
                continue
            rel = md.relative_to(DOCS).as_posix()
            sources[rel] = hashlib.md5(content.encode("utf-8")).hexdigest()

    stale = [p for p, h in sources.items() if p in db_state and db_state[p] != h]
    orphan = [p for p in db_state if p not in sources]
    never = [p for p in sources if p not in db_state]
    return ("drift" if (stale or orphan or never) else "ok"), {
        "stale": stale, "orphan": orphan, "never": never,
        "files_total": len(sources),
    }


def main() -> int:
    print("=" * 74)
    print("四位一體一致性：ADR × 知識地圖 × 架構圖 × 向量庫（weekly 92）")
    print("=" * 74)

    if not DOCS.is_dir():
        print(f"\n✗ 找不到 {DOCS} —— 無法判定（不視為通過）")
        return 2

    reds: list[str] = []
    yellows: list[str] = []

    # ①
    missing_adr = check_adr_vs_map()
    print(f"\n① ADR ↔ 知識地圖：{len(missing_adr)} 篇未被地圖提及")
    for a in missing_adr:
        print(f"    [RED  ] docs/adr/{a}.md 沒有出現在 docs/knowledge-map/")
        reds.append(f"ADR 未入地圖: {a}")

    # ②
    ghost = check_diagram_symbols()
    print(f"\n② 架構圖 node ↔ 原始碼：{len(ghost)} 個符號在程式碼裡找不到")
    for name, src in ghost:
        print(f"    [YELLOW] {name}（出現於 docs/diagrams/{src}）")
        yellows.append(f"架構圖指向不存在的符號: {name}")

    # ③
    status, detail = check_vector_freshness()
    if status == "unavailable":
        print(f"\n③ 向量庫 ↔ 檔案雜湊：**連不到 DB，不可判定** —— {detail.get('error')}")
        print("    「查不到」不等於「沒問題」，故不視為通過。")
        return 2
    print(f"\n③ 向量庫 ↔ 檔案雜湊：來源 {detail['files_total']} 個檔")
    for label, key, why in (
        ("內容已變、向量是舊的", "stale", "docs 改了但沒重新向量化"),
        ("DB 有、來源已刪", "orphan", "索引裡的垃圾，RAG 會檢索到不存在的文件"),
        ("來源有、DB 沒有", "never", "從未進過向量庫"),
    ):
        items = detail[key]
        if items:
            print(f"    [RED  ] {label}：{len(items)} 個（{why}）")
            for p in items[:5]:
                print(f"             · {p}")
            if len(items) > 5:
                print(f"             …其餘 {len(items) - 5} 個")
            reds.append(f"{label} {len(items)} 個")

    print()
    if reds:
        print("⚠️ 這一類的危險是**畫面上看不出來**：RAG 檢索到舊內容或不存在的文件時，")
        print("   回答看起來一樣正常。修法：後台『增量同步』或 POST /api/knowledge-base/embed")
        print(f"\nStatus: [RED] {len(reds)} 項不一致｜另有 {len(yellows)} 項待確認")
        return 2
    if yellows:
        print(f"Status: [YELLOW] {len(yellows)} 項待確認（架構圖可以畫計畫中的元件，未必是錯）")
        return 1
    print("Status: [GREEN] 四者一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
