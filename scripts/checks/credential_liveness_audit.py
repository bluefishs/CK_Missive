# -*- coding: utf-8 -*-
"""憑證存活稽核 —— 提請複查（2026-08-05，owner：token 應有提請複查）

## 為何需要這支

憑證失效是**最典型的沉默失敗**：token 死了，那條管道就什麼都不做，
而 job 照樣回 success。今年已經發生過至少三次，每一次都是事後才知道：

  ‧ Telegram bot token 401 —— 5 個 job 對著死管道推播，直到 08-03 全面收斂才發現
  ‧ LINE 免費月配額用罄（06 月下旬）—— 通知整個月靜默
  ‧ GITHUB_TOKEN 未設 —— `/admin/deployment` 功能等於不存在

共同形狀：**沒有任何機制在問「我們的憑證還活著嗎」**。

## 設計取捨（都是刻意的）

1. **不印任何憑證值**，只印名稱、來源、狀態與遮罩後的指紋（前 4 碼）。
2. **分三態**：`ok`（已設定且實測可用）／`unset`（未設定）／`invalid`（已設定但實測失敗）。
   `unset` 不一定是問題 —— 有些功能本來就沒啟用；**但它必須被看見**，
   而不是靜靜地讓某個功能不存在。
3. **只對可安全探測的憑證做實測**：唯讀、冪等、不送出任何訊息、不消耗配額。
   會產生副作用的（如 LINE push）一律**不實測**，改看既有的用量指標。
4. **到期/輪換提醒**：`SECRET_ROTATION_SOP.md` 有輪換規範但沒有人在計時。
   這裡以「最後修改日」估算年齡，超過門檻即提請複查（不是失效，是該看一眼）。

用法：
    python scripts/checks/credential_liveness_audit.py
    python scripts/checks/credential_liveness_audit.py --ci    # invalid 即 exit 1
退出碼：0 全部可用或已知未設定 / 1 有 invalid（--ci）/ 2 無法探測（未驗完）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
CONTAINER = "ck_missive_backend"
ROTATE_WARN_DAYS = 180  # 超過即提請複查（非失效）

# 只列可安全探測或需要被看見的憑證。加項目時必須註明「不實測」的理由。
CREDENTIALS = [
    {"name": "TELEGRAM_BOT_TOKEN", "probe": "telegram",
     "why": "推播管道。2026-08 實測 401＝已死，5 個 job 對它推了不知多久"},
    {"name": "GROQ_API_KEY", "probe": "groq",
     "why": "LLM 主力 provider（免費 tier）"},
    {"name": "NVIDIA_API_KEY", "probe": None,
     "why": "LLM 第二順位。不實測：探測即消耗配額，且失敗會落 Ollama 不影響服務"},
    {"name": "LINE_CHANNEL_ACCESS_TOKEN", "probe": "line_quota",
     "why": "唯一活著的推播管道。只查配額（唯讀），**不送訊息**"},
    {"name": "MCP_SERVICE_TOKEN", "probe": "service_token",
     "why": "Hermes/外部整合的服務憑證，可對自家唯讀端點驗"},
    {"name": "GITHUB_TOKEN", "probe": None,
     "why": "部署歷史功能。未設＝該功能不存在（UI 檢核長期跳過該頁）"},
    {"name": "CK_SSO_JWT_SECRET", "probe": None,
     "why": "跨 repo SSO 驗章。不實測：L41 教訓是跨 repo drift，屬 sso_ttl/secret audit 的範疇"},
]


def _env_from_container() -> dict:
    """讀容器實際生效的 env（不是 .env 檔）—— config drift 的教訓（L70）。"""
    try:
        out = subprocess.run(["docker", "exec", CONTAINER, "printenv"],
                             capture_output=True, text=True, timeout=25)
        if out.returncode != 0:
            return {}
        return dict(
            line.split("=", 1) for line in out.stdout.splitlines() if "=" in line
        )
    except Exception:
        return {}


def _mask(v: str) -> str:
    if not v:
        return "-"
    return f"{v[:4]}…({len(v)} 字元)"


def _probe_in_container(lines: list[str]) -> tuple[str, str]:
    """在**應用實際執行的容器內、用應用實際用的 client（httpx）** 探測。

    2026-08-05 首跑教訓：初版在 host 用 urllib 打 Groq，得到 HTTP 403 →
    差點回報「Groq 主力憑證已死」。實際是 **Cloudflare error 1010 擋 urllib 的 UA**，
    同一把 key 在容器內用 httpx 打 chat/completions 回 **200**。
    憑證是否可用，只有「在真正使用它的環境、用真正使用它的方式」問才算數
    ——與「cron 消費端必須在 cron 實際執行的容器裡驗」是同一條規則。
    """
    try:
        # 探測腳本以 list 傳入再 join —— 直接寫含 \n 的字串在多層 shell/heredoc 下
        # 會被吃掉（本專案已踩過 5 次），list 沒有跳脫字元就沒有這個風險。
        out = subprocess.run(["docker", "exec", CONTAINER, "python", "-c", "\n".join(lines)],
                             capture_output=True, text=True, timeout=40)
        line = (out.stdout or "").strip().splitlines()
        payload = line[-1] if line else ""
        if payload.startswith("OK "):
            return "ok", payload[3:]
        if payload.startswith("INVALID "):
            return "invalid", payload[8:]
        return "unknown", (payload or (out.stderr or "")[:60] or "無輸出")
    except Exception as e:  # noqa: BLE001
        return "unknown", f"探測失敗 {str(e)[:40]}"


def _probe_telegram(_t: str) -> tuple[str, str]:
    return _probe_in_container([
        "import os,httpx",
        "k=os.getenv('TELEGRAM_BOT_TOKEN','')",
        "r=httpx.get(f'https://api.telegram.org/bot{k}/getMe',timeout=15)",
        "d=r.json() if r.status_code==200 else {}",
        "print('OK @'+d['result']['username'] if d.get('ok') else f'INVALID HTTP {r.status_code}')",
    ])


def _probe_groq(_t: str) -> tuple[str, str]:
    # 只送 1 token 的最小請求：足以驗憑證，配額成本可忽略
    return _probe_in_container([
        "import os,httpx",
        "k=os.getenv('GROQ_API_KEY','')",
        "r=httpx.post('https://api.groq.com/openai/v1/chat/completions',"
        "headers={'Authorization':f'Bearer {k}'},"
        "json={'model':'llama-3.3-70b-versatile',"
        "'messages':[{'role':'user','content':'hi'}],'max_tokens':1},timeout=25)",
        # 探測腳本一律**純 ASCII**：命令列含中文經 Windows subprocess 傳進容器會壞掉
        # （實測 stdout/stderr 皆空＝看起來像「無輸出」）。中文在 host 端才組。
        "print('OK inference-200' if r.status_code==200 else f'INVALID HTTP {r.status_code}')",
    ])


def _probe_line_quota(_token: str) -> tuple[str, str]:
    """只讀本月用量（守欄自己用的那個 Redis key），**不呼叫 LINE API、不送訊息**。"""
    month = datetime.now().strftime("%Y-%m")
    try:
        out = subprocess.run(
            ["docker", "exec", "ck_missive_redis", "redis-cli", "--no-auth-warning",
             "GET", f"line:push:count:{month}"],
            capture_output=True, text=True, timeout=15)
        used = (out.stdout or "").strip()
        cap = int(os.getenv("LINE_MONTHLY_SOFT_CAP", "185"))
        if not used:
            return "ok", f"本月尚未推播（軟上限 {cap}）"
        n = int(used)
        state = "invalid" if n >= cap else "ok"
        return state, f"本月已用 {n}/{cap}" + ("（已達軟上限，推播被凍結）" if state == "invalid" else "")
    except Exception as e:  # noqa: BLE001
        return "unknown", f"讀取失敗 {str(e)[:40]}"


def _probe_service_token(_t: str) -> tuple[str, str]:
    """對自家唯讀端點驗（冪等、不改狀態），同樣在容器內用 httpx。"""
    return _probe_in_container([
        "import os,httpx",
        "k=os.getenv('MCP_SERVICE_TOKEN','')",
        "r=httpx.get('http://localhost:8001/api/ai/memory/digest',"
        "headers={'X-Service-Token':k},timeout=20)",
        "print('OK HTTP 200' if r.status_code==200 else f'INVALID HTTP {r.status_code}')",
    ])


PROBES = {"telegram": _probe_telegram, "groq": _probe_groq,
          "line_quota": _probe_line_quota, "service_token": _probe_service_token}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print("憑證存活稽核（提請複查）— 只顯示名稱與遮罩指紋，不印任何憑證值")
    print("=" * 70)

    env = _env_from_container()
    if not env:
        print("✗ 讀不到容器 env —— 無法判定，不等於全部正常（後端未啟動？）")
        return 2

    rows, invalid, unset, unknown = [], [], [], []
    for c in CREDENTIALS:
        name = c["name"]
        val = (env.get(name) or "").strip()
        if not val:
            rows.append((name, "unset", "未設定", "-"))
            unset.append(f"{name} — {c['why']}")
            continue
        if not c["probe"]:
            rows.append((name, "set", "已設定（刻意不實測）", _mask(val)))
            continue
        state, detail = PROBES[c["probe"]](val)
        rows.append((name, state, detail, _mask(val)))
        if state == "invalid":
            invalid.append(f"{name}：{detail} — {c['why']}")
        elif state == "unknown":
            unknown.append(f"{name}：{detail}")

    ICON = {"ok": "🟢", "set": "⚪", "unset": "🟡", "invalid": "🔴", "unknown": "⚠️"}
    for name, state, detail, fp in rows:
        print(f"  {ICON.get(state, '?')} {name:<28} {detail:<34} {fp}")

    # 輪換提醒：.env 最後修改日（估算，非精確輪換日）
    if ENV_FILE.exists():
        age = (datetime.now(timezone.utc)
               - datetime.fromtimestamp(ENV_FILE.stat().st_mtime, timezone.utc)).days
        if age >= ROTATE_WARN_DAYS:
            print(f"\n🟡 `.env` 已 {age} 天未變動（門檻 {ROTATE_WARN_DAYS} 天）——"
                  f"依 SECRET_ROTATION_SOP 提請複查輪換（非失效）")

    if unset:
        print(f"\n🟡 未設定 {len(unset)} 項（不一定是問題，但必須被看見）：")
        for u in unset:
            print(f"      {u}")
    if unknown:
        print(f"\n⚠️ 無法判定 {len(unknown)} 項（未驗完，不等於正常）：")
        for u in unknown:
            print(f"      {u}")
    if invalid:
        print(f"\n🔴 已設定但實測失敗 {len(invalid)} 項：")
        for i in invalid:
            print(f"      {i}")
        print("\nStatus: [RED] 有憑證已死 —— 對應管道正在靜默失敗")
        return 1 if args.ci else 0

    print("\nStatus: [GREEN] 已設定的憑證皆實測可用" if not unknown
          else "\nStatus: [YELLOW] 有項目無法判定（未驗完）")
    return 2 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
