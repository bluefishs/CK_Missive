/**
 * DispatchFormFields Smoke Test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider, Form } from 'antd';
import zhTW from 'antd/locale/zh_TW';
import React from 'react';
import { createTestQueryClient } from '../../test/testUtils';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../services/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('../../components/common/ResponsiveFormRow', () => ({
  ResponsiveFormRow: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-form-row">{children}</div>
  ),
}));

vi.mock('../../types/api', () => ({
  TAOYUAN_WORK_TYPES: [
    '01.地上物查估作業',
    '02.土地協議市價查估作業',
    '03.土地徵收市價查估作業',
  ],
}));

// ============================================================================
// Helpers
// ============================================================================

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhTW}>
        <AntApp><MemoryRouter>{ui}</MemoryRouter></AntApp>
      </ConfigProvider>
    </QueryClientProvider>,
  );
}

/** Wrapper that provides a Form instance to DispatchFormFields */
const FormWrapper: React.FC<{ mode: 'create' | 'edit' | 'quick' }> = ({ mode }) => {
  const [form] = Form.useForm();
  // Dynamically import inside the component would be complex, so we import at top
  // and use a ref approach. For simplicity, we use a child component pattern.
  return (
    <Form form={form}>
      <DispatchFormFieldsLoader form={form} mode={mode} />
    </Form>
  );
};

// We need to import after mocks, so use lazy pattern
let DispatchFormFields: React.FC<{
  form: import('antd').FormInstance;
  mode: 'create' | 'edit' | 'quick';
}>;

const DispatchFormFieldsLoader: React.FC<{
  form: import('antd').FormInstance;
  mode: 'create' | 'edit' | 'quick';
}> = (props) => {
  if (!DispatchFormFields) return null;
  return <DispatchFormFields {...props} />;
};

// ============================================================================
// Tests
// ============================================================================

describe('DispatchFormFields', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const mod = await import('../../components/taoyuan/DispatchFormFields');
    DispatchFormFields = mod.DispatchFormFields;
  });

  it('renders without crashing in create mode', () => {
    const { container } = renderWithProviders(
      <FormWrapper mode="create" />
    );
    expect(container).toBeTruthy();
  });

  it('renders dispatch number field', () => {
    renderWithProviders(<FormWrapper mode="create" />);
    expect(screen.getByText('派工單號')).toBeInTheDocument();
  });

  it('renders project name field', () => {
    renderWithProviders(<FormWrapper mode="create" />);
    expect(screen.getByText('工程名稱/派工事項')).toBeInTheDocument();
  });

  it('renders in edit mode', () => {
    const { container } = renderWithProviders(
      <FormWrapper mode="edit" />
    );
    expect(container).toBeTruthy();
  });

  it('renders in quick mode', () => {
    const { container } = renderWithProviders(
      <FormWrapper mode="quick" />
    );
    expect(container).toBeTruthy();
  });
});
