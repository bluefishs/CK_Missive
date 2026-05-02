# -*- coding: utf-8 -*-
"""Crystal Flow tests — yaml_safe_editor + crystallizer + crystal_applier

Memory Wiki Phase 3 — 結晶 pipeline 安全閘測試。
"""
from __future__ import annotations

import pytest
from pathlib import Path


# ────────── yaml_safe_editor ──────────

def test_validate_yaml_ok():
    from app.services.memory.yaml_safe_editor import validate_yaml
    r = validate_yaml("foo: bar\nbaz: [1, 2, 3]\n")
    assert r.ok is True
    assert r.error is None


def test_validate_yaml_broken():
    from app.services.memory.yaml_safe_editor import validate_yaml
    # 明確的語法錯誤：未閉合 list + 缺冒號混用
    r = validate_yaml("foo: [unclosed\n  - invalid\n: value_no_key")
    assert r.ok is False
    assert r.error is not None


def test_add_synonym_group_new():
    from app.services.memory.yaml_safe_editor import add_synonym_group
    original = """# header comment
agency_synonyms:
  - ["桃園市政府", "桃市府"]
"""
    new_text, added = add_synonym_group(original, "agency_synonyms", ["花蓮縣政府", "花縣府"])
    assert added is True
    assert "花蓮縣政府" in new_text
    # 原註解保留
    assert "header comment" in new_text


def test_add_synonym_group_duplicate():
    from app.services.memory.yaml_safe_editor import add_synonym_group
    original = """agency_synonyms:
  - ["桃園市政府", "桃市府"]
"""
    _, added = add_synonym_group(original, "agency_synonyms", ["桃園市政府", "桃市府"])
    assert added is False  # 完全相同 group → no-op


def test_add_synonym_group_merge_overlap():
    """有交集的 group 應合併。"""
    from app.services.memory.yaml_safe_editor import add_synonym_group
    original = """agency_synonyms:
  - ["桃園市政府", "桃市府"]
"""
    new_text, added = add_synonym_group(original, "agency_synonyms", ["桃園市政府", "市府"])
    assert added is True
    # 應 merge，不應出現兩組
    assert new_text.count("桃園市政府") == 1
    assert "市府" in new_text


def test_add_intent_rule_new():
    from app.services.memory.yaml_safe_editor import add_intent_rule
    original = """rules:
  - name: existing
    pattern: "^hi$"
"""
    new_text, added = add_intent_rule(
        original, {"name": "new_rule", "pattern": "test"},
    )
    assert added is True
    assert "new_rule" in new_text
    assert "existing" in new_text  # 原規則保留


def test_add_intent_rule_duplicate_name():
    from app.services.memory.yaml_safe_editor import add_intent_rule
    original = """rules:
  - name: existing
    pattern: "^hi$"
"""
    _, added = add_intent_rule(original, {"name": "existing", "pattern": "new"})
    assert added is False  # 同名 → no-op


def test_diff_summary_truncates():
    from app.services.memory.yaml_safe_editor import diff_summary
    before = "\n".join(f"line{i}" for i in range(100))
    after = "\n".join(f"line{i}_mod" for i in range(100))
    summary = diff_summary(before, after, max_lines=10)
    assert "more lines" in summary


# ────────── Crystallizer ──────────

@pytest.fixture
def temp_phase3(tmp_path, monkeypatch):
    """重導所有路徑到 tmp。"""
    from app.services.memory import crystallizer as cs
    from app.services.memory import crystal_applier as ca

    patterns = tmp_path / "patterns"
    proposals = tmp_path / "proposals"
    crystals = tmp_path / "crystals"
    snapshots = tmp_path / "snapshots"
    synonyms = tmp_path / "synonyms.yaml"
    intent = tmp_path / "intent_rules.yaml"

    for d in (patterns, proposals, crystals, snapshots):
        d.mkdir(parents=True)

    synonyms.write_text(
        "# header\nagency_synonyms:\n  - [\"桃園市政府\", \"桃市府\"]\n",
        encoding="utf-8",
    )
    intent.write_text("rules:\n  - name: seed\n    pattern: test\n", encoding="utf-8")

    monkeypatch.setattr(cs, "PATTERNS_DIR", patterns)
    monkeypatch.setattr(cs, "PROPOSALS_DIR", proposals)
    monkeypatch.setattr(ca, "PROPOSALS_DIR", proposals)
    monkeypatch.setattr(ca, "CRYSTALS_DIR", crystals)
    monkeypatch.setattr(ca, "SNAPSHOTS_DIR", snapshots)
    monkeypatch.setattr(ca, "SYNONYMS_YAML", synonyms)
    monkeypatch.setattr(ca, "INTENT_RULES_YAML", intent)

    return {
        "patterns": patterns, "proposals": proposals, "crystals": crystals,
        "snapshots": snapshots, "synonyms": synonyms, "intent": intent,
    }


