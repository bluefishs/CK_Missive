"""
AI 領域查詢模組

PM/ERP 查詢、數位分身、晨報、跨域關聯。
"""

__all__ = [
    "PMQueryService",
    "ERPQueryService",
    "DigitalTwinService",
    "MorningReportService",
    "DispatchProgressSynthesizer",
    "CaseFlowTracker",
    "CrossDomainLinker",
    "CrossDomainMatchEngine",
]


def __getattr__(name: str):
    _map = {
        "PMQueryService": ("pm_query_service", "PMQueryService"),
        "ERPQueryService": ("erp_query_service", "ERPQueryService"),
        "DigitalTwinService": ("digital_twin_service", "DigitalTwinService"),
        "MorningReportService": ("morning_report_service", "MorningReportService"),
        "DispatchProgressSynthesizer": ("dispatch_progress_synthesizer", "DispatchProgressSynthesizer"),
        "CaseFlowTracker": ("case_flow_tracker", "CaseFlowTracker"),
        "CrossDomainLinker": ("cross_domain_linker", "CrossDomainLinker"),
        "CrossDomainMatchEngine": ("cross_domain_matcher", "CrossDomainMatchEngine"),
        "CrossDomainContributionService": ("cross_domain_contribution_service", "CrossDomainContributionService"),
    }
    if name in _map:
        mod_name, attr = _map[name]
        import importlib
        mod = importlib.import_module(f".{mod_name}", __name__)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
