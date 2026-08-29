#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""設定的 LLM 模型在 provider 那邊還存不存在。

## 為什麼有這支（owner 2026-08-29「防呆機制」）

A31：Groq 與 NVIDIA 的設定模型**雙雙下架**，agent 在本地 ollama 上跑了
約 27 天沒有人知道——現場是 `Groq circuit OPEN → NVIDIA circuit OPEN →
走 Ollama` → 合成 35s 逾時、p95 68 秒。

而系統**早就有** `llm_quota_check` 每 6 小時在跑，它一路是綠的：
它量的是**用量配額**（每日請求數／月度額度／成本），從來沒有問
「設定的那個模型還存不存在」。⚠️ 更糟的是**模型不存在會讓用量變低**，
於是那支檢核在最需要出聲的時候給出更好看的答案
（`proxy_metric_looks_good` 家族的教科書案例）。

## 判準（刻意分三態，不把「查不到」當成「沒問題」）

  RED     成功取得 provider 的模型清單，而設定的模型**不在裡面** ⇒ 確定下架
  YELLOW  查詢失敗（403／網路／逾時）⇒ **不下結論**，只說查不到
          （2026-08-29 實測 Groq models 端點回 403，而 NVIDIA 回 83 個模型
            —— 若把查不到當成下架，就會反過來製造假警報）
  GREEN   設定的模型都在清單裡

⚠️ 模型名是 `backend/app/core/ai_connector.py` 的**模組級常數**
（`GROQ_DEFAULT_MODEL` / `NVIDIA_DEFAULT_MODEL`），**不是環境變數** ——
compose 只傳 API key。本腳本直接讀那兩個常數，不猜 env。

## 誰跑它

weekly step 79（`run_fitness_weekly.sh`）。
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
CONNECTOR = ROOT / "backend" / "app" / "core" / "ai_connector.py"

PROVIDERS = {
    "groq": {
        "const": "GROQ_DEFAULT_MODEL",
        "url": "https://api.groq.com/openai/v1/models",
        "chat_url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
    },
    "nvidia": {
        "const": "NVIDIA_DEFAULT_MODEL",
        "url": "https://integrate.api.nvidia.com/v1/models",
        "chat_url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "key_env": "NVIDIA_API_KEY",
    },
}


def _configured_model(const_name: str):
    """從 ai_connector.py 讀模組級常數 —— 不 import（避免拉起整個 app）"""
    if not CONNECTOR.exists():
        return None
    txt = CONNECTOR.read_text(encoding="utf-8")
    # 兩種形式都要認得：直接賦值，以及 2026-08-29 改成的 os.getenv(..., "預設")
    m = re.search(rf'^{const_name}\s*=\s*os\.getenv\([^,]+,\s*["\']([^"\']+)["\']', txt, re.M)
    if m:
        return m.group(1)
    m = re.search(rf'^{const_name}\s*=\s*["\']([^"\']+)["\']', txt, re.M)
    return m.group(1) if m else None