def _make_pattern_file(patterns_dir: Path, t_hash: str, hit: int, success: int, candidate: bool = True):
    """產生一個 pattern 檔案 fixture。"""
    (patterns_dir / f"pattern-{t_hash}.md").write_text(
        f"""---
type: agent_memory
memory_type: pattern
template_hash: {t_hash}
tool_sequence: ["search_documents"]
hit_count: {hit}
success_count: {success}
failure_count: {hit - success}
success_rate: {success / hit:.3f}
crystallization_candidate: {candidate}
---

# Pattern {t_hash}
""",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_crystallizer_scans_eligible_patterns(temp_phase3):
    """符合閾值的 pattern → 產 proposal。"""
    from app.services.memory.crystallizer import Crystallizer

    _make_pattern_file(temp_phase3["patterns"], "abc123", hit=10, success=10)

    crys = Crystallizer()
    proposals = await crys.scan_and_propose()

    assert len(proposals) == 1
    assert proposals[0].source_pattern == "abc123"
    # proposal 檔案確實寫入
    files = list(temp_phase3["proposals"].glob("crystal-*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "status: pending" in content
    assert "abc123" in content


@pytest.mark.asyncio
async def test_crystallizer_skips_below_threshold(temp_phase3):
    """hit 不足 → 不產 proposal。"""
    from app.services.memory.crystallizer import Crystallizer
    _make_pattern_file(temp_phase3["patterns"], "low", hit=3, success=3)  # 5 以下
    proposals = await Crystallizer().scan_and_propose()
    assert len(proposals) == 0


@pytest.mark.asyncio
async def test_crystallizer_skips_candidate_false(temp_phase3):
    from app.services.memory.crystallizer import Crystallizer
    _make_pattern_file(
        temp_phase3["patterns"], "notcand", hit=10, success=10, candidate=False,
    )
    proposals = await Crystallizer().scan_and_propose()
    assert len(proposals) == 0


@pytest.mark.asyncio
async def test_crystallizer_dedup_pending(temp_phase3):
    """同 pattern 已有 pending proposal → 不重複產。"""
    from app.services.memory.crystallizer import Crystallizer
    _make_pattern_file(temp_phase3["patterns"], "dupx", hit=10, success=10)
    p1 = await Crystallizer().scan_and_propose()
    p2 = await Crystallizer().scan_and_propose()
    assert len(p1) == 1
    assert len(p2) == 0


# ────────── CrystalApplier ──────────

@pytest.mark.asyncio
async def test_apply_synonym_proposal(temp_phase3):
    from app.services.memory.crystal_applier import CrystalApplier

    # 直接手寫 synonym proposal（繞過 crystallizer 此測試純測 applier）
    proposal_id = "crystal-synonym-test1"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        f"""---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: test-pat
proposed_by: agent
proposed_at: 2026-04-19
status: pending
---

# Proposal

## Payload

```yaml
category: agency_synonyms
group: ["新北市政府", "新北市府"]
```
""",
        encoding="utf-8",
    )

    applier = CrystalApplier()
    r = await applier.apply_proposal(proposal_id, approved_by="tester")

    assert r.ok is True
    assert r.crystal_id is not None
    assert r.snapshot_path is not None and r.snapshot_path.exists()
    # yaml 真的改了
    new_content = temp_phase3["synonyms"].read_text(encoding="utf-8")
    assert "新北市政府" in new_content
    # 原註解保留
    assert "header" in new_content
    # crystal record 寫了
    crystal_files = list(temp_phase3["crystals"].glob("crystal-*.md"))
    assert len(crystal_files) == 1


@pytest.mark.asyncio
async def test_apply_updates_proposal_status(temp_phase3):
    from app.services.memory.crystal_applier import CrystalApplier

    pid = "crystal-status-test"
    pp = temp_phase3["proposals"] / f"{pid}.md"
    pp.write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: xyz
status: pending
---

```yaml
category: agency_synonyms
group: ["台中市政府", "中市府"]
```
""",
        encoding="utf-8",
    )

    r = await CrystalApplier().apply_proposal(pid)
    assert r.ok is True
    # proposal 狀態改為 applied
    updated = pp.read_text(encoding="utf-8")
    assert "status: applied" in updated
    assert "applied_at:" in updated


@pytest.mark.asyncio
async def test_apply_rejects_non_pending(temp_phase3):
    from app.services.memory.crystal_applier import CrystalApplier
    pid = "crystal-already-applied"
    (temp_phase3["proposals"] / f"{pid}.md").write_text(
        """---
status: applied
target_file: synonyms.yaml
---
```yaml
category: agency_synonyms
group: ["a", "b"]
```
""",
        encoding="utf-8",
    )
    r = await CrystalApplier().apply_proposal(pid)
    assert r.ok is False
    assert "狀態" in r.error


@pytest.mark.asyncio
async def test_rollback_restores_snapshot(temp_phase3):
    """批准後 rollback → yaml 恢復原狀。"""
    from app.services.memory.crystal_applier import CrystalApplier

    original_content = temp_phase3["synonyms"].read_text(encoding="utf-8")

    # 建 proposal + apply
    pid = "crystal-rollback-test"
    (temp_phase3["proposals"] / f"{pid}.md").write_text(
        """---
proposal_kind: synonym
status: pending
target_file: synonyms.yaml
source_pattern: rb-test
---
```yaml
category: agency_synonyms
group: ["高雄市政府", "高市府"]
```
""",
        encoding="utf-8",
    )
    applier = CrystalApplier()
    apply_r = await applier.apply_proposal(pid)
    assert apply_r.ok is True
    assert "高雄市政府" in temp_phase3["synonyms"].read_text(encoding="utf-8")

    # rollback
    rb = await applier.rollback(apply_r.crystal_id)
    assert rb.ok is True
    restored = temp_phase3["synonyms"].read_text(encoding="utf-8")
    assert "高雄市政府" not in restored
    assert restored == original_content


@pytest.mark.asyncio
async def test_apply_missing_proposal(temp_phase3):
    from app.services.memory.crystal_applier import CrystalApplier
    r = await CrystalApplier().apply_proposal("nonexistent-id")
    assert r.ok is False
    assert "不存在" in r.error


# ────────── v6.3 體感型輸出：crystal apply → LINE 推送（ADR-0027）──────────


@pytest.mark.asyncio
async def test_growth_notify_skip_when_no_admin_id(temp_phase3, monkeypatch):
    """無 LINE_ADMIN_USER_ID env → silent skip，不影響 apply 結果。"""
    from app.services.memory.crystal_applier import CrystalApplier

    monkeypatch.delenv("LINE_ADMIN_USER_ID", raising=False)
    proposal_id = "crystal-no-line-id"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: noid-pat
status: pending
---

```yaml
category: agency_synonyms
group: ["臺中市政府", "中市府"]
```
""", encoding="utf-8",
    )
    r = await CrystalApplier().apply_proposal(proposal_id)
    assert r.ok is True  # apply 成功，notify silent skip


@pytest.mark.asyncio
async def test_growth_notify_skip_when_disabled(temp_phase3, monkeypatch):
    """LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉，apply 仍成功。"""
    from app.services.memory.crystal_applier import CrystalApplier

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-test-uid")
    monkeypatch.setenv("LINE_GROWTH_NOTIFY_ENABLED", "false")
    proposal_id = "crystal-disabled-test"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: dis-pat
status: pending
---

```yaml
category: agency_synonyms
group: ["臺南市政府", "南市府"]
```
""", encoding="utf-8",
    )
    r = await CrystalApplier().apply_proposal(proposal_id)
    assert r.ok is True


@pytest.mark.asyncio
async def test_growth_notify_calls_line_push(temp_phase3, monkeypatch):
    """有 LINE_ADMIN_USER_ID 且未顯式關閉 → 呼叫 line_bot.push_message。

    防 silent fail：apply 主流程不可被 notify 失敗影響（ADR-0028 一致性）。
    """
    from app.services.memory import crystal_applier as ca_mod
    from app.services.memory.crystal_applier import CrystalApplier

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-growth-test")
    monkeypatch.delenv("LINE_GROWTH_NOTIFY_ENABLED", raising=False)

    push_calls = []

    class FakeLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            push_calls.append({"user_id": user_id, "text": text})
            return True

    # patch LineBotService 避免真實 LINE API
    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = FakeLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    proposal_id = "crystal-notify-test"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: notify-pat-x
status: pending
---

```yaml
category: agency_synonyms
group: ["基隆市政府", "基市府"]
```
""", encoding="utf-8",
    )

    r = await CrystalApplier().apply_proposal(proposal_id)
    assert r.ok is True
    assert len(push_calls) == 1
    assert push_calls[0]["user_id"] == "U-growth-test"
    # 訊息含關鍵體感詞
    msg = push_calls[0]["text"]
    assert "我學到了" in msg
    assert r.crystal_id in msg
    assert "synonyms.yaml" in msg
    assert "notify-pat-x" in msg


