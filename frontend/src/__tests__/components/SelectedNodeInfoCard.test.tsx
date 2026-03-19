/**
 * SelectedNodeInfoCard - Unit Tests
 *
 * Tests: node info display, entity name/type, close button, detail link, business entity link
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../../config/graphNodeConfig', () => ({
  GRAPH_NODE_CONFIG: {},
  getNodeConfig: vi.fn((type: string) => ({
    color: '#999', radius: 5, label: type, description: `${type} node`, detailable: false, visible: true,
  })),
}));

// ============================================================================
// Imports (after mocks)
// ============================================================================

import {
  SelectedNodeInfoCard,
  type SelectedNodeData,
  type SelectedNodeInfoCardProps,
} from '../../components/ai/knowledgeGraph/SelectedNodeInfoCard';
import type { MergedNodeConfig } from '../../config/graphNodeConfig';

// ============================================================================
// Helpers
// ============================================================================

function createNodeConfig(overrides: Partial<MergedNodeConfig> = {}): MergedNodeConfig {
  return {
    color: '#1890ff',
    radius: 6,
    label: '公文',
    detailable: false,
    description: '系統中的公文記錄',
    visible: true,
    ...overrides,
  };
}

function createNode(overrides: Partial<SelectedNodeData> = {}): SelectedNodeData {
  return {
    id: 'person_1',
    label: '王大明',
    type: 'person',
    color: '#eb2f96',
    ...overrides,
  };
}

function createProps(overrides: Partial<SelectedNodeInfoCardProps> = {}): SelectedNodeInfoCardProps {
  return {
    node: createNode(),
    nodeConfig: createNodeConfig({ label: '人物', detailable: true }),
    neighborCount: 5,
    onClose: vi.fn(),
    onViewDetail: vi.fn(),
    ...overrides,
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('SelectedNodeInfoCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders node label and type label', () => {
    render(<SelectedNodeInfoCard {...createProps()} />);
    expect(screen.getByText('王大明')).toBeInTheDocument();
    expect(screen.getByText('人物')).toBeInTheDocument();
  });

  it('renders neighbor count', () => {
    render(<SelectedNodeInfoCard {...createProps({ neighborCount: 12 })} />);
    expect(screen.getByText(/12 個/)).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<SelectedNodeInfoCard {...createProps({ onClose })} />);
    // Close button is the X character
    const closeBtn = screen.getByText('\u2715');
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('renders detail link when nodeConfig.detailable is true', () => {
    render(<SelectedNodeInfoCard {...createProps()} />);
    expect(screen.getByText(/檢視正規化實體詳情/)).toBeInTheDocument();
  });

  it('calls onViewDetail when detail link clicked', () => {
    const onViewDetail = vi.fn();
    render(<SelectedNodeInfoCard {...createProps({ onViewDetail })} />);
    fireEvent.click(screen.getByText(/檢視正規化實體詳情/));
    expect(onViewDetail).toHaveBeenCalledWith('王大明', 'person');
  });

  it('does not render detail link when nodeConfig.detailable is false', () => {
    render(
      <SelectedNodeInfoCard
        {...createProps({
          nodeConfig: createNodeConfig({ detailable: false }),
        })}
      />,
    );
    expect(screen.queryByText(/檢視正規化實體詳情/)).not.toBeInTheDocument();
  });

  it('renders doc_number, category, and status when present', () => {
    render(
      <SelectedNodeInfoCard
        {...createProps({
          node: createNode({
            id: 'doc_1',
            type: 'document',
            label: '公文-001',
            color: '#1890ff',
            doc_number: 'A-113-0001',
            category: '收文',
            status: '已辦結',
          }),
          nodeConfig: createNodeConfig({ label: '公文', detailable: false }),
        })}
      />,
    );
    expect(screen.getByText(/A-113-0001/)).toBeInTheDocument();
    expect(screen.getByText(/收文/)).toBeInTheDocument();
    expect(screen.getByText(/已辦結/)).toBeInTheDocument();
  });
});
