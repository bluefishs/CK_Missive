"""Fitness step 63 (v6.12, 2026-05-30): 規範 vs 現況對應檢核 — 程式圖譜 + LLM Wiki 雙源

Owner 要求：透過程式圖譜與 llmwiki 對應規範與現況做檢核機制與進化執行成效。

對應 4 類規範：
- ADR (docs/adr/*.md)
- Lessons (wiki/memory/lessons/L*.md)
- SOPs (.claude/rules/*.md)
- Fitness steps (scripts/checks/*.py)

對應 3 類現況：
- code-graph entities (canonical_entities graph_domain='code')
- LLM Wiki pages (wiki/**/*.md)
- 真活 metric (governance_* + scheduler_job_*)

漂移檢測：
- 規範存在但 code 沒對應 (規範 over-prescribed)
- code 變但規範未更新 (規範 stale)
- lesson 編號 vs 檔案 vs 引用一致性
- ADR 編號 vs 規範引用一致性
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path
# 2026-08-15：weekly 跑在 host（cp950），而 ✅🔴⚠ 這些符號 cp950 編不出來。
# 崩潰是**路徑相依**的 —— 平常走 GREEN 分支沒事，偏偏在要報問題的那一刻崩掉，
# 而那時看到的是 UnicodeEncodeError 不是它本來要講的事。同 L49.8（.ps1 的 BOM）家族。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[2]


def fetch_metrics() -> dict[str, float]:
    """從 /metrics 抓所有 governance_* / scheduler_job_* 指標"""
    try:
        with urllib.request.urlopen("http://localhost:8001/metrics", timeout=8) as r:
            text = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return {}
    out: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("governance_") or line.startswith("kg_entities") or line.startswith("wiki_pages"):
            try:
                key = line.split("{")[0].split(" ")[0]
                val = float(line.rsplit(" ", 1)[1])
                if key not in out:
                    out[key] = val
            except (ValueError, IndexError):
                continue
    return out


def list_adrs() -> list[tuple[str, str]]:
    """回 [(adr_number, status), ...]
    v6.12 修法 (2026-05-30): 同 adr_lifecycle_check.py regex (接受 blockquote >)
    """
    out = []
    adr_dir = ROOT / "docs" / "adr"
    if not adr_dir.is_dir():
        return out
    STATUS_PATTERN = re.compile(
        r"^(?:\s*[-*>])?\s*\*\*(?:狀態|Status|status)\*\*\s*[:：]\s*"
        r"\*{0,2}`?([A-Za-z_]+)`?\*{0,2}",
        re.MULTILINE,
    )
    for f in sorted(adr_dir.rglob("00*.md")):
        m = re.match(r"^(\d{4})-", f.name)
        if not m:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")[:2000]
        except Exception:
            continue
        sm = STATUS_PATTERN.search(text)
        status = sm.group(1).lower() if sm else "unknown"
        if "archived" in f.parts:
            status = "archived"
        out.append((m.group(1), status))
    return out


def list_lessons() -> list[str]:
    """回 ['L01', 'L02', ...]

    2026-08-27 修：原本只讀 `wiki/memory/lessons/`，而那個目錄**是空的**
    ⇒ 這支檢核三個月來一直印「Lessons (wiki/memory): 0」然後判「無漂移」。
    真正的 lessons 集中在 `docs/architecture/LESSONS_REGISTRY.md`（82 條）。

    ⚠️ **同一個 bug 在同一個 repo 裡已經修過一次**：
    `generate_governance_dashboard.py:112` 的註解白紙黑字寫著
    「L67 同型修（2026-06-11）：原讀空目錄 wiki/memory/lessons/ → Lessons 永遠 0；
      真實 lessons 集中在 LESSONS_REGISTRY.md」。
    兩支腳本讀同一份東西，當時只修了其中一支 —— 而沒被修的那支不會報錯，
    它只是安靜地回 0，然後說一切正常。掃全同型的價值就在這裡。
    """
    out: list[str] = []
    registry = ROOT / "docs" / "architecture" / "LESSONS_REGISTRY.md"
    if registry.is_file():
        for line in registry.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"^##\s+(L\d+)\s", line)
            if m:
                out.append(m.group(1))
    if out:
        return out
    # fallback：舊目錄（目前是空的，保留是為了有人日後改回檔案制）
    lesson_dir = ROOT / "wiki" / "memory" / "lessons"
    if not lesson_dir.is_dir():
        return out
    for f in sorted(lesson_dir.glob("L*.md")):
        m = re.match(r"^(L\d+)_", f.name)
        if m:
            out.append(m.group(1))
    return out


def list_fitness_steps() -> list[str]:
    """從 scripts/checks/ 抓 *.py 對應 fitness step
    粗算：以 _audit.py / _check.py / _guard.py 結尾
    """
    out = []
    checks_dir = ROOT / "scripts" / "checks"
    if not checks_dir.is_dir():
        return out
    for f in sorted(checks_dir.glob("*.py")):
        n = f.name
        if n.endswith("_audit.py") or n.endswith("_check.py") or n.endswith("_guard.py"):
            out.append(n)
    return out


def list_sop_rules() -> list[str]:
    """.claude/rules/*.md SOP 規範清單"""
    out = []
    rules_dir = ROOT / ".claude" / "rules"
    if not rules_dir.is_dir():
        return out
    for f in sorted(rules_dir.glob("*.md")):
        out.append(f.name)
    return out


def check_facade_b_alignment() -> list[str]:
    """ADR-0036 B 方案：10 facade .py 應已不存在"""
    drift = []
    facades_dir = ROOT / "backend" / "app" / "services" / "contracts" / "facades"
    expected_zero = ["agency.py", "ai.py", "audit.py", "calendar.py",
                     "contract.py", "document.py", "erp.py",
                     "notification.py", "tender.py", "vendor.py"]
    for f in expected_zero:
        if (facades_dir / f).exists():
            drift.append(f"  ⚠ ADR-0036 B 方案應廢但 facades/{f} 仍存在")
    return drift


def check_lesson_id_continuity(lessons: list[str]) -> list[str]:
    """lesson 編號連續性 — 若有缺號可能漂移"""
    out = []
    if not lessons:
        return out
    nums = sorted(int(re.sub(r"\D", "", L)) for L in lessons)
    expected = set(range(nums[0], nums[-1] + 1))
    actual = set(nums)
    missing = expected - actual
    if missing:
        recent_missing = sorted(n for n in missing if n >= 40)
        if recent_missing:
            # 為每個 missing 編號查 MEMORY.md 引用 — 若有引用則是 stale link
            mem_path = Path.home() / ".claude/projects/D--CKProject-CK-Missive/memory/MEMORY.md"
            stale_refs = []
            if mem_path.exists():
                try:
                    mem_text = mem_path.read_text(encoding="utf-8", errors="ignore")
                    for n in recent_missing:
                        # L4X 引用樣式：lesson_l43_ / L43_ / [L43]
                        if re.search(rf"(lesson_l{n}_|L{n}_|\[L{n}\])", mem_text, re.IGNORECASE):
                            stale_refs.append(n)
                except Exception:
                    pass
            out.append(f"  ⚠ Lesson 編號缺號 (≥L40): {recent_missing}")
            if stale_refs:
                out.append(f"    └ 其中 {stale_refs} 在 MEMORY.md 有引用 → stale reference 漂移")
            else:
                out.append(f"    └ MEMORY.md 無引用 → 家族隱含 (L4x family / 合併歸檔可)")
    return out


def check_wiki_lessons_link(metrics: dict) -> list[str]:
    """`governance_lessons_total` 的名字說 lessons，量到的其實是 failures。

    2026-08-27 修。原本的比對是：

        metric(governance_lessons_total) vs list_lessons() + failures/

    而 `list_lessons()` 讀的是空目錄（恆 0），metric 的實作
    （`memory_wiki_metrics.py:418`）合算 `lessons/` + `failures/` 也等於只有 failures
    ⇒ **兩邊都在數同一批 18 個 failures 檔，恆等，這個比對永遠不會報。**

    這裡改成分開對，讓「名字」與「量的東西」的落差看得見：

      1. metric 對得上 failures/ 檔數嗎（它實際在量的東西）
      2. LESSONS_REGISTRY 讀得到條目嗎（讀 0 = 又讀錯地方了，是哨兵不是統計）
    """
    out = []
    metric_count = metrics.get("governance_lessons_total", 0)

    failures_dir = ROOT / "wiki" / "memory" / "failures"
    failures = len(list(failures_dir.glob("*.md"))) if failures_dir.is_dir() else 0
    if metric_count > 0 and abs(metric_count - failures) > 2:
        out.append(
            f"  ⚠ governance_lessons_total={metric_count:.0f} vs wiki/memory/failures/={failures}"
            f" (drift > 2)"
        )

    registry_count = len(list_lessons())
    if registry_count == 0:
        # 這一項刻意是哨兵：registry 有 80+ 條，讀到 0 只有一種可能 —— 讀錯地方。
        out.append(
            "  ⚠ LESSONS_REGISTRY.md 讀到 0 條 —— 這不是「沒有 lesson」，是解析或路徑壞了"
        )
    return out


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== 規範 vs 現況 對應檢核 (step 63 / governance alignment) ===")
    print()

    metrics = fetch_metrics()
    print("┌─ 真活 metric ─┐")
    for k in ("governance_lessons_total", "governance_lessons_l4x_family_count",
              "governance_wiki_pages_total", "governance_wiki_freshness_hours",
              "governance_pipeline_red_consecutive_days",
              "governance_fitness_report_freshness_hours",
              "kg_entities_total"):
        v = metrics.get(k)
        if v is not None:
            print(f"  {k:50} {v:>10}")
    print()

    adrs = list_adrs()
    lessons = list_lessons()
    fitness = list_fitness_steps()
    sops = list_sop_rules()

    active_adr = sum(1 for _, s in adrs if s in ("accepted", "proposed", "proposal"))
    print(f"┌─ 規範清單盤點 ─┐")
    print(f"  ADRs:                   total={len(adrs):>3}  active={active_adr}")
    print(f"  Lessons (LESSONS_REGISTRY): {len(lessons):>3}")
    print(f"  SOPs (.claude/rules):   {len(sops):>3}")
    # 2026-08-27：標明數法。這裡只數檔名以 _audit/_check/_guard 結尾的（126），
    # 而 scripts/checks/ 頂層實際有 178 支 —— 兩個數字都不是錯的，
    # 但不標數法的話，跟 README 的 178 擺在一起會被當成漂移。
    print(f"  Fitness scripts (*_audit/_check/_guard): {len(fitness):>3}")
    print()

    print(f"┌─ 漂移檢測 ─┐")
    issues: list[str] = []

    # 1. Facade B 方案對齊
    issues.extend(check_facade_b_alignment())

    # 2. Lesson 編號連續性
    issues.extend(check_lesson_id_continuity(lessons))

    # 3. wiki lessons metric vs file
    issues.extend(check_wiki_lessons_link(metrics))

    # 4. KG / wiki 平衡
    kg_total = metrics.get("kg_entities_total", 0)
    wiki_total = metrics.get("governance_wiki_pages_total", 0)
    if kg_total > 0 and wiki_total > 0:
        ratio = wiki_total / kg_total
        if ratio < 0.005:  # < 0.5% wiki vs KG
            issues.append(f"  ⚠ Wiki/KG 比例極低 ({ratio*100:.2f}%) — 知識可能未轉 wiki narrative")

    # 5. 元覆盤新鮮度
    fitness_age_hours = metrics.get("governance_fitness_report_freshness_hours", 999)
    if fitness_age_hours > 48:
        issues.append(f"  ⚠ Pipeline report 距今 {fitness_age_hours:.0f}h > 48h 門檻")

    if not issues:
        print("  ✓ 規範 vs 現況 對應完整，無漂移")
    else:
        for i in issues:
            print(i)
    print()

    # 2026-08-27：原本這裡印五行「進化執行成效」，而那五行是 2026-05-30 寫死的字串
    # （"本日新增 lesson: L52 + L53"、"Fitness 51→63 step"…），三個月來每天印同一句。
    # 固定文字不是成效，它只是讓輸出看起來很豐富 —— 而讀的人會以為那是今天量到的。
    # 改成只印真的算得出來的東西；算不出來的就不要印。
    print(f"┌─ 本次實際量到 ─┐")
    print(f"  Lessons (registry) : {len(lessons)}")
    print(f"  ADRs (active/total): {active_adr}/{len(adrs)}")
    print(f"  SOPs (.claude/rules): {len(sops)}")
    print(f"  Fitness scripts    : {len(fitness)} （只數 *_audit/_check/_guard；頂層總數見 scripts/checks/README.md）")
    live_gauges = [k for k in metrics if k.startswith("governance_")]
    print(f"  governance_* gauge : {len(live_gauges)} 個 expose 中")
    print()

    if issues and strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
