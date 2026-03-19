/**
 * GraphToolbar - Unit Tests
 *
 * Tests: toolbar renders, search input, 2D/3D toggle, type filter tags, action buttons
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../../config/graphNodeConfig', () => ({
  GRAPH_NODE_CONFIG: {
    document: { color: '#1890ff', radius: 6, label: '公文', detailable: false, description: '公文記錄' },
    agency: { color: '#fa8c16', radius: 5, label: '機關', detailable: false, description: '機關' },
    person: { color: '#eb2f96', radius: 4, label: '人物', detailable: true, description: '人物' },
  },
  getNodeConfig: vi.fn((type: string) => ({
    color: '#999', radius: 5, label: type, description: `${type} node`, detailable: false,
  })),
  getMergedNodeConfig: vi.fn((type: string) => ({
    color: '#999', radius: 5, label: type, description: `${type} node`,
  })),
  getAllMergedConfigs: vi.fn(() => ({})),
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { GraphToolbar, type GraphToolbarProps } from '../../components/ai/knowledgeGraph/GraphToolbar';
import type { GraphNode, GraphEdge } from '../../types/ai';
import type { MergedNodeConfig } from '../../config/graphNodeConfig';

// ============================================================================
// Helpers
// ============================================================================

function renderWithAntd(ui: React.ReactElement) {
  return render(
    <ConfigProvider locale={zhTW}>
      <AntApp>{ui}</AntApp>
    </ConfigProvider>,
  );
}

const mockNodes: GraphNode[] = [
  { id: '1', type: 'document', label: 'Doc 1' },
  { id: '2', type: 'document', label: 'Doc 2' },
  { id: '3', type: 'agency', label: 'Agency 1' },
  { id: '4', type: 'person', label: 'Person 1' },
];

const mockEdges: GraphEdge[] = [
  { source: '1', target: '3', label: '發文', type: 'sends' },
  { source: '1', target: '4', label: '提及', type: 'mentions' },
];

const mockMergedConfigs: Record<string, MergedNodeConfig> = {
  document: { color: '#1890ff', radius: 6, label: '公文', detailable: false, description: '公文記錄', visible: true },
  agency: { color: '#fa8c16', radius: 5, label: '機關', detailable: false, description: '機關', visible: true },
  person: { color: '#eb2f96', radius: 4, label: '人物', detailable: true, description: '人物', visible: true },
};

function createProps(overrides: Partial<GraphToolbarProps> = {}): GraphToolbarProps {
  return {
    searchText: '',
    onSearchChange: vi.fn(),
    onSearchSubmit: vi.fn(),
    apiSearching: false,
    visibleTypes: new Set(['document', 'agency', 'person']),
    onTypeToggle: vi.fn(),
    onSettingsOpen: vi.fn(),
    onZoomToFit: vi.fn(),
    onRefresh: vi.fn(),
    rawNodes: mockNodes,
    rawEdges: mockEdges,
    mergedConfigs: mockMergedConfigs,
    ...overrides,
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('GraphToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders search input with placeholder', () => {
    renderWithAntd(<GraphToolbar {...createProps()} />);
    expect(screen.getByPlaceholderText('搜尋節點（Enter 擴展搜尋）')).toBeInTheDocument();
  });

  it('fires onSearchChange when typing in search input', () => {
    const onSearchChange = vi.fn();
    renderWithAntd(<GraphToolbar {...createProps({ onSearchChange })} />);
    const input = screen.getByPlaceholderText('搜尋節點（Enter 擴展搜尋）');
    fireEvent.change(input, { target: { value: '王' } });
    expect(onSearchChange).toHaveBeenCalledWith('王');
  });

  it('fires onSearchSubmit on Enter key', () => {
    const onSearchSubmit = vi.fn();
    renderWithAntd(<GraphToolbar {...createProps({ onSearchSubmit })} />);
    const input = screen.getByPlaceholderText('搜尋節點（Enter 擴展搜尋）');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSearchSubmit).toHaveBeenCalled();
  });

  it('renders type filter tags for present node types', () => {
    renderWithAntd(<GraphToolbar {...createProps()} />);
    // Should render label for document, agency (in "公文" group), person (in "AI 提取" group)
    // "公文" appears both as group label and type tag, so use getAllByText
    expect(screen.getAllByText('公文').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('機關')).toBeInTheDocument();
    expect(screen.getByText('人物')).toBeInTheDocument();
  });

  it('renders 2D/3D toggle when dimension prop provided', () => {
    renderWithAntd(
      <GraphToolbar
        {...createProps({
          dimension: '2d',
          onDimensionChange: vi.fn(),
        })}
      />,
    );
    expect(screen.getByText('2D')).toBeInTheDocument();
    expect(screen.getByText('3D')).toBeInTheDocument();
  });

  it('does not render 2D/3D toggle when dimension prop not provided', () => {
    renderWithAntd(<GraphToolbar {...createProps()} />);
    expect(screen.queryByText('2D')).not.toBeInTheDocument();
  });

  it('fires onDimensionChange when switching dimension', () => {
    const onDimensionChange = vi.fn();
    renderWithAntd(
      <GraphToolbar
        {...createProps({
          dimension: '2d',
          onDimensionChange,
        })}
      />,
    );
    fireEvent.click(screen.getByText('3D'));
    expect(onDimensionChange).toHaveBeenCalledWith('3d');
  });

  it('renders edge type legend for edges in the graph', () => {
    renderWithAntd(<GraphToolbar {...createProps()} />);
    expect(screen.getByText('發文')).toBeInTheDocument();
    expect(screen.getByText('提及')).toBeInTheDocument();
  });

  it('renders view mode toggle when viewMode provided', () => {
    renderWithAntd(
      <GraphToolbar
        {...createProps({
          viewMode: 'entity',
          onViewModeChange: vi.fn(),
        })}
      />,
    );
    expect(screen.getByText('核心關係')).toBeInTheDocument();
    expect(screen.getByText('完整網絡')).toBeInTheDocument();
  });
});
