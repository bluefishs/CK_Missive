"""
測試 scripts/checks/schema_lazy_load_guard.py 能偵測 lazy-load 風險
"""
import sys
from pathlib import Path

# 加入 scripts 路徑
SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts" / "checks"
sys.path.insert(0, str(SCRIPTS_DIR))

from schema_lazy_load_guard import check_file  # type: ignore


def test_detects_getattr_aliases(tmp_path):
    bad = tmp_path / "bad_schema.py"
    bad.write_text(
        '''
class UserResponse:
    @classmethod
    def model_validate(cls, obj):
        aliases = getattr(obj, 'aliases', None) or []
        return cls()
''',
        encoding="utf-8",
    )
    issues = check_file(bad)
    assert len(issues) == 1
    assert issues[0][0] >= 4  # getattr line
    assert "aliases" in issues[0][1]
    assert "lazy-load" in issues[0][1]


def test_safe_dict_get_pattern_passes(tmp_path):
    good = tmp_path / "good_schema.py"
    good.write_text(
        '''
class UserResponse:
    @classmethod
    def model_validate(cls, obj):
        aliases = obj.__dict__.get('aliases') or []
        return cls()
''',
        encoding="utf-8",
    )
    issues = check_file(good)
    assert issues == []


def test_unrelated_getattr_is_ignored(tmp_path):
    good = tmp_path / "unrelated.py"
    good.write_text(
        '''
value = getattr(obj, 'some_non_relationship_field', 'default')
''',
        encoding="utf-8",
    )
    issues = check_file(good)
    assert issues == []


def test_actual_schemas_dir_is_clean():
    """實戰：當前 backend/app/schemas/ 不應有任何 lazy-load 風險"""
    schemas_dir = Path(__file__).resolve().parents[2] / "app" / "schemas"
    assert schemas_dir.exists()
    total = 0
    for py in schemas_dir.rglob("*.py"):
        total += len(check_file(py))
    assert total == 0, f"schemas 目錄發現 {total} 個 lazy-load 風險"
