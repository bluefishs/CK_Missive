#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 33 — React Query queryKey Drift Audit (L39)

防範 silent dead invalidate — invalidate 寫 key A，但 useQuery 用 key B，A≠B。

觸發事件：v6.10.1 (2026-05-20) 揭發
  - dispatch 158「公文 2 筆」chronic bug：5/18 第一次修 invalidate ['dispatch-orders']
    完全 silent dead — 真實 useQuery 用 queryKeys.taoyuanDispatch.orders() =
    ['taoyuan-dispatch-orders', ...]
  - 同型反模式 L39 + L29 (dict-key contract drift) + L28 (JSON-as-TEXT schema drift)
  - audit 揭發 12 個 silent dead invalidate（admin-users / adminUsers 等）

Detection 邏輯（按 first token prefix 比對）：
  1. 全 frontend/src/**/*.{ts,tsx} 抽 `invalidateQueries({ queryKey: ['xxx', ...] })` first token
  2. 抽 `useQuery({ queryKey: ['xxx', ...] })` first token
  3. queryConfig.ts 內定義的 SSOT prefix tokens
  4. invalidate first token NOT IN (useQuery tokens ∪ SSOT tokens) → silent dead

Exit codes:
  0 — current dead ≤ baseline
  1 — --ci strict mode 且 current > baseline (淨增加)

Usage:
  python scripts/checks/queryKey_drift_audit.py
  python scripts/checks/queryKey_drift_audit.py --ci
  python scripts/checks/queryKey_drift_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# v6.13 (2026-05-31) L52 family 第 8 案修法:
# container 內 /app/frontend/src 不 mount (host-side only 設計)
# 修法: 若不存在，graceful skip exit 0 (不算 fail)
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"
BASELINE_FILE = PROJECT_ROOT / "scripts" / "checks" / "queryKey_drift_baseline.json"

INVALIDATE_RE = re.compile(
    r"invalidateQueries\(\s*\{\s*queryKey:\s*\[\s*['\"]([\w\-]+)['\"]"
)
# v6.10.2 (2026-05-20) audit 自身修法：支援 useQuery<TypeParam>(...) 泛型格式
# 起因：5/20 揭發 mfa-status / profile / wiki-* 等 6 token 被誤標 dead，
#       實際對應 useQuery 用了 useQuery<MFAStatus>({...}) 泛型 — 原 regex 漏掃
USEQUERY_RE = re.compile(
    r"useQuery\s*(?:<[^>]+>)?\s*\(\s*\{\s*queryKey:\s*\[\s*['\"]([\w\-]+)['\"]"
)
SSOT_TOKEN_RE = re.compile(r"\[\s*['\"]([\w\-]+)['\"]")


def scan_frontend() -> Tuple[Dict[str, List[str]], Set[str], Set[str]]:
    """Returns (invalidate_tokens, useQuery_tokens, SSOT_tokens)."""
    inv_tokens: Dict[str, List[str]] = {}
    uq_tokens: Set[str] = set()

    if not FRONTEND_SRC.exists():
        # v6.13 (2026-05-31): container 內 frontend/src 未 mount 是設計 (host-side only)
        # 改 INFO 不算 fail，避免 fitness 假 ERROR
        print(f"[INFO] frontend/src not present (container env, host-side audit only): {FRONTEND_SRC}",
              file=sys.stderr)
        return inv_tokens, uq_tokens, set()

    for path in FRONTEND_SRC.rglob("*.ts"):
        if "node_modules" in str(path) or ".test." in path.name:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for tok in INVALIDATE_RE.findall(content):
            inv_tokens.setdefault(tok, []).append(rel)
        for tok in USEQUERY_RE.findall(content):
            uq_tokens.add(tok)

    for path in FRONTEND_SRC.rglob("*.tsx"):
        if "node_modules" in str(path) or ".test." in path.name:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for tok in INVALIDATE_RE.findall(content):
            inv_tokens.setdefault(tok, []).append(rel)
        for tok in USEQUERY_RE.findall(content):
            uq_tokens.add(tok)

    # SSOT — queryConfig.ts
    ssot_tokens: Set[str] = set()
    ssot_path = FRONTEND_SRC / "config" / "queryConfig.ts"
    if ssot_path.exists():
        try:
            qcontent = ssot_path.read_text(encoding="utf-8")
            ssot_tokens = set(SSOT_TOKEN_RE.findall(qcontent))
        except (OSError, UnicodeDecodeError):
            pass

    return inv_tokens, uq_tokens, ssot_tokens


