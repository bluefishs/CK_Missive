# -*- coding: utf-8 -*-
"""服務埠暴露稽核 —— 資料層不得從區域網路無保護連入（2026-08-10）。

## 起因

owner 的長期指示是「**有資安風險皆不應該公開**」，而既有的
`public_exposure_audit`（2026-08-05）只問一件事：**五個公開網域的 HTTP
表面上開了什麼**。它問得很好，但它的座標系是「公網 HTTP」——
資料庫埠根本不在那個座標系裡，所以再怎麼跑都不會發現。

2026-08-10 清點腳本存量時實測發現：

  * `ck_missive_postgres` 發佈為 `0.0.0.0:5434`，**區域網路任一裝置可連入**
  * 該資料庫的密碼是佈署當時的預設值，**以該密碼從 LAN 位址登入成功並讀出業務資料**
  * `ck_missive_redis` 發佈為 `0.0.0.0:6380`，**未設密碼，PING 直接回 PONG**

不是公網（Cloudflare Tunnel 只代理 HTTP 應用），但「不在公網」與「安全」是兩件事。

## 這支問的問題

    我們在區域網路上，開了哪些不該開的 TCP 埠？

判定分兩層，缺一不可：

  1. **綁定位址**：`0.0.0.0` / `::` 才會被 LAN 看見；`127.0.0.1` 不會
  2. **是否無保護**：能連上不一定進得去。Redis 用不需憑證的 `PING` 實測；
     Postgres **不實際嘗試登入**（那需要在檢核裡放一份憑證，本身就是風險），
     改為讀容器 env 比對弱密碼特徵 —— 全程不印出任何憑證內容

## ⚠️ 只報不改

改埠綁定要重建容器。本專案最嚴重的事故（L43）正是「重建 postgres 時
compose 指向錯的 volume」造成整個資料庫變成空殼。所以這支**只報告**，
修法與 L43 前置檢查寫在輸出裡，由 owner 決定何時執行。

用法：
    python scripts/checks/service_port_exposure_audit.py
    python scripts/checks/service_port_exposure_audit.py --self-test
"""
from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 資料層／快取層：這些一旦從 LAN 進得去，等同整份資料外流。
# 比對用容器名片段（本 portfolio 的命名慣例）。
SENSITIVE = {
    "postgres": "資料庫",
    "redis": "快取／工作佇列",
    "mongo": "資料庫",
    "elastic": "搜尋索引",
    "minio": "物件儲存",
    "clickhouse": "資料庫",
}

# 刻意對外的埠 —— **必須寫理由**，否則這份清單會慢慢變成「全部豁免」。
ALLOWLIST = {
    # 這些是應用本身的服務埠，由上層（Cloudflare Tunnel / 反向代理 / 應用認證）保護
    "grafana": "觀測介面，有自身帳密；五系統共用",
    "prometheus": "僅 LAN，無寫入介面；為觀測棧內部抓取目標",
    "adminer": "資料庫管理介面，有自身登入",
}

WEAK_PATTERNS = [
    (r"password", "含 'password' 字樣"),
    (r"changeme|default|secret123|admin123", "常見預設字串"),
    (r"20\d\d", "含年份（多為佈署當時的預設值）"),
]


