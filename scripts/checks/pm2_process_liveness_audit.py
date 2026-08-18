# -*- coding: utf-8 -*-
"""PM2 程序存活稽核 —— 三個排程層裡最後一個沒有哨兵的那層（2026-08-10）。

## 為什麼要有這一支

portfolio 有**三個**排程層，2026-08-10 覆盤時量到只有兩個有人看：

| 層 | 誰在跑 | 存活哨兵 |
|---|---|---|
| Windows 排程（23 支 CK-*） | 作業系統 | `windows_task_liveness_audit.py`（weekly 28） |
| 容器內 APScheduler（53 jobs） | backend 容器 | `producer_output_watchdog.py` + `scheduler_liveness_audit` |
| **PM2（16 支）** | host PM2 daemon | **只有 `CK_Website/scripts/check-cron-coverage.cjs`** |

而那支問的是「設定檔宣告的 8 條 cron 有沒有在 PM2 註冊」——**註冊不等於在跑**。
本專案已經為這句話付過三次學費（2026-08-01「排程註冊了不等於排程會跑」同一輪踩三次），
而 PM2 這一層至今沒有任何人在問「它上次跑完了沒、成功了沒」。

這不是「訊號沒有接收者」，是**整整一層不在任何座標系裡** —— 與 2026-08-10 發現
「資料庫埠不在 public_exposure_audit 的視野裡」是同一個形狀（A 型盲區）。

## 判讀 PM2 狀態的兩個坑（先踩過才寫得對）

**坑 1：`stopped` 對 cron 型是正常狀態。** 16 支裡 9 支是 `cron_restart` + `autorestart:false`，
跑完就退出、等下次 fire。**看到一排 stopped 就判故障會產出 9 個假紅**，
而假紅比沒有告警更糟——它會訓練人忽略這份輸出。

**坑 2：`exit_code` 對 online 型是殘值。** `ck-showcase-frontend` 現在 online、
uptime 從 07-30 至今，`exit_code` 卻是 1（那是更早某次退出留下的）。
只有 stopped 的 cron 型才能拿 exit_code 判上次跑得如何。

## 判準

  常駐型（無 cron_restart）：status 必須 online
  cron 型：
    · 依 cron 表達式往回掃出「上次應該 fire 的時間」
    · 最後啟動時間早於它、且已超過 grace → 錯過了（RED）
    · grace = min(該 cron 的實際間隔, 6h) —— 自我縮放，不用一個拍腦袋的固定值
    · exit_code != 0 → 上次跑失敗（RED）
  所有型：
    · script 檔案不存在 → 永遠起不來（RED）
    · script 位於暫存目錄 → 開機自啟清單指向會被清掉的路徑（RED）

  **無法解析的 cron 表達式 → 拒絕執行（exit 2）**，不猜。
  猜出來的綠燈與沒有檢查是同一件事。

## 已知限制（寫出來，不假裝沒有）

PM2 的 cron **不補跑**：機器關機期間錯過的 fire 不會在開機後補上，
與 Windows 排程沒設 `StartWhenAvailable` 是同一家族（2026-08-02 踩過）。
所以本稽核報「錯過」時，可能的原因包含「那段時間機器是關的」——
輸出會把最後啟動時間一起印出來，讓人自己判斷，而不是替人下結論。

## 用法

  python scripts/checks/pm2_process_liveness_audit.py
  python scripts/checks/pm2_process_liveness_audit.py --self-test   # 驗判準有沒有鑑別力
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - 舊版 Python 無此方法
    pass


# ---------------------------------------------------------------------------
# 已知且刻意接受的狀態。**必須附理由** —— 只有名字的豁免等於沒有豁免，
# 三個月後沒有人記得為什麼放它過去（2026-08-05 producer registry 同一條規矩）。
# ---------------------------------------------------------------------------
KNOWN_ACCEPTABLE: dict[str, str] = {}

# ---------------------------------------------------------------------------
# 已知根因對照（2026-08-17）
#
# **這不是豁免** —— 這些項目仍然判 RED（備份真的壞了）。
# 它的用途是：紅的時候直接說出「這是誰的、卡在什麼」，
# 而不是讓人每週從頭追一次 log。
#
# 2026-08-17 查證：三支 RED 其實是**同一件事** ——
#   ck-kv-snapshot 在 PM2 非互動環境沒有 Cloudflare 認證而失敗
#   → CK_Website 的 KV 備份 30 天沒更新（可用 8 份／空 22 份）
#   → ck-sso-health 與 ck-sso-contract-probe 讀到 STALE 跟著紅
#
# 三個 RED 看起來像三個問題，實際只有一個。沒有這張對照表，
# 每週都會有人分別去追那三支。
# ---------------------------------------------------------------------------
KNOWN_ROOT_CAUSE: dict[str, str] = {
    "ck-kv-snapshot":
        # ⚠️ 2026-08-18 owner 更正：**wrangler 用的是互動式 OAuth 登入，不是 API token**。
        # 我原本寫「未設 CLOUDFLARE_API_TOKEN」——那個描述會讓人去找一把
        # 不存在的 token，而真因是「PM2 非互動環境拿不到 `wrangler login`
        # 建立的那個 OAuth session」。**指向錯誤修法的根因，比沒有根因更糟。**
        "根因＝wrangler 走互動式 OAuth（`wrangler login`），"
        "而 PM2 是非互動環境，拿不到那個 session → 5/5 namespace 全讀不到。"
        "屬 CK_Website。腳本已刻意不 rotate 以免擠掉僅存的可用備份。"
        "兩條路（由 owner 選）：①改用非互動憑證（Workers KV 讀取權限）"
        "並注入 PM2 環境；②把這支移出 PM2、改由具備 OAuth session 的環境執行。",
    "ck-sso-health":
        "下游症狀 —— 讀到 ck-kv-snapshot 產出的 STALE 備份。修上游即恢復。",
    "ck-sso-contract-probe":
        "下游症狀 —— 同 ck-sso-health。修上游即恢復。",
}

# 暫存目錄特徵：script 落在這些路徑底下代表它活不過一次清理。
TEMP_MARKERS = ("\\temp\\", "/temp/", "\\tmp\\", "/tmp/", "appdata\\local\\temp")


# ---------------------------------------------------------------------------
# 最小 cron 解析。刻意不引入 croniter：
#   多一個依賴，就多一個「host 有裝、容器沒裝」的失效面（L52 家族）。
#   而我們只需要「往回找上一次 fire」，暴力回掃已經夠快也夠精確。
# ---------------------------------------------------------------------------
class CronParseError(ValueError):
    pass


def _parse_field(spec: str, lo: int, hi: int) -> set[int]:
    """把單一 cron 欄位展開成允許值集合。無法解析就丟例外，不回退成 '全部允許'。"""
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise CronParseError(f"空欄位: {spec!r}")
        step = 1
        if "/" in part:
            part, _, step_s = part.partition("/")
            if not step_s.isdigit() or int(step_s) < 1:
                raise CronParseError(f"步進值不合法: {spec!r}")
            step = int(step_s)
        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            a, _, b = part.partition("-")
            if not (a.isdigit() and b.isdigit()):
                raise CronParseError(f"區間不合法: {spec!r}")
            start, end = int(a), int(b)
        elif part.isdigit():
            start = end = int(part)
        else:
            raise CronParseError(f"無法解析: {spec!r}")
        if start < lo or end > hi or start > end:
            raise CronParseError(f"超出範圍 [{lo},{hi}]: {spec!r}")
        out.update(range(start, end + 1, step))
    if not out:
        raise CronParseError(f"展開後為空: {spec!r}")
    return out


def parse_cron(expr: str) -> dict:
    fields = expr.split()
    if len(fields) != 5:
        raise CronParseError(f"需要 5 個欄位，得到 {len(fields)}: {expr!r}")
    minute, hour, dom, month, dow = fields
    return {
        "minute": _parse_field(minute, 0, 59),
        "hour": _parse_field(hour, 0, 23),
        "dom": _parse_field(dom, 1, 31),
        "month": _parse_field(month, 1, 12),
        # cron 的星期：0 與 7 都是星期日
        "dow": {d % 7 for d in _parse_field(dow, 0, 7)},
        "dom_restricted": dom.strip() != "*",
        "dow_restricted": dow.strip() != "*",
    }


def cron_matches(dt: datetime, c: dict) -> bool:
    if dt.minute not in c["minute"] or dt.hour not in c["hour"]:
        return False
    if dt.month not in c["month"]:
        return False
    cron_dow = (dt.weekday() + 1) % 7  # Python Mon=0 → cron Sun=0
    dom_ok = dt.day in c["dom"]
    dow_ok = cron_dow in c["dow"]
    # 標準 cron 語意：兩者都有限制時取聯集，否則取交集
    if c["dom_restricted"] and c["dow_restricted"]:
        return dom_ok or dow_ok
    return dom_ok and dow_ok


def previous_fires(now: datetime, c: dict, count: int = 2, max_days: int = 70) -> list[datetime]:
    """從 now 往回掃，回傳最近 count 次應該 fire 的時間（新到舊）。"""
    cur = now.replace(second=0, microsecond=0)
    limit = count if count > 0 else 1
    found: list[datetime] = []
    for _ in range(max_days * 24 * 60):
        cur -= timedelta(minutes=1)
        if cron_matches(cur, c):
            found.append(cur)
            if len(found) >= limit:
                break
    return found


# ---------------------------------------------------------------------------
# 取得 PM2 狀態
# ---------------------------------------------------------------------------
def load_pm2_processes() -> list[dict]:
    """讀 `pm2 jlist`。

    ⚠️ 必須寫檔再讀，不能直接接管線。2026-08-10 實測：
    `pm2 jlist | python` 在 Windows 上會因編碼轉換而讓 JSON 壞在中段
    （報 Invalid \\escape），同一份輸出寫成檔案再讀則完全正常。
    這一行註解是為了擋住「下次有人覺得管線比較簡潔」。
    """
    exe = shutil.which("pm2")
    if not exe:
        raise RuntimeError(
            "找不到 pm2 指令。本稽核設計為在 host 執行（weekly 由 "
            "CK_Missive-Fitness-Weekly 排程觸發）。找不到依賴時拒絕執行，"
            "而不是靜靜跳過 —— 靜靜跳過會讓『沒有檢查』長得跟『檢查通過』一樣。"
        )
    tmp = Path(tempfile.gettempdir()) / "pm2_liveness_jlist.json"
    with open(tmp, "w", encoding="utf-8") as fh:
        proc = subprocess.run([exe, "jlist"], stdout=fh, stderr=subprocess.DEVNULL, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"pm2 jlist 退出碼 {proc.returncode}")
    raw = tmp.read_text(encoding="utf-8", errors="strict")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise RuntimeError("pm2 jlist 回傳的不是清單")
    return data


def normalize(p: dict) -> dict:
    env = p.get("pm2_env") or {}
    uptime_ms = env.get("pm_uptime")
    return {
        "name": p.get("name") or "(無名)",
        "status": env.get("status"),
        "cron": (env.get("cron_restart") or "").strip(),
        "exit_code": env.get("exit_code"),
        "restarts": env.get("restart_time"),
        "script": env.get("pm_exec_path") or "",
        "cwd": env.get("pm_cwd") or "",
        "last_start": datetime.fromtimestamp(uptime_ms / 1000) if uptime_ms else None,
    }


# ---------------------------------------------------------------------------
# 判定
# ---------------------------------------------------------------------------
def evaluate(procs: list[dict], now: datetime) -> tuple[list[str], list[str], list[str]]:
    """回傳 (紅燈, 說明, 逐項狀態)。無法解析的 cron 直接丟例外由呼叫端轉 RED。"""
    reds: list[str] = []
    notes: list[str] = []
    rows: list[str] = []

    for pr in sorted(procs, key=lambda x: x["name"]):
        name = pr["name"]
        problems: list[str] = []

        # --- 殭屍條目：與是不是 cron 型無關，先判 ---
        script = pr["script"]
        if script and not Path(script).exists():
            problems.append("script 檔案不存在 → 永遠起不來")
        elif script and any(m in script.lower() for m in TEMP_MARKERS):
            problems.append(
                "script 位於暫存目錄 → 已被 pm2 save 寫進開機自啟清單，"
                "但該目錄會被清理，重開機後起不來"
            )

        if not pr["cron"]:
            # --- 常駐型 ---
            kind = "常駐"
            if pr["status"] != "online":
                problems.append(f"常駐程序狀態為 {pr['status']}（應為 online）")
            detail = f"status={pr['status']}"
        else:
            # --- cron 型：stopped 是正常的，要看的是「上次該跑的時候跑了嗎」---
            kind = "cron"
            c = parse_cron(pr["cron"])  # 解析不了就讓它炸，由呼叫端轉 RED
            fires = previous_fires(now, c, count=2)
            if not fires:
                problems.append(f"70 天內沒有任何應 fire 時點（表達式 {pr['cron']!r} 形同停用）")
                detail = f"cron={pr['cron']}"
            else:
                last_expected = fires[0]
                interval = (fires[0] - fires[1]) if len(fires) >= 2 else timedelta(hours=6)
                grace = min(interval, timedelta(hours=6))
                ls = pr["last_start"]
                if ls is None:
                    problems.append("PM2 沒有記錄任何啟動時間")
                elif ls < last_expected and now > last_expected + grace:
                    late = now - last_expected
                    problems.append(
                        f"錯過了 {last_expected:%m-%d %H:%M} 那次 fire"
                        f"（已逾 {late.total_seconds() / 3600:.1f}h，最後啟動 {ls:%m-%d %H:%M}）"
                    )
                if pr["status"] == "stopped" and pr["exit_code"] not in (0, None):
                    problems.append(f"上次執行退出碼 {pr['exit_code']}（非 0＝失敗）")
                detail = (
                    f"cron={pr['cron']} 上次應 fire={last_expected:%m-%d %H:%M} "
                    f"最後啟動={ls:%m-%d %H:%M}" if ls else f"cron={pr['cron']}"
                )

        if problems and name in KNOWN_ACCEPTABLE:
            notes.append(f"· {name}: {'；'.join(problems)} —— 已知可接受（{KNOWN_ACCEPTABLE[name]}）")
            rows.append(f"  [GREEN] {name:<26} {kind:<4} {detail}")
        elif problems:
            for p in problems:
                reds.append(f"{name}: {p}")
            rows.append(f"  [RED  ] {name:<26} {kind:<4} {detail}")
        else:
            rows.append(f"  [GREEN] {name:<26} {kind:<4} {detail}")

    return reds, notes, rows


# ---------------------------------------------------------------------------
# 鑑別力自我測試 —— 判準若「不會動」，看起來會跟「很乾淨」一模一樣
# ---------------------------------------------------------------------------
def self_test() -> int:
    now = datetime(2026, 8, 10, 20, 40)
    cases = [
        (
            "正向：每 15 分鐘的 cron 剛跑過",
            [{"name": "ok-15m", "status": "stopped", "cron": "*/15 * * * *", "exit_code": 0,
              "restarts": 6, "script": __file__, "cwd": "",
              "last_start": datetime(2026, 8, 10, 20, 30)}],
            0,
        ),
        (
            "正向：每月 1 號的 cron，這個月已跑過",
            [{"name": "ok-monthly", "status": "stopped", "cron": "0 3 1 * *", "exit_code": 0,
              "restarts": 1, "script": __file__, "cwd": "",
              "last_start": datetime(2026, 8, 1, 3, 0)}],
            0,
        ),
        (
            "正向：常駐程序 online（exit_code 殘值 1 不得誤判）",
            [{"name": "ok-daemon", "status": "online", "cron": "", "exit_code": 1,
              "restarts": 0, "script": __file__, "cwd": "",
              "last_start": datetime(2026, 7, 30, 13, 59)}],
            0,
        ),
        (
            "負向：每日 cron 已兩天沒跑",
            [{"name": "bad-missed", "status": "stopped", "cron": "30 4 * * *", "exit_code": 0,
              "restarts": 3, "script": __file__, "cwd": "",
              "last_start": datetime(2026, 8, 8, 4, 30)}],
            1,
        ),
        (
            "負向：cron 有跑但上次退出碼非 0",
            [{"name": "bad-exit", "status": "stopped", "cron": "0 5 * * *", "exit_code": 2,
              "restarts": 4, "script": __file__, "cwd": "",
              "last_start": datetime(2026, 8, 10, 5, 0)}],
            1,
        ),
        (
            "負向：常駐程序掉成 stopped",
            [{"name": "bad-daemon", "status": "stopped", "cron": "", "exit_code": 0,
              "restarts": 0, "script": __file__, "cwd": "",
              "last_start": datetime(2026, 8, 1, 0, 0)}],
            1,
        ),
        (
            "負向：script 指向不存在的檔案",
            [{"name": "bad-ghost", "status": "online", "cron": "", "exit_code": 0,
              "restarts": 0, "script": r"C:\no\such\file.cjs", "cwd": "",
              "last_start": datetime(2026, 8, 1, 0, 0)}],
            1,
        ),
        (
            "負向：script 落在暫存目錄（開機自啟指向會被清掉的路徑）",
            [{"name": "bad-temp", "status": "stopped", "cron": "", "exit_code": 0,
              "restarts": 0, "script": str(Path(tempfile.gettempdir()) / "probe.cjs"),
              "cwd": "", "last_start": datetime(2026, 8, 8, 21, 51)}],
            1,
        ),
    ]
    # 讓「暫存目錄」那一例的檔案真的存在，才驗得到 TEMP_MARKERS 而非「檔案不存在」
    probe = Path(tempfile.gettempdir()) / "probe.cjs"
    probe.write_text("// self-test fixture\n", encoding="utf-8")

    print("=== 判準鑑別力自我測試 ===")
    failed = 0
    for label, procs, expect_red in cases:
        reds, _, _ = evaluate(procs, now)
        got = 1 if reds else 0
        mark = "✓" if got == expect_red else "✗"
        if got != expect_red:
            failed += 1
        print(f"  {mark} {label:<44} 預期紅={expect_red} 實際={got}"
              + (f"  → {reds[0]}" if reds else ""))

    # 無法解析的表達式必須拒絕執行，不得回退成綠
    print("  ---")
    for expr in ("0 4 * *", "@daily", "0 99 * * *"):
        try:
            parse_cron(expr)
            print(f"  ✗ {expr!r} 應該要無法解析卻通過了")
            failed += 1
        except CronParseError:
            print(f"  ✓ 拒絕無法解析的表達式 {expr!r}")

    try:
        probe.unlink()
    except OSError:
        pass

    if failed:
        print(f"\n✗ 判準有 {failed} 項不符預期")
        return 2
    print("\n✓ 判準有鑑別力（正向 3 例、負向 5 例、拒絕解析 3 例）")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    print("=" * 70)
    print("PM2 程序存活稽核 —— 註冊了不等於在跑")
    print("=" * 70)

    try:
        raw = load_pm2_processes()
    except Exception as exc:
        print(f"\n✗ 無法取得 PM2 狀態：{exc}")
        return 2

    procs = [normalize(p) for p in raw]
    if not procs:
        print("\n✗ PM2 回報 0 個程序 —— 這不是綠燈，是 daemon 可能沒起來")
        return 2

    now = datetime.now()
    try:
        reds, notes, rows = evaluate(procs, now)
    except CronParseError as exc:
        print(f"\n✗ 有無法解析的 cron 表達式：{exc}")
        print("  拒絕執行 —— 猜出來的綠燈與沒有檢查是同一件事。")
        return 2

    n_cron = sum(1 for p in procs if p["cron"])
    print(f"  {len(procs)} 支程序（cron 型 {n_cron}／常駐 {len(procs) - n_cron}）"
          f"｜現在 {now:%Y-%m-%d %H:%M}\n")
    for r in rows:
        print(r)

    if notes:
        print("\n說明：")
        for n in notes:
            print(f"  {n}")

    print("\n" + "=" * 70)
    if reds:
        print(f"RED: {len(reds)} 項")
        for r in reds:
            print(f"  · {r}")

        # 已知根因：紅的時候直接說出「這是誰的、卡在什麼」，
        # 而不是讓人每週從頭追一次 log。
        hits = [(n, why) for n, why in KNOWN_ROOT_CAUSE.items()
                if any(n in r for r in reds)]
        if hits:
            print("\n  已知根因（仍判 RED，這不是豁免）：")
            for n, why in hits:
                print(f"    · {n}：{why}")

        print("\n  ⚠️ PM2 的 cron 不補跑 —— 機器關機期間錯過的 fire 不會補上"
              "（同 Windows 排程沒設 StartWhenAvailable）。")
        print("     上面已印出最後啟動時間，請據此判斷是「真的停了」還是「那段時間機器是關的」。")
        return 2
    print(f"GREEN: {len(procs)} 支 PM2 程序皆存活")
    return 0


if __name__ == "__main__":
    sys.exit(main())
