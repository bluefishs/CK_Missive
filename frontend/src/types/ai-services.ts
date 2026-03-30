/**
 * AI 服務基礎設施型別 (SSOT)
 *
 * Ollama、RAG、回饋、分析、Agent、數位分身、語音、統計
 *
 * @domain ai-services
 * @version 1.0.0
 * @date 2026-03-29
 */

// ============================================================================
// Ollama 管理
// ============================================================================

export interface OllamaGpuLoadedModel {
  name: string;
  size: number;
  size_vram: number;
}

export interface OllamaGpuInfo {
  loaded_models: OllamaGpuLoadedModel[];
}

export interface OllamaStatusResponse {
  available: boolean;
  message: string;
  models: string[];
  required_models: string[];
  required_models_ready: boolean;
  missing_models: string[];
  gpu_info: OllamaGpuInfo | null;
  groq_available: boolean;
  groq_message: string;
}

export interface OllamaEnsureModelsResponse {
  ollama_available: boolean;
  installed: string[];
  pulled: string[];
  failed: string[];
}

export interface OllamaWarmupResponse {
  results: Record<string, boolean>;
  all_success: boolean;
}

// ============================================================================
// RAG 問答
// ============================================================================

export interface RAGQueryRequest {
  question: string;
  top_k?: number;
  similarity_threshold?: number;
}

export interface RAGSourceItem {
  document_id: number;
  doc_number: string;
  subject: string;
  doc_type: string;
  category: string;
  sender: string;
  receiver: string;
  doc_date: string;
  similarity: number;
}

export interface RAGQueryResponse {
  success: boolean;
  answer: string;
  sources: RAGSourceItem[];
  retrieval_count: number;
  latency_ms: number;
  model: string;
}

export interface RAGStreamRequest {
  question: string;
  top_k?: number;
  similarity_threshold?: number;
  history?: Array<{ role: string; content: string }>;
  session_id?: string;
}

// ============================================================================
// AI 回饋
// ============================================================================

export interface AIFeedbackSubmitRequest {
  conversation_id: string;
  message_index: number;
  feature_type: 'agent' | 'rag';
  score: 1 | -1;
  question?: string;
  answer_preview?: string;
  feedback_text?: string;
  latency_ms?: number;
  model?: string;
}

export interface AIFeedbackSubmitResponse {
  success: boolean;
  message: string;
}

export interface AIFeedbackStatsResponse {
  success: boolean;
  total_feedback: number;
  positive_count: number;
  negative_count: number;
  positive_rate: number;
  by_feature: Record<string, {
    total: number;
    positive: number;
    negative: number;
    positive_rate: number;
  }>;
  recent_negative: Array<{
    id: number;
    question?: string;
    answer_preview?: string;
    feature_type: string;
    created_at?: string;
  }>;
}

export interface AIAnalyticsOverviewResponse {
  success: boolean;
  ai_feature_usage: Record<string, {
    count: number;
    cache_hits: number;
    errors: number;
    avg_latency_ms: number;
  }>;
  feedback_summary: {
    total_feedback: number;
    positive_count: number;
    negative_count: number;
    positive_rate: number;
    by_feature: Record<string, unknown>;
  };
  search_stats: Record<string, unknown>;
  unused_features: string[];
}

// ============================================================================
// AI 分析持久化
// ============================================================================

export interface DocumentAIAnalysisResponse {
  id: number;
  document_id: number;
  summary?: string | null;
  summary_confidence?: number | null;
  suggested_doc_type?: string | null;
  doc_type_confidence?: number | null;
  suggested_category?: string | null;
  category_confidence?: number | null;
  classification_reasoning?: string | null;
  keywords?: string[] | null;
  keywords_confidence?: number | null;
  entities_count: number;
  relations_count: number;
  llm_provider?: string | null;
  llm_model?: string | null;
  processing_ms: number;
  status: string;
  is_stale: boolean;
  analyzed_at?: string | null;
}

export interface DocumentAIAnalysisStatsResponse {
  total_documents: number;
  analyzed_documents: number;
  stale_documents: number;
  without_analysis: number;
  coverage_percent: number;
  avg_processing_ms: number;
}

export interface DocumentAIAnalysisBatchResponse {
  success: boolean;
  processed: number;
  success_count: number;
  error_count: number;
  skip_count: number;
  message: string;
}

// ============================================================================
// SSE Callbacks
// ============================================================================

export type SSEErrorCode = 'RATE_LIMITED' | 'SERVICE_ERROR' | 'STREAM_TIMEOUT' | 'EMBEDDING_ERROR' | 'LLM_ERROR' | 'VALIDATION_ERROR';

export interface RAGStreamCallbacks {
  onSources: (sources: RAGQueryResponse['sources'], count: number) => void;
  onToken: (token: string) => void;
  onDone: (latencyMs: number, model: string) => void;
  onError?: (error: string, code?: SSEErrorCode) => void;
}

// ============================================================================
// Chat / Agent 共用型別
// ============================================================================

export interface AgentStepInfo {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'react' | 'self_awareness' | 'proactive_alert';
  step_index: number;
  step?: string;
  tool?: string;
  params?: Record<string, unknown>;
  summary?: string;
  count?: number;
  confidence?: number;
  action?: 'answer' | 'continue' | 'refine';
  identity?: string;
  personality?: string;
  message?: string;
  strengths?: string[];
  reasoning?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: RAGSourceItem[];
  latency_ms?: number;
  model?: string;
  retrieval_count?: number;
  streaming?: boolean;
  agentSteps?: AgentStepInfo[];
  toolsUsed?: string[];
  iterations?: number;
  feedbackScore?: 1 | -1 | null;
  agentIdentity?: string;
}

// ============================================================================
// Agent Stream Callbacks
// ============================================================================

