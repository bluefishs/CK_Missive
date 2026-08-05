# -*- coding: utf-8 -*-
"""Producer 產出判定的**單一實作**（2026-08-05）。

## 為什麼要有這個檔

`producer_outcome_registry.json` 一直被說成是 SSOT，但真正決定「綠或紅」的是
**判定邏輯**，而那份邏輯先前有兩份各自獨立的 Python：

  * host   `scripts/checks/producer_output_watchdog.py`
  * 容器內 `backend/app/core/scheduler.py :: cron_outcome_freshness_job`

同一份 registry、兩份判定 → 08-04 就咬過一次：registry 早已有 `db_row_count`
（07-20 加）與 `json_result`（08-04 加），但容器那份只認 3 種、**認不得就靜靜跳過**，
於是那些 producer 在「每天無人值守的自動告警」裡根本不存在，手動跑 host 卻全綠。
當時的處置是替容器補上型別＋加「認不得就出聲」守衛 —— 那是補丁，不是根治：
只要判定有兩份，下一個新型別就會再發生一次。

## 分工

判定是純函式（本檔），IO 由各自的呼叫端做 —— 因為兩邊的 IO 天生不同：
host 用 psycopg2 連 localhost:5434、容器用 async SQLAlchemy；路徑基準也不同。
**能共用的是判斷，不是連線方式**，硬把 IO 也抽在一起反而是過度抽象。

  load_registry()  讀 + 驗證 registry（缺檔/壞掉/空 → 拋例外，絕不靜默退化）
  build_count_sql() db_* 兩種信號的 SQL（單一來源，避免兩邊 WHERE 寫法漂移）
  resolve_path()   registry 的 repo 相對路徑 → 各自環境的實際路徑
  judge()          純判定：給它事實，回傳「哪裡不對」或 None
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable, Optional

# registry 結構版本。改變欄位語意時 +1，兩端讀到不認識的版本一律拒絕執行
# （而不是用舊語意去解讀新資料然後印綠燈）。
SCHEMA_VERSION = 1

KNOWN_SIGNALS = frozenset(
    {"file_fresh", "cron_detail", "db_table_today", "db_row_count", "json_result"}
)

# job self-report 的 detail.reason 若落在這裡，代表產出異常（沉默成功）
PROBLEM_REASONS = frozenset(
    {"fetch_failed", "weekday_zero_suspicious", "exception", "connector_none",
     "no_token", "error"}
)


class RegistryUnavailable(RuntimeError):
    """registry 不可用 —— 呼叫端必須視為「未驗完」，不得當成「全部正常」。"""


def load_registry(config_path: Path) -> list[dict]:
    """讀取並驗證 registry。任何問題一律拋 RegistryUnavailable。

    **刻意沒有 fallback**：先前 host 端在檔案讀不到時會靜靜退回一份內建的
    `_FALLBACK_REGISTRY`（07-18 的舊副本），那份還含著 08-02 已證實會遮蔽
    ezbid 死亡 48 天的「pcc+ezbid 合併監控」。也就是說：registry 一旦消失，
    這支專門偵測沉默失敗的工具會用一份已知有缺陷的清單繼續印綠燈。
    第二份副本本身就是這個檔案要消滅的東西。
    """
    if not config_path.exists():
        raise RegistryUnavailable(f"registry 不存在：{config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RegistryUnavailable(f"registry 不是合法 JSON：{config_path}：{e}") from e

    version = data.get("schema_version", 1)
    if version != SCHEMA_VERSION:
        raise RegistryUnavailable(
            f"registry schema_version={version}，本判定模組只認 {SCHEMA_VERSION}。"
            f"（版本不符時用舊語意解讀新資料會產生看似正常的錯誤結論）"
        )

    producers = data.get("producers") or []
    if not producers:
        raise RegistryUnavailable(f"registry 內 0 個 producer：{config_path}（0 項不等於全部健康）")

    # 2026-08-05：拒絕測試用的假 producer 留在正式 registry。
    #
    # 08-04 做負向測試時，我把兩筆假 producer（`__負向測試_不存在檔`、
    # `__負向測試_未知信號`）加進**正式** registry 檔並觸發 job 驗證它會出聲 ——
    # 它確實出聲了，然後把告警寫進正式 digest buffer，隔天 07:30 推給了 owner。
    # 驗證機制自己污染了正式輸出，與「測試把假告警寫進晨報緩衝區」同型。
    #
    # 結構性防法：`__` 前綴保留給測試，且**正式 registry 一律不得含有** ——
    # 負向測試要用 tmp 檔跑 load_registry()，不要改這一份。
    test_entries = sorted({
        p.get("name", "") for p in producers if str(p.get("name", "")).startswith("__")
    })
    if test_entries:
        raise RegistryUnavailable(
            f"正式 registry 含測試用 producer：{test_entries}。"
            f"（`__` 前綴保留給測試；負向測試請用 tmp registry 檔，不要改正式那份 ——"
            f"2026-08-04 就是這樣把假告警送進了 owner 的晨報）"
        )

    unknown = sorted({
        p.get("signal") for p in producers if p.get("signal") not in KNOWN_SIGNALS
    })
    if unknown:
        raise RegistryUnavailable(
            f"registry 含本模組不認得的 signal：{unknown}。"
            f"認得的：{sorted(KNOWN_SIGNALS)}。"
            f"（認不得就跳過＝那些 producer 在自動告警裡等於不存在）"
        )
    return producers


def resolve_path(root: Path, rel: str, *, strip_backend_prefix: bool) -> Path:
    """registry 內的路徑是 **repo root 相對**；換算成呼叫端的實際位置。

    容器內 `/app` 就是 repo 的 `backend/`，所以 `backend/` 前綴要剝掉（L52 家族）；
    `wiki/`、`docs/` 兩邊都掛在 /app 底下，不受影響。
    """
    if strip_backend_prefix and rel.startswith("backend/"):
        rel = rel[len("backend/"):]
    return root / rel


def build_count_sql(spec: dict) -> str:
    """db_table_today / db_row_count 的 SQL —— 單一來源。

    先前兩端各自組字串，WHERE 與日期比較的寫法只要有一邊改動就會悄悄分歧，
    而分歧的症狀是「兩邊給出不同的綠燈」，沒有任何錯誤訊息。
    """
    signal = spec["signal"]
    where = spec.get("where")
    # where 一律加括號：host 版原本有、容器版原本沒有 —— 對 `source='pcc'` 這種
    # 單一條件沒差，但只要有人寫 `a=1 OR b=2` 兩邊就會得出不同答案，而症狀是
    # 「兩邊各自給出綠燈」，不會有任何錯誤訊息。這正是要消滅的漂移。
    if signal == "db_table_today":
        sql = (f"SELECT COUNT(*) FROM {spec['table']} "
               f"WHERE {spec['date_col']}::date = CURRENT_DATE")
        if where:
            sql += f" AND ({where})"
        return sql
    if signal == "db_row_count":
        sql = f"SELECT COUNT(*) FROM {spec['table']}"
        if where:
            sql += f" WHERE ({where})"
        return sql
    raise ValueError(f"build_count_sql 不適用於 signal={signal}")


def _count(value: Any) -> int:
    """把 list/dict/數字/None 一律換算成一個數量。"""
    if isinstance(value, (list, dict)):
        return len(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def judge(
    spec: dict,
    *,
    now: Optional[float] = None,
    is_weekend: bool = False,
    newest_mtime: Optional[float] = None,
    latest_event: Optional[dict] = None,
    db_value: Optional[int] = None,
    json_files: Optional[Iterable[Path]] = None,
) -> Optional[str]:
    """純判定：給定事實，回傳問題描述；沒問題回 None。

    呼叫端只負責取事實（檔案 mtime／cron 事件／DB 數字／輸出 JSON），
    要不要算紅燈全部在這裡決定，兩端因此不可能再分歧。
    """
    now = now if now is not None else time.time()
    name = spec.get("name", "?")
    signal = spec.get("signal")

    if signal == "file_fresh":
        age_h = (now - newest_mtime) / 3600 if newest_mtime else 9999
        if age_h > spec["max_h"]:
            return f"{name}: {age_h:.0f}h 前 (門檻 {spec['max_h']}h)"
        return None

    if signal == "cron_detail":
        if not latest_event:
            return None          # 沒有事件＝該 job 這輪沒跑到，交由 cron 存活檢查管
        detail = latest_event.get("detail") or {}
        reason = detail.get("reason")
        ok_zero = set(spec.get("ok_zero_reasons") or [])
        if reason in PROBLEM_REASONS:
            return f"{name}: 產出異常 reason={reason}（沉默成功）"
        # 2026-08-05：key 根本不在 detail 裡 → 該 job 沒有回報，這**不能算通過**。
        # 先前寫法是 `detail.get(key) == 0`，而 None != 0，於是「job 完全不回 detail」
        # 反而一路綠燈 —— 註冊為 producer 卻不回報，正是要抓的沉默成功。
        if spec["key"] not in detail:
            return f"{name}: detail 未回報 {spec['key']}（job 沒有 self-report＝沉默成功）"
        if detail.get(spec["key"]) == 0 and reason not in ok_zero:
            return f"{name}: {spec['key']}=0 非合理零 reason={reason}（沉默成功）"
        return None

    if signal == "db_table_today":
        if db_value is None:
            return f"{name}: 無法查詢 {spec['table']}（未驗完，不得視為正常）"
        if not db_value and not (spec.get("weekend_legit") and is_weekend):
            return f"{name}: {spec['table']} 今日 0（非合理空＝疑沉默失敗）"
        return None

    if signal == "db_row_count":
        if db_value is None:
            return f"{name}: 無法查詢 {spec['table']}（未驗完，不得視為正常）"
        if db_value < spec.get("min", 0):
            return f"{name}: {spec['table']} 僅 {db_value} < 下限 {spec['min']}（疑資料塌陷）"
        return None

    if signal == "json_result":
        files = sorted(json_files or [], key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return f"{name}: {spec['path']} 不存在（檢核器沒產出）"
        try:
            data = json.loads(files[0].read_text(encoding="utf-8"))
        except Exception as e:
            return f"{name}: 結果檔無法解析（{e}）"
        bad = []
        if spec.get("fail_key") and _count(data.get(spec["fail_key"])) > 0:
            bad.append(f"{spec['fail_key']}={_count(data.get(spec['fail_key']))}")
        # min_key 是必要的：只驗 fail=0 會讓「掃到 0 條也叫綠」（2026-08-03 立法）
        if spec.get("min_key") and _count(data.get(spec["min_key"])) < spec.get("min_value", 0):
            bad.append(f"{spec['min_key']}={_count(data.get(spec['min_key']))}<{spec.get('min_value')}")
        if spec.get("ok_key") and not data.get(spec["ok_key"]):
            bad.append(f"{spec['ok_key']}={data.get(spec['ok_key'])}")
        for k, want in (spec.get("expect") or {}).items():
            if data.get(k) != want:
                bad.append(f"{k}={data.get(k)}≠{want}")
        if bad:
            return f"{name}: {'、'.join(bad)}（檢核跑了但結果是紅的）"
        return None

    # load_registry() 已擋掉未知 signal；走到這裡代表有人繞過它直接呼叫 judge()
    return f"{name}: 未支援的 signal「{signal}」（judge 收到未經 load_registry 驗證的 spec）"
