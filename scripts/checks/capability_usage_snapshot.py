# -*- coding: utf-8 -*-
"""能力使用度快照 —— 第 6 階「價值層」的資料收集（2026-08-01）

## 為何需要這支

六階檢核階梯的前五階都在問「機制有沒有在跑」，沒有一階在問
**「跑出來的東西有沒有人用」**。這個缺口的代價是實測過的：
`proactive_alert` 累積 4094 筆、未讀 4708 —— 通知中心實質死亡，
而所有巡檢當時全綠，因為每個機制都「正常運作」。

## 為何不用靜態分析

既有 `capability_usage_audit`（87 findings）與 `dead_ui_detector`（143 候選）
都是靜態推論：grep 前端有沒有出現這個字串。噪音大到無法採信
（標準 §3 立法：任何比對工具採信前須先驗鑑別力）。

本腳本改用**真實流量**：Prometheus 的 `http_requests_total{endpoint=...}`。
這是「有沒有人用」的直接證據，不是推論。

## 刻意不做的事

- **不告警**。價值層的產出是**決策輸入**，不是每日打擾。
  把它接成每日告警，一週內就會變成第 4709 筆沒人看的通知。
- **不在資料不足時給結論**。視窗不足時明確標示「資料不足」並 exit 2——
  「未驗完」不得被讀成「沒問題」。

## 前提（2026-08-01 查證才發現）

本專案**自 2026-04-19 起就不在任何 Prometheus 抓取目標中**（約 3.5 個月），
因此 5 個 Missive Grafana dashboard 與相關 alert rule 一直沒有資料。
設定檔註解說目標「已搬到 CK_AaaP/monitoring/prometheus.yml」，但**該檔不存在**，
而 lvrland/pile/kmap/DT 後來都加回平台設定，唯獨主產品沒有。已於本日補回。

用法：
    python scripts/checks/capability_usage_snapshot.py            # 快照
    python scripts/checks/capability_usage_snapshot.py --json     # 只印 JSON
退出碼：0 資料足夠且已產出 / 1 執行失敗 / 2 資料不足或無法查詢（未驗完）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # L49.8：cp950 host
except Exception:
    pass

PROM_URL = os.environ.get("PROMETHEUS_URL", "http://127.0.0.1:19090")
# **必須限定本專案** —— 平台 Prometheus 同時抓多個專案，且 endpoint 標籤
# 不含服務名。首版沒限定，結果把 lvrland 的 /api/analytics/*、/api/basemap-db/*
# 一起算進 CK_Missive 的「能力」裡（標準 §3：先驗鑑別力）。
PROM_JOB = os.environ.get("SELFAUDIT_PROM_JOB", "ck-missive")
WINDOW_DAYS = 7
# 判定門檻：資料深度不足這個天數就只觀察、不下結論。
#
# 2026-08-04 由 30 → 14（owner 決議）。原本的 30 **結構上永遠達不到**：
# 平台 Prometheus 用預設保留期 15 天，資料深度被釘在 15.x（8/02 量到 15.6、
# 8/03 量到 15.37 —— 看起來像在累積，其實是被裁掉舊資料後的浮動）。
# 也就是說這個門檻不是「還沒到」，是「不會到」，而腳本每次都禮貌地說
# 「資料不足、拒絕給結論」，沒有人會發現那是永久狀態。
#   兩條路：拉高保留期（動到五系統共用的觀測棧）或降門檻。owner 選降門檻。
#
# ⚠️ 代價（判定時必讀，別讓它變成誤刪的依據）：
#   14 天深度 + 7 天視窗＝只涵蓋約兩個週循環，**看不到月週期**。
#   月結、月報、年度作業這類低頻功能在此視窗必然是 0 流量，
#   **不得**據此判定為死功能 —— 零流量清單對這類功能只能作為人工複核的線索。
MIN_DATA_DAYS = 14
DECISION_DATE = "2026-08-31"

# `path` 標籤改記路由樣板（而非原始 URL）的日期。見下方 schema_settled 說明。
PATH_LABEL_TEMPLATED_SINCE = datetime(2026, 8, 4, tzinfo=timezone.utc)

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT.parent / "wiki" / "memory" / "integration-health" / "capability-usage.json"

# 零流量但屬合理的端點 —— 不是「沒人用」，是「本來就不該有前端流量」。
# 加項目時必須寫理由，否則這份清單會變成掩蓋問題的地毯。
EXEMPT_PREFIXES = [
    ("/api/health", "健康檢查：由 cloudflared/docker healthcheck 呼叫，不經 middleware 統計"),
    ("/api/line/", "webhook：由 LINE 平臺呼叫"),
    ("/api/telegram/", "webhook：由 Telegram 平臺呼叫"),
    ("/api/discord/", "webhook：由 Discord 平臺呼叫"),
    ("/api/public/", "公開端點：多為未登入探針"),
    ("/metrics", "Prometheus 自身抓取"),
    ("/docs", "OpenAPI 文件"),
    ("/openapi.json", "OpenAPI 文件"),
]


def _query(expr: str) -> list[dict]:
    url = f"{PROM_URL}/api/v1/query?query=" + urllib.parse.quote(expr)
    with urllib.request.urlopen(url, timeout=20) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus 查詢失敗：{payload}")
    return payload["data"]["result"]


def _data_depth_days() -> float:
    """TSDB 實際擁有多少天的資料。

    不可用 `status/runtimeinfo` 的 startTime —— 那是**行程啟動時間**，
    Prometheus 一重啟就歸零，但 TSDB 裡的歷史資料還在
    （實測：重啟後 startTime 報 0 天，實際有 15 天）。
    `prometheus_tsdb_lowest_timestamp_seconds` 才是資料本身的起點。
    """
    result = _query("prometheus_tsdb_lowest_timestamp_seconds")
    if not result:
        return -1.0  # 取不到就回負值，由呼叫端當「未知」處理，不可當成 0
    try:
        oldest = float(result[0]["value"][1])
    except (IndexError, KeyError, ValueError):
        return -1.0
    return (datetime.now(timezone.utc).timestamp() - oldest) / 86400


def _detect_path_label() -> str | None:
    """偵測本專案用哪個標籤存路徑。

    **各專案不一致**（2026-08-01 實測）：CK_Missive 的
    `prometheus_middleware` 用 `path`，CK_lvrland_Webmap 用 `endpoint`。
    寫死任一個，在另一個專案就會回「1 筆空標籤序列」——看起來像
    「沒有任何候選」，實際是標籤名不符。
    """
    override = os.environ.get("SELFAUDIT_PATH_LABEL")
    if override:
        return override
    for label in ("path", "endpoint", "handler", "route"):
        try:
            result = _query(f'count by ({label}) (http_requests_total{{job="{PROM_JOB}"}})')
        except Exception:  # noqa: BLE001
            return None
        # 有多個不同值才算真的是路徑標籤（只有 1 筆空標籤代表該標籤不存在）
        if len(result) > 1 or (result and result[0]["metric"].get(label)):
            return label
    return None


def _exempt_reason(endpoint: str) -> str | None:
    for prefix, reason in EXEMPT_PREFIXES:
        if endpoint.startswith(prefix):
            return reason
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="只輸出 JSON")
    args = ap.parse_args()

    quiet = args.json
    if not quiet:
        print("=" * 66)
        print("能力使用度快照（第 6 階 價值層 — 資料收集，不下結論）")
        print("=" * 66)

    # 1) Prometheus 可達性 —— 缺外部依賴一律 raise/exit 2，不得沉默跳過（契約規則 4）
    try:
        depth = _data_depth_days()
        # 必須是 sum 不是 count —— count by 數的是「序列筆數」，對每個曾出現過的
        # endpoint 都 ≥1，於是全部看起來都有流量（首版寫錯，122 個全判為 active、
        # 0 個候選）。sum 才是實際請求數：同一組資料下 122 → 31。
        # 這正是標準 §3「採信任何比對/統計工具前必須先驗鑑別力」的實例。
        path_label = _detect_path_label()
        if not path_label:
            print(f'✗ job="{PROM_JOB}" 的 http_requests_total 沒有可辨識的路徑標籤。')
            print("  已試：path / endpoint / handler / route。可設 SELFAUDIT_PATH_LABEL 指定。")
            print("  **這不是「沒有候選」**，是標籤結構不符，無法分析。")
            return 2
        seen = _query(
            f"sum by ({path_label}) "
            f'(increase(http_requests_total{{job="{PROM_JOB}"}}[{WINDOW_DAYS}d]))'
        )
    except (urllib.error.URLError, OSError, RuntimeError, KeyError) as exc:
        print(f"✗ 無法查詢 Prometheus（{PROM_URL}）：{exc}")
        print("  這是外部依賴缺失，不是「沒問題」。設 PROMETHEUS_URL 或確認容器狀態。")
        return 2

    if not seen:
        # 兩種可能：本專案未被抓取，或指標改名。兩者都不是「全部沒人用」。
        print(f'✗ job="{PROM_JOB}" 查不到任何 http_requests_total 樣本。')
        print("  可能原因（依序查）：")
        print(f"    1. 本專案不在 Prometheus 抓取目標中 —— 查 {PROM_URL}/targets")
        print("    2. job 名稱不符 —— 設 SELFAUDIT_PROM_JOB")
        print("    3. 指標名稱/標籤已變更")
        print("  **0 筆不等於全部沒人用**，在確認之前不得作為任何判定依據。")
        return 2

    active, zero = {}, []
    for item in seen:
        ep = item["metric"].get(path_label)
        if not ep:
            continue
        try:
            val = float(item["value"][1])
        except (IndexError, ValueError):
            val = 0.0
        if val > 0:
            active[ep] = val
        else:
            zero.append(ep)

    # 一個帶 endpoint 標籤的序列都沒有 → 不是「全部沒人用」，是**沒有可用資料**。
    # 實際踩到：剛把本專案加進抓取目標時，increase() 需要 ≥2 次取樣才有值，
    # 此時查詢回 1 筆無標籤序列 → 上面的「查不到樣本」守衛沒擋住，
    # 卻印出「0 個候選」看起來像健康。
    if not active and not zero:
        print(f'✗ job="{PROM_JOB}" 有序列但沒有任何帶 {path_label} 標籤的資料點。')
        print(f"  最可能：本專案剛加入抓取，increase() 需至少 2 次取樣（約 {WINDOW_DAYS} 分鐘後重試）。")
        print("  **這不是「沒有候選」**，是資料尚不可用。")
        return 2

    exempt = [(e, _exempt_reason(e)) for e in zero if _exempt_reason(e)]
    unexempt = [e for e in zero if not _exempt_reason(e)]
    # **API 能力與前端頁面路由必須分開**——後端對 SPA 路由回 index.html，
    # 所以 `/admin/backup` 這種會出現在 http_requests_total 裡，但它不是「一個 API 能力」。
    # 混在一起會讓「dead capability」清單充滿頁面路徑而失去意義（首版 404 筆多為此類）。
    candidates = sorted(e for e in unexempt if e.startswith("/api/"))
    page_routes_zero = sorted(e for e in unexempt if not e.startswith("/api/"))

    # depth < 0 代表取不到深度（未知），與「資料不足」都不得視為足夠
    #
    # 2026-08-04 追加第二道門檻：**量測基準變更日**。
    # 首次拿出 79 個候選時，裡面近半是 `/documents-enhanced/2645/detail` 這種**實例路徑**
    # ——因為 `path` 標籤記的是原始 URL 而不是路由樣板。這種項目為 0 只代表
    # 「這 7 天沒人開 2645 這份公文」，回答不了「這個能力還有沒有人用」，
    # 清單整份不可採信（標準 §3：先驗鑑別力）。middleware 已於當日改記路由樣板，
    # 但 [7d] 視窗要完全落在改版後才乾淨，否則新舊兩種標籤會混在同一份清單裡。
    days_since_schema = (datetime.now(timezone.utc) - PATH_LABEL_TEMPLATED_SINCE).days
    schema_settled = days_since_schema >= WINDOW_DAYS
    sufficient = depth >= MIN_DATA_DAYS and schema_settled
    snapshot = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prometheus": PROM_URL,
        "job": PROM_JOB,
        "path_label": path_label,
        "window_days": WINDOW_DAYS,
        "data_depth_days": round(depth, 2),
        "data_sufficient": sufficient,
        "min_data_days": MIN_DATA_DAYS,
        "path_label_templated_since": PATH_LABEL_TEMPLATED_SINCE.date().isoformat(),
        "days_since_path_label_change": days_since_schema,
        "schema_settled": schema_settled,
        "decision_date": DECISION_DATE,
        "counts": {
            "endpoints_seen": len(seen),
            "active": len(active),
            "zero_traffic_exempt": len(exempt),
            "zero_traffic_api_candidates": len(candidates),
            "zero_traffic_page_routes": len(page_routes_zero),
        },
        "top_active": sorted(active.items(), key=lambda kv: -kv[1])[:15],
        "zero_traffic_api_candidates": candidates,
        "zero_traffic_page_routes": page_routes_zero,
        "exempt": [{"endpoint": e, "reason": r} for e, r in exempt],
        # 明確寫進產出，避免日後有人拿不足的資料當結論
        "caveat": (
            "本快照僅為資料收集。data_sufficient=false 時不得據此判定任何能力為 dead；"
            f"判定時點為 {DECISION_DATE}。"
            f"⚠️ path 標籤自 {PATH_LABEL_TEMPLATED_SINCE.date()} 起改記路由樣板（原為原始 URL，"
            f"使清單充滿 /documents-enhanced/2645/detail 這種實例路徑而不可採信）；"
            f"[{WINDOW_DAYS}d] 視窗需完全落在改版後才乾淨。"
            f"⚠️ 觀測深度上限受 Prometheus 保留期（15d）約束，門檻 2026-08-04 由 30 降為 "
            f"{MIN_DATA_DAYS} 天：{WINDOW_DAYS} 日視窗只涵蓋約兩個週循環、看不到月週期，"
            "月結/月報/年度作業必然為 0 流量，**不得**據此判為死功能，只能作人工複核線索。"
        ),
        "known_blind_spot": "monthly_and_seasonal_cycles",
    }

    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        # 2026-08-09：把**真正卡住的那一項**講出來。
        # 原本一律印「判定需 ≥N 天 → 不足」，但 sufficient 是兩個條件的 and：
        # 實測深度 15.1（已達 14）卻印「不足」，讀的人會以為還要等資料長出來，
        # 實際卡的是 path label 改版後的 7 日穩定期（8/11 自然解除）。
        # 說錯原因會讓人等錯東西 —— 同 L82 家族。
        depth_ok = depth >= MIN_DATA_DAYS
        print(f"  Prometheus 資料深度：{depth:.1f} 天"
              f"（需 ≥{MIN_DATA_DAYS} 天 → {'足夠' if depth_ok else '不足'}）")
        print(f"  path label 穩定期：{days_since_schema}/{WINDOW_DAYS} 天"
              f"（需 ≥{WINDOW_DAYS} 天 → {'足夠' if schema_settled else '尚未滿足'}）")
        if not sufficient:
            blocker = "資料深度" if not depth_ok else "path label 穩定期"
            print(f"  → 目前卡在：**{blocker}**")
        print(f"  近 {WINDOW_DAYS} 日有流量：{len(active)} 個 endpoint")
        print(f"  零流量（已豁免）：{len(exempt)}")
        print(f"  零流量 API（待判定候選）：{len(candidates)}")
        print(f"  零流量頁面路由（另計，非 API 能力）：{len(page_routes_zero)}")
        if candidates[:10]:
            for e in candidates[:10]:
                print(f"      {e}")
            if len(candidates) > 10:
                print(f"      …另 {len(candidates) - 10} 個")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    if not quiet:
        print(f"\n  已寫入 {OUT_PATH.relative_to(ROOT.parent)}")

    # 2026-08-10：退出碼語意修正 —— 原本「尚不可判定」與「Prometheus 掛了」
    # **一律回 2（RED）**，於是這支永遠接不進任何 runner：接了就會週週紅到 8/31，
    # 而每週紅一次的告警幾週後就沒人看（L31 家族）。所以它一直沒有執行者，
    # 而沒有執行者就代表 **8/31 那天不會有任何人想起要下判定**。
    #
    # 三態拆開：
    #   外部依賴壞（Prometheus 不可達／標籤不符／0 樣本）→ 2 RED（上方已 return，不變）
    #   資料還在累積、且未到判定時點                   → 0 GREEN（正常等待，不是故障）
    #   已到判定時點（無論資料夠不夠）                 → 1 YELLOW（提請決策）
    #
    # 關鍵在最後一條：**到期本身就是要有人看的事件**。沒有它，這份快照會一直
    # 安靜地產出 JSON 而沒有任何人被叫醒 —— 那正是本專案反覆記的「訊號存在但沒有接收者」。
    due = date.today().isoformat() >= DECISION_DATE

    if not sufficient:
        if not quiet:
            # 兩道門檻的原因必須分開講 —— 混成一句「資料不足」會讓人以為只要再等
            # 深度就會夠，而實際卡住的可能是量測基準剛換（等的天數不一樣）。
            print("\n⚪ 尚不可判定 —— 僅供觀察，本次不下任何結論。")
            if depth < MIN_DATA_DAYS:
                print(f"   • 資料深度 {depth:.1f}/{MIN_DATA_DAYS} 天（受 Prometheus 保留期上限約束）")
            if not schema_settled:
                ready = PATH_LABEL_TEMPLATED_SINCE.date().toordinal() + WINDOW_DAYS
                print(f"   • path 標籤 {PATH_LABEL_TEMPLATED_SINCE.date()} 改記路由樣板，"
                      f"已過 {days_since_schema}/{WINDOW_DAYS} 天")
                print(f"     （在此之前清單會混入改版前的實例路徑，不可採信；"
                      f"預計 {datetime.fromordinal(ready).date()} 起乾淨）")
            print(f"   判定時點：{DECISION_DATE}")
            if due:
                print(f"\n🟡 但**判定時點 {DECISION_DATE} 已到**，資料卻仍不足 ——")
                print("   該等的已經等完了。請人工決定：放寬門檻、換量測方式，或延後並寫明新日期。")
        return 1 if due else 0

    if not quiet:
        print("\n✅ 資料足夠，可進入判定（仍須人工核實季節性功能）")
        if due:
            print(f"\n🟡 判定時點 {DECISION_DATE} 已到且資料足夠 —— **這是提請決策，不是故障**。")
            print(f"   請逐一核實 {len(candidates)} 個零流量 API 候選後下結論，")
            print(f"   並把 DECISION_DATE 改為下一個檢視點（否則此提醒會每週重複）。")
    return 1 if due else 0


if __name__ == "__main__":
    sys.exit(main())
