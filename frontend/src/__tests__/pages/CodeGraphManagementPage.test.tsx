/**
 * CodeGraphManagementPage Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/aiApi', () => ({
  aiApi: {
    getGraphStats: vi.fn().mockResolvedValue({ total_entities: 0, total_relationships: 0, entity_type_distribution: {} }),
    getTopEntities: vi.fn().mockResolvedValue({ entities: [] }),
    getEntityGraph: vi.fn().mockResolvedValue({ success: true, nodes: [], edges: [] }),
    ingestCodeGraph: vi.fn().mockResolvedValue({ success: true }),
    detectCycles: vi.fn().mockResolvedValue({ cycles: [] }),
    analyzeArchitecture: vi.fn().mockResolvedValue({ layers: [] }),
  },
}));

vi.mock('../../components/ai/KnowledgeGraph', () => ({
  KnowledgeGraph: () => <div data-testid="mock-knowledge-graph">KnowledgeGraph</div>,
}));

vi.mock('../../hooks/useCodeWikiGraph', () => ({
  useCodeWikiGraph: vi.fn(() => ({
    graphData: null, isLoading: false, error: null, refetch: vi.fn(),
  })),
}));

vi.mock('../../hooks/utility/useAuthGuard', () => ({
  useAuthGuard: vi.fn(() => ({
    hasPermission: () => true, isAdmin: true, isAuthenticated: true,
    user: { id: 1, role: 'admin' },
  })),
}));

vi.mock('../../pages/codeGraph', () => ({
  CodeGraphSidebar: () => <div>Sidebar</div>,
  ModuleConfigPanel: () => <div>ModuleConfig</div>,
  ArchitectureOverviewTab: () => <div>ArchOverview</div>,
}));

vi.mock('../../config/moduleGraphConfig', () => ({
  getModuleMappings: vi.fn(() => ({})),
  saveModuleMappings: vi.fn(),
  resetModuleMappings: vi.fn(),
  buildModuleGraphData: vi.fn(() => ({ nodes: [], links: [] })),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>{ui}</MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

describe('CodeGraphManagementPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/CodeGraphManagementPage');
    renderWithProviders(<mod.default />);
    expect(screen.getByTestId('mock-knowledge-graph')).toBeInTheDocument();
  });
});
