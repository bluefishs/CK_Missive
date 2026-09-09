/**
 * 報價單詳情「費用核銷」分頁：列點擊必須依型別導向（2026-09-09 owner「/erp/expenses/23 找不到資料」）。
 *
 * 08-15 讓卡片切換核銷／請款／開票三種型別後，表格會列出請款列，而列點擊不分型別一律開**費用單**詳情，
 * 於是請款 #23 被當成費用單 #23（不存在）⇒ 404。三種 id 是三張表的 id，只有 expense 有獨立詳情頁。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import { createTestQueryClient } from '../../test/testUtils';

const { navigateMock, records } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  records: [
    { type: 'expense', id: 5, date: '2026-04-09', description: 'AB-123', amount: 762, status: 'verified' },
    { type: 'billing', id: 23, date: '2026-03-20', description: '第一期款項', amount: 126000, status: 'unpaid' },
  ],
}));

vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNavigate: () => navigateMock,
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));
vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../api/client', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  default: {
    post: vi.fn().mockResolvedValue({
      data: {
        records,
        summary: {
          expense_total: 762, expense_count: 1,
          billing_total: 126000, billing_count: 1,
          invoice_total: 0, invoice_count: 0,
        },
      },
    }),
  },
}));

vi.mock('../../hooks', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useResponsive: vi.fn(() => ({ isMobile: false, isTablet: false, isDesktop: true })),
}));

import ExpensesTab from '../../pages/erpQuotation/ExpensesTab';

function renderTab() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter initialEntries={['/erp/quotations/125?tab=expenses']}>
            <ExpensesTab caseCode="CK2025_PM_02_162" />
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

describe('報價單費用分頁 列點擊依型別導向', () => {
  beforeEach(() => navigateMock.mockClear());

  it('核銷列 → 費用單詳情（帶自己的 id）', async () => {
    renderTab();
    const cell = await screen.findByText('AB-123');
    fireEvent.click(cell);
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/erp/expenses/5'));
  });

  it('切到請款後點列 → 不得拿請款 id 去開費用單；導回應收帳款分頁', async () => {
    renderTab();
    await screen.findByText('AB-123');
    // 卡片切換型別：請款卡的標題
    fireEvent.click(screen.getByText(/請款/));
    const cell = await screen.findByText('第一期款項');
    fireEvent.click(cell);
    await waitFor(() => expect(navigateMock).toHaveBeenCalled());
    const calls = navigateMock.mock.calls.map((c) => JSON.stringify(c[0]));
    expect(calls.some((c) => c.includes('/erp/expenses/23'))).toBe(false);
    expect(calls.some((c) => c.includes('tab=receivable'))).toBe(true);
  });
});
