/**
 * SynonymManagementPanel 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
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
    listSynonyms: vi.fn(),
    createSynonym: vi.fn(),
    updateSynonym: vi.fn(),
    deleteSynonym: vi.fn(),
    reloadSynonyms: vi.fn(),
  },
}));

vi.mock('../../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

// Mock queryConfig to avoid dependency issues
vi.mock('../../../../config/queryConfig', () => ({
  queryKeys: {
    aiSynonyms: {
      all: ['ai-synonyms'],
      list: (params: Record<string, unknown>) => ['ai-synonyms', 'list', params],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 0 },
  },
}));

import { SynonymManagementContent, DEFAULT_CATEGORIES, CATEGORY_COLORS } from '../SynonymManagementPanel';

// ── Test data ──
const mockSynonymItems = [
  {
    id: 1,
    category: 'agency_synonyms',
    words: '桃園市政府, 桃市府, 市政府',
    is_active: true,
    created_at: '2026-01-01T00:00:00',
  },
  {
    id: 2,
    category: 'doc_type_synonyms',
    words: '函, 公函, 來函',
    is_active: true,
    created_at: '2026-01-02T00:00:00',
  },
  {
    id: 3,
    category: 'status_synonyms',
    words: '已結案, 結案, 完成',
    is_active: false,
    created_at: '2026-01-03T00:00:00',
  },
];

const mockSynonymsResponse = {
  items: mockSynonymItems,
  total: 3,
  categories: ['agency_synonyms', 'doc_type_synonyms', 'status_synonyms'],
};

const mockEmptyResponse = {
  items: [],
  total: 0,
  categories: [],
};

const mockReloadSuccess = {
  success: true,
  message: '同義詞已重新載入',
  total_groups: 3,
  total_words: 9,
};

// ── Helpers ──
function setupDefaultMocks() {
  mockAiApi.listSynonyms.mockResolvedValue(mockSynonymsResponse);
  mockAiApi.createSynonym.mockResolvedValue({ id: 4, category: 'business_synonyms', words: '工程, 專案', is_active: true });
  mockAiApi.updateSynonym.mockResolvedValue({ id: 1, category: 'agency_synonyms', words: '桃園市政府, 桃市府', is_active: true });
  mockAiApi.deleteSynonym.mockResolvedValue({ success: true });
  mockAiApi.reloadSynonyms.mockResolvedValue(mockReloadSuccess);
}

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

// ── Tests ──
describe('SynonymManagementContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading state ──
  it('renders loading state while data is fetching', () => {
    mockAiApi.listSynonyms.mockReturnValue(new Promise(() => {}));

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    expect(document.querySelector('.ant-spin-spinning')).toBeTruthy();
  });

  // ── Empty state ──
  it('renders empty table when no synonyms exist', async () => {
    mockAiApi.listSynonyms.mockResolvedValue(mockEmptyResponse);

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/共 0 組/)).toBeInTheDocument();
      expect(screen.getByText(/0 啟用/)).toBeInTheDocument();
      expect(screen.getByText(/0 詞/)).toBeInTheDocument();
    });
  });

  // ── Data rendering ──
  it('renders synonym data in the table', async () => {
    setupDefaultMocks();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // Category tags
      expect(screen.getByText('機關名稱')).toBeInTheDocument();
      expect(screen.getByText('公文類型')).toBeInTheDocument();
      expect(screen.getByText('狀態別稱')).toBeInTheDocument();
    });

    // Synonym word tags
    expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    expect(screen.getByText('桃市府')).toBeInTheDocument();
    expect(screen.getByText('市政府')).toBeInTheDocument();
    expect(screen.getByText('函')).toBeInTheDocument();
    expect(screen.getByText('公函')).toBeInTheDocument();
  });

  it('renders correct statistics in the header', async () => {
    setupDefaultMocks();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      // 3 groups, 2 active, 9 total words
      expect(screen.getByText(/共 3 組/)).toBeInTheDocument();
      expect(screen.getByText(/2 啟用/)).toBeInTheDocument();
      expect(screen.getByText(/9 詞/)).toBeInTheDocument();
    });
  });

  it('renders title and description', async () => {
    setupDefaultMocks();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('AI 同義詞管理')).toBeInTheDocument();
      expect(screen.getByText(/管理 AI 自然語言搜尋使用的同義詞字典/)).toBeInTheDocument();
    });
  });

  it('renders action buttons', async () => {
    setupDefaultMocks();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('新增群組')).toBeInTheDocument();
      expect(screen.getByText('手動同步')).toBeInTheDocument();
    });
  });

  // ── Search / filter ──
  it('filters synonyms by search text', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('搜尋同義詞...');
    await user.type(searchInput, '桃園');

    // Should still show the matching item
    expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    // Non-matching items should be filtered out
    expect(screen.queryByText('函')).not.toBeInTheDocument();
  });

  // ── Add modal ──
  it('opens add modal when clicking add button', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('新增群組')).toBeInTheDocument();
    });

    await user.click(screen.getByText('新增群組'));

    await waitFor(() => {
      expect(screen.getByText('新增同義詞群組')).toBeInTheDocument();
      // antd v6 inserts spaces between CJK characters in buttons
      expect(screen.getByRole('button', { name: /儲.*存/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /取.*消/ })).toBeInTheDocument();
    });
  });

  it('closes modal when clicking cancel', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('新增群組')).toBeInTheDocument();
    });

    await user.click(screen.getByText('新增群組'));

    await waitFor(() => {
      expect(screen.getByText('新增同義詞群組')).toBeInTheDocument();
    });

    // antd v6 inserts spaces between CJK characters in buttons
    const cancelBtn = screen.getByRole('button', { name: /取.*消/ });
    await user.click(cancelBtn);

    // Verify cancel doesn't trigger any API calls
    expect(mockAiApi.createSynonym).not.toHaveBeenCalled();
    expect(mockAiApi.updateSynonym).not.toHaveBeenCalled();
  });

  // ── Edit modal ──
  it('opens edit modal when clicking edit button', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    });

    // Find edit buttons (there should be one per row)
    const editButtons = document.querySelectorAll('[aria-label="edit"]');
    expect(editButtons.length).toBeGreaterThan(0);
    await user.click(editButtons[0] as HTMLElement);

    await waitFor(() => {
      expect(screen.getByText('編輯同義詞群組')).toBeInTheDocument();
    });
  });

  // ── Toggle active status ──
  it('toggles synonym active state via switch', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    });

    // Find switch elements - 3 from table rows + 1 from force-rendered modal form
    const switches = document.querySelectorAll('.ant-switch');
    expect(switches.length).toBeGreaterThanOrEqual(3);

    // Click first switch (currently active, should call update with is_active: false)
    await user.click(switches[0] as HTMLElement);

    await waitFor(() => {
      expect(mockAiApi.updateSynonym).toHaveBeenCalledWith({
        id: 1,
        is_active: false,
      });
    });
  });

  // ── Delete ──
  it('shows delete confirmation popover', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    });

    // Find delete buttons
    const deleteButtons = document.querySelectorAll('[aria-label="delete"]');
    expect(deleteButtons.length).toBeGreaterThan(0);
    await user.click(deleteButtons[0] as HTMLElement);

    await waitFor(() => {
      expect(screen.getByText('確認刪除')).toBeInTheDocument();
      expect(screen.getByText('確定要刪除此同義詞群組嗎？')).toBeInTheDocument();
    });
  });

  it('deletes synonym after confirming popover', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    });

    const deleteButtons = document.querySelectorAll('[aria-label="delete"]');
    await user.click(deleteButtons[0] as HTMLElement);

    await waitFor(() => {
      expect(screen.getByText('確認刪除')).toBeInTheDocument();
    });

    // Click the confirm button in the popconfirm (antd v6 adds spaces between CJK chars)
    const confirmBtn = screen.getByRole('button', { name: /確.*認/ });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockAiApi.deleteSynonym).toHaveBeenCalledWith(1);
    });
  });

  // ── Reload / sync ──
  it('calls reloadSynonyms when clicking manual sync button', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('手動同步')).toBeInTheDocument();
    });

    await user.click(screen.getByText('手動同步'));

    await waitFor(() => {
      expect(mockAiApi.reloadSynonyms).toHaveBeenCalledTimes(1);
    });
  });

  it('shows sync success status after manual reload', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('手動同步')).toBeInTheDocument();
    });

    await user.click(screen.getByText('手動同步'));

    await waitFor(() => {
      // The success message from reloadSynonyms result
      const body = document.body.textContent || '';
      expect(body).toContain('已同步');
    });
  });

  it('shows sync error status when reload fails', async () => {
    setupDefaultMocks();
    mockAiApi.reloadSynonyms.mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('手動同步')).toBeInTheDocument();
    });

    await user.click(screen.getByText('手動同步'));

    await waitFor(() => {
      const body = document.body.textContent || '';
      expect(body).toContain('同步失敗');
    });
  });

  // ── Create flow ──
  it('creates a new synonym group via modal', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('新增群組')).toBeInTheDocument();
    });

    await user.click(screen.getByText('新增群組'));

    await waitFor(() => {
      expect(screen.getByText('新增同義詞群組')).toBeInTheDocument();
    });

    // Fill in the words field
    const wordsInput = screen.getByPlaceholderText('桃園市政府, 桃市府, 市政府, 市府');
    await user.type(wordsInput, '工程, 專案, 項目');

    // Select category - click the category Select then choose an option
    const modal = screen.getByText('新增同義詞群組').closest('.ant-modal') as HTMLElement;
    const categorySelect = within(modal).getByText('選擇或輸入分類').closest('.ant-select') as HTMLElement;
    await user.click(categorySelect);

    await waitFor(() => {
      expect(screen.getByText('業務用語')).toBeInTheDocument();
    });
    await user.click(screen.getByText('業務用語'));

    // Submit (antd v6 adds spaces between CJK chars)
    await user.click(screen.getByRole('button', { name: /儲.*存/ }));

    await waitFor(() => {
      expect(mockAiApi.createSynonym).toHaveBeenCalledWith({
        category: 'business_synonyms',
        words: '工程, 專案, 項目',
        is_active: true,
      });
    });
  });

  // ── API call on mount ──
  it('calls listSynonyms API on mount', async () => {
    setupDefaultMocks();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(mockAiApi.listSynonyms).toHaveBeenCalledTimes(1);
    });
  });

  // ── Auto-sync after CRUD ──
  it('auto-syncs after successful create', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('新增群組')).toBeInTheDocument();
    });

    // Open modal and fill form
    await user.click(screen.getByText('新增群組'));

    await waitFor(() => {
      expect(screen.getByText('新增同義詞群組')).toBeInTheDocument();
    });

    const wordsInput = screen.getByPlaceholderText('桃園市政府, 桃市府, 市政府, 市府');
    await user.type(wordsInput, '測試');

    const modal = screen.getByText('新增同義詞群組').closest('.ant-modal') as HTMLElement;
    const categorySelect = within(modal).getByText('選擇或輸入分類').closest('.ant-select') as HTMLElement;
    await user.click(categorySelect);
    await waitFor(() => {
      // '機關名稱' appears both in table tag and dropdown option
      expect(screen.getAllByText('機關名稱').length).toBeGreaterThanOrEqual(2);
    });
    // Click the dropdown option (last occurrence)
    const options = screen.getAllByText('機關名稱');
    await user.click(options[options.length - 1]!);

    // antd v6 adds spaces between CJK chars in buttons
    await user.click(screen.getByRole('button', { name: /儲.*存/ }));

    await waitFor(() => {
      expect(mockAiApi.createSynonym).toHaveBeenCalled();
    });

    // reloadSynonyms should be called automatically after create
    await waitFor(() => {
      expect(mockAiApi.reloadSynonyms).toHaveBeenCalled();
    });
  });

  it('auto-syncs after successful toggle', async () => {
    setupDefaultMocks();
    const user = userEvent.setup();

    render(<SynonymManagementContent />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('桃園市政府')).toBeInTheDocument();
    });

    const switches = document.querySelectorAll('.ant-switch');
    await user.click(switches[0] as HTMLElement);

    await waitFor(() => {
      expect(mockAiApi.updateSynonym).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockAiApi.reloadSynonyms).toHaveBeenCalled();
    });
  });
});

// ── Exported constants ──
describe('SynonymManagementPanel constants', () => {
  it('DEFAULT_CATEGORIES has 4 categories', () => {
    expect(DEFAULT_CATEGORIES).toHaveLength(4);
    expect(DEFAULT_CATEGORIES.map((c) => c.value)).toEqual([
      'agency_synonyms',
      'doc_type_synonyms',
      'status_synonyms',
      'business_synonyms',
    ]);
  });

  it('CATEGORY_COLORS maps all default categories', () => {
    for (const cat of DEFAULT_CATEGORIES) {
      expect(CATEGORY_COLORS[cat.value]).toBeDefined();
    }
    expect(CATEGORY_COLORS.agency_synonyms).toBe('blue');
    expect(CATEGORY_COLORS.doc_type_synonyms).toBe('green');
    expect(CATEGORY_COLORS.status_synonyms).toBe('orange');
    expect(CATEGORY_COLORS.business_synonyms).toBe('purple');
  });
});
