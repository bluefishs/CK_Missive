# Testing Requirements

## Minimum Test Coverage: 80%

Test Types (ALL required):
1. **Unit Tests** - Individual functions, utilities, components
2. **Integration Tests** - API endpoints, database operations
3. **E2E Tests** - Critical user flows (Playwright)

## Test-Driven Development

MANDATORY workflow:
1. Write test first (RED)
2. Run test - it should FAIL
3. Write minimal implementation (GREEN)
4. Run test - it should PASS
5. Refactor (IMPROVE)
6. Verify coverage (80%+)

## Troubleshooting Test Failures

1. Use **tdd-guide** agent
2. Check test isolation
3. Verify mocks are correct
4. Fix implementation, not tests (unless tests are wrong)

## Agent Support

- **tdd-guide** - Use PROACTIVELY for new features, enforces write-tests-first
- **e2e-runner** - Playwright E2E testing specialist

## 負向測試的記憶體邊界（2026-09-08 主機硬當後立規，L150）

- **禁用「刪 dunder 再呼叫內建協定」**：`del m.__iter__`／`del m.__len__` 之後 `set(m)`／`list(m)`／`len(m)` 會讓 MagicMock 無限迭代（單一 python.exe 長到 151 GB、整台主機硬當）。要驗 `TypeError` 用 `MagicMock(spec=[...])` 或 `m.__iter__ = Mock(side_effect=TypeError)`。
- **一次性執行的 python**（對話中、腳本中）必須帶 `PYGUARD_MAX_GB=2`（或更小）與真正的逾時：`subprocess.run(timeout=)`、PowerShell `Wait-Process -Timeout` + `Stop-Process`。**Git Bash 的 `timeout` 在 Windows 殺不掉子 python，不算逾時。**
- **背景執行**前先設 `PYGUARD_MAX_GB`，結束時檢查輸出檔有沒有 `MemoryError`。
- 主機層規則與事件單：`~/.claude/rules/memory-safety.md`、`docs/incidents/2026-09-08-host-oom-mock-negative-test.md`。
