/**
 * VendorPage Tests
 *
 * Tests for the vendor management page including:
 * - Page title renders
 * - Statistics display
 * - Search input and filter controls
 * - Action buttons (add vendor)
 * - Table renders with data
 * - Navigation on row click
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// Dynamic import needs a longer timeout for module resolution in full test suite
const WAIT_OPTS = { timeout: 5000 };

// ==========================================================================
// Mocks
// ==========================================================================

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

const mockVendors = [
  {
    id: 1,
    vendor_name: 'Vendor Alpha',
    vendor_code: 'VND-001',
    contact_person: 'John',
    phone: '02-12345678',
    email: 'john@alpha.com',
    business_type: '測量業務',
    rating: 5,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    vendor_name: 'Vendor Beta',
    vendor_code: 'VND-002',
    contact_person: 'Jane',
    phone: '02-87654321',
    email: 'jane@beta.com',
    business_type: '工程顧問',
    rating: 3,
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-02-01T00:00:00Z',
  },
];

vi.mock('../../hooks', () => ({
  useResponsive: vi.fn(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    responsiveValue: (v: Record<string, unknown>) => v.desktop ?? v.tablet ?? v.mobile,
  })),
  useVendorsPage: vi.fn(() => ({
    vendors: mockVendors,
    pagination: { total: 2, page: 1, limit: 10, total_pages: 1, has_next: false, has_prev: false },
    isLoading: false,
    isError: false,
  })),
}));

vi.mock('../../router/types', () => ({
  ROUTES: {
    VENDOR_CREATE: '/vendors/create',
    VENDOR_EDIT: '/vendors/:id/edit',
  },
}));

vi.mock('../../constants', () => ({
  BUSINESS_TYPE_OPTIONS: [
    { label: '測量業務', value: '測量業務' },
    { label: '工程顧問', value: '工程顧問' },
  ],
  getBusinessTypeColor: vi.fn(() => 'blue'),
  getRatingColor: vi.fn(() => 'gold'),
}));

vi.mock('../../components/common', () => ({
  ResponsiveTable: (props: Record<string, unknown>) => {
    const dataSource = props.dataSource as Array<Record<string, unknown>> || [];
    return (
      <div data-testid="responsive-table">
        <table>
          <tbody>
            {dataSource.map((item: Record<string, unknown>) => (
              <tr
                key={item.id as number}
                data-testid={`vendor-row-${item.id}`}
                onClick={() => {
                  const onRow = props.onRow as ((record: Record<string, unknown>) => { onClick: () => void }) | undefined;
                  if (onRow) onRow(item).onClick();
                }}
              >
                <td>{item.vendor_name as string}</td>
                <td>{item.contact_person as string}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  },
}));

// ==========================================================================
// Helpers
// ==========================================================================

function renderVendorPage() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp>
          <MemoryRouter>
            <React.Suspense fallback={<div>Loading...</div>}>
              <VendorPageWrapper />
            </React.Suspense>
          </MemoryRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

function VendorPageWrapper() {
  const [Page, setPage] = React.useState<React.FC | null>(null);
  React.useEffect(() => {
    import('../../pages/VendorPage').then((mod) => {
      setPage(() => mod.default);
    });
  }, []);
  if (!Page) return <div>Loading...</div>;
  return <Page />;
}

// ==========================================================================
// Tests
// ==========================================================================

describe('VendorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByText('廠商管理')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders vendor total statistic', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByText('總廠商數')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the add vendor button', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByText('新增廠商')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the search input', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋廠商名稱、聯絡人或營業項目')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders the data table', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByTestId('responsive-table')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders vendor data rows in the table', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByText('Vendor Alpha')).toBeInTheDocument();
      expect(screen.getByText('Vendor Beta')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('navigates to create page when add button is clicked', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByText('新增廠商')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByText('新增廠商'));
    expect(mockNavigate).toHaveBeenCalledWith('/vendors/create');
  });

  it('navigates to edit page when a row is clicked', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByTestId('vendor-row-1')).toBeInTheDocument();
    }, WAIT_OPTS);
    fireEvent.click(screen.getByTestId('vendor-row-1'));
    expect(mockNavigate).toHaveBeenCalledWith('/vendors/1/edit');
  });

  it('updates search text when typing in search input', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜尋廠商名稱、聯絡人或營業項目')).toBeInTheDocument();
    }, WAIT_OPTS);
    const searchInput = screen.getByPlaceholderText('搜尋廠商名稱、聯絡人或營業項目');
    fireEvent.change(searchInput, { target: { value: 'alpha' } });
    expect(searchInput).toHaveValue('alpha');
  });

  it('renders business type filter select', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByText('營業項目篩選')).toBeInTheDocument();
    }, WAIT_OPTS);
  });

  it('renders rating filter select', async () => {
    renderVendorPage();
    await waitFor(() => {
      expect(screen.getByText('評價篩選')).toBeInTheDocument();
    }, WAIT_OPTS);
  });
});
