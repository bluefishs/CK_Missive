/** api-knowledge — 知識庫瀏覽器/實體配對型別 */

// ============================================================================
// 知識庫瀏覽器 (Knowledge Base)
// ============================================================================

export interface FileInfo {
  name: string;
  path: string;
}

export interface SectionInfo {
  name: string;
  path: string;
  files: FileInfo[];
}

export interface TreeResponse {
  success: boolean;
  sections: SectionInfo[];
}

export interface FileContentResponse {
  success: boolean;
  content: string;
  filename: string;
}

export interface AdrInfo {
  number: string;
  title: string;
  status: string;
  date: string;
  path: string;
}

export interface AdrListResponse {
  success: boolean;
  items: AdrInfo[];
}

export interface DiagramInfo {
  name: string;
  path: string;
  title: string;
}

export interface DiagramListResponse {
  success: boolean;
  items: DiagramInfo[];
}

export interface KBSearchResult {
  file_path: string;
  filename: string;
  excerpt: string;
  line_number: number;
  relevance_score: number;
}

export interface KBSearchResponse {
  success: boolean;
  results: KBSearchResult[];
  total: number;
}

// ============================================================================
// Dispatch Entity Matching
// ============================================================================

/** 實體配對 API 回應型別 */
export interface EntitySimilarityPair {
  incoming_doc_id: number;
  outgoing_doc_id: number;
  shared_entity_count: number;
  jaccard: number;
  shared_entities: string[];
}

export interface EntitySimilarityResponse {
  success: boolean;
  pairs: EntitySimilarityPair[];
  total_entities: number;
  incoming_count?: number;
  outgoing_count?: number;
}

/** NER 公文對照建議型別 */
export interface CorrespondenceSuggestion {
  incoming_doc_id: number;
  outgoing_doc_id: number;
  confidence: 'confirmed' | 'high' | 'medium' | 'low';
  score: number;
  shared_entity_count: number;
  shared_entities: string[];
  incoming_doc?: {
    doc_id: number;
    link_type: string;
    doc_number: string | null;
    subject: string | null;
    doc_date: string | null;
  };
  outgoing_doc?: {
    doc_id: number;
    link_type: string;
    doc_number: string | null;
    subject: string | null;
    doc_date: string | null;
  };
}

export interface DispatchEntityInfo {
  id: number;
  name: string;
  type: string;
}

export interface CorrespondenceSuggestionsResponse {
  success: boolean;
  suggestions: CorrespondenceSuggestion[];
  dispatch_entities: DispatchEntityInfo[];
  stats?: {
    incoming_count: number;
    outgoing_count: number;
    total_suggestions: number;
    confirmed: number;
    high: number;
    medium: number;
  };
  message?: string;
}
