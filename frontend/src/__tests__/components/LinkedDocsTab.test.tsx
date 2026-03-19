/**
 * LinkedDocsTab 單元測試
 *
 * 測試 PM 案件關聯公文頁籤的三種狀態：載入中 / 無文件 / 有文件
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('../../hooks/business/usePMCases', () => ({
  usePMLinkedDocuments: vi.fn(),
}));

import LinkedDocsTab from '../../pages/pmCase/LinkedDocsTab';
import { usePMLinkedDocuments } from '../../hooks/business/usePMCases';

describe('LinkedDocsTab', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    vi.clearAllMocks();
  });

  it('shows empty when no documents', () => {
    vi.mocked(usePMLinkedDocuments).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof usePMLinkedDocuments>);

    render(<LinkedDocsTab caseCode="CK2025_PM_01_001" />);
    expect(screen.getByText('此案號尚無關聯公文')).toBeTruthy();
  });

  it('renders document table with data', () => {
    vi.mocked(usePMLinkedDocuments).mockReturnValue({
      data: [
        { id: 1, doc_number: 'DOC-001', subject: '測試公文', doc_type: '收文', doc_date: '2025-01-15' },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof usePMLinkedDocuments>);

    render(<LinkedDocsTab caseCode="CK2025_PM_01_001" />);
    expect(screen.getByText('DOC-001')).toBeTruthy();
    expect(screen.getByText('測試公文')).toBeTruthy();
  });

  it('shows loading state', () => {
    vi.mocked(usePMLinkedDocuments).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof usePMLinkedDocuments>);

    const { container } = render(<LinkedDocsTab caseCode="CK2025_PM_01_001" />);
    expect(container.querySelector('.ant-spin')).toBeTruthy();
  });
});