def _load_env_key(key_env: str):
    """.env 是本專案的環境設定 SSOT（禁 backend/.env）"""
    v = os.getenv(key_env)
    if v:
        return v
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith(f"{key_env}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main() -> int:
    reds, yellows, greens = [], [], []

    for name, cfg in PROVIDERS.items():
        model = _configured_model(cfg["const"])
        if not model:
            yellows.append(f"  [YELLOW] {name}: 讀不到 {cfg['const']} 常數（ai_connector.py 結構變了？）")
            continue
        key = _load_env_key(cfg["key_env"])
        if not key:
            yellows.append(f"  [YELLOW] {name}: 沒有 {cfg['key_env']}，無法查詢（不下結論）")
            continue
        # ⚠️ 2026-08-29 修正：原本用 `urllib` 打 models 端點，Groq 一律回
        # **403 error code 1010** —— 那是 **Cloudflare 的 bot 判定**（擋 urllib
        # 預設 UA），不是模型狀態。本 repo 判準 9 記過同一件事，而我在寫這支
        # 的**當天又踩了一次**：工具在待測對象上失效，交回來的是看起來正常的
        # YELLOW。改用 `httpx`（與 `ai_connector` 同一個 client）後 Groq 立刻
        # 回真相：舊模型 404、`openai/gpt-oss-120b` 200。
        #
        # 且改為打 **chat 端點實際呼叫**而非列清單 —— NVIDIA 實測過
        # 「模型在 83 個清單裡但呼叫回 404 Function not found」⇒
        # **清單存在不等於可呼叫**，而我們要保證的是後者。
        ids: set = set()
        try:
            import httpx
            with httpx.Client(timeout=30) as c:
                r = c.post(
                    cfg["chat_url"],
                    json={"model": model,
                          "messages": [{"role": "user", "content": "ping"}],
                          "max_tokens": 1},
                    headers={"Authorization": f"Bearer {key}"},
                )
            code = r.status_code
        except Exception as e:
            yellows.append(f"  [YELLOW] {name}: 探測失敗 {type(e).__name__} —— 不下結論")
            continue

        if code == 200:
            greens.append(f"  [ok   ] {name}: `{model}` **實際呼叫成功**（HTTP 200）")
        elif code in (401, 403):
            yellows.append(
                f"  [YELLOW] {name}: HTTP {code} —— 憑證或存取被擋，"
                f"**無法判斷** `{model}` 是否還在（不是「沒問題」也不是「下架了」）")
        elif code == 404:
            # 候選＝共用「家族詞」的模型。只從**去掉 org 前綴**的部分取，
            # 用完整名會撈到 "nvidia" 而 83 個 nvidia/* 全部命中（實測過，等於沒篩）。
            try:
                import httpx as _hx
                with _hx.Client(timeout=25) as c2:
                    lr = c2.get(cfg["url"], headers={"Authorization": f"Bearer {key}"})
                if lr.status_code == 200:
                    ids = {m["id"] for m in lr.json().get("data", [])}
            except Exception:
                pass
            fam = [w for w in re.findall(r"[a-z]{6,}", model.split("/")[-1])
                   if w not in ("instruct", "versatile")]
            near = sorted(i for i in ids if any(f in i for f in fam))[:6]
            reds.append(
                f"  [RED  ] {name}: 設定的 `{model}` **實際呼叫回 404（不存在）**"
                + (f"\n           同家族清單中有：{', '.join(near)}"
                   f"\n           ⚠️ **清單有不等於可呼叫** —— NVIDIA 實測過"
                   f"「在 83 個清單裡但呼叫回 Function not found」，換之前逐一實打"
                   if near else ""))
        else:
            yellows.append(f"  [YELLOW] {name}: HTTP {code} —— 非預期回應，不下結論")

    print("=" * 74)
    print("設定的 LLM 模型是否還存在（weekly 73）")
    print("=" * 74)
    for line in reds + yellows + greens:
        print(line)

    if reds:
        print(f"\n⚠️ 模型不存在時 fallback 會一路退到本地 ollama —— 而 `llm_quota_check`")
        print(f"   量的是用量配額，用量變低反而讓它更綠。這支就是為了補那個盲區。")
        print(f"   修法：改 `backend/app/core/ai_connector.py` 的常數（**不是 env**，")
        print(f"   compose 沒有傳模型名），換模型會影響回答品質與 TPM 假設 ⇒ owner 決策。")
        print(f"\nStatus: [RED] {len(reds)} 個 provider 的設定模型已不存在")
        return 1
    if yellows and not greens:
        print(f"\nStatus: [YELLOW] 全部查不到 —— 這不代表沒問題，只代表**這次沒問到**")
        return 0
    if yellows:
        print(f"\nStatus: [YELLOW] {len(greens)} 個確認可用、{len(yellows)} 個查不到（不下結論）")
        return 0
    print("\nStatus: [GREEN] 所有設定的模型都還在 provider 清單裡")
    return 0


if __name__ == "__main__":
    sys.exit(main())
