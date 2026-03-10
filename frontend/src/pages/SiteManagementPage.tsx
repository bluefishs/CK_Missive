/**
 * Site Management Page - Navigation Menu Management
 * @description 導覽選單管理頁面 - 新版 UI（與 Webmap 一致）
 * @version 2.0.0 - 2026-01-10 升級為新版介面
 */

import { useState, useMemo, useEffect, useRef } from 'react';
import type { FC, Key } from 'react';
import {
  Tree, TreeSelect, Button, Space, Modal, Form, Input, Select, Switch,
  Card, Popconfirm, Tag, Tooltip, Alert, Tabs, App
} from 'antd';
import type { TreeProps } from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ReloadOutlined, ClockCircleOutlined, SafetyOutlined,
  HolderOutlined, FolderOutlined, LinkOutlined, TabletOutlined,
  GlobalOutlined, MenuOutlined, SettingOutlined
} from '@ant-design/icons';
import { secureApiService } from '../services/secureApiService';
import { navigationService } from '../services/navigationService';
import { usePermissions } from '../hooks';
import SiteConfigManagement from '../components/site-management/SiteConfigManagement';
import './SiteManagementPage.css';
import { logger } from '../utils/logger';
import type { NavigationItem } from '../types/navigation';

const { Option } = Select;
const { TextArea } = Input;

interface TreeNodeData {
  title: React.ReactNode;
  key: number;
  id: number;
  parent_id: number | null;
  children: TreeNodeData[];
}

import type { NavigationFormValues } from '../types/forms';

type FormValues = NavigationFormValues;

interface ValidPath {
  path: string | null;
  description: string;
}

