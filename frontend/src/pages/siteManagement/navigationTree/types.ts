import type { Key } from 'react';
import type { NavigationItem } from '../../../types/navigation';
import type { NavigationFormValues } from '../../../types/forms';

export interface TreeNodeData {
  title: React.ReactNode;
  key: number;
  id: number;
  parent_id: number | null;
  children: TreeNodeData[];
}

export type FormValues = NavigationFormValues;

export interface ValidPath {
  path: string | null;
  description: string;
}

export interface TreeSelectOption {
  title: string;
  value: number;
  key: number;
  children?: TreeSelectOption[];
}

/** Handlers passed from the orchestrator to the tree view */
export interface TreeNodeHandlers {
  onAddChild: (item: NavigationItem) => void;
  onEdit: (item: NavigationItem) => void;
  onDelete: (id: number) => Promise<void>;
}

/** Props for NavigationTreeView */
export interface NavigationTreeViewProps {
  treeData: TreeNodeData[];
  expandedKeys: Key[];
  onExpandedKeysChange: (keys: Key[]) => void;
  isDragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDrop: (info: Parameters<NonNullable<import('antd').TreeProps['onDrop']>>[0]) => void;
}

/** Props for NavigationFormModal */
export interface NavigationFormModalProps {
  open: boolean;
  editingItem: NavigationItem | null;
  /** Pre-filled parent_id when adding a child (ignored when editingItem is set) */
  defaultParentId: number | null;
  parentOptions: TreeSelectOption[];
  validPaths: ValidPath[];
  confirmLoading: boolean;
  onSubmit: (values: FormValues) => Promise<void>;
  onCancel: () => void;
}
