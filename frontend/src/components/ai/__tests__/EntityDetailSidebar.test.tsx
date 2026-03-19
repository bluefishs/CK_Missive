/**
 * EntityDetailSidebar 單元測試
 *
 * 測試正規化實體詳情側邊欄的各種狀態與互動。
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/components/ai/__tests__/EntityDetailSidebar.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// ---------------------------------------------------------------------------
// Mock setup (vi.hoisted)
// ---------------------------------------------------------------------------
const mockAiApi = vi.hoisted(() => ({
  searchGraphEntities: vi.fn(),
  getEntityDetail: vi.fn(),
  getEntityTimeline: vi.fn(),
}));

vi.mock('../../../api/aiApi', () => ({
  aiApi: mockAiApi,
}));

vi.mock('../../../config/graphNodeConfig', () => ({
  getMergedNodeConfig: vi.fn((type: string) => ({
    color: type === 'agency' ? '#1890ff' : '#52c41a',
    label: type === 'agency' ? '機關' : type,
    description: `${type} 節點`,
  })),
  CODE_ENTITY_TYPES: new Set([
    'py_module', 'py_class', 'py_function', 'db_table',
    'ts_module', 'ts_component', 'ts_hook',
  ]),
}));

// ---------------------------------------------------------------------------
// Import after mocks
// ---------------------------------------------------------------------------
import { EntityDetailSidebar } from '../EntityDetailSidebar';

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------
function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
}

function renderWithQuery(ui: React.ReactElement) {
  const qc = createQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      {ui}
    </QueryClientProvider>,
  );
}

/**
 * Wait for the detail content to finish loading.
 * The title bar always shows entityName immediately (from props),
 * so we must wait for a label that only renders after the query resolves.
 */
