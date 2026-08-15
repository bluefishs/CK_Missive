"""
自動安全掃描服務

定期掃描專案程式碼，偵測常見資安問題並寫入 DB。
整合至 scheduler.py 每日排程。

掃描項目：
1. 硬編碼密鑰偵測（API Key、Token、Password）
2. SQL 注入風險（字串拼接 SQL）
3. 不安全函數使用（eval、exec、pickle）
4. 缺少認證裝飾器的端點
5. pip/npm 依賴漏洞（audit）

Version: 1.0.0
Created: 2026-03-27
"""

import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.paths import BACKEND_DIR, FRONTEND_DIR  # v6.10 P1-E SSOT


@dataclass
class ScanFinding:
    """單一掃描發現"""
    title: str
    severity: str  # critical/high/medium/low/info
    owasp_category: str  # A01-A10
    file_path: str = ""
    line_number: int = 0
    code_snippet: str = ""
    remediation: str = ""
    cwe_id: str = ""


class SecurityScanner:
    """自動安全掃描器"""

    # 硬編碼密鑰模式
    _SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|secret|token|password|passwd)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{8,}["\']',
         "硬編碼密鑰", "critical", "A02", "CWE-798"),
        (r'(?i)(sk-[a-zA-Z0-9]{20,}|gsk_[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,})',
         "API Key 外洩", "critical", "A02", "CWE-798"),
    ]

    # SQL 注入模式
    _SQL_INJECTION_PATTERNS = [
        (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|DROP).*\{',
         "f-string SQL 拼接", "high", "A03", "CWE-89"),
        (r'\.format\(.*(?:SELECT|INSERT|UPDATE|DELETE)',
         ".format() SQL 拼接", "high", "A03", "CWE-89"),
        (r'%\s*\(.*(?:SELECT|INSERT|UPDATE|DELETE)',
         "% 格式化 SQL 拼接", "high", "A03", "CWE-89"),
    ]

    # 不安全函數
    _UNSAFE_FUNCTIONS = [
        (r'\beval\s*\(', "使用 eval()", "high", "A03", "CWE-95"),
        (r'\bexec\s*\(', "使用 exec()", "high", "A03", "CWE-95"),
        (r'\bpickle\.loads?\s*\(', "使用 pickle（反序列化風險）", "medium", "A08", "CWE-502"),
        (r'\byaml\.load\s*\([^)]*\)', "使用 yaml.load（應用 safe_load）", "medium", "A08", "CWE-502"),
    ]

    # 缺少認證
    _NO_AUTH_PATTERN = re.compile(
        r'@router\.(post|get|put|delete)\([^)]*\)\s*\n'
        r'async\s+def\s+\w+\([^)]*\)(?!.*(?:require_auth|optional_auth|Depends))',
        re.MULTILINE,
    )

    def __init__(self, db: AsyncSession, project_name: str = "CK_Missive"):
        self.db = db
        self.project_name = project_name

    async def run_full_scan(self) -> Dict[str, Any]:
        """執行完整安全掃描"""
        t0 = time.time()
        findings: List[ScanFinding] = []

        # 1. 程式碼掃描
        findings.extend(self._scan_code_patterns())

        # 2. 認證檢查
        findings.extend(self._scan_missing_auth())

        # 3. pip audit（背景、非阻塞）
        findings.extend(self._scan_pip_audit())

        # 4. 依賴檢查
        findings.extend(self._scan_env_secrets())

        duration = time.time() - t0

        # 統計
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        # 寫入 DB
        scan_id = await self._save_scan(findings, counts, duration)
        await self._save_issues(findings, scan_id)

        return {
            "scan_id": scan_id,
            "total_issues": len(findings),
            "duration_seconds": round(duration, 1),
            **counts,
        }

    # L72 fix (2026-06-12): rglob 不可遞迴進掛載資料目錄（backups/uploads/logs 內 Windows mount
    #   附件檔會 OSError [Errno 5] 中斷整個掃描 → security_scan 每次 crash silent dormant，L49.2 同族）。
    #   改 os.walk 容錯遍歷（onerror 跳過）+ 只掃源碼 app/ + prune 資料目錄。
    _SCAN_EXCLUDE_DIRS = {"backups", "uploads", "logs", "attachments", "__pycache__",
                          "node_modules", ".git", "alembic", "scripts", "tests"}

    def _scan_code_patterns(self) -> List[ScanFinding]:
        """掃描程式碼中的安全模式"""
        findings = []
        # 只掃源碼套件 app/（容器 /app/app；非掛載資料目錄）
        source_root = BACKEND_DIR / "app"
        if not source_root.exists():
            source_root = BACKEND_DIR
        py_files = []
        for dirpath, dirnames, filenames in os.walk(source_root, onerror=lambda e: None):
            # in-place prune 排除目錄（含掛載資料目錄，防 OSError 崩潰）
            dirnames[:] = [d for d in dirnames if d not in self._SCAN_EXCLUDE_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                if "test" in fn.lower() or "security_scanner" in fn:
                    continue
                py_files.append(Path(dirpath) / fn)

        all_patterns = self._SECRET_PATTERNS + self._SQL_INJECTION_PATTERNS + self._UNSAFE_FUNCTIONS

        for filepath in py_files:
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                for pattern, title, severity, owasp, cwe in all_patterns:
                    for match in re.finditer(pattern, content):
                        line_no = content[:match.start()].count("\n") + 1
                        snippet = content[max(0, match.start() - 20):match.end() + 20].strip()
                        # 排除 .env 讀取和註解
                        if "os.getenv" in snippet or "os.environ" in snippet:
                            continue
                        if snippet.lstrip().startswith("#"):
                            continue
                        # 2026-08-15：SQL 注入規則只看「f-string 裡有 SQL 關鍵字且有 {」，
                        # **分不出插進去的是「值」還是「表名／欄名」**。
                        # 而表名與欄名本來就無法用 bind 參數表達 —— 那不是漏寫參數，
                        # 是 SQL 的限制。實測 5 筆 high 全是假陽性：
                        #   documents/delete.py、user_management.py、main.py
                        #     → 表名來自程式碼內的**固定 list 常值**
                        #   tender_module/graph_case.py
                        #     → 先擋掉非白名單的 target_type 才用
                        #   repositories/admin_repository.py
                        #     → 已通過格式驗證＋白名單，且用雙引號包裹
                        # 收窄判準：**同一行有 bind 參數（:name）就不算注入** ——
                        # 值走參數化時，剩下的插值只可能是識別碼。
                        # 假陽性堆在資安看板上比沒有更糟：它會訓練人略過紅字，
                        # 於是真的注入出現時也不會有人看（本專案反覆記過的告警疲勞）。
                        if owasp == "A03" and "SQL" in title:
                            _ls = content.rfind(chr(10), 0, match.start()) + 1
                            _le = content.find(chr(10), match.end())
                            _line = content[_ls:_le if _le > 0 else None]
                            if re.search(r":[a-zA-Z_][a-zA-Z0-9_]*", _line):
                                continue
                        findings.append(ScanFinding(
                            title=title,
                            severity=severity,
                            owasp_category=owasp,
                            cwe_id=cwe,
                            file_path=str(filepath.relative_to(BACKEND_DIR)),
                            line_number=line_no,
                            code_snippet=snippet[:200],
                        ))
            except Exception:
                pass

        return findings

    def _scan_missing_auth(self) -> List[ScanFinding]:
        """偵測缺少認證裝飾器的端點"""
        findings = []
        endpoint_dir = BACKEND_DIR / "app" / "api" / "endpoints"
        for filepath in endpoint_dir.rglob("*.py"):
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                # 簡化檢查：找所有 @router 行，確認下一個函數有 Depends(require_auth)
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "@router." in line and "summary=" in line:
                        # 檢查接下來 5 行有沒有 require_auth 或 optional_auth
                        block = "\n".join(lines[i:i + 8])
                        # 所有認證方式：require_auth, optional_auth, get_current_user, verify_service_token
                        _AUTH_MARKERS = ("require_auth", "optional_auth", "get_current_user",
                                         "require_admin", "verify_service_token", "Depends(")
                        if any(m in block for m in _AUTH_MARKERS):
                            continue
                        # 排除 health/public/webhook 等合法公開端點
                        if any(kw in line.lower() for kw in ("health", "public", "webhook")):
                            continue
                            findings.append(ScanFinding(
                                title="端點缺少認證裝飾器",
                                severity="high",
                                owasp_category="A01",
                                cwe_id="CWE-862",
                                file_path=str(filepath.relative_to(BACKEND_DIR)),
                                line_number=i + 1,
                                code_snippet=line.strip()[:100],
                                remediation="加入 Depends(require_auth()) 參數",
                            ))
            except Exception:
                pass
        return findings

    def _scan_pip_audit(self) -> List[ScanFinding]:
        """pip-audit 依賴漏洞掃描（同步，有超時保護）"""
        findings = []
        try:
            # 2026-08-15：容器內 pip-audit 一直是**跑不起來**的 ——
            # 容器使用者沒有 home 目錄，pip-audit 建快取時
            # `PermissionError: [Errno 13] Permission denied: '/nonexistent'`，
            # 而下面的 `except Exception` 只 logger.debug 一行 →
            # 回空清單 → 掃描報「0 個依賴漏洞」。
            # **那不是乾淨，是從來沒掃過**，而兩者在報告上長得一模一樣。
            # 給它一個一定寫得進去的快取目錄。
            import os as _os
            _env = {**_os.environ}
            _env.setdefault("HOME", "/tmp")
            result = subprocess.run(
                ["pip-audit", "--format=json", "--desc", "--cache-dir", "/tmp/.pip-audit-cache"],
                capture_output=True, text=True, timeout=120,
                cwd=str(BACKEND_DIR), env=_env,
            )
            if result.returncode != 0 and result.stdout:
                import json
                vulns = json.loads(result.stdout)
                for vuln in vulns.get("dependencies", []):
                    for v in vuln.get("vulns", []):
                        findings.append(ScanFinding(
                            title=f"依賴漏洞: {vuln['name']} {vuln.get('version', '')}",
                            severity="high" if v.get("fix_versions") else "medium",
                            owasp_category="A06",
                            cwe_id=v.get("id", ""),
                            file_path="requirements.txt",
                            remediation=f"升級到 {', '.join(v.get('fix_versions', []))}",
                        ))
        # 依賴掃描沒跑成功時**必須出聲**（ADR-0028）。
        # 原本三個分支都是 logger.debug —— 於是「掃了沒問題」與
        # 「根本沒掃」在報告上完全一樣，而後者持續了不知道多久。
        except FileNotFoundError:
            logger.warning("依賴掃描未執行：pip-audit 未安裝 —— "
                           "本次結果**不包含**依賴漏洞，不得解讀為沒有漏洞")
        except subprocess.TimeoutExpired:
            logger.warning("依賴掃描未執行：pip-audit 逾時 —— 結果不含依賴漏洞")
        except Exception as e:
            logger.warning("依賴掃描未執行：%s —— 結果不含依賴漏洞", e)
        return findings

    def _scan_env_secrets(self) -> List[ScanFinding]:
        """檢查 .env 是否被追蹤"""
        findings = []
        env_file = BACKEND_DIR.parent / ".env"
        gitignore = BACKEND_DIR.parent / ".gitignore"

        if env_file.exists() and gitignore.exists():
            gitignore_content = gitignore.read_text(encoding="utf-8", errors="ignore")
            if ".env" not in gitignore_content:
                findings.append(ScanFinding(
                    title=".env 檔案未被 .gitignore 排除",
                    severity="critical",
                    owasp_category="A02",
                    cwe_id="CWE-200",
                    file_path=".gitignore",
                    remediation="在 .gitignore 加入 .env",
                ))
        return findings

    async def _save_scan(self, findings: List[ScanFinding], counts: dict, duration: float) -> int:
        """儲存掃描記錄"""
        from app.extended.models.security import SecurityScan, SecurityIssue
        from sqlalchemy import func as _func, select as _sel

        # 即時安全分數：基於所有 open issues（不只本次掃描）
        sev_q = await self.db.execute(
            _sel(SecurityIssue.severity, _func.count())
            .where(SecurityIssue.status == "open")
            .group_by(SecurityIssue.severity)
        )
        open_sev = dict(sev_q.all())
        score = max(0, 100
            - open_sev.get("critical", 0) * 25
            - open_sev.get("high", 0) * 10
            - open_sev.get("medium", 0) * 3
            - open_sev.get("low", 0) * 1)

        scan = SecurityScan(
            project_name=self.project_name,
            scan_type="full",
            status="completed",
            total_issues=len(findings),
            critical_count=counts.get("critical", 0),
            high_count=counts.get("high", 0),
            medium_count=counts.get("medium", 0),
            low_count=counts.get("low", 0),
            info_count=counts.get("info", 0),
            security_score=score,
            duration_seconds=duration,
            completed_at=datetime.now(),
            created_by="auto-scanner",
        )
        self.db.add(scan)
        await self.db.flush()
        await self.db.refresh(scan)
        return scan.id

    async def _save_issues(self, findings: List[ScanFinding], scan_id: int):
        """儲存發現的問題（去重：同檔同行不重複建立）"""
        from app.extended.models.security import SecurityIssue
        from sqlalchemy import select

        # 2026-08-15：路徑正規化。實測 open 的 67 筆裡有 18 筆用反斜線、
        # 49 筆用斜線，而**正規化後只有 18 個不重複路徑** —— 同一批問題
        # 被記了兩套，因為去重比對的是原始字串。掃描來源在 Windows 上
        # 走 os.path，在容器內走 posix，兩邊產生的 file_path 形狀不同。
        # 2026-08-15：**同一次掃描內**也要去重。
        # 原本只查 DB，而同批新增的列還沒 flush → 10 筆一模一樣的
        # 「依賴漏洞: aiohttp 3.13.3」（同檔、同 line 0、同 scan_id）全部通過檢查。
        seen_in_batch: set = set()
        for f in findings:
            if f.file_path:
                f.file_path = f.file_path.replace("\\", "/")
            batch_key = (f.file_path, f.line_number, f.title)
            if batch_key in seen_in_batch:
                continue
            seen_in_batch.add(batch_key)
            # 去重檢查
            existing = await self.db.execute(
                select(SecurityIssue).where(
                    SecurityIssue.file_path == f.file_path,
                    SecurityIssue.line_number == f.line_number,
                    SecurityIssue.title == f.title,
                    SecurityIssue.status != "resolved",
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue

            issue = SecurityIssue(
                project_name=self.project_name,
                scan_id=scan_id,
                title=f.title,
                severity=f.severity,
                owasp_category=f.owasp_category,
                cwe_id=f.cwe_id,
                file_path=f.file_path,
                line_number=f.line_number,
                code_snippet=f.code_snippet,
                remediation=f.remediation,
            )
            self.db.add(issue)

        # 2026-08-15：自動關閉「這次沒再掃到」的問題。
        #
        # 在此之前 open 的列只增不減 —— 程式碼修好了，那一列仍然 open。
        # 實測：本次掃描只找到 7 個問題，而看板上是 **61 個 open high**，
        # 十倍的差距全是歷史殘留。資安看板顯示一個假的大數字，
        # 比顯示 0 更糟：它讓人放棄看它。
        #
        # 只關閉「本次掃描涵蓋範圍內」的類型（同一組 owasp_category），
        # 避免把別的來源建立的問題誤關。
        scanned_keys = {(f.file_path, f.line_number, f.title) for f in findings}
        scanned_cats = {f.owasp_category for f in findings if f.owasp_category}
        if scanned_cats:
            rows = (await self.db.execute(
                select(SecurityIssue).where(
                    SecurityIssue.status == "open",
                    SecurityIssue.project_name == self.project_name,
                    SecurityIssue.owasp_category.in_(scanned_cats),
                )
            )).scalars().all()
            closed = 0
            for row in rows:
                key = ((row.file_path or "").replace("\\", "/"), row.line_number, row.title)
                if key not in scanned_keys:
                    row.status = "resolved"
                    closed += 1
            if closed:
                logger.info("自動關閉本次未再掃到的資安問題: %d 筆", closed)

        await self.db.commit()
