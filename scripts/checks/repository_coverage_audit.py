"""Fitness step 70 (v6.12, 2026-05-31): Repository:db_table 覆蓋率 audit

對齊 KG_ARCHITECTURE_HOLISTIC_REVIEW_20260531.md 建議 #1:
repository 18 vs db_table 63 = 1:3.5 覆蓋不足，應 1:1.5 內

偵測:
- 每個 db_table 是否有對應 repository
- 沒對應的 db_table 列出供補 (P0 優先)
- 計算覆蓋率比例

設計: 從 backend/app/extended/models/ + backend/app/repositories/ 靜態分析
不依賴 backend running
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Windows cp950 防護（L49.8 家族；v6.18 8-audit 硬化漏掉本圖譜 audit，2026-06-12 補）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


ROOT = Path(__file__).resolve().parents[2]


def list_db_tables_from_models() -> set[str]:
    """從 backend/app/extended/models/*.py 抓 __tablename__"""
    tables = set()
    models_dir = ROOT / "backend" / "app" / "extended" / "models"
    if not models_dir.is_dir():
        return tables
    for f in models_dir.rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'__tablename__\s*=\s*["\']([^"\']+)["\']', text):
            tables.add(m.group(1))
    return tables


def list_repositories() -> set[str]:
    """從 backend/app/repositories/ 抓 *_repository.py module name"""
    repos = set()
    repo_dir = ROOT / "backend" / "app" / "repositories"
    if not repo_dir.is_dir():
        return repos
    for f in repo_dir.rglob("*_repository.py"):
        if "__pycache__" in f.parts or f.name == "base_repository.py":
            continue
        name = f.stem.replace("_repository", "")
        repos.add(name)
    return repos


def list_repo_to_tables() -> dict[str, set[str]]:
    """v6.12 A+C 升級 (2026-05-31): 讀 repository file content 抓對應 table

    smart match 策略：
    1. 抓 from app.extended.models import XxxModel
    2. 抓 self.model = XxxModel
    3. 對應 Model class 找 __tablename__ → set of tables
    4. 也 fallback filename match (向後相容)
    """
    repo_dir = ROOT / "backend" / "app" / "repositories"
    models_dir = ROOT / "backend" / "app" / "extended" / "models"
    if not repo_dir.is_dir() or not models_dir.is_dir():
        return {}

    # 先建 model_class → table_name 映射
    model_to_table: dict[str, str] = {}
    for f in models_dir.rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # 抓 class Foo(Base): / __tablename__
        # 簡化: 抓 class Foo + 同 file 內 __tablename__
        classes = re.findall(r"^class\s+(\w+)\s*\(", text, re.MULTILINE)
        tablenames = re.findall(r'__tablename__\s*=\s*["\']([^"\']+)["\']', text)
        # 配對 (簡化: 假設順序對齊)
        for cls, tbl in zip(classes, tablenames):
            model_to_table[cls] = tbl

    # 對每個 repository 抓 import 的 model
    repo_to_tables: dict[str, set[str]] = {}
    for f in repo_dir.rglob("*_repository.py"):
        if "__pycache__" in f.parts or f.name == "base_repository.py":
            continue
        repo_name = f.stem.replace("_repository", "")
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        tables = set()
        # 抓 from .models import XxxModel / from app.extended.models import XxxModel
        for m in re.finditer(r"from\s+[\w\.]+models[\w\.]*\s+import\s+([^\n]+)", text):
            imports = m.group(1)
            for cls in re.findall(r"\b([A-Z]\w+)\b", imports):
                if cls in model_to_table:
                    tables.add(model_to_table[cls])
        # 抓 self.model = XxxModel
        for m in re.finditer(r"self\.model\s*=\s*(\w+)", text):
            cls = m.group(1)
            if cls in model_to_table:
                tables.add(model_to_table[cls])

        # Fallback: filename → table (向後相容)
        if not tables:
            # 試 plural variations
            for variant in (repo_name + "s", repo_name, repo_name.replace("_", "")):
                tables.add(variant)

        repo_to_tables[repo_name] = tables
    return repo_to_tables


def classify_table(table: str, repos: set[str], repo_to_tables: dict[str, set[str]]) -> str:
    """v6.12 升級: smart match — repo_to_tables 內找到即 covered"""
    # 智能匹配: repo file content import 對應 model
    for repo, tables in repo_to_tables.items():
        if table in tables:
            return "covered"
    # Fallback: filename
    singular = table.rstrip("s") if table.endswith("s") else table
    for c in [table, singular, table.replace("_", "")]:
        if c in repos:
            return "covered"
    return "missing"


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== Repository:db_table 覆蓋率 audit (step 70 / KG 建議 #1) ===")
    print()

    tables = list_db_tables_from_models()
    repos = list_repositories()
    repo_to_tables = list_repo_to_tables()  # v6.12 A 升級
    print(f"db_table count (from models __tablename__): {len(tables)}")
    print(f"repository count (from *_repository.py):    {len(repos)}")
    print(f"目標覆蓋率: 1:1.5 內 (即 repo ≥ table * 0.67)")
    print()

    covered = []
    missing = []
    for t in sorted(tables):
        if classify_table(t, repos, repo_to_tables) == "covered":
            covered.append(t)
        else:
            missing.append(t)

    coverage_pct = (len(covered) / len(tables) * 100) if tables else 0
    ratio = (len(repos) / len(tables)) if tables else 0
    print(f"覆蓋率: {len(covered)}/{len(tables)} ({coverage_pct:.0f}%)")
    print(f"比例:   1:{len(tables)/len(repos):.1f} (repository:db_table)")
    print()

    if missing:
        print(f"🟡 {len(missing)} db_table 無對應 repository (建議優先補):")
        # 列頭 10 個高頻補完目標
        for t in missing[:15]:
            print(f"    - {t}")
        if len(missing) > 15:
            print(f"    ... 還有 {len(missing) - 15} 個")
    else:
        print("✅ 所有 db_table 有對應 repository")
    print()

    # 等級判定
    if coverage_pct >= 80:
        verdict = "🟢 GREEN (≥80%)"
    elif coverage_pct >= 60:
        verdict = "🟡 YELLOW (60-80%)"
    else:
        verdict = "🔴 RED (<60%)"
    print(f"Verdict: {verdict}")
    print()
    print("修法建議 (對齊 KG_ARCHITECTURE_HOLISTIC_REVIEW §5 #1):")
    print("- 目標 1:1.5 (每 repo ≤ 2 table)")
    print("- 優先補高頻 table 對應 repository")
    print("- 對齊 v6.10 P1 Phase B (Bounded Context Contract Layer)")

    if coverage_pct < 60 and strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
