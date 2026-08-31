"""Container image freshness check (L51.7.1 / fitness step 47, 2026-05-30)

⚠️ 2026-08-30：容器沒跑／docker 不可用時**原本 `return 0`** ⇒ weekly
顯示**綠燈，而它什麼都沒驗**。那是「無法驗證」被記成「驗過了沒問題」。

runner 有三態（`0=GREEN / 1=YELLOW / 2+=RED`），而這個情境正是 YELLOW：
**「未驗」不是「沒有 drift」，也不是「壞了」。** 已改回 1。

（由 CK_AaaP 指出他們的快照守門在服務不起來時只黃字不擋而查出。
本 repo 19 支依賴外部服務的稽核裡，只有這一支的**退出碼來源函式**
在 except 裡 return 0 —— 另外四支是輔助函式的回傳值，不是退出碼。）


L51 incident 揭發: docker cp 修法不持久，image 內檔過舊導致 5 防護層
silent disabled 36h。本 check 自動偵測 host 與 container 內檔 hash drift，
強迫 rebuild image 才能標 OK。

設計：
- 對 N 個 critical backend 檔做 md5 比對 host vs container
- 任一 drift → RED
- container 未起 → **YELLOW（exit 1）**，不是 SKIP／不是綠
  （2026-08-30 改；原本是 `return 0` ⇒ 綠燈而什麼都沒驗）
- 預設不入 strict fail（dev 環境可能沒 docker）

Usage:
  python scripts/checks/container_image_freshness_check.py
  python scripts/checks/container_image_freshness_check.py --strict
  python scripts/checks/container_image_freshness_check.py --container=ck_missive_backend
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
# 2026-08-15：weekly 跑在 host（cp950），而 ✅🔴⚠ 這些符號 cp950 編不出來。
# 崩潰是**路徑相依**的 —— 平常走 GREEN 分支沒事，偏偏在要報問題的那一刻崩掉，
# 而那時看到的是 UnicodeEncodeError 不是它本來要講的事。同 L49.8（.ps1 的 BOM）家族。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ⚠️ 這是一份**明列**的清單，不是掃出來的 —— 所以新加的關鍵檔**不會自己進來**。
#
# 2026-08-31 實測到這份清單兩個相反方向的失效，同一天、同一個人（我）造成：
#   · `app/core/scheduler.py` 改了但沒 docker cp ⇒ **被抓到**（清單裡有它）
#   · `app/services/ai/misc/kb_embedding.py` docker cp 進去了但映像是舊的
#     ⇒ **完全隱形**（清單裡沒有它）
# 後者更危險：容器現在是對的，而下一次 `--force-recreate` 會靜靜退回壞的版本，
# 那時沒有任何訊號會說「你剛剛失去了一個修法」。
#
# ⇒ 加關鍵檔時要一併加進這裡。判準是：**這個檔壞掉時，使用者看得到什麼？**
#   `kb_embedding.py` 壞掉＝知識庫搜尋全部 500（2026-08-31 實證，且是從未成功過）。
CRITICAL_FILES = [
    "main.py",
    "app/core/scheduler.py",
    "app/core/memory_wiki_metrics.py",
    "app/services/contracts/adapters/messaging_default.py",
    "app/services/tender/business_recommendation.py",
    "app/api/endpoints/auth/common.py",
    "app/api/endpoints/auth/profile.py",
    "app/api/endpoints/tender_module/search.py",
    "app/api/endpoints/tender_module/enrichment_review.py",
    "app/services/tender/enrichment.py",
    "app/services/tender/metrics.py",
    # 2026-08-31：知識庫檢索鏈。壞掉的症狀是搜尋全部 500，而它曾經壞了很久沒人知道。
    "app/services/ai/misc/kb_embedding.py",
    "app/api/endpoints/knowledge_base.py",
]


def container_vs_image_drift(container: str, image: str = "ck-missive-backend:production"):
    """執行中的容器與它的映像，哪些 .py 不一樣（＝容器一被重建就會失去的東西）。

    ## 這與本檔原有的檢查是**兩個不同的問題**

    | 問題 | 比誰 | 回答什麼 |
    |---|---|---|
    | 原有 `CRITICAL_FILES` | host vs 容器 | 容器跑的是不是 repo 現在的碼 |
    | 本函式 | **容器 vs 映像** | **容器被重建時會失去哪些修法** |

    重啟指引問的是後者，而它原本只能靠人手抄一份清單。
    2026-08-31 實測：手抄的列了 14 個，真實是 25 個 —— 差的 11 個沒有人會發現。

    ## 為什麼掃整棵樹而不是清單

    清單有兩個病：漏了不會有人知道（沒有訊號），而且它會跟著程式漂移。
    整棵樹只要**兩次 docker 呼叫**（各一次 `find | md5sum`），
    比逐檔比對的 N×2 次快兩個數量級，而且不可能漏。

    Returns:
        (drift_list, error) —— 取不到時 drift_list 為 None，**呼叫端不得當成 0**。
    """
    cmd = "find /app/app -name '*.py' -type f -exec md5sum {} + | sort -k2"

    def _collect(argv):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                return None, (r.stderr or "").strip()[:160]
            out = {}
            for line in r.stdout.splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    out[parts[1].strip()] = parts[0]
            return out, None
        except Exception as exc:  # noqa: BLE001 — 回傳 None 讓呼叫端知道「未驗」
            return None, f"{type(exc).__name__}: {exc}"[:160]

    cont, err = _collect(["docker", "exec", container, "sh", "-c", cmd])
    if cont is None:
        return None, f"讀容器失敗：{err}"
    img, err = _collect(["docker", "run", "--rm", "--entrypoint", "sh", image, "-c", cmd])
    if img is None:
        return None, f"讀映像失敗：{err}"

    drift = sorted(
        p for p in set(cont) | set(img)
        if cont.get(p) != img.get(p)
    )
    return drift, None


def _deploy_gap(root: str, image_commit: str):
    """映像的建置點距離現在的 HEAD 有多遠：(落後幾個 commit, 建置點距今幾小時)。

    任一項取不到就回 None —— **不可判定不等於沒問題**，呼叫端不得當成 0。
    """
    behind = age_h = None
    try:
        r = subprocess.run(
            ["git", "rev-list", "--count", f"{image_commit}..HEAD"],
            capture_output=True, text=True, timeout=10, cwd=root,
        )
        if r.returncode == 0 and r.stdout.strip().isdigit():
            behind = int(r.stdout.strip())
    except Exception:
        pass
    try:
        import datetime as _dt
        r = subprocess.run(
            ["git", "log", "-1", "--format=%ct", image_commit],
            capture_output=True, text=True, timeout=10, cwd=root,
        )
        if r.returncode == 0 and r.stdout.strip().isdigit():
            age_h = (_dt.datetime.now().timestamp() - int(r.stdout.strip())) / 3600
    except Exception:
        pass
    return behind, age_h


def host_md5(path: Path) -> str:
    """計算 host 檔案 md5（前 8 chars）"""
    if not path.exists():
        return ""
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def container_md5(container: str, path: str) -> str:
    """從 container 內取檔 md5（直接 read 內容算 md5，避 docker exec md5sum 路徑轉換）"""
    try:
        # cat 比 md5sum 更可靠（不會被 git bash 路徑轉換影響）
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"  # git bash protection
        result = subprocess.run(
            ["docker", "exec", container, "cat", path],
            capture_output=True, timeout=10, env=env,
        )
        if result.returncode != 0:
            return ""
        h = hashlib.md5()
        h.update(result.stdout)
        return h.hexdigest()
    except Exception:
        return ""


def check_build_identity(container: str) -> tuple[int, list[str]]:
    """第二個維度：內容對齊 ≠ 身分可辨識。

    2026-08-27 加。這支檢核原本只問「容器裡的檔案跟 host 一不一樣」，
    而它今天回全綠 —— 11/11 match、0 drift。同一時刻實測容器內：

        CK_BUILD_COMMIT=unknown
        CK_BUILD_VERSION=unknown
        /api/health/detailed → build={"version":"unknown","commit":"unknown"}

    ⇒ **內容確實對齊，但沒有人說得出線上跑的是哪一個 commit。**
    那正是 2026-08-21 建立 `build_info.py` 要解決的問題，它已經悄悄回來了。

    根因不是有人忘記，是**流程本身漏了那一步**：
    `scripts/deploy/build-args.sh` 只在它自己的註解裡被提到，
    `CONTAINER_DEPLOYMENT_SOP.md` §2.1 的 build 指令沒有 source 它，
    也沒有任何檢核在看這個欄位 ⇒ 照 SOP 做就一定會得到 unknown。

    判 YELLOW 不判 RED：系統是好的、資料是好的，只是「出事時說不出跑的是哪一版」。
    它會一直亮到下次帶 build-args 重建映像為止 —— 那是真的還沒解決，不是假紅。
    """
    problems: list[str] = []
    env = {}
    try:
        r = subprocess.run(
            ["docker", "exec", container, "printenv"],
            capture_output=True, text=True, timeout=10,
        )
        for line in r.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    except Exception as exc:
        # 讀不到就說讀不到，不要當成通過
        return 1, [f"無法讀取容器環境變數：{exc}"]

    commit = env.get("CK_BUILD_COMMIT", "")
    version = env.get("CK_BUILD_VERSION", "")

    if not commit or commit == "unknown":
        problems.append("CK_BUILD_COMMIT=unknown —— 線上這個容器無法對應到任何 commit")
    if not version or version == "unknown":
        problems.append("CK_BUILD_VERSION=unknown —— 線上這個容器無法對應到任何語意版號")

    if not problems:
        # 有值就再問一句：它跟現在的 HEAD 是不是同一個？
        #
        # ⚠️ 2026-08-30 修正：原本這裡的理由是「不相等不必然是問題
        # （HEAD 可能已經往前走了而還沒部署），所以只印出來讓人自己判斷」。
        # 那對「落後 1 個 commit」是對的 —— **但它沒有區分 1 個和 38 個**。
        #
        # 實測當日：映像停在前一天，**落後 38 個 commit**，而這支檢核每天都在跑、
        # 每天都印那一行提示，**從來不會紅**。當日 9 項新機制有 5 項因此
        # 停在原始碼層（含 secret guard 與 KB 每日同步），而是 owner 問起才發現。
        # ⇒ **訊號存在、每天在跑、印得出來，就是永遠不會出聲。**
        #
        # 門檻的取法：開發中落後幾個 commit 是常態，不該吵；
        # 但「一整天的工作沒有部署」值得知道，「三天沒部署」該出聲。
        try:
            root = str(Path(__file__).resolve().parents[2])
            head = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5, cwd=root,
            ).stdout.strip()
        except Exception:
            head = ""
        note = f"  · runtime = {version} @ {commit}"
        if head:
            base = commit.replace("-dirty", "")
            same = base == head
            note += f"   host HEAD = {head}   {'（同一份）' if same else '（HEAD 已前進，尚未部署）'}"
            print(note)
            if not same:
                behind, age_h = _deploy_gap(root, base)
                if behind is not None:
                    print(f"       落後 {behind} 個 commit"
                          + (f"，映像建置點距今 {age_h:.0f} 小時" if age_h is not None else ""))
                    if behind >= 50 or (age_h is not None and age_h >= 72):
                        problems.append(
                            f"映像落後 {behind} 個 commit"
                            + (f"／{age_h:.0f} 小時" if age_h is not None else "")
                            + " —— 已提交的修法沒有在跑"
                        )
                    elif behind >= 20 or (age_h is not None and age_h >= 24):
                        print("       ⚠️ 超過一天份的工作尚未部署（未判紅，但值得看一眼）")
        else:
            print(note)

    return (1 if problems else 0), problems


def main(strict: bool = False, container: str = "ck_missive_backend") -> int:
    print(f"=== Container Image Freshness Check (L51.7.1 / fitness step 60) ===")
    print(f"  container: {container}")

    # 確認 container 在跑
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0 or "true" not in result.stdout:
            print(f"  [YELLOW] container {container} 沒在跑 —— **未驗**，不是「沒有 drift」")
            return 1
    except Exception:
        print("  [YELLOW] docker 不可用 —— **未驗**，不是「沒有 drift」")
        return 1

    print()
    drift_count = 0
    missing_count = 0
    match_count = 0

    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"

    for rel_path in CRITICAL_FILES:
        host_path = backend_dir / rel_path
        cont_path = f"/app/{rel_path}"

        host_hash = host_md5(host_path)
        cont_hash = container_md5(container, cont_path)

        if not host_hash:
            print(f"  ?  {rel_path}: host file missing")
            missing_count += 1
        elif not cont_hash:
            print(f"  ?  {rel_path}: container file missing or unreadable")
            missing_count += 1
        elif host_hash == cont_hash:
            print(f"  ✓  {rel_path}")
            match_count += 1
        else:
            print(f"  ✗  {rel_path}  DRIFT (host={host_hash[:10]} cont={cont_hash[:10]})")
            drift_count += 1

    print()
    print(f"Summary: {match_count} match, {drift_count} drift, {missing_count} missing")

    # 容器 vs 映像（重建後會失去什麼）—— 與上面那組是不同的問題，見函式說明。
    print()
    print("--- 容器 vs 映像：一旦容器被重建就會失去的檔 ---")
    only_in_container, err = container_vs_image_drift(container)
    if only_in_container is None:
        print(f"  [YELLOW] 無法判定（{err}）—— **未驗**，不是「沒有差異」")
    elif not only_in_container:
        print("  ✓ 容器與映像一致 —— 怎麼重啟都安全")
    else:
        print(f"  ⚠ {len(only_in_container)} 個檔只存在於執行中的容器：")
        for p in only_in_container[:40]:
            print(f"      {p}")
        if len(only_in_container) > 40:
            print(f"      …另 {len(only_in_container) - 40} 個")
        print("    → `docker restart` 與機器重開會保留；"
              "`--force-recreate`／`down` 會全部消失。正解是先跑一次部署。")

    if drift_count > 0:
        print()
        print("⚠ Image vs Source drift detected (L51 incident 同型)")
        print("  原因可能: docker cp 修法未跟 rebuild image")
        print("  修法: docker compose -f docker-compose.production.yml build backend")
        print("        docker compose -f docker-compose.production.yml up -d backend")
        # 2026-08-11：原本 `if strict: return 1`，不帶旗標就 return 0 ——
        # 於是它印著「drift detected」卻回綠燈（L83 家族第三支；08-10 才在
        # powershell_bom_audit 修過同型）。呼叫端一律不傳旗標，所以實際上
        # 這支從來沒有讓任何 runner 變色過。
        #
        # 判 YELLOW（1）而非 RED：程式改了還沒 rebuild 是**開發中的正常狀態**，
        # 但如果到了週日 02:30 weekly 執行時還有 drift，那就是真的忘了部署
        # （L79「寫好+測試綠 ≠ 在系統裡」），該有人看一眼。
        return 1
    if match_count >= len(CRITICAL_FILES) - 1:  # 容忍 1 個 missing
        print("✅ Image 與 source 對齊")

    # ── 第二個維度：身分綁定（2026-08-27 加，理由見 check_build_identity docstring）
    print()
    print("--- build 身分綁定 ---")
    ident_rc, ident_problems = check_build_identity(container)
    if ident_problems:
        for msg in ident_problems:
            print(f"  ✗  {msg}")
        print()
        print("⚠ 內容對齊了，但線上跑的是哪一份說不出來")
        print("  修法（build 時帶身分，不是事後補文件）:")
        print("    source scripts/deploy/build-args.sh")
        print("    docker compose -f docker-compose.production.yml build backend")
        print("    docker compose -f docker-compose.production.yml up -d backend")
        return 1
    print("✅ build 身分可辨識")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--container", default="ck_missive_backend")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict, container=args.container))
