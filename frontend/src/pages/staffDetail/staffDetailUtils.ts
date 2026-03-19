/**
 * StaffDetailPage utility functions
 * @description Shared helpers for staff detail sub-components
 */

/** Error response detail shape */
interface ErrorDetail {
  msg?: string;
}

/** Axios-like error response shape */
interface ApiErrorResponse {
  response?: {
    data?: {
      detail?: string | ErrorDetail[];
    };
  };
}

/** Extract a readable error message from an API error */
export const extractErrorMessage = (error: unknown): string => {
  const apiError = error as ApiErrorResponse;
  const detail = apiError?.response?.data?.detail;
  if (!detail) return '操作失敗，請稍後再試';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((e: ErrorDetail) => e.msg || JSON.stringify(e)).join(', ');
  }
  return JSON.stringify(detail);
};

/** Map certification type to tag color */
export const getCertTypeColor = (type: string): string => {
  switch (type) {
    case '核發證照': return 'blue';
    case '評量證書': return 'green';
    case '訓練證明': return 'orange';
    default: return 'default';
  }
};

/** Map certification status to tag color */
export const getCertStatusColor = (status: string): string => {
  switch (status) {
    case '有效': return 'success';
    case '已過期': return 'error';
    case '已撤銷': return 'default';
    default: return 'default';
  }
};
