#!/usr/bin/env python
"""履歷組裝器 —— 一個模組／ADR／主題的來龍去脈，一次組出來。

## 為什麼要這一支

要回答「這個模組是什麼、誰在用、誰在看、為什麼長這樣」，目前得翻 **9 個地方**：

| 來源 | 現況規模 | 記的是 |
|---|---|---|
| `CLAUDE.md` 里程碑 | 58 條 | 那一輪做了什麼、為什麼 |
| `docs/architecture/LESSONS_REGISTRY.md` | 80 條 | 踩過的坑與防復發 |
| `docs/adr/` | 25 份 | 決策與取捨 |
| `docs/architecture/` | 100 份 | 設計與盤點 |
| `docs/runbooks/` | 41 份 | 出事時怎麼辦 |
| `wiki/memory/` | 366 檔 | 日誌／模式／失敗 |
| git commit | 1973 個 | 實際改了什麼 |
| `scripts/checks/README.md` | 157 支 | 誰在跑它 |
| `producer_outcome_registry.json` | 32 筆 | 誰在看它的產出 |

每一份單獨看都合理，合起來的後果是：**同一件事的來龍去脈散在九處，
而沒有任何一處是完整的**。於是每次覆盤都從搜尋開始，而搜尋會漏
——今天 `tender_cache` 的 NameError 最早日誌是 2026-05-27，
在那之後的每一次覆盤都沒看見它。

## 為什麼不是「再寫一份履歷文件」

因為那會變成第 10 份，而且是唯一需要人手動維護的一份 ——
本專案反覆踩過的正是這個（`.claude/rules/cross-file-ssot-governance.md`：
同一件事有兩份說法時，沒有任何一方會報錯）。

**履歷是組出來的，不是寫出來的。** 九個來源維持原狀各司其職，
本支負責在需要的時候把它們對齊到同一個主題上。

## 用法

    python scripts/dev/dossier.py backend/app/extended/models/tender_cache.py
    python scripts/dev/dossier.py tender_cache          # 關鍵字
    python scripts/dev/dossier.py ADR-0021              # ADR 編號
    python scripts/dev/dossier.py --md > /tmp/x.md      # 輸出 markdown
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str], cwd: Path | None = None) -> str:
    try:
        r = subprocess.run(args, cwd=str(cwd or ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=90)
        return r.stdout
    except Exception:
        return ""


def _grep_files(pattern: str, paths: list[Path], max_hits: int = 12) -> list[tuple[Path, int, str]]:
    """在指定檔案集合裡找 pattern，回 (檔案, 行號, 該行)。"""
    rx = re.compile(re.escape(pattern), re.I)
    out: list[tuple[Path, int, str]] = []
    for p in paths:
        if not p.is_file():
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if rx.search(line):
                    out.append((p, i, line.strip()[:200]))
                    if len(out) >= max_hits:
                        return out
        except Exception:
            continue
    return out


def resolve_target(arg: str) -> tuple[str, Path | None]:
    """回 (關鍵字, 檔案路徑或 None)。接受檔案路徑、模組關鍵字、ADR 編號。"""
    p = Path(arg)
    if p.exists() and p.is_file():
        return p.stem, p.resolve()
    if (ROOT / arg).exists() and (ROOT / arg).is_file():
        return Path(arg).stem, (ROOT / arg).resolve()
    if re.fullmatch(r"(?i)adr[-_]?\d{3,4}", arg):
        num = re.sub(r"\D", "", arg)
        for sub in ("adr", "adr/archived", "archive"):
            for cand in (ROOT / "docs" / sub).glob(f"*{num}*.md"):
                return f"ADR-{num}", cand
        # 找不到檔案不等於這條 ADR 不存在 —— 它可能在別的 repo（跨 repo 用 FQID
        # `<Repo>#<4-digit>`，見 CONVENTIONS.md）或已歸檔。說清楚比靜靜留白好。
        print(f"※ 本 repo 的 docs/adr* 找不到 {num} 的檔案 —— "
              f"可能屬別的 repo（跨 repo ADR 用 FQID）或已歸檔；"
              f"以下改以關鍵字模式組裝\n", file=sys.stderr)
        return f"ADR-{num}", None
    # 關鍵字：試著在 backend/frontend 找同名檔
    for base in ("backend/app", "frontend/src", "scripts"):
        for cand in (ROOT / base).rglob(f"{arg}.py"):
            return arg, cand
        for cand in (ROOT / base).rglob(f"{arg}.*"):
            return arg, cand
    return arg, None


def section_what(path: Path | None) -> list[str]:
    if path is None or path.suffix != ".py":
        if path and path.suffix == ".md":
            head = [l for l in path.read_text(encoding="utf-8", errors="ignore").splitlines()[:12] if l.strip()]
            return head[:6]
        return ["（無對應檔案，以關鍵字模式組裝）"]
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8", errors="ignore")))
    except Exception:
        doc = None
    if not doc:
        return ["（該模組沒有 docstring —— 履歷的第一段本來就該由它提供）"]
    return [l for l in doc.strip().splitlines()[:8]]


def section_consumers(keyword: str, path: Path | None) -> list[str]:
    """誰在用它 —— **真的 import**，不是提到它的名字。

    第一版用 stem 子字串比對，結果把只在註解裡寫「從 tender_cache_service.py
    拆出」的檔案也算成消費端。本專案的規矩是：交付不可信的清單比不交付更糟
    （SELF_AUDIT_EVOLUTION_STANDARD §3）。所以這裡只認 import 述句。
    """
    if path is None:
        return []
    stem = path.stem
    if path.suffix != ".py":
        # ADR 的檔名字根（`0028-error-contract-silent-failure-policy`）幾乎不會
        # 出現在程式碼裡 —— 大家寫的是 `ADR-0028`。用檔名去搜，得到的會是
        # 一份看起來「沒什麼人在用」的假清單，而那正好是最誤導人的結論。
        needle = keyword if keyword.upper().startswith("ADR-") else stem
        out = _run(["git", "grep", "-l", "-I", "-e", needle, "--",
                    "backend", "frontend/src", "scripts"])
        return [f for f in out.splitlines() if f and Path(f).name != path.name][:15]

    # import 述句才算：`import x.y.stem` / `from x.y.stem import ...` / `from .stem import`
    rx = re.compile(
        rf"^\s*(?:from\s+[\w.]*\b{re.escape(stem)}\b\s+import|import\s+[\w.]*\b{re.escape(stem)}\b)",
        re.M,
    )
    out = _run(["git", "grep", "-l", "-I", "-e", stem, "--", "backend", "scripts"])
    hits: list[str] = []
    for rel in out.splitlines():
        if not rel or Path(rel).name == path.name:
            continue
        f = ROOT / rel
        try:
            if rx.search(f.read_text(encoding="utf-8", errors="ignore")):
                hits.append(rel)
        except Exception:
            continue
    return hits[:15]


def section_who_runs(keyword: str) -> list[str]:
    rows: list[str] = []
    readme = ROOT / "scripts" / "checks" / "README.md"
    for _p, _i, line in _grep_files(keyword, [readme], max_hits=4):
        rows.append(f"scripts/checks/README.md：{line}")
    reg = ROOT / "backend" / "config" / "producer_outcome_registry.json"
    if reg.exists():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            for pr in data.get("producers", []):
                if keyword.lower() in json.dumps(pr, ensure_ascii=False).lower():
                    rows.append(f"producer registry：{pr.get('name')} ← {pr.get('signal')}")
        except Exception:
            pass
    sched = ROOT / "backend" / "app" / "core" / "scheduler.py"
    for _p, i, line in _grep_files(keyword, [sched], max_hits=3):
        rows.append(f"scheduler.py:{i}：{line}")
    return rows


def section_history(path: Path | None, keyword: str) -> list[str]:
    if path is not None:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        out = _run(["git", "log", "--follow", "--date=short",
                    "--format=%ad  %h  %s", "--", rel])
    else:
        out = _run(["git", "log", "--date=short", "--format=%ad  %h  %s",
                    f"--grep={keyword}", "-i"])
    lines = [l for l in out.splitlines() if l.strip()]
    return lines[:20]


def section_lessons(keyword: str) -> list[str]:
    reg = ROOT / "docs" / "architecture" / "LESSONS_REGISTRY.md"
    hits = _grep_files(keyword, [reg], max_hits=40)
    if not hits:
        return []
    # 把命中行往回對應到所屬的 ## L 標題
    text = reg.read_text(encoding="utf-8", errors="ignore").splitlines()
    heads: list[tuple[int, str]] = [
        (i, l) for i, l in enumerate(text, 1) if re.match(r"^## L\d+", l)
    ]
    seen, out = set(), []
    for _p, ln, _line in hits:
        owner = None
        for i, h in heads:
            if i <= ln:
                owner = h
            else:
                break
        if owner and owner not in seen:
            seen.add(owner)
            out.append(owner.lstrip("# ").strip()[:160])
    return out


def section_docs(keyword: str) -> list[str]:
    paths = (list((ROOT / "docs" / "adr").glob("*.md"))
             + list((ROOT / "docs" / "architecture").glob("*.md"))
             + list((ROOT / "docs" / "runbooks").glob("*.md")))
    hits = _grep_files(keyword, paths, max_hits=60)
    seen, out = set(), []
    for p, _i, _l in hits:
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if rel not in seen:
            seen.add(rel)
            out.append(rel)
    return out[:12]


def section_milestones(keyword: str) -> list[str]:
    cm = ROOT / "CLAUDE.md"
    out = []
    for _p, _i, line in _grep_files(keyword, [cm], max_hits=6):
        m = re.search(r"v6\.\d+ \(\d\d-\d\d[^)]*\)", line)
        tag = m.group(0) if m else "CLAUDE.md"
        idx = line.lower().find(keyword.lower())
        out.append(f"{tag} … {line[max(0, idx - 90): idx + 130]}")
    return out


def render(keyword: str, path: Path | None, md: bool) -> str:
    b = []
    title = f"履歷：{keyword}" + (f"（{os.path.relpath(path, ROOT)}）" if path else "")
    b.append(("# " if md else "") + title)
    b.append("")

    blocks = [
        ("它是什麼", section_what(path)),
        ("誰在用它", section_consumers(keyword, path)),
        ("誰在跑它 / 誰在看它", section_who_runs(keyword)),
        ("變更歷程", section_history(path, keyword)),
        ("相關教訓（LESSONS_REGISTRY）", section_lessons(keyword)),
        ("相關決策與文件", section_docs(keyword)),
        ("里程碑提及", section_milestones(keyword)),
    ]
    for name, rows in blocks:
        b.append(("## " if md else "── ") + name + ("" if md else " " + "─" * max(2, 46 - len(name))))
        if not rows:
            b.append("  （查無）—— 這本身是資訊：沒有人寫過它、沒有人在看它")
        else:
            for r in rows:
                b.append(("- " if md else "  ") + str(r))
        b.append("")
    return "\n".join(b)


WIKI_TOPICS = ROOT / "wiki" / "topics"


def emit_wiki(keyword: str, path: Path | None) -> Path:
    """把履歷落地成 wiki topic 頁 —— 走既有 LLM Wiki 管線，不另建第二套。

    為什麼放 `wiki/topics/` 而不新增子目錄：`WIKI_SUBDIRS` 是 SSOT
    （`services/wiki/service.py`），加一個目錄要動 backend 並 rebuild，
    而 v6.41 才踩過「子目錄清單寫死多處、漏改 rebuild_index 的 labels」。
    用既有目錄，既有的 lint／index／搜尋立刻涵蓋它，零 backend 變更。

    既有的「ADR 索引」「Lessons Registry 索引」是各自獨立的清單；
    本頁做的是**把它們對齊到同一個主題上** —— ADR 不知道誰實作它、
    誰在強制它、它生出了哪些教訓，那正是每次覆盤都要重新搜尋的原因。
    """
    WIKI_TOPICS.mkdir(parents=True, exist_ok=True)
    body = render(keyword, path, md=True)
    today = _run(["git", "log", "-1", "--date=short", "--format=%ad"]).strip() or "unknown"
    src = os.path.relpath(path, ROOT).replace("\\", "/") if path else "(關鍵字模式)"
    fm = (
        "---\n"
        f"title: 履歷 {keyword}\n"
        "type: topic\n"
        f"created: {today}\n"
        f"sources: [{src}, docs/adr, docs/architecture/LESSONS_REGISTRY.md, git log]\n"
        "tags: [履歷, 治理, 整合, auto-compiled]\n"
        "confidence: high\n"
        "---\n\n"
        "> 本頁由 `scripts/dev/dossier.py` 組出，**不要手改** ——\n"
        "> 它的九個來源各自維持原狀，本頁只負責把它們對齊到同一個主題上。\n\n"
    )
    out = WIKI_TOPICS / f"履歷 {keyword}.md"
    out.write_text(fm + body, encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="組出一個模組／ADR／主題的履歷")
    ap.add_argument("target", nargs="?", help="檔案路徑、模組關鍵字，或 ADR-0021")
    ap.add_argument("--md", action="store_true", help="輸出 markdown")
    ap.add_argument("--emit-wiki", action="store_true",
                    help="落地成 wiki/topics/ 頁（走既有 LLM Wiki 管線）")
    ap.add_argument("--all-adr", action="store_true",
                    help="為 docs/adr/ 每一篇 ADR 產出履歷頁")
    args = ap.parse_args()

    if args.all_adr:
        adrs = sorted((ROOT / "docs" / "adr").glob("[0-9]*.md"))
        print(f"為 {len(adrs)} 篇 ADR 組裝履歷…")
        for a in adrs:
            num = re.match(r"(\d+)", a.name)
            if not num:
                continue
            key = f"ADR-{num.group(1)}"
            p = emit_wiki(key, a)
            print(f"  ✓ {p.name}")
        return 0

    if not args.target:
        ap.error("需要 target（或用 --all-adr）")
    keyword, path = resolve_target(args.target)
    if args.emit_wiki:
        p = emit_wiki(keyword, path)
        print(f"已落地：{os.path.relpath(p, ROOT)}")
        return 0
    print(render(keyword, path, args.md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
