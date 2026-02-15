export { useProjectWorkData } from './useProjectWorkData';
export type {
  DispatchCorrespondenceGroup,
  BatchGroup,
  WorkOverviewStats,
} from './useProjectWorkData';
export {
  getBatchColor,
  BATCH_COLORS,
  milestoneLabel,
  milestoneColor,
  statusLabel,
  statusColor,
} from './useProjectWorkData';

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
export { buildChains, flattenChains, getEffectiveDoc, getEffectiveDocId, getDocDirection, isOutgoingDocNumber, buildDocPairs } from './chainUtils';
export type { DocPair, DocPairs } from './chainUtils';
export type { ChainNode } from './chainUtils';
export {
  WORK_CATEGORY_GROUPS,
  WORK_CATEGORY_LABELS,
  WORK_CATEGORY_COLORS,
  CHAIN_STATUS_OPTIONS,
  getCategoryLabel,
  getCategoryColor,
  getStatusLabel,
  getStatusColor,
} from './chainConstants';
