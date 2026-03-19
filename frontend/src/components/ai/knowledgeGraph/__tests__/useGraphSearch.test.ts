/**
 * useGraphSearch Hook Unit Tests
 *
 * Tests for the knowledge graph search hook: local search matching,
 * search text updates, initial state.
 *
 * Run:
 *   cd frontend && npx vitest run src/components/ai/knowledgeGraph/__tests__/useGraphSearch.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGraphSearch } from '../useGraphSearch';
import type { GraphNode } from '../../../../types/ai';

// ============================================================================
// Mock dependencies
// ============================================================================

// Mock antd App.useApp to provide message
vi.mock('antd', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('antd');
  return {
    ...actual,
    App: {
      ...(actual.App as Record<string, unknown>),
      useApp: () => ({
        message: { info: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() },
        notification: {},
        modal: {},
      }),
    },
  };
});

// Mock aiApi to avoid real API calls
vi.mock('../../../../api/aiApi', () => ({
  aiApi: {
    searchGraphEntities: vi.fn().mockResolvedValue({ results: [] }),
  },
}));

// ============================================================================
// Helpers
// ============================================================================

function makeNode(overrides: Partial<GraphNode> = {}): GraphNode {
  return {
    id: 'node-1',
    type: 'document',
    label: 'Test Node',
    ...overrides,
  };
}

const sampleNodes: GraphNode[] = [
  makeNode({ id: 'doc-1', type: 'document', label: '桃園市政府公文' }),
  makeNode({ id: 'person-1', type: 'person', label: '張三' }),
  makeNode({ id: 'agency-1', type: 'agency', label: '桃園市政府水務局' }),
  makeNode({ id: 'project-1', type: 'project', label: '橋梁修繕工程' }),
  makeNode({ id: 'dispatch-1', type: 'dispatch', label: '派工單007' }),
];

// ============================================================================
// Tests
// ============================================================================

describe('useGraphSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty results initially', () => {
    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: sampleNodes }),
    );

    expect(result.current.searchText).toBe('');
    expect(result.current.localSearchMatchIds).toBeNull();
    expect(result.current.apiSearchMatchIds).toBeNull();
    expect(result.current.searchMatchIds).toBeNull();
    expect(result.current.apiSearching).toBe(false);
    expect(result.current.aliasHint).toBeNull();
  });

  it('updates search term via setSearchText', () => {
    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: sampleNodes }),
    );

    act(() => {
      result.current.setSearchText('桃園');
    });

    expect(result.current.searchText).toBe('桃園');
  });

  it('filters nodes locally by label match', () => {
    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: sampleNodes }),
    );

    act(() => {
      result.current.setSearchText('桃園');
    });

    // Should match '桃園市政府公文' and '桃園市政府水務局'
    const matchIds = result.current.localSearchMatchIds;
    expect(matchIds).not.toBeNull();
    expect(matchIds!.size).toBe(2);
    expect(matchIds!.has('doc-1')).toBe(true);
    expect(matchIds!.has('agency-1')).toBe(true);
  });

  it('returns null for local matches when search text is empty', () => {
    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: sampleNodes }),
    );

    act(() => {
      result.current.setSearchText('');
    });

    expect(result.current.localSearchMatchIds).toBeNull();
  });

  it('returns null for local matches when search text is whitespace only', () => {
    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: sampleNodes }),
    );

    act(() => {
      result.current.setSearchText('   ');
    });

    expect(result.current.localSearchMatchIds).toBeNull();
  });

  it('performs case-insensitive local search', () => {
    const nodes: GraphNode[] = [
      makeNode({ id: 'n1', label: 'TestDocument' }),
      makeNode({ id: 'n2', label: 'Another Item' }),
    ];

    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: nodes }),
    );

    act(() => {
      result.current.setSearchText('testdocument');
    });

    expect(result.current.localSearchMatchIds!.has('n1')).toBe(true);
    expect(result.current.localSearchMatchIds!.size).toBe(1);
  });

  it('matches nodes by doc_number', () => {
    const nodes: GraphNode[] = [
      makeNode({ id: 'n1', label: '公文A', doc_number: '桃府工字第1130001號' }),
      makeNode({ id: 'n2', label: '公文B', doc_number: '桃府水字第1140002號' }),
    ];

    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: nodes }),
    );

    act(() => {
      result.current.setSearchText('1130001');
    });

    expect(result.current.localSearchMatchIds!.has('n1')).toBe(true);
    expect(result.current.localSearchMatchIds!.has('n2')).toBe(false);
  });

  it('merged searchMatchIds falls back to local when no API results', () => {
    const { result } = renderHook(() =>
      useGraphSearch({ rawNodes: sampleNodes }),
    );

    act(() => {
      result.current.setSearchText('張三');
    });

    // searchMatchIds should equal localSearchMatchIds when apiSearchMatchIds is null
    expect(result.current.searchMatchIds).toBe(result.current.localSearchMatchIds);
    expect(result.current.searchMatchIds!.has('person-1')).toBe(true);
  });
});