def lan_ip() -> str:
    """取本機的 LAN 位址；取不到就回空字串（判定會據此降級而非假裝通過）。"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetIPAddress -AddressFamily IPv4 | "
             "Where-Object {$_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*'} | "
             "Select-Object -First 1).IPAddress"],
            capture_output=True, text=True, timeout=45,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def published() -> list[tuple[str, str, int]]:
    """回傳 (容器名, 綁定位址, 主機埠)。只取有發佈到主機的。"""
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=90,
        )
    except Exception:
        return []
    # docker 對同一個埠會同時列出 IPv4 與 IPv6 兩筆（0.0.0.0 與 [::]），
    # 不去重的話同一個發現會印兩次 —— 一份重複的清單會讓人以為問題比實際更多，
    # 而清單一旦不可盡信，就沒有人會逐條看。以 (容器, 埠) 去重，
    # 綁定位址取「最寬」的那個（只要有一筆是對外綁定就算對外）。
    seen: dict[tuple[str, int], str] = {}
    for line in r.stdout.splitlines():
        if "\t" not in line:
            continue
        name, ports = line.split("\t", 1)
        for m in re.finditer(r"([\d.]+|\[::\]):(\d+)->", ports):
            bind, port = m.group(1), int(m.group(2))
            key = (name, port)
            prev = seen.get(key)
            if prev is None or (prev not in ("0.0.0.0", "[::]") and bind in ("0.0.0.0", "[::]")):
                seen[key] = bind
    return [(n, b, p) for (n, p), b in seen.items()]


def reachable(host: str, port: int, timeout: float = 4.0) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def redis_open(host: str, port: int) -> bool | None:
    """True=無需認證即可下指令；False=有保護；None=判不出來。

    用 PING 而非任何寫入指令 —— 唯讀、冪等、不需憑證。
    """
    s = socket.socket()
    s.settimeout(5)
    try:
        s.connect((host, port))
        s.sendall(b"PING\r\n")
        r = s.recv(64)
        if b"PONG" in r:
            return True
        if b"NOAUTH" in r or b"WRONGPASS" in r:
            return False
        return None
    except Exception:
        return None
    finally:
        s.close()


def weak_password(container: str) -> str | None:
    """讀容器 env 判斷密碼是否為弱值。**永不印出內容**，只回傳命中的特徵名稱。"""
    for var in ("POSTGRES_PASSWORD", "MONGO_INITDB_ROOT_PASSWORD"):
        try:
            r = subprocess.run(
                ["docker", "exec", container, "printenv", var],
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            continue
        v = r.stdout.strip()
        if not v:
            continue
        for pat, why in WEAK_PATTERNS:
            if re.search(pat, v, re.I):
                return why
        if len(v) < 20:
            return f"長度僅 {len(v)} 字元（建議 ≥20）"
    return None


def judge(findings: list[dict]) -> int:
    return 2 if findings else 0


def self_test() -> int:
    """鑑別力：判準要能分辨「開著」與「關著」，也要分辨綁定位址。"""
    bad = []
    cases = [
        ("有暴露", [{"c": "x"}], 2),
        ("無暴露", [], 0),
    ]
    for name, f, expect in cases:
        got = judge(f)
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {name:22s} 預期 exit={expect} 實際={got}")
        if not ok:
            bad.append(name)

    # 綁定位址解析：0.0.0.0 與 127.0.0.1 必須分得開，否則整支沒有意義
    sample = "0.0.0.0:5434->5432/tcp, 127.0.0.1:9999->9999/tcp, [::]:6380->6379/tcp"
    got = {m.group(1) for m in re.finditer(r"([\d.]+|\[::\]):(\d+)->", sample)}
    ok = got == {"0.0.0.0", "127.0.0.1", "[::]"}
    print(f"  {'✓' if ok else '✗'} {'綁定位址解析':22s} {sorted(got)}")
    if not ok:
        bad.append("parse")

    # 弱密碼特徵：要抓得到常見形態，也不能把強密碼誤判
    hits = [w for p, w in WEAK_PATTERNS if re.search(p, "ck_password_2024", re.I)]
    ok2 = len(hits) >= 1
    strong = "Xk9#mQ2vLp7!zRt4Ng8W"
    ok3 = not any(re.search(p, strong, re.I) for p, _ in WEAK_PATTERNS) and len(strong) >= 20
    print(f"  {'✓' if ok2 else '✗'} {'弱密碼特徵命中':22s}")
    print(f"  {'✓' if ok3 else '✗'} {'強密碼不誤判':22s}")
    if not (ok2 and ok3):
        bad.append("weak-pattern")

    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 3、負向 3）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--strict", action="store_true", help="相容旗標，判定不受影響")
    ap.add_argument("--ci", action="store_true", help="相容旗標，判定不受影響")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=" * 70)
    print("服務埠暴露稽核 —— 資料層不得從區域網路無保護連入")
    print("=" * 70)

    ports = published()
    if not ports:
        # 掃到 0 個不等於「沒有暴露」—— 多半是 docker 不可用或格式變了
        print("✗ 未取得任何已發佈的容器埠 —— 無法判定，不視為通過")
        print("  （docker 未執行、或 `docker ps` 輸出格式已變更）")
        return 2

    ip = lan_ip()
    print(f"  已發佈埠 {len(ports)} 個｜本機 LAN 位址 {ip or '（取不到）'}")

    findings, safe = [], 0
    for name, bind, port in ports:
        klass = next((v for k, v in SENSITIVE.items() if k in name.lower()), None)
        if not klass:
            continue
        if any(k in name.lower() for k in ALLOWLIST):
            continue
        if bind not in ("0.0.0.0", "[::]"):
            safe += 1
            continue

        item = {"name": name, "port": port, "klass": klass, "why": []}
        if ip and reachable(ip, port):
            item["why"].append("LAN 位址實測可連入")
        if "redis" in name.lower():
            r = redis_open(ip or "127.0.0.1", port)
            if r is True:
                item["why"].append("未設密碼（PING 直接回應）")
            elif r is False:
                item["why"].append("有密碼保護")
        w = weak_password(name)
        if w:
            item["why"].append(f"密碼為弱值：{w}")

        # 綁 0.0.0.0 本身就是發現；後面幾項決定嚴重度
        findings.append(item)

    print()
    if not findings:
        print(f"  ✓ 敏感服務皆未綁 0.0.0.0（僅本機可連 {safe} 個）")
    for f in findings:
        print(f"  🔴 {f['name']}（{f['klass']}）主機埠 {f['port']} 綁 0.0.0.0")
        for w in f["why"]:
            print(f"       · {w}")

    if findings:
        print()
        print("  修法（**不要由檢核自動執行**）：")
        print("    1. compose 的 ports 由 \"5434:5432\" 改為 \"127.0.0.1:5434:5432\"")
        print("       → host 端工具連 localhost 不受影響，LAN 即不可見")
        print("    2. ⚠️ 重建 postgres 前必須先確認 volume 名稱（L43：那次重建")
        print("       掛到空殼 volume，整個資料庫看起來還在、其實是空的）")
        print("    3. 密碼輪換另案，需同步更新所有消費端")

    code = judge(findings)
    print()
    print(f"Status: [{'RED' if code >= 2 else 'GREEN'}]")
    return code


if __name__ == "__main__":
    sys.exit(main())
