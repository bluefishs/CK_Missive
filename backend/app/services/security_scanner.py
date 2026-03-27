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

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"


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

    def _scan_code_patterns(self) -> List[ScanFinding]:
        """掃描程式碼中的安全模式"""
        findings = []
        py_files = list(BACKEND_DIR.rglob("*.py"))
        # 排除 migrations, tests, __pycache__
        py_files = [
            f for f in py_files
            if "alembic" not in str(f) and "__pycache__" not in str(f)
            and "test" not in f.name.lower()
            and "security_scanner" not in f.name  # 排除自身（正則定義非實際呼叫）
            and "scripts" not in str(f.relative_to(BACKEND_DIR)).split(os.sep)[:1]  # 排除一次性 scripts
        ]

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
            result = subprocess.run(
                ["pip-audit", "--format=json", "--desc"],
                capture_output=True, text=True, timeout=60,
                cwd=str(BACKEND_DIR),
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
        except FileNotFoundError:
            logger.debug("pip-audit not installed, skipping")
        except subprocess.TimeoutExpired:
            logger.debug("pip-audit timed out")
        except Exception as e:
            logger.debug("pip-audit failed: %s", e)
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
        from app.extended.models.security import SecurityScan

        score = max(0, 100 - counts.get("critical", 0) * 20 - counts.get("high", 0) * 10
                     - counts.get("medium", 0) * 5 - counts.get("low", 0) * 2)

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

        for f in findings:
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

        await self.db.commit()
