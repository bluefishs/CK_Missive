#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""自主測試機制圖（weekly 113，僅報告）——把散在各處的測試層盤成一張表：每層看得見什麼、看不見什麼、誰觸發、留痕在哪、
最近一次結果多新。產出 docs/health/TESTING_MAP.md 給人看，不判紅（判紅是各層自己的事；這支只回答「有沒有人在跑」）。

owner 2026-09-06：「把現在散在各處的自主測試層（push 閘門、每日 runner、頁面走查、併發、部署態、視覺、效能探針、
跨 repo 互驗）盤成一張完整的機制圖……再標出缺口與補法」。

層的定義寫在本檔（靜態）；新鮮度從各層的留痕檔動態讀（動態）。兩者分開：定義不會因為沒跑而消失，
沒跑會以「留痕過期」出現在表上——那正是這張表要照出來的東西。
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

ROOT = repo_root()  # 不自算路徑（weekly 93）：自算算錯是靜默的，會讀到別的檔
IH = ROOT / "wiki" / "memory" / "integration-health"
OUT = ROOT / "docs" / "health" / "TESTING_MAP.md"

# (層, 觸發者／頻率, 看得見, 看不見, 留痕檔或位置, 新鮮度上限小時 or None)
LAYERS = [
    ("提交閘門 pre-commit（husky）", "每次 git commit（本機）", "TS 編譯、ESLint、Python 語法、敏感檔、secret 前綴、skills 格式", "任何測試、任何行為；只驗「能不能編譯」", "終端輸出，不留檔", None),
    ("提交訊息 commit-msg", "每次 commit", "commitlint 格式", "—", "終端", None),
    ("post-commit 知識地圖", "每次 commit（背景）", "docs 變動 → 知識地圖重生", "—", "docs/knowledge-map/", None),
    ("推送閘門 pre-push（husky）", "每次 git push（09-06 起，A46 快速版）", "推送範圍相關的 pytest／vitest，對基線只擋新失敗", "改了但沒有對應測試檔的程式（會印「沒有相關測試」）；全套", "終端輸出", None),
    ("後端單元／整合測試 pytest", "weekly 24（host）；無 commit 閘門", "服務／repository／schema 的邏輯回歸；asyncpg 競態 lint；os.kill 陷阱", "跨表資料鏈、真實 DB 漂移", "backend/tests/known_failures.json（基線）、weekly 24 輸出", None),
    ("前端單元測試 vitest（228 檔）", "weekly 114（host）；無 commit 閘門", "元件渲染、hook 邏輯；mock 有沒有跟上 barrel 的新 export", "真實 API、跨頁流程", "frontend/tests/known_failures.json（基線）、weekly 114 輸出", None),
    ("每日 runner（容器 02:00，17 步）", "APScheduler fitness_daily", "容器環境對齊、映像新鮮度、volume／healthcheck SSOT、排程沉默、儀表板新鮮度、CRLF、DB 交易、模組匯入、八條生命跡象、知識文庫新鮮度、容器重啟迴圈、**業務鏈探針 32 斷言（09-06 起）**", "頁面、視覺、效能、跨 repo", "wiki/memory/integration-health/、LINE 晨報 digest", 30),
    ("每週 runner（host 週日 02:30，114 步）", "Windows 排程 CK_Missive-Fitness-Weekly", "架構／規範／資料語意／金流對帳／RWD 閘門／同步 I/O／名稱鍵…（見 scripts/checks/README.md）", "即時故障（一週才看一次）", "wiki/memory/fitness_weekly_last_run.json、digest", 8 * 24),
    ("頁面走查 ui_page_sweep（host 04:30）", "Windows 排程 CK_Missive-SelfAudit-Sweep", "41 頁載入錯誤、console error、API 4xx/5xx；手機探針 390／768／1024 整頁溢出", "畫面對不對、數字對不對", "integration-health/ui-sweep.json", 30),
    ("流程走查 ui_flow_smoke（host 04:15 admin／05:10 user）", "Windows 排程 CK_Missive-SelfAudit-Flow(-User)", "20 條流程斷言（元素在、數量對、深連結、回歸鎖）＋資料防護（走查不得動到資料）", "版面／截字／顏色語意／遮蔽／手感", "integration-health/ui-flow.json、ui-flow.user.json", 30),
    ("手機品質閘門 rwd_mobile_quality（weekly 111）", "weekly（host Playwright 登入 390／1440）", "截字、字級<11px、點擊目標<28px、fixed 遮蔽、統計卡獨列、下拉塌陷", "互動後的畫面（只拍載入後）", "integration-health/rwd-quality.json、rwd-quality-desktop.json、基線 .rwd_quality_baseline.json", 8 * 24),
    ("視覺走查 run.sh --visual（--click 先點再拍）", "**手動**（session 內）", "人看圖才看得出的：截字、遮蔽、配色、版面", "cron 裡沒人看圖 ⇒ 不排程", "docs/health/visual/<日期>/", None),
    ("部署態 8 層（deploy-public.sh）", "每次部署", "tsc 閘門、build 身分、容器內 health、host、公網 200、認證鏈、**業務鏈探針 32 斷言**", "沒有部署的日子（⇒ 09-06 起探針也進每日）", "部署 log（scratchpad／終端）", None),
    ("效能探針 route_cost_probe.cjs", "**手動**", "每路由冷／暖 API 支數與 wall、同體重複", "後端內部耗時（用 pg_stat_statements／REQUEST_END）", "session scratchpad；未入庫", None),
    ("SQL 剖析 pg_stat_statements", "常駐（09-06 起）", "每句 SQL 的 calls／mean／total", "應用層路徑", "postgres 內；無留痕匯出", None),
    ("併發／事件迴圈", "weekly 112（同步 I/O AST）、每日 6（agent_query 飢餓）、unit（asyncpg 競態 lint）", "async 路徑上的同步呼叫、gather 共用 session", "真實負載下的行為（無壓測）", "基線 .async_sync_io_baseline.txt", 8 * 24),
    ("能力使用（零流量）", "host 04:50", "7 日零流量 API、無呼叫者短名單", "月週期功能", "integration-health/capability-usage.json", 30),
    ("跨 repo 互驗（AaaP）", "AaaP drift §40／§54／§72、ck-contract-verify 每 10 分鐘、health-smoke C-6", "排程存活與 rc、日誌佔比、colo、契約端點存在（GET／POST 都探）、bridge 可達", "端點回什麼（只看存在）", "CK_AaaP/platform/CROSS_SESSION_BLOCKERS.md、AaaP 的 drift 報告", None),
    ("備份驗證", "CK_Website check-backup-run-result（每晚）；weekly 45 四類完整性", "robocopy 錯誤碼、四類備份存在", "還原可不可用（只驗存在）", "D:/Backup/CKProject_Backup.log、weekly 45", None),
    ("執行期看門狗", "cron_events、watchdog、容器重啟迴圈（每日 15）、Prometheus 告警（AaaP）", "排程有沒有跑、容器有沒有 die、探針 probe_success", "業務正確性", "logs/cron_events.jsonl、Prometheus", None),
]