@pytest.mark.asyncio
async def test_growth_notify_failure_does_not_break_apply(temp_phase3, monkeypatch):
    """notify 拋例外時，apply 主流程仍回 ok=True（best-effort，ADR-0028）。"""
    from app.services.memory.crystal_applier import CrystalApplier

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-fail-test")

    class BrokenLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            raise RuntimeError("simulated LINE API outage")

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = BrokenLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    proposal_id = "crystal-fail-test"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: fail-pat
status: pending
---

```yaml
category: agency_synonyms
group: ["新竹市政府", "竹市府"]
```
""", encoding="utf-8",
    )

    r = await CrystalApplier().apply_proposal(proposal_id)
    assert r.ok is True  # 主流程不破
    assert r.crystal_id is not None


# ────────── v6.6 Phase A3 5b：crystal rollback → LINE 通知 ──────────


@pytest.mark.asyncio
async def test_rollback_calls_line_notify(temp_phase3, monkeypatch):
    """rollback 成功 → LINE 推送「↩ 我撤回了一條規則」。"""
    from app.services.memory.crystal_applier import CrystalApplier

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-rollback-test")
    monkeypatch.delenv("LINE_GROWTH_NOTIFY_ENABLED", raising=False)

    push_calls = []

    class FakeLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            push_calls.append({"user_id": user_id, "text": text})
            return True

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = FakeLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    # 先 apply 一條 proposal
    proposal_id = "crystal-rollback-setup"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: rb-pat
status: pending
---

```yaml
category: agency_synonyms
group: ["嘉義市政府", "嘉市府"]
```
""", encoding="utf-8",
    )
    applier = CrystalApplier()
    apply_r = await applier.apply_proposal(proposal_id)
    assert apply_r.ok is True
    push_calls.clear()  # 清掉 apply 那次的 notify

    # rollback
    rb = await applier.rollback(apply_r.crystal_id)
    assert rb.ok is True
    assert len(push_calls) == 1
    assert push_calls[0]["user_id"] == "U-rollback-test"
    msg = push_calls[0]["text"]
    assert "我撤回了一條規則" in msg
    assert apply_r.crystal_id in msg


