"""
AI 雜項模組

語音轉文字、使用者偏好、技能掃描、Code Wiki、NemoClaw Agent。
"""

__all__ = [
    "NemoClawAgent",
    "VoiceTranscriber",
    "UserQueryTracker",
    "CodeWikiGenerator",
    "SkillSnapshotService",
    "DiffImpactAnalyzer",
]


def __getattr__(name: str):
    _map = {
        "NemoClawAgent": ("nemoclaw_agent", "NemoClawAgent"),
        "VoiceTranscriber": ("voice_transcriber", "VoiceTranscriber"),
        "get_voice_transcriber": ("voice_transcriber", "get_voice_transcriber"),
        "UserQueryTracker": ("user_query_tracker", "UserQueryTracker"),
        "get_query_tracker": ("user_query_tracker", "get_query_tracker"),
        "CodeWikiGenerator": ("code_wiki_generator", "CodeWikiGenerator"),
        "SkillSnapshotService": ("skill_snapshot_service", "SkillSnapshotService"),
        "DiffImpactAnalyzer": ("diff_impact_analyzer", "DiffImpactAnalyzer"),
        "scan_skills": ("skill_scanner", "scan_skills"),
    }
    if name in _map:
        mod_name, attr = _map[name]
        import importlib
        mod = importlib.import_module(f".{mod_name}", __name__)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
