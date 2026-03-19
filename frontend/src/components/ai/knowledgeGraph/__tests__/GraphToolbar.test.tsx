/**
 * GraphToolbar Unit Tests
 *
 * Tests for the knowledge graph toolbar component: search input, buttons,
 * dimension switch, view mode switch.
 *
 * Run:
 *   cd frontend && npx vitest run src/components/ai/knowledgeGraph/__tests__/GraphToolbar.test.tsx
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GraphToolbar } from '../GraphToolbar';
import type { GraphToolbarProps } from '../GraphToolbar';
import type { GraphNode } from '../../../../types/ai';
import type { MergedNodeConfig } from '../../../../config/graphNodeConfig';

// Minimal mock for Ant Design components to avoid full render issues
vi.mock('antd', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('antd');
  return {
    ...actual,
    // Keep real components but ensure App context exists
  };
});

// ============================================================================
// Helpers
// ============================================================================

function makeMergedConfig(overrides: Partial<MergedNodeConfig> = {}): MergedNodeConfig {
  return {
    color: '#1890ff',
    radius: 6,
    label: '公文',
    detailable: false,
    description: '測試節點',
    visible: true,
    ...overrides,
  };
}

function makeNode(overrides: Partial<GraphNode> = {}): GraphNode {
  return {
    id: 'node-1',
    type: 'document',
    label: 'Test Node',
    ...overrides,
  };
}

function defaultProps(overrides: Partial<GraphToolbarProps> = {}): GraphToolbarProps {
  return {
    searchText: '',
    onSearchChange: vi.fn(),
    onSearchSubmit: vi.fn(),
    apiSearching: false,
    visibleTypes: new Set(['document']),
    onTypeToggle: vi.fn(),
    onSettingsOpen: vi.fn(),
    onZoomToFit: vi.fn(),
    onRefresh: vi.fn(),
    rawNodes: [makeNode()],
    mergedConfigs: { document: makeMergedConfig() },
    ...overrides,
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('GraphToolbar', () => {
  it('renders search input', () => {
    render(<GraphToolbar {...defaultProps()} />);

    const input = screen.getByPlaceholderText('搜尋節點（Enter 擴展搜尋）');
    expect(input).toBeDefined();
  });

  it('calls onSearchChange when typing in search input', () => {
    const onSearchChange = vi.fn();
    render(<GraphToolbar {...defaultProps({ onSearchChange })} />);

    const input = screen.getByPlaceholderText('搜尋節點（Enter 擴展搜尋）');
    fireEvent.change(input, { target: { value: '測試' } });

    expect(onSearchChange).toHaveBeenCalledWith('測試');
  });

  it('renders reload button and calls onRefresh when clicked', () => {
    const onRefresh = vi.fn();
    render(<GraphToolbar {...defaultProps({ onRefresh })} />);

    // ReloadOutlined button has a tooltip "重新載入"
    // Find the button by its aria-label or role
    const buttons = screen.getAllByRole('button');
    // The reload button is the last one in the Space
    const reloadButton = buttons[buttons.length - 1];
    fireEvent.click(reloadButton!);

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('renders 2D/3D mode switch when dimension props provided', () => {
    const onDimensionChange = vi.fn();
    render(
      <GraphToolbar
        {...defaultProps({
          dimension: '2d',
          onDimensionChange,
        })}
      />,
    );

    // Segmented should render 2D and 3D options
    expect(screen.getByText('2D')).toBeDefined();
    expect(screen.getByText('3D')).toBeDefined();
  });

  it('does not render 2D/3D switch when dimension props not provided', () => {
    render(<GraphToolbar {...defaultProps()} />);

    expect(screen.queryByText('2D')).toBeNull();
    expect(screen.queryByText('3D')).toBeNull();
  });

  it('renders view mode switch when viewMode props provided', () => {
    const onViewModeChange = vi.fn();
    render(
      <GraphToolbar
        {...defaultProps({
          viewMode: 'entity',
          onViewModeChange,
        })}
      />,
    );

    expect(screen.getByText('核心關係')).toBeDefined();
    expect(screen.getByText('完整網絡')).toBeDefined();
  });

  it('does not render view mode switch when viewMode not provided', () => {
    render(<GraphToolbar {...defaultProps()} />);

    expect(screen.queryByText('核心關係')).toBeNull();
    expect(screen.queryByText('完整網絡')).toBeNull();
  });

  it('renders type filter tags for present node types', () => {
    const nodes: GraphNode[] = [
      makeNode({ id: 'n1', type: 'document', label: 'Doc1' }),
      makeNode({ id: 'n2', type: 'project', label: 'Proj1' }),
    ];
    const mergedConfigs: Record<string, MergedNodeConfig> = {
      document: makeMergedConfig({ label: '公文' }),
      project: makeMergedConfig({ label: '承攬案件', color: '#52c41a' }),
    };

    render(
      <GraphToolbar
        {...defaultProps({
          rawNodes: nodes,
          mergedConfigs,
          visibleTypes: new Set(['document', 'project']),
        })}
      />,
    );

    // '公文' appears as both group label and tag label, so use getAllByText
    expect(screen.getAllByText('公文').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('承攬案件')).toBeDefined();
  });
});
