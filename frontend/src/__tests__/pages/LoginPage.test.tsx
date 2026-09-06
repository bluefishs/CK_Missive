/**
 * LoginPage 測試 — 2026-09-06 重寫
 *
 * 原本 12 支測的是帳密表單（品牌標題／帳號密碼欄位／快速進入／註冊連結…）。
 * 那個表單 v5.9.4（ADR-0033）就整個移除了，/login 只剩一個 legacy redirect 到 /entry；
 * 12 支自那天起全紅，而沒有人跑前端測試所以沒人知道（A111）。
 * 現在只驗它唯一還在做的事：導向 /entry，且保留 returnUrl。
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import React from 'react';
import LoginPage from '../../pages/LoginPage';
import { ROUTES } from '../../router/types';

const LocationProbe: React.FC = () => {
  const loc = useLocation();
  return <div data-testid="loc">{loc.pathname + loc.search}</div>;
};

const renderAt = (initial: string) =>
  render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path={ROUTES.ENTRY} element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );

describe('LoginPage（legacy redirect）', () => {
  it('導向 /entry', () => {
    renderAt('/login');
    expect(screen.getByTestId('loc').textContent).toBe(ROUTES.ENTRY);
  });

  it('保留 returnUrl 並做 URL 編碼', () => {
    renderAt('/login?returnUrl=/documents?page=2');
    expect(screen.getByTestId('loc').textContent).toBe(
      `${ROUTES.ENTRY}?returnUrl=${encodeURIComponent('/documents?page=2')}`,
    );
  });

  it('不再渲染帳密表單（ADR-0033）', () => {
    renderAt('/login');
    expect(screen.queryByText('帳號密碼登入')).toBeNull();
    expect(document.querySelector('input[type="password"]')).toBeNull();
  });
});
