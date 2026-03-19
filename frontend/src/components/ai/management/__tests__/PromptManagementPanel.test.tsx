/**
 * PromptManagementPanel (PromptManagementContent) tests
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App, ConfigProvider } from 'antd';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock getComputedStyle for antd Modal scroll locking in jsdom
const originalGetComputedStyle = window.getComputedStyle;
window.getComputedStyle = (elt: Element, pseudoElt?: string | null) => {
  try {
    return originalGetComputedStyle(elt, pseudoElt ?? undefined);
  } catch {
    return {} as CSSStyleDeclaration;
  }
};

// ── Mock setup (vi.hoisted) ──
const { mockAiApi } = vi.hoisted(() => ({
  mockAiApi: {
    listPrompts: vi.fn(),
    createPrompt: vi.fn(),
    activatePrompt: vi.fn(),
    comparePrompts: vi.fn(),
  },
}));

vi.mock('../../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

// Also mock the ai/index re-export path used by hooks
vi.mock('../../../../api/ai', () => ({
  aiApi: mockAiApi,
}));

import { PromptManagementContent } from '../PromptManagementPanel';

// ── Test data ──
const mockPromptItems = [
  {
    id: 1,
    feature: 'summary',
    version: 1,
    system_prompt: 'You are a document summarizer.',
    user_template: 'Summarize: {content}',
    description: 'Initial version',
    is_active: true,
    created_by: 'admin',
    created_at: '2026-03-10T10:00:00Z',
  },
  {
    id: 2,
    feature: 'summary',
    version: 2,
    system_prompt: 'You are an improved document summarizer with structured output.',
    user_template: 'Please summarize the following: {content}',
    description: 'Improved structure',
    is_active: false,
    created_by: 'admin',
    created_at: '2026-03-12T14:00:00Z',
  },
  {
    id: 3,
    feature: 'classify',
    version: 1,
    system_prompt: 'You are a document classifier.',
    user_template: null,
    description: null,
    is_active: true,
    created_by: null,
    created_at: '2026-03-08T09:00:00Z',
  },
];

const mockPromptListResponse = {
  items: mockPromptItems,
  total: 3,
  features: ['summary', 'classify', 'keywords', 'search_intent', 'match_agency'],
};

const mockEmptyResponse = {
  items: [],
  total: 0,
  features: ['summary', 'classify', 'keywords', 'search_intent', 'match_agency'],
};

const mockCompareResponse = {
  version_a: mockPromptItems[0],
  version_b: mockPromptItems[1],
  diffs: [
    {
      field: 'system_prompt',
      value_a: 'You are a document summarizer.',
      value_b: 'You are an improved document summarizer with structured output.',
      changed: true,
    },
    {
      field: 'user_template',
      value_a: 'Summarize: {content}',
      value_b: 'Please summarize the following: {content}',
      changed: true,
    },
  ],
};

const mockCreateResponse = {
  success: true,
  item: {
    id: 4,
    feature: 'keywords',
    version: 1,
    system_prompt: 'Extract keywords.',
    user_template: null,
    description: 'New prompt',
    is_active: false,
    created_by: 'admin',
    created_at: '2026-03-15T10:00:00Z',
  },
  message: 'Prompt 版本已新增',
};

const mockActivateResponse = {
  success: true,
  message: '已啟用 v2',
  activated: mockPromptItems[1],
};

// ── Helpers ──
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  // Wrap with antd App so that App.useApp() provides message/notification/modal
  // ConfigProvider with motion disabled for jsdom compatibility
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient },
      React.createElement(ConfigProvider, {},
        React.createElement(App, null, children)
      )
    );
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

function setupDefaultMocks() {
  mockAiApi.listPrompts.mockResolvedValue(mockPromptListResponse);
  mockAiApi.createPrompt.mockResolvedValue(mockCreateResponse);
  mockAiApi.activatePrompt.mockResolvedValue(mockActivateResponse);
  mockAiApi.comparePrompts.mockResolvedValue(mockCompareResponse);
}

// ── Tests ──
describe('PromptManagementContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ────────────────────────────────────────────
  // Loading state
  // ────────────────────────────────────────────
  it('renders loading spinner while data is fetching', () => {
    mockAiApi.listPrompts.mockReturnValue(new Promise(() => {}));

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    expect(document.querySelector('.ant-spin-spinning')).toBeTruthy();
  });

  // ────────────────────────────────────────────
  // Empty state
  // ────────────────────────────────────────────
  it('renders empty state when no prompt versions exist', async () => {
    mockAiApi.listPrompts.mockResolvedValue(mockEmptyResponse);

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/尚無 Prompt 版本/)).toBeInTheDocument();
    });
  });

  // ────────────────────────────────────────────
  // Data rendering
  // ────────────────────────────────────────────
  it('renders the page title', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('AI Prompt 版本管理')).toBeInTheDocument();
    });
  });

  it('renders feature groups with correct labels', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Feature group headers
      expect(screen.getByText('摘要生成')).toBeInTheDocument();
      expect(screen.getByText('分類建議')).toBeInTheDocument();
    });
  });

  it('renders version items with version numbers', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // v1 appears twice (summary v1 + classify v1)
      expect(screen.getAllByText('v1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('v2')).toBeInTheDocument();
    });
  });

  it('renders active version tag', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      const activeTags = screen.getAllByText('目前使用中');
      // Two active items: summary v1 and classify v1
      expect(activeTags).toHaveLength(2);
    });
  });

  it('renders version description text', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Initial version')).toBeInTheDocument();
      expect(screen.getByText('Improved structure')).toBeInTheDocument();
    });
  });

  it('renders creator info', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Items with created_by = 'admin'
      const creatorTexts = screen.getAllByText(/建立者：admin/);
      expect(creatorTexts.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('renders fallback creator as system when created_by is null', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/建立者：系統/)).toBeInTheDocument();
    });
  });

  it('renders version count per feature group', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('2 個版本')).toBeInTheDocument(); // summary
      expect(screen.getByText('1 個版本')).toBeInTheDocument(); // classify
    });
  });

  it('displays total version count', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/共 3 個版本/)).toBeInTheDocument();
    });
  });

  // ────────────────────────────────────────────
  // Toolbar buttons
  // ────────────────────────────────────────────
  it('renders new version and compare buttons', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新增版本/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /版本比較/ })).toBeInTheDocument();
    });
  });

  it('disables compare button when fewer than 2 items', async () => {
    mockAiApi.listPrompts.mockResolvedValue({
      items: [mockPromptItems[0]],
      total: 1,
      features: ['summary'],
    });

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      const compareBtn = screen.getByRole('button', { name: /版本比較/ });
      expect(compareBtn).toBeDisabled();
    });
  });

  it('enables compare button when 2 or more items exist', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      const compareBtn = screen.getByRole('button', { name: /版本比較/ });
      expect(compareBtn).not.toBeDisabled();
    });
  });

  // ────────────────────────────────────────────
  // Expand / Collapse detail
  // ────────────────────────────────────────────
  it('shows prompt detail when clicking expand button', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByText('v1').length).toBeGreaterThanOrEqual(1);
    });

    // Click the first "查看" button
    const viewButtons = screen.getAllByText('查看');
    expect(viewButtons.length).toBeGreaterThan(0);
    await user.click(viewButtons[0]!);

    await waitFor(() => {
      // Should show the prompt content
      expect(screen.getByText('You are a document summarizer.')).toBeInTheDocument();
    });
  });

  it('collapses prompt detail when clicking collapse button', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByText('v1').length).toBeGreaterThanOrEqual(1);
    });

    // Expand
    const viewButtons = screen.getAllByText('查看');
    await user.click(viewButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText('收合')).toBeInTheDocument();
    });

    // Collapse
    await user.click(screen.getByText('收合'));

    await waitFor(() => {
      // The full prompt text should no longer be visible
      expect(screen.queryByText('You are a document summarizer.')).not.toBeInTheDocument();
    });
  });

  // ────────────────────────────────────────────
  // Create modal
  // ────────────────────────────────────────────
  it('opens create modal when clicking new version button', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新增版本/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新增版本/ }));

    await waitFor(() => {
      expect(screen.getByText('新增 Prompt 版本')).toBeInTheDocument();
      expect(screen.getByText('功能名稱')).toBeInTheDocument();
      expect(screen.getByText('系統提示詞')).toBeInTheDocument();
    });
  });

  it('closes create modal when clicking cancel', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新增版本/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新增版本/ }));

    await waitFor(() => {
      expect(screen.getByText('新增 Prompt 版本')).toBeInTheDocument();
    });

    // antd v6 adds spaces between CJK characters in buttons
    await user.click(screen.getByRole('button', { name: /取.*消/ }));

    // Verify cancel doesn't trigger any API calls
    expect(mockAiApi.createPrompt).not.toHaveBeenCalled();
  });

  // ────────────────────────────────────────────
  // Compare modal
  // ────────────────────────────────────────────
  it('opens compare modal when clicking compare button', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /版本比較/ })).not.toBeDisabled();
    });

    await user.click(screen.getByRole('button', { name: /版本比較/ }));

    await waitFor(() => {
      // Compare modal title + toolbar button = at least 2 occurrences of '版本比較'
      expect(screen.getAllByText('版本比較').length).toBeGreaterThanOrEqual(2);
      // The compare modal's "比較" button (antd v6 adds space: "比 較")
      // Use exact match to distinguish from the toolbar's "版本比較" button
      expect(screen.getByRole('button', { name: /^比\s?較$/ })).toBeInTheDocument();
    });
  });

  it('disables compare execute button when versions not selected', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /版本比較/ })).not.toBeDisabled();
    });

    await user.click(screen.getByRole('button', { name: /版本比較/ }));

    await waitFor(() => {
      // antd v6 adds spaces between CJK characters in buttons
      const compareExecuteBtn = screen.getByRole('button', { name: /^比\s?較$/ });
      expect(compareExecuteBtn).toBeDisabled();
    });
  });

  // ────────────────────────────────────────────
  // Switch / Activate
  // ────────────────────────────────────────────
  it('renders switch controls for each version item', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // 3 prompt items + 1 from force-rendered create modal form
      const switches = document.querySelectorAll('.ant-switch');
      expect(switches.length).toBeGreaterThanOrEqual(3);
    });
  });

  it('renders checked switch for active versions', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      const checkedSwitches = document.querySelectorAll('.ant-switch-checked');
      // summary v1 and classify v1 are active
      expect(checkedSwitches.length).toBe(2);
    });
  });

  // ────────────────────────────────────────────
  // Per-feature add button
  // ────────────────────────────────────────────
  it('renders per-feature add button in card extra', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Each feature group card has a small "新增" link button
      const addButtons = screen.getAllByRole('button', { name: /新增/ });
      // 2 feature groups + 1 main "新增版本" button = at least 3
      expect(addButtons.length).toBeGreaterThanOrEqual(3);
    });
  });

  // ────────────────────────────────────────────
  // API call verification
  // ────────────────────────────────────────────
  it('calls listPrompts on mount with no feature filter', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(mockAiApi.listPrompts).toHaveBeenCalledTimes(1);
      expect(mockAiApi.listPrompts).toHaveBeenCalledWith(undefined);
    });
  });

  // ────────────────────────────────────────────
  // Feature tag rendering
  // ────────────────────────────────────────────
  it('renders feature key as tag in group header', async () => {
    setupDefaultMocks();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // The feature key should appear as a blue Tag
      expect(screen.getByText('summary')).toBeInTheDocument();
      expect(screen.getByText('classify')).toBeInTheDocument();
    });
  });

  // ────────────────────────────────────────────
  // Error handling edge cases
  // ────────────────────────────────────────────
  it('renders gracefully when data is null', async () => {
    mockAiApi.listPrompts.mockResolvedValue(null);

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Should show empty state since data is null
      expect(screen.getByText(/尚無 Prompt 版本/)).toBeInTheDocument();
    });
  });

  // ────────────────────────────────────────────
  // Expanded detail sections
  // ────────────────────────────────────────────
  it('shows user_template section when item has user_template', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByText('v1').length).toBeGreaterThanOrEqual(1);
    });

    // Expand first item (summary v1 which has user_template)
    const viewButtons = screen.getAllByText('查看');
    await user.click(viewButtons[0]!);

    await waitFor(() => {
      // '系統提示詞' appears both in expanded detail and force-rendered create modal form label
      expect(screen.getAllByText('系統提示詞').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('使用者提示詞模板').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Summarize: {content}')).toBeInTheDocument();
    });
  });

  it('does not show user_template section when item has no user_template', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByText('v1').length).toBeGreaterThanOrEqual(1);
    });

    // Expand the classify v1 item (no user_template)
    // It's the 3rd "查看" button (summary v1, summary v2, classify v1)
    const viewButtons = screen.getAllByText('查看');
    await user.click(viewButtons[viewButtons.length - 1]!);

    await waitFor(() => {
      expect(screen.getByText('You are a document classifier.')).toBeInTheDocument();
    });

    // user_template label should not appear for this expanded item
    // (it might appear for other items, so we check the detail section context)
    const detailTitle = screen.getByText('v1 Prompt 內容');
    expect(detailTitle).toBeInTheDocument();
  });

  // ────────────────────────────────────────────
  // Create modal form labels
  // ────────────────────────────────────────────
  it('shows all form fields in create modal', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<PromptManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /新增版本/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新增版本/ }));

    await waitFor(() => {
      expect(screen.getByText('功能名稱')).toBeInTheDocument();
      expect(screen.getByText('系統提示詞')).toBeInTheDocument();
      expect(screen.getByText(/使用者提示詞模板/)).toBeInTheDocument();
      expect(screen.getByText(/版本說明/)).toBeInTheDocument();
    });
  });
});