def load_baseline() -> Dict:
    """Load baseline; first run → empty (default total=0)."""
    if not BASELINE_FILE.exists():
        return {"total_baseline": 0, "dead_tokens": []}
    try:
        with open(BASELINE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[WARN] baseline load failed: {exc}", file=sys.stderr)
        return {"total_baseline": 0, "dead_tokens": []}


# ---------------------------------------------------------------------------
# 第二種形態：queryKey 撞號（2026-08-20 新增）
#
# 上面那一段管的是「invalidate 的 key 沒有人在用」＝ key **漂移**。
# 這一段管的是相反的一面：**同一個 key、不同的資料源**。
#
# 觸發事件：`/contract-cases/194/staff/create`「同仁又變成代碼」。
#   `useContractCaseData`（承攬案件詳情）與 `ContractCaseStaffFormPage`
#   都用 `['contract-case-user-options']`，但一個打 `users/list`（admin-only）、
#   一個打 `users/assignable`。於是**誰先載入誰就決定了快取內容** ——
#   從詳情頁點進「新增承辦同仁」時，create 頁沿用的是詳情頁留下的結果，
#   改 create 頁那一支根本不會生效。而清單空掉時 AntD Select 會顯示原始
#   數字 id，看起來像資料壞了，其實是載入失敗。
#
# key 撞號本身不是錯（同一份資料本來就該共用快取），**源不一致才是**。
#
# 判準刻意收窄，否則沒有鑑別力（第一版用「首 token + 任何差異」報 30 個，
# 逐一看幾乎全是假陽性：mutation 的 invalidate 被算進來、
# `['tender','search']` 與 `['tender','detail']` 本來就該不同）：
#   1. 只看 useQuery，不看 mutation
#   2. queryKey 必須**全部是字面字串**（含變數的 key 天生就會分流，無可比性）
#   3. 資料源**交集為空**才算不一致（同檔的 mutation 會溢進比對範圍）
#
# 實測：現況 0；把 useContractCaseData 改回修法前的寫法即報 1；還原回 0。
# ---------------------------------------------------------------------------

_SRC_RE = re.compile(
    r"([A-Z][A-Z0-9_]*_ENDPOINTS\.[A-Za-z0-9_]+)|(\b[a-z][A-Za-z0-9]*Api\.[A-Za-z0-9_]+)"
)
_LITERAL_KEY_RE = re.compile(r"\[\s*(?:'[^']*'\s*,?\s*)+\]")


def scan_key_source_collisions():
    """找出「同一個全字面 queryKey，資料源交集為空」的組合。"""
    src_root = PROJECT_ROOT / "frontend" / "src"
    if not src_root.exists():
        return []
    uses = {}
    files = list(src_root.rglob("*.ts")) + list(src_root.rglob("*.tsx"))
    for f in files:
        if "__tests__" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r"useQuery\s*(?:<[^>]*>)?\s*\(\s*\{", text):
            blk = text[m.end(): m.end() + 1500]
            nxt = blk.find("useQuery(")
            if nxt > 0:
                blk = blk[:nxt]
            km = re.search(r"queryKey:\s*(\[[^\]]*\])", blk)
            if not km:
                continue
            raw = km.group(1).strip()
            if not _LITERAL_KEY_RE.fullmatch(raw):
                continue
            key = tuple(re.findall(r"'([^']*)'", raw))
            srcs = {a or b for a, b in _SRC_RE.findall(blk[km.end(): km.end() + 900])}
            srcs = {s for s in srcs if not s.startswith("messageApi.")}
            if not srcs:
                continue
            rel = str(f.relative_to(src_root)).replace("\\", "/")
            uses.setdefault(key, set()).add((rel, tuple(sorted(srcs))))
    out = []
    for key, entries in sorted(uses.items()):
        sets = [set(s) for _, s in entries]
        if len(sets) > 1 and not set.intersection(*sets):
            out.append((key, sorted(entries)))
    return out


