#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: SOUL.md 跨 repo 同步漂移偵測

CONSCIOUSNESS_INTEGRATION_ANALYSIS.md 額外發現的整合斷鏈：
- wiki/SOUL.md (Missive 為 SSOT) vs CK_AaaP/runbooks/hermes-stack/SOUL.md (Hermes 用)
- soul_loader.py docstring 聲稱「同步鏡像」但**無實作** — docstring lie
- 結果：Web UI 用戶（Missive 8KB SOUL）vs Telegram/LINE 用戶（Hermes 5KB SOUL）
  看到的是不同人格的「坤哥」

⚠️ 2026-08-02 重要修正：上面那段前提（2026-04-25 寫的）**已經不成立**，理由有二。

1. **架構定調改了**：ADR-CK-003 意識體聯邦（2026-06-03）明確區分
   「坤哥＝Missive 平臺的意識體」與「meta profile＝AaaP 的整體大腦」。
   兩者是**不同的意識體**，不是同一個人格的兩份鏡像 —— 內容不同是設計，不是 drift。
2. **比對對象是不生效的檔案**：Hermes `active_profile=meta`，真正載入的是
   `/opt/data/profiles/meta/SOUL.md`（8806 bytes）；本檢查比對的
   `runbooks/hermes-stack/SOUL.md` 對應的是 root `/opt/data/SOUL.md`（5621 bytes，**不生效**）。
   這正是 2026-06-02 記載過的「一直在改錯檔」。

因此本檢查**不再建議跑同步腳本**：那會 (a) 寫到不生效的檔案，
(b) 若有人照著同步到 meta，會覆蓋掉 6/16 加入的業務查詢強制規則（baseline GO 的關鍵）。
另有實證支持不要動：6/16 實測 SOUL 強化（D-α/D-β）為**負向**——qwen 仍捏造且觸發
慢檢索 113-280s，已還原並立法「瓶頸在模型強度不在 prompt，勿再投 prompt 層」。

保留本檢查的理由：仍可看出 Hermes 端部署包的人格檔是否整個空掉/損毀。
判定改以「Hermes 端還有沒有可用人格」為準，而非「是否與 Missive 一致」。

用法：
    python scripts/checks/soul_mirror_drift_check.py
    python scripts/checks/soul_mirror_drift_check.py --ci   # drift 即 exit 1

Version: 1.0.0 (2026-04-25)
關聯:
- docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §4 整合斷鏈
- backend/app/services/memory/soul_loader.py docstring 待誠實化
- 修復：scripts/sync/sync_soul_to_hermes.sh（手動同步）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

MISSIVE_SOUL = Path("wiki/SOUL.md")
HERMES_SOUL = Path("../CK_AaaP/runbooks/hermes-stack/SOUL.md")


def load(p: Path) -> str | None:
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


# 跨層該一致的「核心人格不變量」— 兩層 persona 角色可不同，但這些底線必須一致。
# 對齊本檔 §SEVERE 判定（line 97 同款關鍵字）+ CONSCIOUSNESS_INTEGRATION_ANALYSIS §10.4。
CORE_INVARIANTS = ["身份", "三信念", "倫理紅線", "反迴聲"]


def core_invariant_gap(m_secs: list[str], h_secs: list[str]) -> list[str]:
    """回傳 Missive(SSOT) 有、但 Hermes 缺的核心不變量關鍵字清單（跨層該一致卻不一致）。"""
    missing = []
    for kw in CORE_INVARIANTS:
        in_m = any(kw in s for s in m_secs)
        in_h = any(kw in s for s in h_secs)
        if in_m and not in_h:
            missing.append(kw)
    return missing