export interface AgentStreamCallbacks {
  onThinking: (step: string, stepIndex: number) => void;
  onRole?: (identity: string, context: string) => void;
  onToolCall: (tool: string, params: Record<string, unknown>, stepIndex: number, reasoning?: string) => void;
  onToolResult: (tool: string, summary: string, count: number, stepIndex: number) => void;
  onReact?: (step: string, stepIndex: number, confidence: number, action: string) => void;
  onSelfAwareness?: (data: { identity: string; personality: string; strengths: string[]; alertCount: number }) => void;
  onProactiveAlert?: (message: string, count: number) => void;
  onSources: (sources: RAGQueryResponse['sources'], count: number) => void;
  onToken: (token: string) => void;
  onDone: (latencyMs: number, model: string, toolsUsed: string[], iterations: number) => void;
  onError?: (error: string, code?: SSEErrorCode) => void;
}

// ============================================================================
// Agent Topology
// ============================================================================

export interface AgentNode {
  id: string;
  type: 'leader' | 'engine' | 'role' | 'plugin';
  label: string;
  description: string;
  status: 'active' | 'degraded' | 'offline' | 'unknown';
  capabilities: string[];
  project: string;
  context?: string;
  triggers?: string[];
}

export interface AgentEdge {
  source: string;
  target: string;
  label: string;
  type: 'delegation' | 'data_flow';
}

export interface AgentTopologyResponse {
  nodes: AgentNode[];
  edges: AgentEdge[];
  meta: { total_nodes: number; total_edges: number; timestamp: string };
}

// ============================================================================
// Phase 3A 統計型別
// ============================================================================

export interface ToolSuccessRateItem {
  tool_name: string;
  total_calls: number;
  success_count: number;
  success_rate: number;
  avg_latency_ms: number;
  avg_result_count: number;
}

export interface ToolSuccessRatesResponse {
  tools: ToolSuccessRateItem[];
  degraded_tools: string[];
  source: string;
}

export interface AgentTraceQuery {
  context?: string;
  feedback_only?: boolean;
  limit?: number;
}

export interface AgentTracesResponse {
  traces: Record<string, unknown>[];
  total_count: number;
  route_distribution: Record<string, number>;
}

export interface TraceToolCallItem {
  tool_name: string;
  call_order: number;
  duration_ms: number;
  success: boolean;
  result_count: number;
  error_message?: string | null;
  created_at?: string | null;
}

export interface TraceDetailResponse {
  id: number;
  query_id: string;
  question: string;
  context?: string | null;
  route_type: string;
  total_ms: number;
  iterations: number;
  total_results: number;
  correction_triggered: boolean;
  react_triggered: boolean;
  plan_tool_count: number;
  model_used?: string | null;
  tools_used?: string[] | null;
  answer_preview?: string | null;
  feedback_score?: number | null;
  created_at?: string | null;
  tool_calls: TraceToolCallItem[];
}

export interface PatternItem {
  pattern_key: string;
  template: string;
  tool_sequence: string[];
  hit_count: number;
  success_rate: number;
  avg_latency_ms: number;
  score: number;
}

export interface PatternsResponse {
  patterns: PatternItem[];
  total_count: number;
}

export interface LearningsResponse {
  learnings: Record<string, unknown>[];
  stats: Record<string, unknown>;
}

export interface ProactiveAlertItem {
  alert_type: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  entity_type: string;
  entity_id?: number;
  metadata?: Record<string, unknown>;
}

export interface ProactiveAlertsResponse {
  total_alerts: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  alerts: ProactiveAlertItem[];
}

export interface DailyTrendItem {
  date: string;
  query_count: number;
  avg_latency_ms: number;
  avg_results: number;
  avg_feedback: number | null;
}

export interface DailyTrendResponse {
  trend: DailyTrendItem[];
  days: number;
}

export interface ToolRegistryItem {
  name: string;
  description: string;
  category: string;
  priority: number;
  contexts: string[];
  is_degraded: boolean;
  total_calls: number;
  success_rate: number;
  avg_latency_ms: number;
}

export interface ToolRegistryResponse {
  tools: ToolRegistryItem[];
  total_count: number;
  degraded_count: number;
}

// ============================================================================
// 語音轉文字
// ============================================================================

export interface VoiceTranscriptionResult {
  text: string;
  language: string;
  duration_ms: number;
  source: 'groq' | 'ollama';
}

// ============================================================================
// Digital Twin (數位分身)
// ============================================================================

export interface DelegateRequest {
  question: string;
  session_id?: string;
  context?: Record<string, unknown>;
}

export interface DigitalTwinStreamCallbacks {
  onToken: (token: string) => void;
  onDone: (latencyMs: number, answer?: string) => void;
  onError: (error: string) => void;
  onStatus?: (status: string, detail?: string) => void;
}

export interface TaskJobRecord {
  job_id: string;
  status: string;
  agent_id: string;
  input: string;
  result: string | null;
  error: string | null;
  source: string;
  correlation_id: string | null;
  approval_reason: string | null;
  approval_by: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// QA Impact Analysis
// ============================================================================

export interface QaAffectedModule {
  layer: 'backend' | 'frontend';
  category: string;
  files: string[];
  count: number;
  risk: 'high' | 'medium' | 'low';
}

export interface QaImpactResponse {
  success: boolean;
  changed_files_count: number;
  affected: QaAffectedModule[];
  recommendation: 'full_qa' | 'diff_aware_qa' | 'quick_qa' | 'no_changes';
  message: string;
  summary?: {
    backend_changes: number;
    frontend_changes: number;
    other_changes: number;
    high_risk_modules: number;
    has_migrations: boolean;
  };
  suggested_commands?: Record<string, string>;
  error?: string;
}
