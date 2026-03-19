import { useState, useMemo, useCallback, useRef } from 'react';
import type { FC, Key } from 'react';
import { Button, Space, Card, Tag, Tooltip, Alert, App } from 'antd';
import type { TreeProps } from 'antd';
import { PlusOutlined, ReloadOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { secureApiService } from '../../services/secureApiService';
import { navigationService } from '../../services/navigationService';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { logger } from '../../utils/logger';
import type { NavigationItem } from '../../types/navigation';
import {
  NavigationTreeView,
  NavigationFormModal,
  convertToTreeData,
  FALLBACK_VALID_PATHS,
} from './navigationTree';
import type {
  TreeNodeData,
  FormValues,
  ValidPath,
  TreeSelectOption,
  TreeNodeHandlers,
} from './navigationTree';

const findItemById = (items: NavigationItem[], id: number): NavigationItem | null => {
  if (!items || items.length === 0) return null;
  for (const item of items) {
    if (item.id === id) return item;
    if (item.children) {
      const found = findItemById(item.children, id);
      if (found) return found;
    }
  }
  return null;
};

const getAllKeys = (items: NavigationItem[]): Key[] => {
  let keys: Key[] = [];
  items.forEach(item => {
    keys.push(item.id);
    if (item.children && item.children.length > 0) {
      keys = keys.concat(getAllKeys(item.children));
    }
  });
  return keys;
};

export const NavigationTreePanel: FC = () => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // Modal / form state
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<NavigationItem | null>(null);
  const [defaultParentId, setDefaultParentId] = useState<number | null>(null);

  // Tree state
  const [expandedKeys, setExpandedKeys] = useState<Key[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const stableTreeDataRef = useRef<TreeNodeData[]>([]);

  // Data fetching
  const { data: navData, isLoading: loading } = useQuery({
    queryKey: ['site-navigation'],
    queryFn: async () => {
      const result = await secureApiService.getNavigationItems() as { items?: NavigationItem[] };
      const items = result.items || [];
      setExpandedKeys(getAllKeys(items));
      return { items, lastUpdated: new Date() };
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const navigationItems = useMemo(() => navData?.items ?? [], [navData?.items]);
  const lastUpdated = navData?.lastUpdated ?? null;

  const { data: validPaths = [] } = useQuery({
    queryKey: ['site-valid-paths'],
    queryFn: async () => {
      try {
        const result = await secureApiService.getValidPaths() as {
          success?: boolean;
          data?: { paths?: ValidPath[] };
        };
        if (result.success && result.data?.paths) {
          return result.data.paths;
        }
      } catch (error) {
        logger.error('Failed to load valid paths:', error);
      }
      return FALLBACK_VALID_PATHS;
    },
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const loadNavigation = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['site-navigation'] });
  }, [queryClient]);

  // After-mutation helper
  const refreshAfterMutation = useCallback(() => {
    navigationService.clearNavigationCache();
    // Invalidate both local and Layout navigation queries
    queryClient.invalidateQueries({ queryKey: ['site-navigation'] });
    queryClient.invalidateQueries({ queryKey: ['navigation'] });
    window.dispatchEvent(new CustomEvent('navigation-updated'));
  }, [queryClient]);

  // CRUD handlers
  const handleSubmit = async (values: FormValues): Promise<void> => {
    try {
      const actualParentId = values.parent_id === 0 ? null : values.parent_id;

      let calculatedLevel = 1;
      if (actualParentId !== null && actualParentId !== undefined) {
        const parentItem = findItemById(navigationItems, actualParentId);
        if (parentItem) {
          calculatedLevel = parentItem.level + 1;
        }
      }

      const submitData = {
        ...values,
        parent_id: actualParentId,
        level: calculatedLevel,
        sort_order: values.sort_order || editingItem?.sort_order || 0,
      };

      if (editingItem) {
        await secureApiService.updateNavigationItem({ id: editingItem.id, ...submitData });
        message.success('更新成功');
      } else {
        await secureApiService.createNavigationItem(submitData);
        message.success('新增成功');
      }

      setModalVisible(false);
      setEditingItem(null);
      setDefaultParentId(null);
      refreshAfterMutation();
    } catch (error) {
      logger.error('Submit error:', error);
      message.error('操作失敗');
    }
  };

  const handleDelete = async (id: number): Promise<void> => {
    try {
      await secureApiService.deleteNavigationItem(id);
      message.success('刪除成功');
      refreshAfterMutation();
    } catch (error) {
      logger.error('Delete error:', error);
      message.error('刪除失敗');
    }
  };

  // Modal openers
  const handleEdit = (item: NavigationItem): void => {
    setEditingItem(item);
    setDefaultParentId(null);
    setModalVisible(true);
  };

  const handleAddChild = (item: NavigationItem): void => {
    setEditingItem(null);
    setDefaultParentId(item.id);
    setModalVisible(true);
  };

  const handleAddTopLevel = (): void => {
    setEditingItem(null);
    setDefaultParentId(null);
    setModalVisible(true);
  };

  // Drag-and-drop
  const handleDrop: TreeProps['onDrop'] = async (info) => {
    if (!Array.isArray(navigationItems) || navigationItems.length === 0) {
      message.error('導覽資料載入失敗');
      setIsDragging(false);
      return;
    }

    const dropKey = info.node.key as number;
    const dragKey = info.dragNode.key as number;
    const dropPos = info.node.pos.split('-');
    const dropPosition = info.dropPosition - Number(dropPos[dropPos.length - 1]);

    const draggedItem = findItemById(navigationItems, dragKey);
    const targetItem = findItemById(navigationItems, dropKey);

    if (!draggedItem || !targetItem) {
      message.error('找不到拖曳項目');
      return;
    }

    try {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { children: _c, id: _id, created_at: _ca, updated_at: _ua, ...itemData } = draggedItem;

      if (dropPosition === 0) {
        const targetChildren = targetItem.children || [];
        const newSortOrder = targetChildren.length > 0
          ? Math.max(...targetChildren.map(c => c.sort_order)) + 1
          : 1;
        await secureApiService.updateNavigationItem({
          ...itemData, id: dragKey,
          parent_id: targetItem.id,
          level: targetItem.level + 1,
          sort_order: newSortOrder,
        });
        message.success('已移入目標項目');
      } else {
        const newSortOrder = dropPosition < 0
          ? targetItem.sort_order
          : targetItem.sort_order + 1;
        await secureApiService.updateNavigationItem({
          ...itemData, id: dragKey,
          parent_id: targetItem.parent_id,
          level: targetItem.level,
          sort_order: newSortOrder,
        });
        message.success('已調整順序');
      }
      refreshAfterMutation();
    } catch (error) {
      logger.error('Drag-drop error:', error);
      message.error('移動失敗');
    }
    setIsDragging(false);
  };

  // Tree node handlers (passed to convertToTreeData)
  const treeNodeHandlers: TreeNodeHandlers = useMemo(() => ({
    onAddChild: handleAddChild,
    onEdit: handleEdit,
    onDelete: handleDelete,
  // eslint-disable-next-line react-hooks/exhaustive-deps -- handlers reference stable state setters
  }), [navigationItems]);

  // Derived data
  const parentOptions = useMemo(() => {
    const getDescendantIds = (item: NavigationItem): number[] => {
      let ids = [item.id];
      if (item.children) {
        item.children.forEach(child => { ids = ids.concat(getDescendantIds(child)); });
      }
      return ids;
    };

    let excludeIds: Set<number> = new Set();
    if (editingItem?.id) {
      const itemToExclude = findItemById(navigationItems, editingItem.id);
      if (itemToExclude) {
        excludeIds = new Set(getDescendantIds(itemToExclude));
      }
    }

    const buildOptions = (items: NavigationItem[]): TreeSelectOption[] => {
      if (!items || items.length === 0) return [];
      const options: TreeSelectOption[] = [];
      items.forEach(item => {
        if (excludeIds.has(item.id)) return;
        const option: TreeSelectOption = { title: item.title, value: item.id, key: item.id };
        if (item.children && item.children.length > 0) {
          const childOptions = buildOptions(item.children);
          if (childOptions.length > 0) option.children = childOptions;
        }
        options.push(option);
      });
      return options;
    };

    const topLevelOption: TreeSelectOption = { title: '📁 頂層（無父層）', value: 0, key: 0 };
    return [topLevelOption, ...buildOptions(navigationItems)];
  }, [navigationItems, editingItem]);

  const treeData = useMemo(() => {
    const newTreeData = convertToTreeData(navigationItems, treeNodeHandlers);
    if (!isDragging) {
      stableTreeDataRef.current = newTreeData;
    }
    return isDragging ? stableTreeDataRef.current : newTreeData;
  }, [navigationItems, isDragging, treeNodeHandlers]);

  return (
    <Card
      title="導覽選單設定"
      extra={
        <Space>
          <Tooltip title="最後更新時間">
            <Tag icon={<ClockCircleOutlined />} color="blue">
              {lastUpdated ? lastUpdated.toLocaleTimeString('zh-TW') : '未載入'}
            </Tag>
          </Tooltip>
          <Button icon={<ReloadOutlined />} onClick={loadNavigation} loading={loading}>
            重新整理
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddTopLevel}>
            新增頂層項目
          </Button>
        </Space>
      }
    >
      <Alert
        title="即時同步已啟用"
        description="新增、編輯或刪除項目後，導覽選單會立即更新。可拖曳調整結構（支援拖曳至項目內）。"
        type="success"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <NavigationTreeView
        treeData={treeData}
        expandedKeys={expandedKeys}
        onExpandedKeysChange={setExpandedKeys}
        isDragging={isDragging}
        onDragStart={() => setIsDragging(true)}
        onDragEnd={() => setIsDragging(false)}
        onDrop={handleDrop}
      />

      <NavigationFormModal
        open={modalVisible}
        editingItem={editingItem}
        defaultParentId={defaultParentId}
        parentOptions={parentOptions}
        validPaths={validPaths}
        confirmLoading={loading}
        onSubmit={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingItem(null);
          setDefaultParentId(null);
        }}
      />
    </Card>
  );
};
