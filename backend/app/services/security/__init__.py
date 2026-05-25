"""Security bounded context (DDD Wave 9, 2026-05-05).

Houses OWASP scanning + future security primitives (rate-limit policies,
PII masks, threat tracker integration).

Public API:
    .scanner — SecurityScanner / ScanFinding
"""
from .scanner import SecurityScanner, ScanFinding  # noqa: F401
