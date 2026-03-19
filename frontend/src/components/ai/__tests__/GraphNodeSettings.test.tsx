/**
 * GraphNodeSettings 元件測試
 *
 * @version 1.0.0
 * @created 2026-03-15
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { App, ConfigProvider } from 'antd';

const { mockGetUserOverrides, mockSaveUserOverrides, mockResetUserOverrides } = vi.hoisted(
  () => ({
    mockGetUserOverrides: vi.fn(() => ({})),
    mockSaveUserOverrides: vi.fn(),
    mockResetUserOverrides: vi.fn(),
  }),
);

vi.mock('../../../config/graphNodeConfig', () => ({
  GRAPH_NODE_CONFIG: {
    document: { color: '#1890ff', label: '公文', description: '公文節點', radius: 6 },
    dispatch: { color: '#52c41a', label: '派工', description: '派工節點', radius: 5 },
    agency: { color: '#fa8c16', label: '機關', description: '機關節點', radius: 7 },
    project: { color: '#722ed1', label: '工程', description: '工程節點', radius: 6 },
    person: { color: '#eb2f96', label: '人物', description: '人物節點', radius: 5 },
    location: { color: '#13c2c2', label: '地點', description: '地點節點', radius: 5 },
    date: { color: '#bfbfbf', label: '日期', description: '日期節點', radius: 4 },
  },
  getUserOverrides: mockGetUserOverrides,
  saveUserOverrides: mockSaveUserOverrides,
  resetUserOverrides: mockResetUserOverrides,
}));

import { GraphNodeSettings } from '../GraphNodeSettings';

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider>
      <App>{children}</App>
    </ConfigProvider>
  );
}

describe('GraphNodeSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetUserOverrides.mockReturnValue({});
  });

  it('open=false 時抽屜不可見', () => {
    render(
      <Wrapper>
        <GraphNodeSettings open={false} onClose={vi.fn()} />
      </Wrapper>,
    );
    const drawer = document.querySelector('.ant-drawer');
    if (drawer) {
      expect(drawer.classList.contains('ant-drawer-open')).toBe(false);
    }
  });

  it('open=true 時渲染抽屜標題', () => {
    render(
      <Wrapper>
        <GraphNodeSettings open={true} onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(screen.getByText('知識圖譜節點設定')).toBeInTheDocument();
  });

  it('渲染操作提示', () => {
    render(
      <Wrapper>
        <GraphNodeSettings open={true} onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(
      screen.getByText(/僅顯示圖譜中實際存在的節點類型/),
    ).toBeInTheDocument();
  });

  it('渲染重置按鈕', () => {
    render(
      <Wrapper>
        <GraphNodeSettings open={true} onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(screen.getByText('重置')).toBeInTheDocument();
  });

  it('activeTypes 過濾僅顯示存在的節點群組', () => {
    const activeTypes = new Set(['document', 'agency']);
    render(
      <Wrapper>
        <GraphNodeSettings open={true} onClose={vi.fn()} activeTypes={activeTypes} />
      </Wrapper>,
    );
    expect(screen.getByText('公文 / 派工')).toBeInTheDocument();
    expect(screen.queryByText('人物 / 地點')).not.toBeInTheDocument();
  });

  it('所有群組都有時渲染節點類型群組', () => {
    render(
      <Wrapper>
        <GraphNodeSettings open={true} onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(screen.getByText('公文 / 派工')).toBeInTheDocument();
    expect(screen.getByText('人物 / 地點')).toBeInTheDocument();
  });

  it('載入覆蓋設定', () => {
    mockGetUserOverrides.mockReturnValue({
      document: { color: '#ff0000' },
    });
    render(
      <Wrapper>
        <GraphNodeSettings open={true} onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(mockGetUserOverrides).toHaveBeenCalled();
  });

  it('open 時重新載入設定', () => {
    const { rerender } = render(
      <Wrapper>
        <GraphNodeSettings open={false} onClose={vi.fn()} />
      </Wrapper>,
    );
    const callCount = mockGetUserOverrides.mock.calls.length;
    rerender(
      <Wrapper>
        <GraphNodeSettings open={true} onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(mockGetUserOverrides.mock.calls.length).toBeGreaterThan(callCount);
  });

  it('渲染節點類型標籤', () => {
    render(
      <Wrapper>
        <GraphNodeSettings
          open={true}
          onClose={vi.fn()}
          activeTypes={new Set(['document', 'dispatch'])}
        />
      </Wrapper>,
    );
    // Node type labels from GRAPH_NODE_CONFIG
    expect(document.body.textContent).toContain('公文');
    expect(document.body.textContent).toContain('派工');
  });
});
