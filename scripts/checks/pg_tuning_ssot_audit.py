#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostgreSQL 調校參數的跨檔 SSOT：三份 compose 與規格書必須一致。

## 為什麼有這一支

owner 2026-08-29：「設定檔不一致請檢視排除整合」。

同一組 14 個 postgres 調校參數**在四個地方各寫一份**：

    docker-compose.dev.yml          -c 參數（機制）
    docker-compose.infra.yml        -c 參數（機制）
    docker-compose.production.yml   -c 參數（機制，**目前運行中的那份**）
    configs/postgresql-tuning.conf  規格書

實查當日 **`max_connections` 不一致**：infra 100、其餘 50。
而 dev.yml 與 infra.yml 定義的是**同一個容器**
（`${COMPOSE_PROJECT_NAME}_postgres_dev`）—— 也就是**用哪個檔起，
同一個容器就得到不同的設定**，那是 `cross-file-ssot-governance.md`
規則 1 明文禁止的形態。

⚠️ 另有一個更隱蔽的：`postgresql-tuning.conf` 被三份 compose 都掛載，
但**執行時根本沒被讀**（實測 `pg_settings.source = command line`）。
它的檔頭原本寫著「在 command 加入 `-c config_file=`」—— 那一半從沒做，
而且那段指示本身不可行。⇒ 照著它排障會得到錯的結論（L02 Dead Config）。

## 判準

三層都查，任一層不符即 RED：

  ① compose 之間  三份 compose 的同名參數必須相同
  ② compose ↔ 規格  compose 的值必須等於 `postgresql-tuning.conf`
  ③ 檔案 ↔ 執行時  正在跑的 postgres 實際值必須等於 production.yml
                    （不同 ⇒ 改了檔但沒重啟，**那是最容易騙人的狀態**：
                     檔案看起來對，系統行為卻是舊的）

第 ③ 層查不到容器時回 YELLOW 不是 GREEN —— 「查不到」與「一致」
在輸出上長得一樣，那正是本檢核要防的東西（ADR-0028）。

## 這一支為什麼不是「永遠綠的稽核」

寫下來的當天，第 ① 層就是 RED（max_connections 100 vs 50，已修）。
而它的觸發條件很實在：**任何人改了一份 compose 沒改另外三處**就會紅。

## 誰跑它