// 導覽管理組件
const NavigationManagementImproved: FC = () => {
  const { message } = App.useApp();
  const [navigationItems, setNavigationItems] = useState<NavigationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<NavigationItem | null>(null);
  const [form] = Form.useForm<FormValues>();
  const [expandedKeys, setExpandedKeys] = useState<Key[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const stableTreeDataRef = useRef<TreeNodeData[]>([]);
  const [validPaths, setValidPaths] = useState<ValidPath[]>([]);

  // Icon options
  const iconOptions = [
    'DashboardOutlined', 'FileTextOutlined', 'FolderOutlined',
    'CalendarOutlined', 'BarChartOutlined', 'SettingOutlined',
    'TeamOutlined', 'UserOutlined', 'GlobalOutlined',
    'DatabaseOutlined', 'SafetyOutlined', 'BankOutlined',
    'ExperimentOutlined', 'ApartmentOutlined', 'RocketOutlined',
    'CloudServerOutlined', 'EnvironmentOutlined', 'ShopOutlined',
    'ProjectOutlined', 'NumberOutlined', 'ScheduleOutlined',
    'ApiOutlined', 'LinkOutlined', 'MonitorOutlined',
    'SecurityScanOutlined', 'EyeOutlined', 'LineChartOutlined',
    'GoogleOutlined', 'SendOutlined', 'PlusOutlined', 'FormOutlined',
  ];

  // Load navigation data
  const loadNavigation = async () => {
    setLoading(true);
    try {
      const result = await secureApiService.getNavigationItems() as { items?: NavigationItem[] };
      const items = result.items || [];
      setNavigationItems(items);
      setLastUpdated(new Date());

      // Auto expand all nodes
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
      setExpandedKeys(getAllKeys(items));
    } catch (error) {
      logger.error('Failed to load navigation:', error);
      message.error('載入導覽資料失敗');
    } finally {
      setLoading(false);
    }
  };

// Load valid paths for dropdown
  const loadValidPaths = async () => {
    try {
      const result = await secureApiService.getValidPaths() as { success?: boolean; data?: { paths?: ValidPath[] } };
      if (result.success && result.data?.paths) {
        setValidPaths(result.data.paths);
      }
    } catch (error) {
      logger.error('Failed to load valid paths:', error);
      // 如果 API 失敗，使用內建的路徑列表作為後備
      setValidPaths([
        { path: null, description: '（無 - 群組項目）' },
        { path: '/dashboard', description: '儀表板' },
        { path: '/documents', description: '公文管理' },
        { path: '/document-numbers', description: '發文字號管理' },
        { path: '/contract-cases', description: '承攬計畫' },
        { path: '/agencies', description: '機關管理' },
        { path: '/vendors', description: '廠商管理' },
        { path: '/staff', description: '承辦同仁' },
        { path: '/calendar', description: '行事曆' },
        { path: '/pure-calendar', description: '專案行事曆' },
        { path: '/reports', description: '統計報表' },
        { path: '/profile', description: '個人資料' },
        { path: '/admin/database', description: '資料庫管理' },
        { path: '/admin/user-management', description: '使用者管理' },
        { path: '/admin/site-management', description: '網站管理' },
        { path: '/admin/permissions', description: '權限管理' },
        { path: '/admin/dashboard', description: '管理員面板' },
        { path: '/admin/backup', description: '備份管理' },
        { path: '/admin/deployment', description: '部署管理' },
        { path: '/admin/ai-assistant', description: 'AI 助理管理' },
        { path: '/ai/knowledge-graph', description: '知識圖譜探索' },
        { path: '/ai/code-wiki', description: '代碼圖譜' },
        { path: '/system', description: '系統監控' },
        { path: '/google-auth-diagnostic', description: 'Google認證診斷' },
        { path: '/unified-form-demo', description: '統一表單示例' },
        { path: '/api-mapping', description: 'API對應表' },
        { path: '/api/docs', description: 'API文件' },
        { path: '/taoyuan/dispatch', description: '派工管理' },
      ]);
    }
  };

  useEffect(() => {
    loadNavigation();
    loadValidPaths();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Helper to find item by id
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

  // Handle add/edit submit
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
      form.resetFields();
      setEditingItem(null);

      // 清除導覽快取，確保其他頁面能載入最新資料
      navigationService.clearNavigationCache();
      // 觸發導覽更新事件，通知 DynamicLayout 重新載入
      window.dispatchEvent(new CustomEvent('navigation-updated'));
      loadNavigation();
    } catch (error) {
      logger.error('Submit error:', error);
      message.error('操作失敗');
    }
  };

  // Handle delete
  const handleDelete = async (id: number): Promise<void> => {
    try {
      await secureApiService.deleteNavigationItem(id);
      message.success('刪除成功');

      // 清除導覽快取，確保其他頁面能載入最新資料
      navigationService.clearNavigationCache();
      // 觸發導覽更新事件，通知 DynamicLayout 重新載入
      window.dispatchEvent(new CustomEvent('navigation-updated'));
      loadNavigation();
    } catch (error) {
      logger.error('Delete error:', error);
      message.error('刪除失敗');
    }
  };

  // Open edit dialog
  const handleEdit = (item: NavigationItem): void => {
    setEditingItem(item);
    form.setFieldsValue({
      ...item,
      parent_id: item.parent_id === null ? 0 : item.parent_id
    } as unknown as FormValues);
    setModalVisible(true);
  };

  // Open add child item dialog
  const handleAddChild = (parent: NavigationItem): void => {
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue({
      parent_id: parent.id,
      level: parent.level + 1,
      is_visible: true,
      is_enabled: true,
      target: '_self'
    } as FormValues);
    setModalVisible(true);
  };

  // Open add top-level item dialog
  const handleAddTopLevel = (): void => {
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue({
      parent_id: 0,
      level: 1,
      is_visible: true,
      is_enabled: true,
      target: '_self'
    } as FormValues);
    setModalVisible(true);
  };

  // Drag handlers
  const handleDragStart: TreeProps['onDragStart'] = () => {
    setIsDragging(true);
  };

  const handleDragEnd: TreeProps['onDragEnd'] = () => {
    setIsDragging(false);
  };

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

    if (dropPosition === 0) {
      // Drop into target node (成為子項目)
      try {
        // 排除不應傳送的欄位：children, id, created_at, updated_at
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { children: _children1, id: _dragId1, created_at: _ca1, updated_at: _ua1, ...itemData } = draggedItem;
        // 計算新的 sort_order（放到目標的子項目最後）
        const targetChildren = targetItem.children || [];
        const newSortOrder = targetChildren.length > 0
          ? Math.max(...targetChildren.map(c => c.sort_order)) + 1
          : 1;
        await secureApiService.updateNavigationItem({
          ...itemData,
          id: dragKey,
          parent_id: targetItem.id,
          level: targetItem.level + 1,
          sort_order: newSortOrder
        });
        message.success('已移入目標項目');
        navigationService.clearNavigationCache();
        window.dispatchEvent(new CustomEvent('navigation-updated'));
        loadNavigation();
      } catch (error) {
        logger.error('Move error:', error);
        message.error('移動失敗');
      }
    } else {
      // Drop beside target (同層重新排序或移動到其他層級)
      try {
        // 排除不應傳送的欄位：children, id, created_at, updated_at
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { children: _children2, id: _dragId2, created_at: _ca2, updated_at: _ua2, ...itemData } = draggedItem;
        // 計算新的 sort_order（放在目標項目的前後）
        const newSortOrder = dropPosition < 0
          ? targetItem.sort_order  // 放在前面，取相同排序（後端會調整）
          : targetItem.sort_order + 1; // 放在後面
        await secureApiService.updateNavigationItem({
          ...itemData,
          id: dragKey,
          parent_id: targetItem.parent_id,
          level: targetItem.level,
          sort_order: newSortOrder
        });
        message.success('已調整順序');
        navigationService.clearNavigationCache();
        window.dispatchEvent(new CustomEvent('navigation-updated'));
        loadNavigation();
      } catch (error) {
        logger.error('Level change error:', error);
        message.error('移動失敗');
      }
    }
    setIsDragging(false);
  };

  // Helper: 判斷導覽項目類型
  // 優先判斷是否有子項目（Group），其次判斷路徑格式
  const getNavigationType = (item: NavigationItem): { type: 'tab' | 'page' | 'group'; tabKey?: string } => {
    // 有子項目的都是 Group（無論是否有 path）
    if (item.children && item.children.length > 0) {
      return { type: 'group' };
    }
    // 無路徑的是 Group
    if (!item.path) {
      return { type: 'group' };
    }
    // 路徑包含 ?tab= 的是 Tab
    if (item.path.includes('?tab=')) {
      const match = item.path.match(/\?tab=([^&]+)/);
      return { type: 'tab', tabKey: match?.[1] };
    }
    // 其他的是 Page
    return { type: 'page' };
  };

  // Render Tree node
  const renderTreeNode = (item: NavigationItem): React.ReactNode => {
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
              onClick={(e) => { e.stopPropagation(); handleAddChild(item); }}
            />
          </Tooltip>
          <Tooltip title="編輯">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={(e) => { e.stopPropagation(); handleEdit(item); }}
            />
          </Tooltip>
          <Tooltip title="刪除">
            <Popconfirm
              title="確定刪除此項目？"
              description="刪除後將立即從導覽選單中移除"
              onConfirm={() => handleDelete(item.id)}
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

  // Convert to Tree data
  const convertToTreeData = (items: NavigationItem[]): TreeNodeData[] => {
    if (!items || items.length === 0) return [];
    return items.map(item => ({
      title: renderTreeNode(item),
      key: item.id,
      id: item.id,
      parent_id: item.parent_id,
      children: item.children ? convertToTreeData(item.children) : []
    }));
  };

  // Build parent options
  const parentOptions = useMemo(() => {
    const getDescendantIds = (item: NavigationItem): number[] => {
      let ids = [item.id];
      if (item.children) {
        item.children.forEach(child => {
          ids = ids.concat(getDescendantIds(child));
        });
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

    interface TreeSelectOption {
      title: string;
      value: number;
      key: number;
      children?: TreeSelectOption[];
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

    const topLevelOption = { title: '📁 頂層（無父層）', value: 0, key: 0 };
    return [topLevelOption, ...buildOptions(navigationItems)];
  // eslint-disable-next-line react-hooks/exhaustive-deps -- findItemById is a local pure utility, not a dep
  }, [navigationItems, editingItem]);

  const treeData = useMemo(() => {
    const newTreeData = convertToTreeData(navigationItems);
    if (!isDragging) {
      stableTreeDataRef.current = newTreeData;
    }
    return isDragging ? stableTreeDataRef.current : newTreeData;
  // eslint-disable-next-line react-hooks/exhaustive-deps -- convertToTreeData is a local pure utility, not a dep
  }, [navigationItems, isDragging]);

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
          <Button
            icon={<ReloadOutlined />}
            onClick={loadNavigation}
            loading={loading}
          >
            重新整理
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAddTopLevel}
          >
            新增頂層項目
          </Button>
        </Space>
      }
    >
      <Alert
        message="即時同步已啟用"
        description="新增、編輯或刪除項目後，導覽選單會立即更新。可拖曳調整結構（支援拖曳至項目內）。"
        type="success"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Tree
        showLine={{ showLeafIcon: false }}
        draggable={{
          icon: <HolderOutlined style={{ cursor: 'grab', color: '#999', marginRight: 8 }} />,
          nodeDraggable: () => true
        }}
        blockNode
        expandedKeys={expandedKeys}
        onExpand={setExpandedKeys}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDrop={handleDrop}
        allowDrop={() => true}
        treeData={treeData}
        className={`navigation-tree ${isDragging ? 'is-dragging' : ''}`}
      />

      <Modal
        title={editingItem ? '編輯導覽項目' : '新增導覽項目'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingItem(null);
        }}
        onOk={() => form.submit()}
        confirmLoading={loading}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            is_visible: true,
            is_enabled: true,
            target: '_self',
            level: 1
          }}
        >
          <Form.Item label="標題" name="title" rules={[{ required: true, message: '請輸入標題' }]}>
            <Input placeholder="例如：公文管理" />
          </Form.Item>

          <Form.Item
            label="識別碼 (Key)"
            name="key"
            rules={[{ required: true, message: '請輸入識別碼' }]}
            tooltip="程式使用的唯一識別碼"
          >
            <Input placeholder="例如：documents" />
          </Form.Item>

          <Form.Item label="路徑" name="path" tooltip="URL 路徑，群組項目可選擇「無」">
            <Select
              placeholder="選擇路徑"
              allowClear
              showSearch
              optionFilterProp="children"
              filterOption={(input, option) =>
                (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
              }
            >
              {validPaths.map((item) => (
                <Option key={item.path ?? 'null'} value={item.path ?? ''}>
                  {item.path ? `${item.description} (${item.path})` : item.description}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="圖示" name="icon" rules={[{ required: true, message: '請選擇圖示' }]}>
            <Select placeholder="選擇圖示" showSearch>
              {iconOptions.map(icon => (
                <Option key={icon} value={icon}>{icon}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="說明" name="description">
            <TextArea rows={2} placeholder="此功能的簡短說明" />
          </Form.Item>

          <Form.Item label="父層項目" name="parent_id" tooltip="選擇父層項目或頂層">
            <TreeSelect
              treeData={parentOptions}
              placeholder="選擇父層項目"
              allowClear
              treeDefaultExpandAll
              showSearch
              treeNodeFilterProp="title"
              fieldNames={{ label: 'title', value: 'value', children: 'children' }}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="排序順序" name="sort_order" tooltip="數字越小越前面">
            <Input type="number" min={0} placeholder="0 = 自動排至最後" />
          </Form.Item>

          <Form.Item label="所需權限" name="permission_required" tooltip="留空表示不需權限">
            <Input placeholder="例如：documents:read" />
          </Form.Item>

          <Space>
            <Form.Item label="顯示" name="is_visible" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="啟用" name="is_enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
};

// 主頁面組件
export const SiteManagementPage: FC = () => {
  const [activeTab, setActiveTab] = useState('navigation');
  const { isAdmin, isSuperuser } = usePermissions();

  const getAvailableTabs = () => {
    const tabs = [];

    if (isAdmin()) {
      tabs.push({
        key: 'navigation',
        label: (
          <span>
            <MenuOutlined />
            導覽列管理
          </span>
        ),
        children: <NavigationManagementImproved />
      });
    }

    if (isSuperuser()) {
      tabs.push({
        key: 'config',
        label: (
          <span>
            <SettingOutlined />
            網站配置
          </span>
        ),
        children: <SiteConfigManagement />
      });
    }

    return tabs;
  };

  const tabItems = getAvailableTabs();

  if (tabItems.length === 0) {
    return (
      <div className="site-management-page">
        <Card>
          <Alert
            message="權限不足"
            description="您沒有足夠的權限存取網站管理功能。"
            type="warning"
            showIcon
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="site-management-page">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
            <GlobalOutlined style={{ fontSize: 24, marginRight: 12, color: '#1890ff' }} />
            <div>
              <h2 style={{ margin: 0 }}>網站管理</h2>
              <span style={{ color: '#666' }}>管理網站導覽列結構、排序和各項配置設定</span>
            </div>
          </div>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="large"
            items={tabItems}
          />
        </Space>
      </Card>
    </div>
  );
};

export default SiteManagementPage;