async function waitForDetailLoaded(labelText = '正規名稱') {
  await waitFor(() => {
    expect(screen.getByText(labelText)).toBeInTheDocument();
  });
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const ENTITY_SEARCH_RESULT = {
  results: [{ id: 42, canonical_name: '桃園市政府', entity_type: 'agency' }],
};

const ENTITY_DETAIL = {
  success: true,
  id: 42,
  canonical_name: '桃園市政府',
  entity_type: 'agency',
  description: null,
  alias_count: 2,
  mention_count: 15,
  first_seen_at: '2025-01-10T08:00:00',
  last_seen_at: '2026-03-01T12:30:00',
  aliases: ['桃園市府', '桃市府'],
  documents: [
    {
      document_id: 101,
      mention_text: '桃園市政府',
      confidence: 0.95,
      subject: '關於道路修繕案',
      doc_number: '桃府工字第1140001234號',
      doc_date: '2025-06-15',
    },
    {
      document_id: 102,
      mention_text: '桃園市府',
      confidence: 0.88,
      subject: '水利設施檢查報告',
      doc_number: '桃府水字第1140005678號',
      doc_date: '2025-07-20',
    },
  ],
  relationships: [
    {
      id: 1,
      direction: 'outgoing' as const,
      relation_type: 'ISSUED_BY',
      relation_label: '發文機關',
      target_name: '承德營造',
      target_type: 'vendor',
      target_id: 10,
      source_name: '桃園市政府',
      source_type: 'agency',
      source_id: 42,
      weight: 5,
      valid_from: '2025-01-15T00:00:00',
      valid_to: null,
      document_count: 3,
    },
    {
      id: 2,
      direction: 'incoming' as const,
      relation_type: 'RECEIVED_BY',
      relation_label: '受文機關',
      target_name: '桃園市政府',
      target_type: 'agency',
      target_id: 42,
      source_name: '內政部',
      source_type: 'agency',
      source_id: 50,
      weight: 2,
      valid_from: null,
      valid_to: null,
      document_count: 1,
    },
  ],
};

const ENTITY_TIMELINE = {
  entity_id: 42,
  timeline: [
    {
      id: 1,
      direction: 'outgoing' as const,
      relation_type: 'ISSUED_BY',
      relation_label: '發文機關',
      other_name: '承德營造',
      other_type: 'vendor',
      weight: 5,
      valid_from: '2025-01-15T00:00:00',
      valid_to: null,
      invalidated_at: null,
      document_count: 3,
    },
  ],
};

const EMPTY_DETAIL = {
  success: true,
  id: 99,
  canonical_name: '空實體',
  entity_type: 'person',
  description: null,
  alias_count: 0,
  mention_count: 1,
  first_seen_at: null,
  last_seen_at: null,
  aliases: [],
  documents: [],
  relationships: [],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('EntityDetailSidebar - 正規化實體詳情側邊欄', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // =========================================================================
  // 1. 基本渲染
  // =========================================================================
  describe('基本渲染', () => {
    it('visible=false 時不發起 API 查詢', () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={false}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      expect(mockAiApi.searchGraphEntities).not.toHaveBeenCalled();
    });

    it('entityName 為空字串時不發起 API 查詢', () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName=""
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      expect(mockAiApi.searchGraphEntities).not.toHaveBeenCalled();
    });

    it('visible=true 且 entityName 有值時發起查詢', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(mockAiApi.searchGraphEntities).toHaveBeenCalledWith({
          query: '桃園市政府',
          limit: 1,
        });
      });
    });
  });

  // =========================================================================
  // 2. 載入狀態
  // =========================================================================
  describe('載入狀態', () => {
    it('查詢中顯示 Spin 載入指示', async () => {
      // Never resolve to keep loading state
      mockAiApi.searchGraphEntities.mockReturnValue(new Promise(() => {}));

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('查詢正規化實體...')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 3. 錯誤狀態
  // =========================================================================
  describe('錯誤狀態', () => {
    it('searchGraphEntities 無結果時顯示錯誤訊息', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue({ results: [] });

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="不存在的實體"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('尚未建立正規化實體')).toBeInTheDocument();
      });
    });

    it('API 拋出錯誤時顯示錯誤訊息', async () => {
      mockAiApi.searchGraphEntities.mockRejectedValue(new Error('Network error'));

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 4. 完整資料渲染
  // =========================================================================
  describe('完整資料渲染', () => {
    beforeEach(() => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);
    });

    it('顯示實體名稱與類型標籤', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();
      // entityName appears in title + Descriptions canonical_name
      const nameElements = screen.getAllByText('桃園市政府');
      expect(nameElements.length).toBeGreaterThanOrEqual(2);
      // '機關' appears in title Tag + relationship otherType labels
      const agencyLabels = screen.getAllByText('機關');
      expect(agencyLabels.length).toBeGreaterThanOrEqual(1);
    });

    it('顯示基本資訊（正規名稱、提及次數、別名數）', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();

      expect(screen.getByText('正規名稱')).toBeInTheDocument();
      expect(screen.getByText('提及次數')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getByText('別名數')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('顯示首次/最近出現日期', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();

      expect(screen.getByText('首次出現')).toBeInTheDocument();
      expect(screen.getByText('2025-01-10')).toBeInTheDocument();
      expect(screen.getByText('最近出現')).toBeInTheDocument();
      expect(screen.getByText('2026-03-01')).toBeInTheDocument();
    });

    it('顯示別名列表', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();

      expect(screen.getByText('桃園市府')).toBeInTheDocument();
      expect(screen.getByText('桃市府')).toBeInTheDocument();
    });

    it('顯示關聯公文列表', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();

      expect(screen.getByText('桃府工字第1140001234號')).toBeInTheDocument();
      expect(screen.getByText('桃府水字第1140005678號')).toBeInTheDocument();
      expect(screen.getByText(/關於道路修繕案/)).toBeInTheDocument();
      expect(screen.getByText(/水利設施檢查報告/)).toBeInTheDocument();
    });

    it('顯示關係列表（含方向箭頭與權重）', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();

      // Outgoing relationship (may appear in both relationships and timeline sections)
      const issuedByTags = screen.getAllByText('發文機關');
      expect(issuedByTags.length).toBeGreaterThanOrEqual(1);
      // '承德營造' appears in both relationships and timeline sections
      const vendorElements = screen.getAllByText('承德營造');
      expect(vendorElements.length).toBeGreaterThanOrEqual(1);

      // Incoming relationship
      expect(screen.getByText('受文機關')).toBeInTheDocument();
      expect(screen.getByText('內政部')).toBeInTheDocument();

      // Direction arrows (relationships + timeline sections)
      const arrows = screen.getAllByText(/[→←]/);
      expect(arrows.length).toBeGreaterThanOrEqual(2);
    });

    it('顯示關係時間軸', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();

      // Timeline section divider text includes count
      expect(screen.getByText(/關係時間軸/)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // 5. 空資料 / 最小化渲染
  // =========================================================================
  describe('空資料渲染', () => {
    it('無別名、無公文、無關係時不顯示對應區塊', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue({
        results: [{ id: 99, canonical_name: '空實體', entity_type: 'person' }],
      });
      mockAiApi.getEntityDetail.mockResolvedValue(EMPTY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue({ entity_id: 99, timeline: [] });

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="空實體"
          entityType="person"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('空實體')).toBeInTheDocument();
      });

      // These section dividers should NOT be present
      expect(screen.queryByText(/別名/)).not.toBeInTheDocument();
      expect(screen.queryByText(/關聯公文/)).not.toBeInTheDocument();
      expect(screen.queryByText(/關係 \(/)).not.toBeInTheDocument();
      expect(screen.queryByText(/關係時間軸/)).not.toBeInTheDocument();
    });

    it('無 first_seen_at / last_seen_at 時不顯示日期行', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue({
        results: [{ id: 99, canonical_name: '空實體', entity_type: 'person' }],
      });
      mockAiApi.getEntityDetail.mockResolvedValue(EMPTY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue({ entity_id: 99, timeline: [] });

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="空實體"
          entityType="person"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('空實體')).toBeInTheDocument();
      });

      expect(screen.queryByText('首次出現')).not.toBeInTheDocument();
      expect(screen.queryByText('最近出現')).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 6. onClose 回呼
  // =========================================================================
  describe('onClose 回呼', () => {
    it('Drawer 模式 onClose 被傳入 Drawer', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);

      const onClose = vi.fn();
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={onClose}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('桃園市政府')).toBeInTheDocument();
      });

      // Drawer close button
      const closeButtons = screen.getAllByRole('button');
      const closeBtn = closeButtons.find(
        (btn) => btn.querySelector('.anticon-close'),
      );
      if (closeBtn) {
        fireEvent.click(closeBtn);
        expect(onClose).toHaveBeenCalled();
      }
    });

    it('inline 模式點擊關閉圖示觸發 onClose', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);

      const onClose = vi.fn();
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={onClose}
          inline={true}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('桃園市政府')).toBeInTheDocument();
      });

      // In inline mode, CloseOutlined is rendered directly
      const closeIcon = document.querySelector('.anticon-close');
      expect(closeIcon).toBeTruthy();
      if (closeIcon) {
        fireEvent.click(closeIcon);
        expect(onClose).toHaveBeenCalledTimes(1);
      }
    });
  });

  // =========================================================================
  // 7. inline vs Drawer 模式
  // =========================================================================
  describe('inline 模式', () => {
    beforeEach(() => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);
    });

    it('inline=false 時使用 Drawer (預設)', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('桃園市政府')).toBeInTheDocument();
      });

      // Drawer renders with role="dialog" in antd
      expect(document.querySelector('.ant-drawer')).toBeTruthy();
    });

    it('inline=true 時不使用 Drawer', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
          inline={true}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('桃園市政府')).toBeInTheDocument();
      });

      // No Drawer in inline mode
      expect(document.querySelector('.ant-drawer')).toBeNull();
    });
  });

  // =========================================================================
  // 8. renderExtraSections
  // =========================================================================
  describe('renderExtraSections', () => {
    beforeEach(() => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);
    });

    it('renderExtraSections=null 時不渲染額外區塊', async () => {
      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
          renderExtraSections={null}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('桃園市政府')).toBeInTheDocument();
      });

      // No "程式碼資訊" section
      expect(screen.queryByText('程式碼資訊')).not.toBeInTheDocument();
    });

    it('自訂 renderExtraSections 可注入內容', async () => {
      const customRender = vi.fn(() => (
        <div data-testid="custom-section">Custom Content</div>
      ));

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
          renderExtraSections={customRender}
        />,
      );

      await waitForDetailLoaded();

      expect(screen.getByTestId('custom-section')).toBeInTheDocument();
      expect(screen.getByText('Custom Content')).toBeInTheDocument();
      expect(customRender).toHaveBeenCalledWith(
        ENTITY_DETAIL,
        'agency',
      );
    });
  });

  // =========================================================================
  // 9. Code entity 元數據
  // =========================================================================
  describe('Code entity 元數據（預設 renderExtraSections）', () => {
    it('code entity 有 JSON description 時顯示程式碼資訊', async () => {
      const codeDetail = {
        ...ENTITY_DETAIL,
        entity_type: 'py_function',
        description: JSON.stringify({
          file_path: 'app/services/ai/graph_query_service.py',
          lines: 120,
          line_start: 45,
          line_end: 165,
          is_async: true,
          args: ['db', 'request'],
          docstring: 'Query knowledge graph entities.',
        }),
      };
      mockAiApi.searchGraphEntities.mockResolvedValue({
        results: [{ id: 42, canonical_name: 'query_graph', entity_type: 'py_function' }],
      });
      mockAiApi.getEntityDetail.mockResolvedValue(codeDetail);
      mockAiApi.getEntityTimeline.mockResolvedValue({ entity_id: 42, timeline: [] });

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="query_graph"
          entityType="py_function"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText(/程式碼資訊/)).toBeInTheDocument();
      });

      expect(screen.getByText('app/services/ai/graph_query_service.py')).toBeInTheDocument();
      expect(screen.getByText('120')).toBeInTheDocument();
      expect(screen.getByText('async')).toBeInTheDocument();
    });

    it('非 code entity 不顯示程式碼資訊區塊', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('桃園市政府')).toBeInTheDocument();
      });

      expect(screen.queryByText(/程式碼資訊/)).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 10. 公文截斷 / 超過 10 筆提示
  // =========================================================================
  describe('公文列表截斷', () => {
    it('超過 10 筆公文時顯示「還有 N 篇」提示', async () => {
      const manyDocs = Array.from({ length: 15 }, (_, i) => ({
        document_id: i + 1,
        mention_text: '桃園市政府',
        confidence: 0.9,
        subject: `公文主旨 ${i + 1}`,
        doc_number: `DOC-${String(i + 1).padStart(3, '0')}`,
        doc_date: '2025-06-15',
      }));

      const detailWithManyDocs = {
        ...ENTITY_DETAIL,
        documents: manyDocs,
      };

      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(detailWithManyDocs);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitForDetailLoaded();

      expect(screen.getByText(/還有 5 篇/)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // 11. 時間軸截斷
  // =========================================================================
  describe('時間軸截斷', () => {
    it('超過 15 筆時間軸時顯示「還有 N 筆」提示', async () => {
      const manyTimeline = Array.from({ length: 20 }, (_, i) => ({
        id: i + 1,
        direction: 'outgoing' as const,
        relation_type: 'RELATED',
        relation_label: `關係 ${i + 1}`,
        other_name: `實體 ${i + 1}`,
        other_type: 'agency',
        weight: 1,
        valid_from: '2025-01-01T00:00:00',
        valid_to: null,
        invalidated_at: null,
        document_count: 1,
      }));

      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue({ entity_id: 42, timeline: manyTimeline });

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText('桃園市政府')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText(/還有 5 筆/)).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 12. API 呼叫順序
  // =========================================================================
  describe('API 呼叫順序', () => {
    it('先呼叫 searchGraphEntities，再平行呼叫 getEntityDetail + getEntityTimeline', async () => {
      mockAiApi.searchGraphEntities.mockResolvedValue(ENTITY_SEARCH_RESULT);
      mockAiApi.getEntityDetail.mockResolvedValue(ENTITY_DETAIL);
      mockAiApi.getEntityTimeline.mockResolvedValue(ENTITY_TIMELINE);

      renderWithQuery(
        <EntityDetailSidebar
          visible={true}
          entityName="桃園市政府"
          entityType="agency"
          onClose={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(mockAiApi.searchGraphEntities).toHaveBeenCalledTimes(1);
        expect(mockAiApi.getEntityDetail).toHaveBeenCalledWith({ entity_id: 42 });
        expect(mockAiApi.getEntityTimeline).toHaveBeenCalledWith({ entity_id: 42 });
      });
    });
  });
});