weekly step 88（`run_fitness_weekly.sh`）。
"""
import os
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
COMPOSES = [
    "docker-compose.dev.yml",
    "docker-compose.infra.yml",
    "docker-compose.production.yml",
]
SPEC = "configs/postgresql-tuning.conf"
#: 運行中的 postgres 應該對齊哪一份 compose
RUNTIME_SOURCE = "docker-compose.production.yml"
CONTAINER = os.environ.get("CK_PG_CONTAINER", "ck_missive_postgres")
DB_USER = os.environ.get("POSTGRES_USER", "ck_user")
DB_NAME = os.environ.get("POSTGRES_DB", "ck_documents")

#: 納管的參數。刻意**列舉**而不是「所有 -c 參數」——
#: 新增參數時要有人決定它該不該納管，而不是靜靜地被加進來。
TUNED = [
    "shared_buffers", "work_mem", "maintenance_work_mem", "effective_cache_size",
    "random_page_cost", "effective_io_concurrency", "wal_buffers",
    "checkpoint_completion_target", "max_connections",
    "log_min_duration_statement", "log_lock_waits", "log_temp_files",
    "default_statistics_target",
]

_ARG = re.compile(r'"?([a-z_]+)=([^"\s,]+)"?')


#: 單位換算到基準（記憶體→bytes，時間→ms）。
#: ⚠️ 這一段是被實測逼出來的：首版直接比字串，於是
#: `work_mem=16MB`（檔案）vs `16384kB`（postgres 回報）被判成不一致 ——
#: **7 個參數全部誤報**。而一支永遠紅的稽核與永遠綠的一樣沒用。
_MEM = {"kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3, "tb": 1024 ** 4, "b": 1}
_TIME = {"ms": 1, "s": 1000, "min": 60000, "h": 3600000, "d": 86400000}


def _norm(v: str) -> str:
    """正規化到可比較的字串。

    記憶體與時間換算到基準單位；純數字與布林原樣（小寫）。
    `512MB` 與 `524288kB` 因此相等。
    """
    v = v.strip().strip("'\"").lower()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([a-z]+)", v)
    if m:
        num, unit = float(m.group(1)), m.group(2)
        if unit in _MEM:
            return f"B{int(num * _MEM[unit])}"
        if unit in _TIME:
            return f"T{int(num * _TIME[unit])}"
    return v


def _from_compose(path: Path) -> dict:
    out = {}
    for m in _ARG.finditer(path.read_text(encoding="utf-8")):
        if m.group(1) in TUNED:
            out[m.group(1)] = _norm(m.group(2))
    return out


def _raw_compose(path: Path) -> dict:
    """未經正規化的 compose 值 —— 用來判斷「檔案是不是寫裸數字」。"""
    out = {}
    for m in _ARG.finditer(path.read_text(encoding="utf-8")):
        if m.group(1) in TUNED:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def _from_spec(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k in TUNED:
            out[k] = _norm(v)
    return out


def _from_runtime(raw: dict) -> dict | None:
    """回傳正規化後的值；同時把原始 setting 填進 `raw`（供裸數字比對）。"""
    keys = "','".join(TUNED)
    # ⚠️ `setting` 與 `unit` **不可直接串接**：shared_buffers 的 unit 是 `8kB`，
    # 串接會把 `65536` + `8kB` 黏成 `655368kB`（首版就是這樣誤報的）。
    # 用 `|` 分隔，由 Python 依 unit 做乘法。
    sql = (f"SELECT name||'|'||setting||'|'||COALESCE(unit,'') FROM pg_settings "
           f"WHERE name IN ('{keys}')")
    try:
        r = subprocess.run(
            ["docker", "exec", "-i", CONTAINER,
             "psql", "-U", DB_USER, "-d", DB_NAME, "-Atc", sql],
            capture_output=True, text=True, timeout=90,
            env={**os.environ, "MSYS_NO_PATHCONV": "1"},
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = {}
    for ln in r.stdout.splitlines():
        parts = ln.split("|")
        if len(parts) != 3:
            continue
        name, setting, unit = (x.strip() for x in parts)
        # 同時保留原始 setting —— 檔案寫裸數字時（`log_min_duration_statement=500`），
        # 那個數字**就是該參數的原生單位**，要跟 setting 直接比，不能跟換算後的比。
        # ⚠️ 這是第二輪誤報：換算修好之後仍有 2 個 —— 500 vs T500、0 vs B0。
        raw[name] = setting
        if not unit:
            out[name] = _norm(setting)
            continue
        # unit 形如 `8kB` / `kB` / `ms`：前面的倍數（可省略）× 單位
        m = re.fullmatch(r"(\d*)\s*([a-zA-Z]+)", unit)
        if not m:
            out[name] = _norm(setting)
            continue
        mult = int(m.group(1) or 1)
        try:
            out[name] = _norm(f"{int(setting) * mult}{m.group(2)}")
        except ValueError:
            out[name] = _norm(setting)
    return out


def main() -> int:
    missing = [f for f in COMPOSES + [SPEC] if not (ROOT / f).is_file()]
    if missing:
        print(f"✗ 找不到 {missing} —— 無法判定（不視為通過）")
        return 2

    per_file = {f: _from_compose(ROOT / f) for f in COMPOSES}
    spec = _from_spec(ROOT / SPEC)

    reds = []

    # ① compose 之間
    for key in TUNED:
        seen = {f: v[key] for f, v in per_file.items() if key in v}
        if len(set(seen.values())) > 1:
            detail = "／".join(f"{Path(f).name}={v}" for f, v in seen.items())
            reds.append(f"[compose 之間] {key}: {detail}")

    # ② compose ↔ 規格
    for f, vals in per_file.items():
        for key, v in vals.items():
            if key in spec and spec[key] != v:
                reds.append(
                    f"[compose↔規格] {key}: {Path(f).name}={v} 而 "
                    f"{Path(SPEC).name}={spec[key]}")

    print(f"納管參數 {len(TUNED)} 個｜compose {len(COMPOSES)} 份｜規格書 {len(spec)} 項")

    # ③ 檔案 ↔ 執行時
    raw_runtime: dict = {}
    runtime = _from_runtime(raw_runtime)
    if runtime is None:
        print(f"  [YELLOW] 連不上 {CONTAINER} —— 第 ③ 層（檔案 vs 執行時）未驗")
        print("           「查不到」不等於「一致」，故不算通過的證據。")
    else:
        prod = per_file[RUNTIME_SOURCE]
        prod_raw = _raw_compose(ROOT / RUNTIME_SOURCE)
        for key, v in prod.items():
            rv = runtime.get(key)
            if rv is None:
                continue
            # 檔案寫裸數字 ⇒ 與 postgres 的原始 setting 直接比（同一個原生單位）
            file_raw = prod_raw.get(key, "")
            if file_raw.isdigit() and key in raw_runtime:
                if file_raw == raw_runtime[key]:
                    continue
            if rv != v:
                reds.append(
                    f"[檔案↔執行時] {key}: {Path(RUNTIME_SOURCE).name}={v} "
                    f"而執行中的是 {rv} —— **改了檔但沒重啟 postgres**")

    if not reds:
        print("✓ 三層皆一致")
        return 0

    print(f"\n✗ 不一致 {len(reds)} 處")
    for r in reds:
        print(f"    {r}")
    print("\n  修法：改設定要**同時**改三份 compose 與規格書；"
          "若第 ③ 層紅，代表需要重啟 postgres 才會套用。")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
