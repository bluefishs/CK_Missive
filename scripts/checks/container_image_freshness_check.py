"""Container image freshness check (L51.7.1 / fitness step 60, 2026-05-30)

L51 incident 揭發: docker cp 修法不持久，image 內檔過舊導致 5 防護層
silent disabled 36h。本 check 自動偵測 host 與 container 內檔 hash drift，
強迫 rebuild image 才能標 OK。

設計：
- 對 N 個 critical backend 檔做 md5 比對 host vs container
- 任一 drift → RED
- container 未起 → SKIP (informational)
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
]


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
        # 不相等**不必然是問題**（HEAD 可能已經往前走了而還沒部署），
        # 所以只印出來讓人自己判斷，不計入 problems。
        try:
            head = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(Path(__file__).resolve().parents[2]),
            ).stdout.strip()
        except Exception:
            head = ""
        note = f"  · runtime = {version} @ {commit}"
        if head:
            same = commit.replace("-dirty", "") == head
            note += f"   host HEAD = {head}   {'（同一份）' if same else '（HEAD 已前進，尚未部署）'}"
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
            print(f"  [SKIP] container {container} not running")
            return 0
    except Exception:
        print(f"  [SKIP] docker not available")
        return 0

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