# ---------------------------------------------------------------------------
# 第三種形態：queryKey 撞號、資料源相同，**但回傳形狀不同**（2026-08-27 新增）
#
# 觸發事件：owner 第三次回報 `/contract-cases/194/staff/create`「仍無法顯示人名，
# 目前為代號」。上面那一段（第二種形態）當時判 GREEN —— 而它是對的：
# 兩處 08-20 之後**確實都打 `USERS_ENDPOINTS.ASSIGNABLE`**，資料源交集不為空。
#
#   詳情頁 `useContractCaseData`   → 回 [{ id, name, email }]   ← 已 map 過
#   新增同仁頁 `ContractCaseStaffFormPage` → 回 response.items = User[]
#
# 共用同一個 cache key ⇒ 誰先載入誰就決定內容。使用者的動線正是
# 「詳情頁 → 新增承辦同仁」，於是 create 頁拿到 `{id,name,email}`，
# 而 `userDisplayName` 要的 `full_name`／`username` 在那個形狀裡都不存在
# ⇒ 退到 `#${id}` ⇒ 畫面上就是「代號」。
#
# **08-20 修的是「源不一致」，源對齊了，形狀沒有對齊 —— 症狀原封不動。**
# 而它只在那一條動線上出現（直接開 create 頁的網址是正常的），
# 所以走查與人工複驗都驗不出來，只有真實使用者會遇到。
#
# 判準必須是**形狀**，不是文字：
# 我第一版量「queryFn 文字不同」，6 個候選裡報 4 個，逐一核實後
# **有 4 個是假陽性** —— `['ai-management','health']` 之流兩處都是
# `queryFn: () => aiApi.checkHealth()`，完全相同，只是 staleTime／
# refetchInterval 不同而被我的擷取範圍掃進去。真問題只有 1 個。
#
# 所以這裡比對的是**物件字面的鍵集合**（`=> ({a,b,c})` 或 `return {a,b,c}`）：
#   · 兩邊都取得到鍵集合、且集合不同 → 報
#   · 任一邊取不到（例如 `return resp.data`、`() => aiApi.getX()`）→ 不報
#     （寧可漏，不要製造 4 個假陽性 —— 假紅的代價是訓練人忽略這支檢核）
#
# 實測：現況 0；把兩支承攬案件的 hook 改回修法前即報 2（人員＋協力廠商）；還原回 0。
# ---------------------------------------------------------------------------

_OBJ_LITERAL_RE = re.compile(r"(?:=>\s*\(\s*\{|return\s*\{)([^{}]{0,600})\}")
_OBJ_FIELD_RE = re.compile(r"(?:^|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:,]")


def _shape_of(block: str) -> frozenset:
    """從 queryFn 區塊抽出「回傳的物件字面有哪些鍵」。取不到就回空集合。"""
    best: frozenset = frozenset()
    for m in _OBJ_LITERAL_RE.finditer(block):
        fields = frozenset(_OBJ_FIELD_RE.findall(m.group(1)))
        if len(fields) > len(best):
            best = fields
    return best


def scan_key_shape_collisions():
    """同一個全字面 queryKey、資料源有交集，但回傳的物件鍵集合不同。"""
    src_root = PROJECT_ROOT / "frontend" / "src"
    if not src_root.exists():
        return []
    uses = {}
    files = list(src_root.rglob("*.ts")) + list(src_root.rglob("*.tsx"))
    for f in files:
        if "__tests__" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r"useQuery\s*(?:<[^>]*>)?\s*\(\s*\{", text):
            blk = text[m.end(): m.end() + 1500]
            nxt = blk.find("useQuery(")
            if nxt > 0:
                blk = blk[:nxt]
            km = re.search(r"queryKey:\s*(\[[^\]]*\])", blk)
            if not km:
                continue
            raw = km.group(1).strip()
            if not _LITERAL_KEY_RE.fullmatch(raw):
                continue
            key = tuple(re.findall(r"'([^']*)'", raw))
            fn = re.search(r"queryFn:\s*(.{0,1200})", blk, re.S)
            if not fn:
                continue
            shape = _shape_of(fn.group(1))
            if not shape:
                continue   # 取不到形狀就不下結論
            rel = str(f.relative_to(src_root)).replace("\\", "/")
            uses.setdefault(key, set()).add((rel, shape))
    out = []
    for key, entries in sorted(uses.items()):
        shapes = {sh for _, sh in entries}
        if len({p for p, _ in entries}) > 1 and len(shapes) > 1:
            out.append((key, sorted((p, tuple(sorted(sh))) for p, sh in entries)))
    return out


def report_shape_collisions(collisions) -> None:
    if not collisions:
        return
    print("-" * 60)
    print("KEY/SHAPE COLLISION ({}) - 同一個 queryKey 回傳不同形狀:".format(len(collisions)))
    print("-" * 60)
    for key, entries in collisions:
        print("  [X] {}".format(list(key)))
        for fpath, fields in entries:
            print("      <- {}  ->  {{{}}}".format(fpath, ", ".join(fields)))
    print()
    print("  為什麼是問題：資料源相同不代表快取內容相同。誰先載入誰就決定形狀，")
    print("  另一處拿到的欄位全部是 undefined —— 而那在畫面上長得像「資料壞了」。")
    print("  修法：抽成共用 hook（一個 queryFn、一種形狀），呈現形狀留在各自消費端。")
    print()


