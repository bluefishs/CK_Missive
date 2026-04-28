#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notify Consumers — CROSS_REPO_REFERENCE_GUIDE v6.0 通知 detector

落實 §4.3 v2 規劃：pull-based 通知機制。
讀 docs/architecture/consumers.yml，對每 consumer 的 adopted_assets：
  1. FQID → source 檔案路徑映射（如 CK_Missive#run_fitness_v3.0 → scripts/checks/run_fitness.sh）
  2. git log 查該檔案最近 N 天 commit
  3. 對比 consumer 採用日期/版本
  4. 若 source 有更新 → 報「該 consumer 該升級」清單

Owner 月度跑此 detector，根據結果通知各 consumer（手動或未來自動發 issue）。

Usage:
    python scripts/checks/notify_consumers.py
    python scripts/checks/notify_consumers.py --days 30
    python scripts/checks/notify_consumers.py --consumer hermes-agent
    python scripts/checks/notify_consumers.py --ci  # 有 outdated → exit 1

Exit codes:
    0 — 所有 consumer 都同步最新
    1 — 有 outdated consumer（warning 模式仍 0；--ci 才 1）
    2 — consumers.yml 解析失敗

Version: 1.0.0 (2026-04-28)
Refs: L20, L22 (CROSS_REPO_REFERENCE_GUIDE_v1.0 §4.3)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONSUMERS_FILE = Path("docs/architecture/consumers.yml")

# FQID → 預期檔案路徑映射（部分通用範本）
# 對於非通用 FQID，依靠 consumer_version 字串對比
FQID_PATH_MAP = {
    # Tools / Scripts
    "CK_Missive#run_fitness_v3.0": "scripts/checks/run_fitness.sh",
    "CK_Missive#service_dir_entropy_v1.0": "scripts/checks/service_dir_entropy.py",
    "CK_Missive#config_dead_reader_scan_v3.0": "scripts/checks/config_dead_reader_scan.py",
    "CK_Missive#async_session_race_guard_v1.0": "scripts/checks/async_session_race_guard.py",
    "CK_Missive#sse_headers_guard_v1.0": "scripts/checks/sse_headers_guard.py",
    "CK_Missive#schema_lazy_load_guard_v1.0": "scripts/checks/schema_lazy_load_guard.py",
    "CK_Missive#agent_evolution_health_v1.0": "scripts/checks/agent_evolution_health.py",
    "CK_Missive#lessons_drift_check_v1.0": "scripts/checks/lessons_drift_check.py",
    "CK_Missive#dead_ui_detector_v1.0": "scripts/checks/dead_ui_detector.py",
    "CK_Missive#install-template-to_v1.0": "scripts/install-template-to.sh",
    # Docs
    "CK_Missive#STANDARD_REFERENCE_v1.0": "docs/architecture/STANDARD_REFERENCE.md",
    "CK_Missive#TEMPLATE_EXTRACTION_v1.0": "docs/architecture/TEMPLATE_EXTRACTION.md",
    "CK_Missive#WAVE_1_PLAYBOOK_v2.2": "docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md",
    "CK_Missive#WAVE_1_RETROSPECTIVE_v1.0": "docs/architecture/WAVE_1_RETROSPECTIVE.md",
    "CK_Missive#WAVE_2_TO_7_RETROSPECTIVE_v1.0": "docs/architecture/WAVE_2_TO_7_RETROSPECTIVE.md",
    "CK_Missive#WAVE_2_PLAN_v1.0": "docs/architecture/WAVE_2_PLAN.md",
    "CK_Missive#SERVICE_CONTEXT_MAP_v1.0": "docs/architecture/SERVICE_CONTEXT_MAP.md",
    "CK_Missive#LESSONS_REGISTRY_v1.0": "docs/architecture/LESSONS_REGISTRY.md",
    "CK_Missive#CROSS_REPO_REFERENCE_GUIDE_v1.0": "docs/architecture/CROSS_REPO_REFERENCE_GUIDE.md",
    # Backend templates
    "CK_Missive#timeouts_v1.0": "backend/app/core/timeouts.py",
    "CK_Missive#prometheus_middleware_v1.0": "backend/app/core/prometheus_middleware.py",
    # ADR
    "CK_Missive#0028": "docs/adr/0028-error-contract-silent-failure-policy.md",
    "CK_Missive#0029": "docs/adr/0029-adr-lifecycle-policy.md",
    "CK_Missive#0030": "docs/adr/0030-hermes-go-no-go-revision.md",
}