def _age_hours(p: Path) -> float | None:
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        ts = d.get("checked_at") or d.get("captured_at") or d.get("ts")
        if ts:
            t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - t).total_seconds() / 3600
    except Exception:
        pass
    return (datetime.now(timezone.utc) - datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)).total_seconds() / 3600


TRACES = {
    "每日 runner": [ROOT / "wiki" / "memory" / "fitness_daily_history.json"],
    "每週 runner": [ROOT / "wiki" / "memory" / "fitness_weekly_last_run.json"],
    "頁面走查": [IH / "ui-sweep.json"],
    "流程走查": [IH / "ui-flow.json"],
    "手機品質閘門": [IH / "rwd-quality.json"],
    "能力使用": [IH / "capability-usage.json"],
}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== 自主測試機制圖（weekly 113，僅報告）===")
    lines = [f"# 自主測試機制圖（自動產生 {datetime.now().strftime('%Y-%m-%d %H:%M')}）", "",
             "> 由 `scripts/checks/testing_map_report.py` 產生；層的定義在腳本裡，新鮮度從留痕檔讀。",
             "> 這張表回答「每層看得見什麼、看不見什麼、誰觸發、留痕在哪、上次什麼時候跑」——不判紅。", "",
             "| 層 | 觸發／頻率 | 看得見 | 看不見 | 留痕 | 新鮮度 |", "|---|---|---|---|---|---|"]
    stale = 0
    for name, trig, sees, blind, trace, limit in LAYERS:
        fresh = "—"
        for key, paths in TRACES.items():
            if key in name:
                ages = [a for a in (_age_hours(p) for p in paths) if a is not None]
                if ages:
                    a = min(ages)
                    fresh = f"{a:.0f} 小時前"
                    if limit and a > limit:
                        fresh += " ⚠️過期"; stale += 1
                else:
                    fresh = "**無留痕**"; stale += 1
        lines.append(f"| {name} | {trig} | {sees} | {blind} | {trace} | {fresh} |")
    # 測試資產數
    be = len(list((ROOT / "backend" / "tests").rglob("test_*.py")))
    fe = len(list((ROOT / "frontend" / "src").rglob("*.test.ts"))) + len(list((ROOT / "frontend" / "src").rglob("*.test.tsx")))
    flows = len(json.loads((ROOT / "selfaudit.config.json").read_text(encoding="utf-8")).get("flows", []))
    lines += ["", "## 資產數", "", f"- 後端測試檔 {be}；前端測試檔 {fe}；UI 流程 {flows} 條；頁面 {len(list((ROOT / 'frontend' / 'src' / 'pages').glob('*.tsx')))}",
              "- 每日 runner 步數：" + str(sum(1 for l in (ROOT / 'scripts' / 'checks' / 'run_fitness_daily.sh').read_text(encoding='utf-8').splitlines() if l.lstrip().startswith('run_step "'))),
              "- 每週 runner 步數：" + str(sum(1 for l in (ROOT / 'scripts' / 'checks' / 'run_fitness_weekly.sh').read_text(encoding='utf-8').splitlines() if l.lstrip().startswith('run_step "'))),
              "", "## 缺口（定義在 `docs/architecture/AUTONOMOUS_TESTING_MAP.md`，這裡只列名）", "",
              "- 前端 vitest 只在 weekly 114 跑，沒有 commit 閘門；基線 86 項待清（A111）", "- pre-push 只跑相關測試（找不到對應測試的改動不擋）", "- 視覺走查與效能探針只有手動", "- 沒有真實負載（壓測）與 RUM",
              ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"寫入 {OUT.relative_to(ROOT)}；留痕過期或缺 {stale} 層（僅報告）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