def write_drift_snapshot(missive: str, hermes: str) -> None:
    """寫 wiki/memory/soul_drift_snapshot.json — 供 in-container v7_soul_drift metric 讀。

    L73 根因鏈（2026-06-12 覆盤）：metric 註解稱「讀 host 端 fitness 寫的 snapshot」，
    但唯一寫 snapshot 的是 in-container autobiography job，容器看不到 ../CK_AaaP →
    drift=-1 sentinel，永遠回不了真值。本腳本（host 端 fitness step 3，看得到兩個
    SOUL.md）才有資格寫真值。

    指標語意（2026-06-12 owner 確認重定義，CONSCIOUSNESS §10.5）：
    `drift_lines` 不再是「整檔行數差」（兩層 persona 設計上本就不同 → 量錯東西），
    改為 **核心不變量跨層缺口 = core_invariant_gap**（Missive 有、Hermes 缺的核心段數），
    target 0。line_delta 仍保留供參考。
    """
    import json
    from datetime import datetime
    m_lines, h_lines = len(missive.splitlines()), len(hermes.splitlines())
    missing = core_invariant_gap(extract_sections(missive), extract_sections(hermes))
    gap = len(missing)
    snap = Path("wiki/memory/soul_drift_snapshot.json")
    try:
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(json.dumps({
            "missive_lines": m_lines,
            "hermes_lines": h_lines,
            "line_delta": abs(m_lines - h_lines),
            "core_invariant_gap": gap,
            "missing_invariants": missing,
            "drift_lines": gap,  # metric 讀此欄 = core_invariant_gap（語意重定義，名稱保留免破壞 dashboard/alert）
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "soul_mirror_drift_check",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        tag = f"缺 {missing}" if missing else "核心不變量全跨層一致 ✅"
        print(f"📸 snapshot 已更新: core_invariant_gap={gap}（{tag}）line_delta={abs(m_lines - h_lines)}\n")
    except Exception as e:
        print(f"⚠️  snapshot 寫入失敗: {e}\n")


def extract_sections(content: str) -> list[str]:
    """提 ## 標題 list（順序保留）"""
    return re.findall(r"^##\s+(.+)$", content, re.M)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ci", action="store_true", help="drift 時 exit 1")
    args = parser.parse_args()

    print("=== SOUL.md Mirror Drift Check ===\n")

    missive = load(MISSIVE_SOUL)
    hermes = load(HERMES_SOUL)

    if missive is None:
        print(f"✗ {MISSIVE_SOUL} 不存在")
        return 2
    if hermes is None:
        print(f"⚠️  {HERMES_SOUL} 不存在（CK_AaaP 可能未 clone）")
        return 0  # 不算 drift（缺 mirror target 是另一回事）

    print(f"Missive (SSOT): {MISSIVE_SOUL}  {len(missive):>6} chars")
    print(f"Hermes mirror:  {HERMES_SOUL}  {len(hermes):>6} chars")
    print(f"Size delta:     {len(missive) - len(hermes):+d} chars\n")

    # L73: host 端寫真值 snapshot 給 in-container metric 讀（含 0-drift 同步狀態）
    write_drift_snapshot(missive, hermes)

    if missive == hermes:
        print("✅ 完全同步")
        return 0

    # Section drift
    m_secs = extract_sections(missive)
    h_secs = extract_sections(hermes)
    missive_only = [s for s in m_secs if s not in h_secs]
    hermes_only = [s for s in h_secs if s not in m_secs]
    common_count = len(set(m_secs) & set(h_secs))

    print(f"📑 Section 對比：")
    print(f"   Missive sections: {len(m_secs)}")
    print(f"   Hermes sections:  {len(h_secs)}")
    print(f"   共同:             {common_count}")
    print()

    # 判定基準（2026-08-02 改）：不再以「與 Missive 一致」為準 —— 依 ADR-CK-003
    # 兩者是不同意識體，內容不同是設計。真正該警告的是 Hermes 端人格檔整個壞掉。
    HERMES_MIN_SECTIONS = 3
    severity = "🟢 ok（兩者為不同意識體，內容不同屬預期）"
    hermes_broken = len(h_secs) < HERMES_MIN_SECTIONS
    if hermes_broken:
        severity = "🔴 SEVERE — Hermes 端人格檔疑似空掉或損毀"

    if missive_only:
        print("ℹ️ Missive 獨有 sections（屬意識體差異，非 drift）：")
        for s in missive_only:
            print(f"   - {s}")

    if hermes_only:
        print(f"\n🟡 Hermes 獨有（少見，可能是 AaaP 端手動加的）：")
        for s in hermes_only:
            print(f"   - {s}")

    print(f"\n嚴重度: {severity}")

    if hermes_broken:
        print("\n📌 處理方式（Hermes 端人格檔疑似損毀時才需要）：")
        print("   1. 先確認 Hermes 實際載入哪一份：`docker exec ck-hermes-gateway cat /opt/data/active_profile`")
        print("   2. active_profile=meta 時，生效檔是 profiles/<profile>/SOUL.md，**不是 root SOUL.md**")
        print("   3. 這屬 CK_AaaP / CK_Hermes 的維運範圍，不要從 Missive 端覆蓋過去")
    else:
        print("\nℹ️ 兩份 SOUL 內容不同屬預期（ADR-CK-003：坤哥與 meta 是不同意識體）。")
        print("   **不要**跑 scripts/sync/sync_soul_to_hermes.sh —— 它寫到的是不生效的 root 檔，")
        print("   且若有人照著同步進 meta，會蓋掉 6/16 加的業務查詢強制規則。")

    if args.ci and hermes_broken:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
