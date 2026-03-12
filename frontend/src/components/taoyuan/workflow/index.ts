// === Data hooks ===
export { useProjectWorkData } from './useProjectWorkData';
export type {
  DispatchCorrespondenceGroup,
  BatchGroup,
  WorkOverviewStats,
  WorkTypeStageInfo,
} from './useProjectWorkData';
export {
  getBatchColor,
  BATCH_COLORS,
} from './useProjectWorkData';

// === 常數（統一來源：workCategoryConstants.ts） ===
export {
  milestoneLabel,
  milestoneColor,
  statusLabel,
  statusColor,
  getCategoryLabel,
  getCategoryColor,
  MILESTONE_LABELS,
  MILESTONE_COLORS,
  STATUS_LABELS,
  STATUS_COLORS,
  WORK_CATEGORY_GROUPS,
  WORK_CATEGORY_LABELS,
  WORK_CATEGORY_COLORS,
} from './workCategoryConstants';
export type { WorkCategoryItem, WorkCategoryGroup } from './workCategoryConstants';

// === chainConstants (鏈式視圖專用) ===
export {
  CHAIN_STATUS_OPTIONS,
  getStatusLabel,
  getStatusColor,
} from './chainConstants';

// === View components ===
export { CorrespondenceMatrix } from './CorrespondenceMatrix';
export { CorrespondenceBody, DocEntry } from './CorrespondenceBody';
export type { CorrespondenceBodyData, CorrespondenceBodyProps } from './CorrespondenceBody';
export { WorkflowTimelineView } from './WorkflowTimelineView';
export { WorkflowKanbanView } from './WorkflowKanbanView';

// InlineRecordCreator (v1.0.0)
export { InlineRecordCreator } from './InlineRecordCreator';
export type { InlineRecordCreatorProps } from './InlineRecordCreator';

// Chain-based timeline (v2.0.0)
export { ChainTimeline } from './ChainTimeline';
export type { ChainTimelineProps } from './ChainTimeline';

// === chainUtils ===
export {
  buildChains,
  flattenChains,
  getEffectiveDoc,
  getEffectiveDocId,
  getDocDirection,
  isOutgoingDocNumber,
  buildDocPairs,
  buildCorrespondenceMatrix,
  filterBlankRecords,
  computeDocStats,
  computeCurrentStage,
} from './chainUtils';
export type { DocPair, DocPairs, MatrixDocItem, CorrespondenceMatrixRow, EntityPairScore, ChainNode } from './chainUtils';

// === 共用元件 (v2.0.0 模組化) ===
export { WorkRecordStatsCard } from './WorkRecordStatsCard';
export type { WorkRecordStatsCardProps } from './WorkRecordStatsCard';
export { useWorkRecordColumns } from './useWorkRecordColumns';
export type { UseWorkRecordColumnsOptions } from './useWorkRecordColumns';
export { useDeleteWorkRecord } from './useDeleteWorkRecord';
