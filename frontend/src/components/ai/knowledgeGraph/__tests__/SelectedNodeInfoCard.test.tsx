/**
 * SelectedNodeInfoCard Unit Tests
 *
 * Tests for the selected node floating info panel: rendering, close button,
 * type badge display.
 *
 * Run:
 *   cd frontend && npx vitest run src/components/ai/knowledgeGraph/__tests__/SelectedNodeInfoCard.test.tsx
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SelectedNodeInfoCard } from '../SelectedNodeInfoCard';
import type { SelectedNodeData, SelectedNodeInfoCardProps } from '../SelectedNodeInfoCard';
import type { MergedNodeConfig } from '../../../../config/graphNodeConfig';

// ============================================================================
// Helpers
// ============================================================================

function makeNodeConfig(overrides: Partial<MergedNodeConfig> = {}): MergedNodeConfig {
  return {
    color: '#eb2f96',
    radius: 5,
    label: '人物',
    detailable: true,
    description: 'NER 提取的人物實體',
    visible: true,
    ...overrides,
  };
}

function makeNodeData(overrides: Partial<SelectedNodeData> = {}): SelectedNodeData {
  return {
    id: 'person_1',
    label: '張三',
    type: 'person',
    color: '#eb2f96',
    ...overrides,
  };
}

function defaultProps(overrides: Partial<SelectedNodeInfoCardProps> = {}): SelectedNodeInfoCardProps {
  return {
    node: makeNodeData(),
    nodeConfig: makeNodeConfig(),
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
  it('renders node label and type for an entity node', () => {
    render(<SelectedNodeInfoCard {...defaultProps()} />);

    // Node label
    expect(screen.getByText('張三')).toBeDefined();
    // Node type label from config
    expect(screen.getByText('人物')).toBeDefined();
  });

  it('renders close button and calls onClose when clicked', () => {
    const onClose = vi.fn();
    render(<SelectedNodeInfoCard {...defaultProps({ onClose })} />);

    // Close button renders as "✕" character
    const closeButton = screen.getByText('\u2715');
    expect(closeButton).toBeDefined();

    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows entity type badge (nodeConfig.label)', () => {
    const nodeConfig = makeNodeConfig({ label: '機關', description: '公文往來的政府機關' });
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          node: makeNodeData({ type: 'agency', label: '桃園市政府', color: '#fa8c16' }),
          nodeConfig,
        })}
      />,
    );

    expect(screen.getByText('機關')).toBeDefined();
    expect(screen.getByText('桃園市政府')).toBeDefined();
  });

  it('shows neighbor count', () => {
    render(<SelectedNodeInfoCard {...defaultProps({ neighborCount: 12 })} />);

    expect(screen.getByText('關聯節點：12 個')).toBeDefined();
  });

  it('shows doc_number when provided', () => {
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          node: makeNodeData({ doc_number: '桃府工水字第1130001234號' }),
        })}
      />,
    );

    expect(screen.getByText(/桃府工水字第1130001234號/)).toBeDefined();
  });

  it('shows category when provided', () => {
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          node: makeNodeData({ category: '收文' }),
        })}
      />,
    );

    expect(screen.getByText(/收文/)).toBeDefined();
  });

  it('shows "檢視正規化實體詳情" link when detailable is true', () => {
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          nodeConfig: makeNodeConfig({ detailable: true }),
        })}
      />,
    );

    expect(screen.getByText(/檢視正規化實體詳情/)).toBeDefined();
  });

  it('calls onViewDetail when detail link is clicked', () => {
    const onViewDetail = vi.fn();
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          onViewDetail,
          nodeConfig: makeNodeConfig({ detailable: true }),
        })}
      />,
    );

    const detailLink = screen.getByText(/檢視正規化實體詳情/);
    fireEvent.click(detailLink);

    expect(onViewDetail).toHaveBeenCalledWith('張三', 'person');
  });

  it('does not show detail link when detailable is false', () => {
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          nodeConfig: makeNodeConfig({ detailable: false }),
        })}
      />,
    );

    expect(screen.queryByText(/檢視正規化實體詳情/)).toBeNull();
  });

  it('shows "前往對應頁面" link for business entity types', () => {
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          node: makeNodeData({ id: 'doc_123', type: 'document', label: '測試公文' }),
          nodeConfig: makeNodeConfig({ detailable: false, label: '公文' }),
        })}
      />,
    );

    expect(screen.getByText(/前往對應頁面/)).toBeDefined();
  });

  it('does not show "前往對應頁面" for non-business entity types', () => {
    render(
      <SelectedNodeInfoCard
        {...defaultProps({
          node: makeNodeData({ id: 'person_1', type: 'person', label: '張三' }),
          nodeConfig: makeNodeConfig({ detailable: true }),
        })}
      />,
    );

    expect(screen.queryByText(/前往對應頁面/)).toBeNull();
  });
});
