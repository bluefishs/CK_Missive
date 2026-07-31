# -*- coding: utf-8 -*-
"""Regression — 審計腳本自身的可執行性（2026-08-01）

立法背景：2026-08-01 全系統覆盤時發現 **3 支既有審計在 host 上根本跑不起來**，
而且已經失效一段時間、沒有任何人知道：

| 腳本 | 失效原因 |
|---|---|
| `service_dir_entropy.py` | 印 ✗ 時 `UnicodeEncodeError: cp950` → 整支炸掉 |
| `dead_ui_detector.py` | 印 📡 時同上 |
| `capability_usage_audit.py` | 容器名寫死 `ck_missive_postgres_dev`（已不存在）+ ADR grep 慢到跑不完 |

這正是「機制存在 ≠ 機制有用」——治理腳本本身也需要被治理。
（對照 L49.8：PowerShell 腳本缺 BOM 於 cp950 host 解析失敗，同一家族。）

本測試守住三件事，皆為**靜態檢查**（不實際執行審計，避免測試變慢/依賴 DB）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / "scripts" / "checks"

# 會輸出非 ASCII（中文/emoji）的審計腳本 —— 必須有 cp950 韌性
NON_ASCII_OUTPUT_SCRIPTS = [
    "service_dir_entropy.py",
    "dead_ui_detector.py",
    "capability_usage_audit.py",
    "producer_output_watchdog.py",
    "heterogeneous_work_audit.py",
    "navigation_live_integrity_audit.py",
    "ui_smoke_freshness.py",
    "contract_case_code_coverage_audit.py",
]


def _read(name: str) -> str:
    p = CHECKS / name
    if not p.exists():
        pytest.skip(f"{name} 不存在（可能已重構）")
    return p.read_text(encoding="utf-8", errors="ignore")


class TestCp950Resilience:
    """L49.8 家族：cp950 host 上輸出中文/emoji 不得讓審計整支掛掉"""

    @pytest.mark.parametrize("name", NON_ASCII_OUTPUT_SCRIPTS)
    def test_has_stdout_reconfigure_guard(self, name):
        src = _read(name)
        assert "stdout.reconfigure" in src, (
            f"{name} 會輸出非 ASCII 但缺 cp950 韌性 —— "
            "在 Windows host 上會 UnicodeEncodeError 整支炸掉，"
            "而且是靜默失效（沒人會發現審計沒在跑）"
        )


class TestNoStaleContainerNames:
    """容器名寫死 → 容器改名後審計靜默失效"""

    KNOWN_STALE = ["ck_missive_postgres_dev", "ck-missive-backend", "ck_missive_backend_dev"]

    @pytest.mark.parametrize("name", NON_ASCII_OUTPUT_SCRIPTS)
    def test_no_known_stale_container_reference(self, name):
        src = _read(name)
        # 去註解再比對（說明文字裡提到舊名是合理的）
        code = re.sub(r'"""[\s\S]*?"""', "", src)
        code = re.sub(r"(?m)^\s*#.*$", "", code)
        for stale in self.KNOWN_STALE:
            assert stale not in code, (
                f"{name} 引用了已不存在的容器 {stale} → 審計會靜默失敗"
            )


class TestSlowPathHasEscape:
    """已知慢路徑必須有快速模式，否則「跑不完」等於「沒在跑」"""

    def test_capability_audit_defaults_quick_on_windows(self):
        src = _read("capability_usage_audit.py")
        assert "sys.platform.startswith(\"win\")" in src, (
            "capability_usage_audit 的 ADR 反向 grep 在 Windows 上實測 240s 未完 → "
            "Windows 需預設 quick，否則此審計實質失效"
        )
        assert '"--full"' in src, "需保留 --full 供完整分析"


class TestMentionCoverageCategorisation:
    """驗鑑別力後的判準修正（SELF_AUDIT_EVOLUTION_STANDARD §3）"""

    def test_code_domain_exempt_from_mention_deadness(self):
        """code/* 實體來自 AST 匯入，本來就不會有文件 mention，不得算 dead

        實測：tender/knowledge 類命中率 100%（工具有鑑別力），code/* 全 0%
        —— 是判準套錯類別，不是工具壞掉。修判準而非棄工具。
        """
        src = _read("capability_usage_audit.py")
        assert "MENTION_EXEMPT_DOMAINS" in src
        assert 'startswith(MENTION_EXEMPT_DOMAINS)' in src
