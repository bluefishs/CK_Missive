"""
AI 聯邦模組

OpenClaw 聯邦客戶端、服務發現、跨域委派。
"""

__all__ = [
    "FederationClient",
    "get_federation_client",
]


def __getattr__(name: str):
    if name in ("FederationClient", "get_federation_client"):
        from . import federation_client
        return getattr(federation_client, name)
    if name in ("delegate", "delegate_with_patterns", "delegate_auto"):
        from . import federation_delegation
        return getattr(federation_delegation, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
