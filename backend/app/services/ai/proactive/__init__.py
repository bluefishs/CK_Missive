"""
AI 主動觸發模組

截止日提醒、預算超限、主動推薦。
"""

__all__ = [
    "ProactiveRecommender",
    "ProactiveTriggerService",
    "ERPTriggerScanner",
]


def __getattr__(name: str):
    if name == "ProactiveRecommender":
        from .proactive_recommender import ProactiveRecommender
        return ProactiveRecommender
    if name == "ProactiveTriggerService":
        from .proactive_triggers import ProactiveTriggerService
        return ProactiveTriggerService
    if name == "ERPTriggerScanner":
        from .proactive_triggers_erp import ERPTriggerScanner
        return ERPTriggerScanner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
