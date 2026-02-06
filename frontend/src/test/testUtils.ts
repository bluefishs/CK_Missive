/**
 * Shared Test Utilities
 *
 * Provides reusable mock factories, QueryClient helpers, and wrapper components
 * for frontend unit and integration tests.
 *
 * @version 1.0.0
 * @date 2026-02-06
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type {
  OfficialDocument,
  Project,
  Agency,
  AgencyWithStats,
  Vendor,
} from '@/types/api';
import type { PaginatedResponse } from '@/api/types';

// ============================================================================
// QueryClient Helpers
// ============================================================================

/**
 * Create a QueryClient configured for testing.
 *
 * - retry: false to fail fast
 * - gcTime: 0 to avoid stale cache between tests
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Create a wrapper component for renderHook that provides QueryClientProvider.
 *
 * @example
 * ```ts
 * const wrapper = createWrapper();
 * const { result } = renderHook(() => useMyHook(), { wrapper });
 * ```
 */
export function createWrapper(): React.FC<{ children: React.ReactNode }> {
  const queryClient = createTestQueryClient();
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  return Wrapper;
}

// ============================================================================
// Generic Mock Factories
// ============================================================================

/**
 * Build a mock PaginatedResponse for any entity type.
 *
 * @param items  - array of entity objects
 * @param overrides - partial pagination metadata overrides
 */
export function createMockPaginatedResponse<T>(
  items: T[],
  overrides: Partial<PaginatedResponse<T>['pagination']> = {},
): PaginatedResponse<T> {
  return {
    success: true as const,
    items,
    pagination: {
      total: items.length,
      page: 1,
      limit: 20,
      total_pages: 1,
      has_next: false,
      has_prev: false,
      ...overrides,
    },
  };
}

// ============================================================================
// Entity Mock Factories
// ============================================================================

let _idCounter = 1000;

/** Reset the auto-increment counter (call in beforeEach if needed) */
export function resetIdCounter(): void {
  _idCounter = 1000;
}

function nextId(): number {
  return _idCounter++;
}

/**
 * Create a mock OfficialDocument with sensible defaults.
 * Every call produces a unique id unless overridden.
 */
export function createMockDocument(
  overrides: Partial<OfficialDocument> = {},
): OfficialDocument {
  const id = overrides.id ?? nextId();
  return {
    id,
    doc_number: `DOC-${String(id).padStart(4, '0')}`,
    subject: `Test Document ${id}`,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

/**
 * Create a mock Project with sensible defaults.
 */
export function createMockProject(
  overrides: Partial<Project> = {},
): Project {
  const id = overrides.id ?? nextId();
  return {
    id,
    project_name: `Test Project ${id}`,
    project_code: `PROJ-${id}`,
    year: 2026,
    status: 'in_progress',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

/**
 * Create a mock Agency (base interface without stats).
 */
export function createMockAgency(
  overrides: Partial<Agency> = {},
): Agency {
  const id = overrides.id ?? nextId();
  return {
    id,
    agency_name: `Test Agency ${id}`,
    agency_type: '地方機關',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

/**
 * Create a mock AgencyWithStats (extends Agency with statistics).
 */
export function createMockAgencyWithStats(
  overrides: Partial<AgencyWithStats> = {},
): AgencyWithStats {
  const base = createMockAgency(overrides);
  return {
    ...base,
    document_count: 0,
    sent_count: 0,
    received_count: 0,
    last_activity: null,
    primary_type: 'unknown',
    ...overrides,
  };
}

/**
 * Create a mock Vendor with sensible defaults.
 */
export function createMockVendor(
  overrides: Partial<Vendor> = {},
): Vendor {
  const id = overrides.id ?? nextId();
  return {
    id,
    vendor_name: `Test Vendor ${id}`,
    vendor_code: `VND-${id}`,
    business_type: '測量業務',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}