def report_collisions(collisions) -> None:
    """人可讀輸出。刻意說明「為什麼是問題」——只列清單的話，看的人會以為是命名風格。"""
    if not collisions:
        return
    print("-" * 60)
    print("KEY/SOURCE COLLISION ({}) - 同一個 queryKey 對到不同資料源:".format(len(collisions)))
    print("-" * 60)
    for key, entries in collisions:
        print("  [X] {}".format(list(key)))
        for fpath, calls in entries:
            print("      <- {}  ->  {}".format(fpath, ", ".join(calls)))
    print()
    print("  為什麼是問題：誰先載入誰就決定快取內容，改另一處不會生效。")
    print("  修法：把資料源統一（同一份清單就該同一支端點），不是改 key。")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fitness step 33 — React Query queryKey Drift Audit (L39)"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="baseline-aware strict: current dead > baseline 即 exit 1（修一個減一個，禁淨增）",
    )
    parser.add_argument("--json", action="store_true", help="JSON 輸出")
    args = parser.parse_args()

    inv_tokens, uq_tokens, ssot_tokens = scan_frontend()
    real_query_tokens = uq_tokens | ssot_tokens
    dead = sorted(set(inv_tokens.keys()) - real_query_tokens)
    current_total = len(dead)

    baseline = load_baseline()
    baseline_total = baseline.get("total_baseline", 0)
    collisions = scan_key_source_collisions()
    shape_collisions = scan_key_shape_collisions()

    if args.json:
        report = {
            "invalidate_tokens_total": len(inv_tokens),
            "useQuery_tokens_total": len(uq_tokens),
            "ssot_tokens_total": len(ssot_tokens),
            "current_dead_total": current_total,
            "baseline_total": baseline_total,
            "dead_tokens": [
                {"token": t, "callers": inv_tokens[t][:3]} for t in dead
            ],
            "key_source_collisions": [
                {"key": list(k), "sources": [{"file": f, "calls": list(c)} for f, c in v]}
                for k, v in collisions
            ],
            "key_shape_collisions": [
                {"key": list(k), "shapes": [{"file": f, "fields": list(sh)} for f, sh in v]}
                for k, v in shape_collisions
            ],
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if args.ci and (current_total > baseline_total or collisions or shape_collisions):
            return 1
        return 0

    # human format
    print("=" * 60)
    print("React Query queryKey Drift Audit (L39)")
    print(f"v6.10.1 / detect silent dead invalidate")
    print("=" * 60)
    print()
    print(f"  invalidate tokens: {len(inv_tokens)}")
    print(f"  useQuery tokens: {len(uq_tokens)}")
    print(f"  SSOT tokens: {len(ssot_tokens)}")
    print(f"  current dead invalidate: {current_total}")
    print(f"  baseline: {baseline_total}")
    print(f"  queryKey 撞號（同 key 不同源）: {len(collisions)}")
    print(f"  queryKey 撞號（同 key 同源、不同形狀）: {len(shape_collisions)}")
    print()
    report_collisions(collisions)
    report_shape_collisions(shape_collisions)

    if dead:
        print("-" * 60)
        print(f"SILENT DEAD invalidate tokens ({len(dead)}):")
        print("-" * 60)
        for tok in dead:
            callers = inv_tokens[tok][:3]
            print(f"  [X] [{tok}]")
            for c in callers:
                print(f"      <- {c}")
        print()
        print("Fix guidance:")
        print("  1. 找出 invalidate 想 invalidate 的真實 useQuery key")
        print("  2. 改 invalidate 用 queryKeys.<module>.<entity> SSOT")
        print("  3. 禁止散戶手寫 queryKey 字串陣列（如 ['xxx']）")
        print("  4. 修一個減一個，請更新 queryKey_drift_baseline.json")

    # CI enforce
    if args.ci:
        if collisions:
            print("\n[FAIL] queryKey 撞號 {} 組（同 key 不同源）".format(len(collisions)), file=sys.stderr)
            return 1
        if shape_collisions:
            print(
                "\n[FAIL] queryKey 撞號 {} 組（同 key 同源、**回傳形狀不同**）".format(
                    len(shape_collisions)),
                file=sys.stderr,
            )
            return 1
        if current_total > baseline_total:
            print(
                f"\n[FAIL] dead invalidate 淨增加: {baseline_total} → {current_total} "
                f"(+{current_total - baseline_total})",
                file=sys.stderr,
            )
            return 1
        elif current_total < baseline_total:
            print(
                f"\n[INFO] dead invalidate 改善: {baseline_total} → {current_total} "
                f"(-{baseline_total - current_total}) — 請更新 baseline 鎖定改善"
            )
        else:
            print(f"\n[PASS] dead invalidate 持平 baseline {baseline_total}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
