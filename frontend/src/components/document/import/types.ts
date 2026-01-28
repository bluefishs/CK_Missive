export interface PreviewRow {
  row: number;
  data: Record<string, unknown>;
  status: 'valid' | 'warning';
  issues: string[];
  action: 'insert' | 'update';
}

export interface PreviewResult {
  success: boolean;
  filename: string;
  total_rows: number;
  preview_rows: PreviewRow[];
  headers: string[];
  validation: {
    missing_required_fields: string[];
    invalid_categories: number[];
    invalid_doc_types: number[];
    duplicate_doc_numbers: number[];
    existing_in_db: number[];
    will_insert: number;
    will_update: number;
  };
  errors: string[];
}

export interface ImportResult {
  success: boolean;
  filename: string;
  total_rows: number;
  inserted: number;
  updated: number;
  skipped: number;
  errors: string[];
  details?: Array<{
    row: number;
    status: string;
    message: string;
    doc_number: string;
  }>;
}

export type ImportStep = 'upload' | 'preview' | 'result';
