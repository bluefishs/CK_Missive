/**
 * useAppNavigation Hook 單元測試
 * useAppNavigation Hook Unit Tests
 *
 * 測試導覽 Hook (需要 MemoryRouter wrapper)
 *
 * 執行方式:
 *   cd frontend && npm run test -- useAppNavigation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { useAppNavigation } from '../../hooks/utility/useAppNavigation';

// 建立 wrapper (需 Router context)
const createWrapper = () => {
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(MemoryRouter, null, children);
  return Wrapper;
};

// ============================================================================
// useAppNavigation Hook 測試
// ============================================================================

describe('useAppNavigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return all navigation functions', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.goBack).toBe('function');
    expect(typeof result.current.goTo).toBe('function');
    expect(typeof result.current.goToDocument).toBe('function');
    expect(typeof result.current.goToDocumentEdit).toBe('function');
    expect(typeof result.current.goToDocumentCreate).toBe('function');
    expect(typeof result.current.goToDocuments).toBe('function');
    expect(typeof result.current.goToDashboard).toBe('function');
  });

  it('goBack should navigate(-1)', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.goBack();
    });

    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it('goTo should navigate to the given path', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.goTo('/some/path');
    });

    expect(mockNavigate).toHaveBeenCalledWith('/some/path');
  });

  it('goToDocument should navigate to /documents/:id', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.goToDocument(42);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/documents/42');
  });

  it('goToDocumentEdit should navigate to /documents/:id/edit', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.goToDocumentEdit(7);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/documents/7/edit');
  });

  it('goToDocumentCreate should navigate to /documents/create', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.goToDocumentCreate();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/documents/create');
  });

  it('goToDocuments should navigate to /documents', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.goToDocuments();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/documents');
  });

  it('goToDashboard should navigate to /', () => {
    const { result } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.goToDashboard();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('functions should be stable references (useCallback)', () => {
    const { result, rerender } = renderHook(() => useAppNavigation(), {
      wrapper: createWrapper(),
    });

    const firstRender = { ...result.current };
    rerender();

    expect(result.current.goBack).toBe(firstRender.goBack);
    expect(result.current.goTo).toBe(firstRender.goTo);
    expect(result.current.goToDocument).toBe(firstRender.goToDocument);
    expect(result.current.goToDocumentEdit).toBe(firstRender.goToDocumentEdit);
    expect(result.current.goToDocumentCreate).toBe(firstRender.goToDocumentCreate);
    expect(result.current.goToDocuments).toBe(firstRender.goToDocuments);
    expect(result.current.goToDashboard).toBe(firstRender.goToDashboard);
  });
});
