import type { FC } from 'react';
import { Tree, Button, Space, Popconfirm, Tag, Tooltip } from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  SafetyOutlined, HolderOutlined, FolderOutlined,
  LinkOutlined, TabletOutlined,
} from '@ant-design/icons';
import type { NavigationItem } from '../../../types/navigation';
import type { TreeNodeHandlers, NavigationTreeViewProps } from './types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const getNavigationType = (
  item: NavigationItem
): { type: 'tab' | 'page' | 'group'; tabKey?: string } => {
  if (item.children && item.children.length > 0) return { type: 'group' };
  if (!item.path) return { type: 'group' };
  if (item.path.includes('?tab=')) {
    const match = item.path.match(/\?tab=([^&]+)/);
    return { type: 'tab', tabKey: match?.[1] };
  }
  return { type: 'page' };
};

// ---------------------------------------------------------------------------
// Tree node renderer (pure function, receives handlers via closure)
// ---------------------------------------------------------------------------

const renderTreeNode = (
  item: NavigationItem,
  handlers: TreeNodeHandlers,
): React.ReactNode => {
  const navType = getNavigationType(item);

  return (
    <div className="tree-node-content">
      <Space>
        {navType.type === 'tab' && (
          <Tooltip title={`分頁連結 (tab=${navType.tabKey})`}>
            <Tag color="cyan" icon={<TabletOutlined />}>Tab</Tag>
          </Tooltip>
        )}
        {navType.type === 'page' && (
          <Tooltip title="頁面連結">
            <Tag color="blue" icon={<LinkOutlined />}>Page</Tag>
          </Tooltip>
        )}
        {navType.type === 'group' && (
          <Tooltip title="群組容器 (無連結)">
            <Tag color="default" icon={<FolderOutlined />}>Group</Tag>
          </Tooltip>
        )}
        <span className="tree-node-title">{item.title}</span>
        <span className="tree-node-path">({item.path || item.key})</span>
        {!item.is_visible && <Tag color="orange">隱藏</Tag>}
        {!item.is_enabled && <Tag color="red">停用</Tag>}
        {item.permission_required && (
          <Tag color="purple" icon={<SafetyOutlined />}>需要權限</Tag>
        )}
      </Space>
      <Space className="tree-node-actions">
        <Tooltip title="新增子項目">
          <Button
            type="link"
            size="small"
            icon={<PlusOutlined />}
            onClick={(e) => { e.stopPropagation(); handlers.onAddChild(item); }}
          />
        </Tooltip>
        <Tooltip title="編輯">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={(e) => { e.stopPropagation(); handlers.onEdit(item); }}
          />
        </Tooltip>
        <Tooltip title="刪除">
          <Popconfirm
            title="確定刪除此項目？"
            description="刪除後將立即從導覽選單中移除"
            onConfirm={() => handlers.onDelete(item.id)}
            okText="確定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Popconfirm>
        </Tooltip>
      </Space>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Public: convert NavigationItem[] to tree data with rendered nodes
// ---------------------------------------------------------------------------

// eslint-disable-next-line react-refresh/only-export-components
export const convertToTreeData = (
  items: NavigationItem[],
  handlers: TreeNodeHandlers,
): import('./types').TreeNodeData[] => {
  if (!items || items.length === 0) return [];
  return items.map(item => ({
    title: renderTreeNode(item, handlers),
    key: item.id,
    id: item.id,
    parent_id: item.parent_id,
    children: item.children ? convertToTreeData(item.children, handlers) : [],
  }));
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const NavigationTreeView: FC<NavigationTreeViewProps> = ({
  treeData,
  expandedKeys,
  onExpandedKeysChange,
  isDragging,
  onDragStart,
  onDragEnd,
  onDrop,
}) => (
  <Tree
    showLine={{ showLeafIcon: false }}
    draggable={{
      icon: <HolderOutlined style={{ cursor: 'grab', color: '#999', marginRight: 8 }} />,
      nodeDraggable: () => true,
    }}
    blockNode
    expandedKeys={expandedKeys}
    onExpand={onExpandedKeysChange}
    onDragStart={onDragStart}
    onDragEnd={onDragEnd}
    onDrop={onDrop}
    allowDrop={() => true}
    treeData={treeData}
    className={`navigation-tree ${isDragging ? 'is-dragging' : ''}`}
  />
);