@pytest.mark.asyncio
async def test_rollback_notify_skip_when_no_admin_id(temp_phase3, monkeypatch):
    """無 LINE_ADMIN_USER_ID → silent skip，rollback 仍成功。"""
    from app.services.memory.crystal_applier import CrystalApplier

    monkeypatch.delenv("LINE_ADMIN_USER_ID", raising=False)

    proposal_id = "crystal-no-rb-id"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: noid-rb-pat
status: pending
---

```yaml
category: agency_synonyms
group: ["屏東縣政府", "屏縣府"]
```
""", encoding="utf-8",
    )
    applier = CrystalApplier()
    apply_r = await applier.apply_proposal(proposal_id)
    rb = await applier.rollback(apply_r.crystal_id)
    assert rb.ok is True


@pytest.mark.asyncio
async def test_rollback_notify_failure_does_not_break(temp_phase3, monkeypatch):
    """notify 拋例外時 rollback 主流程仍回 ok=True。"""
    from app.services.memory.crystal_applier import CrystalApplier

    monkeypatch.setenv("LINE_ADMIN_USER_ID", "U-rb-broken")

    class BrokenLineBot:
        @property
        def enabled(self):
            return True
        async def push_message(self, user_id, text):
            raise RuntimeError("LINE outage on rollback")

    import sys
    fake_module = type(sys)("app.services.integration.line_bot")
    fake_module.LineBotService = BrokenLineBot
    monkeypatch.setitem(sys.modules, "app.services.integration.line_bot", fake_module)

    proposal_id = "crystal-rb-fail"
    (temp_phase3["proposals"] / f"{proposal_id}.md").write_text(
        """---
type: memory_proposal
proposal_kind: synonym
target_file: synonyms.yaml
source_pattern: rb-fail-pat
status: pending
---

```yaml
category: agency_synonyms
group: ["花蓮縣政府新", "花新府"]
```
""", encoding="utf-8",
    )
    applier = CrystalApplier()
    apply_r = await applier.apply_proposal(proposal_id)
    rb = await applier.rollback(apply_r.crystal_id)
    assert rb.ok is True  # 不破
