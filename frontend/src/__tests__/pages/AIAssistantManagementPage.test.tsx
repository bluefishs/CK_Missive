/**
 * AIAssistantManagementPage Smoke Test
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

vi.mock('../../components/ai/RAGChatPanel', () => ({
  RAGChatPanel: () => <div data-testid="mock-rag-chat">RAGChatPanel</div>,
}));

vi.mock('../../components/ai/management', () => ({
  AgentPerformanceTab: () => <div>AgentPerformanceTab</div>,
  DataAnalyticsTab: () => <div>DataAnalyticsTab</div>,
  DataPipelineTab: () => <div>DataPipelineTab</div>,
  ServiceStatusTab: () => <div>ServiceStatusTab</div>,
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

describe('AIAssistantManagementPage', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders without crashing', async () => {
    const mod = await import('../../pages/AIAssistantManagementPage');
    const Page = mod.default;
    renderWithProviders(<Page />);
    expect(screen.getByText('AI 助理管理')).toBeInTheDocument();
  });
});