def parse_consumers_yml() -> dict | None:
    """簡易 yml parser（避免依賴 pyyaml — 可能 consumer 環境沒裝）"""
    if not CONSUMERS_FILE.exists():
        print(f"❌ {CONSUMERS_FILE} not found", file=sys.stderr)
        return None
    try:
        import yaml
        return yaml.safe_load(CONSUMERS_FILE.read_text(encoding="utf-8"))
    except ImportError:
        print(f"❌ pyyaml not installed: pip install pyyaml", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ yml parse failed: {e}", file=sys.stderr)
        return None


def get_file_last_commit(path: str, days: int) -> tuple[str, datetime] | None:
    """git log 該檔最近一次 commit（hash, date）— None 若 N 天內無更新"""
    try:
        out = subprocess.check_output(
            ["git", "log", f"--since={days} days ago", "--format=%h|%cI",
             "--max-count=1", "--", path],
            text=True, encoding="utf-8",
        ).strip()
        if not out:
            return None
        sha, iso = out.split("|", 1)
        return sha, datetime.fromisoformat(iso)
    except subprocess.CalledProcessError:
        return None


def get_file_commit_count(path: str, days: int) -> int:
    """git log 該檔最近 N 天 commit 數"""
    try:
        out = subprocess.check_output(
            ["git", "log", f"--since={days} days ago", "--oneline", "--", path],
            text=True, encoding="utf-8",
        )
        return sum(1 for ln in out.splitlines() if ln.strip())
    except subprocess.CalledProcessError:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--days", type=int, default=30,
                        help="掃過去 N 天 source 更新（預設 30）")
    parser.add_argument("--consumer", type=str, default=None,
                        help="只看特定 consumer（如 hermes-agent）")
    parser.add_argument("--ci", action="store_true", help="有 outdated 即 exit 1")
    args = parser.parse_args()

    print(f"=== Notify Consumers (source updates in last {args.days} days) ===\n")

    data = parse_consumers_yml()
    if data is None:
        return 2

    consumers = data.get("consumers", [])
    if args.consumer:
        consumers = [c for c in consumers if c.get("id") == args.consumer]

    print(f"📋 Consumers checked: {len(consumers)}\n")

    total_outdated = 0

    for consumer in consumers:
        cid = consumer.get("id", "?")
        status = consumer.get("status", "?")
        print(f"━━━ {cid} (status: {status}) ━━━")
        adopted = consumer.get("adopted_assets", []) or []
        pending = consumer.get("pending_review", []) or []

        if not adopted and not pending:
            print("  (no assets adopted or pending)\n")
            continue

        # 已採用：檢查 source 是否有更新
        outdated_for_consumer = []
        for asset in adopted:
            fqid = asset.get("fqid", "")
            cv = asset.get("consumer_version", "?")
            path = FQID_PATH_MAP.get(fqid)
            if not path:
                print(f"  ⚠️  {fqid:50} (no path mapping)")
                continue
            recent = get_file_last_commit(path, args.days)
            if recent:
                sha, dt = recent
                age = (datetime.now(timezone.utc) - dt).days
                count = get_file_commit_count(path, args.days)
                print(f"  🔄 {fqid:50} consumer={cv} → source 更新 {count} 次 (last {age}d ago, {sha})")
                outdated_for_consumer.append(fqid)
            else:
                print(f"  ✅ {fqid:50} consumer={cv} (source 未更新)")

        # 待採用：列出 source 是否近期有變化（值得評估）
        if pending:
            print(f"  待 review ({len(pending)}):")
            for fqid in pending:
                path = FQID_PATH_MAP.get(fqid)
                if not path:
                    print(f"    📌 {fqid} (no path mapping)")
                    continue
                recent = get_file_last_commit(path, args.days)
                marker = "🆕" if recent else "📌"
                print(f"    {marker} {fqid}")

        if outdated_for_consumer:
            total_outdated += len(outdated_for_consumer)
            print(f"  → 該升級：{len(outdated_for_consumer)} 個 asset")
        print()

    # === Summary ===
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if total_outdated == 0:
        print(f"🎉 所有 consumer 都同步最新（last {args.days} days）")
        return 0
    print(f"⚠️  總計 {total_outdated} 個 (consumer, asset) 該升級")
    print(f"建議行動：")
    print(f"  1. owner 通知對應 consumer 跑 install-template-to.sh 升級")
    print(f"  2. 或更新 consumers.yml 的 consumer_version 反映實際採用版本")
    print(f"  3. 月度健檢若連 3 月未升 → 開 issue 提醒")

    if args.ci:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
