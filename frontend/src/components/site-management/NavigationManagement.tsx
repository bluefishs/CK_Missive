/**
 * 導覽列管理組件
 * @description 管理系統導覽選單的樹狀結構
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Table, Button, Space, Tree, Card, Popconfirm, Tag, Tooltip, Row, Col, App, Input
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined,
  EyeInvisibleOutlined, MenuOutlined,
  CheckOutlined, CloseOutlined, SearchOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { secureApiService } from '../../services/secureApiService';
import type { NavigationItem, NavigationFormData, ParentOption } from '../../types/navigation';
import { formatPermissionLabel } from '../../config/navigationConfig';
import NavigationItemForm from './NavigationItemForm';

const NavigationManagement: React.FC = () => {
  const { message } = App.useApp();
  const [items, setItems] = useState<NavigationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<NavigationItem | null>(null);
  const [viewMode, setViewMode] = useState<'tree' | 'table'>('tree');
  const [searchValue, setSearchValue] = useState('');
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [autoExpandParent, setAutoExpandParent] = useState(true);

  // 載入導覽列數據
  const loadNavigationData = async () => {
    setLoading(true);
    try {
      const data = await secureApiService.getNavigationItems() as { items?: NavigationItem[] };
      const processedItems = ensureUniqueIds(data.items || []);
      setItems(processedItems);
    } catch (error) {
      console.warn('Navigation API not available, using fallback data');
      setItems(getFallbackItems());
    } finally {
      setLoading(false);
    }
  };

  // Fallback 導覽數據
  const getFallbackItems = (): NavigationItem[] => [
    {
      id: 1, title: '儀表板', key: 'dashboard', path: '/dashboard',
      icon: 'DashboardOutlined', parent_id: undefined, sort_order: 1,
      is_visible: true, is_enabled: true, level: 1,
      description: '系統儀表板', target: '_self', children: []
    },
    {
      id: 2, title: '公文管理', key: 'documents', path: '/documents',
      icon: 'FileTextOutlined', parent_id: undefined, sort_order: 2,
      is_visible: true, is_enabled: true, level: 1,
      description: '公文管理功能', target: '_self', children: []
    }
  ];

  // 確保 ID 唯一性
  const ensureUniqueIds = (items: NavigationItem[]): NavigationItem[] => {
    const idMap = new Map<number, boolean>();
    let nextId = 1;

    const processItems = (items: NavigationItem[]): NavigationItem[] => {
      return items.map(item => {
        if (!item.id || idMap.has(item.id)) {
          while (idMap.has(nextId)) nextId++;
          item.id = nextId;
        }
        idMap.set(item.id, true);
        if (item.children?.length) {
          item.children = processItems(item.children);
        }
        return { ...item };
      });
    };

    return processItems(items);
  };

  useEffect(() => {
    loadNavigationData();
  }, []);

  // 顯示新增/編輯對話框
  const showModal = (item?: NavigationItem) => {
    setEditingItem(item || null);
    setModalVisible(true);
  };

  // 提交表單
  const handleSubmit = async (values: NavigationFormData) => {
    try {
      if (editingItem) {
        await secureApiService.updateNavigationItem({ id: editingItem.id, ...values });
        message.success('更新成功');
      } else {
        await secureApiService.createNavigationItem(values);
        message.success('新增成功');
      }
      setModalVisible(false);
      loadNavigationData();
    } catch (error) {
      message.error('操作失敗');
      console.error('Error submitting form:', error);
    }
  };

  // 刪除項目
  const handleDelete = async (id: number) => {
    try {
      await secureApiService.deleteNavigationItem(id);
      message.success('刪除成功');
      loadNavigationData();
    } catch (error) {
      message.error('刪除失敗');
      console.error('Error deleting item:', error);
    }
  };

  // 切換狀態
  const toggleItemStatus = async (id: number, field: 'is_visible' | 'is_enabled', value: boolean) => {
    try {
      await secureApiService.updateNavigationItem({ id, [field]: value });
      message.success('更新成功');
      loadNavigationData();
    } catch (error) {
      message.error('更新失敗');
      console.error('Error updating status:', error);
    }
  };

  // 獲取父級選項
  const getParentOptions = (items: NavigationItem[]): ParentOption[] => {
    const options: ParentOption[] = [];
    const addOptions = (items: NavigationItem[], prefix = '') => {
      items.forEach(item => {
        options.push({ value: item.id, label: `${prefix}${item.title}` });
        if (item.children?.length) {
          addOptions(item.children, `${prefix}${item.title} → `);
        }
      });
    };
    addOptions(items);
    return options;
  };

  // 表格列定義
  const columns: ColumnsType<NavigationItem> = [
    {
      title: '標題',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => (
        <Space>
          <span style={{ marginLeft: (record.level - 1) * 20 }}>
            {record.level > 1 && '└─ '}{text}
          </span>
          {record.icon && <span>({record.icon})</span>}
        </Space>
      ),
    },
    {
      title: '鍵值',
      dataIndex: 'key',
      key: 'key',
      render: (text) => <code>{text}</code>,
    },
    {
      title: '路徑',
      dataIndex: 'path',
      key: 'path',
      render: (text) => text ? <code>{text}</code> : <span style={{ color: '#ccc' }}>無</span>,
    },
    {
      title: '層級',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level) => <Tag color="blue">{level}</Tag>,
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
    },
    {
      title: '所需權限',
      dataIndex: 'permission_required',
      key: 'permission_required',
      width: 150,
      render: (permission) => {
        const { label, color } = formatPermissionLabel(permission);
        return <Tag color={color} style={{ fontSize: '11px' }}>{label}</Tag>;
      },
    },
    {
      title: '狀態',
      key: 'status',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title={record.is_visible ? '可見' : '隱藏'}>
            <Button
              type="text"
              size="small"
              icon={record.is_visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
              onClick={() => toggleItemStatus(record.id, 'is_visible', !record.is_visible)}
            />
          </Tooltip>
          <Tooltip title={record.is_enabled ? '啟用' : '停用'}>
            <Button
              type="text"
              size="small"
              icon={record.is_enabled ? <CheckOutlined /> : <CloseOutlined />}
              onClick={() => toggleItemStatus(record.id, 'is_enabled', !record.is_enabled)}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => showModal(record)} />
          <Popconfirm
            title="確定要刪除這個項目嗎？"
            onConfirm={() => handleDelete(record.id)}
            okText="確定"
            cancelText="取消"
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 平鋪樹狀數據
  const flattenTreeData = (items: NavigationItem[]): NavigationItem[] => {
    const result: NavigationItem[] = [];
    const addItems = (items: NavigationItem[], level = 1) => {
      items.forEach(item => {
        result.push({ ...item, level });
        if (item.children?.length) addItems(item.children, level + 1);
      });
    };
    addItems(items);
    return result;
  };

  // 轉換為 Tree 組件數據
  const convertToTreeData = (items: NavigationItem[]): any[] => {
    const convertItem = (item: NavigationItem): any => ({
      title: (
        <Space>
          <span>{item.title}</span>
          {item.icon && <Tag>{item.icon}</Tag>}
          {(() => {
            const { label, color } = formatPermissionLabel(item.permission_required);
            return <Tag color={color}>{label}</Tag>;
          })()}
          <Space size="small">
            <Tooltip title={item.is_visible ? '可見' : '隱藏'}>
              <Button
                type="text" size="small"
                icon={item.is_visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                onClick={(e) => { e.stopPropagation(); toggleItemStatus(item.id, 'is_visible', !item.is_visible); }}
              />
            </Tooltip>
            <Tooltip title={item.is_enabled ? '啟用' : '停用'}>
              <Button
                type="text" size="small"
                icon={item.is_enabled ? <CheckOutlined /> : <CloseOutlined />}
                onClick={(e) => { e.stopPropagation(); toggleItemStatus(item.id, 'is_enabled', !item.is_enabled); }}
              />
            </Tooltip>
            <Button
              type="text" size="small" icon={<EditOutlined />}
              onClick={(e) => { e.stopPropagation(); showModal(item); }}
            />
            <Popconfirm
              title="確定要刪除這個項目嗎？"
              onConfirm={(e) => { e?.stopPropagation(); handleDelete(item.id); }}
              okText="確定"
              cancelText="取消"
            >
              <Button
                type="text" size="small" danger icon={<DeleteOutlined />}
                onClick={(e) => e.stopPropagation()}
              />
            </Popconfirm>
          </Space>
        </Space>
      ),
      key: `nav-${item.id}`,
      children: item.children?.map(convertItem),
      item
    });
    return items.map(convertItem);
  };

  // 搜索相關函數
  const getMatchedKeys = (items: NavigationItem[], search: string): React.Key[] => {
    const keys: React.Key[] = [];
    const searchItems = (items: NavigationItem[]) => {
      items.forEach(item => {
        const searchLower = search.toLowerCase();
        if (item.title.toLowerCase().includes(searchLower) ||
            item.key?.toLowerCase().includes(searchLower) ||
            item.path?.toLowerCase().includes(searchLower)) {
          keys.push(`nav-${item.id}`);
        }
        if (item.children) searchItems(item.children);
      });
    };
    searchItems(items);
    return keys;
  };

  const getParentKeys = (items: NavigationItem[], targetKeys: React.Key[]): React.Key[] => {
    const parentKeys: React.Key[] = [];
    const findParents = (items: NavigationItem[], parentKey?: React.Key) => {
      items.forEach(item => {
        const currentKey = `nav-${item.id}`;
        if (targetKeys.includes(currentKey) && parentKey) {
          parentKeys.push(parentKey);
        }
        if (item.children) findParents(item.children, currentKey);
      });
    };
    findParents(items);
    return [...new Set(parentKeys)];
  };

  const onSearch = (value: string) => {
    if (value) {
      const matchedKeys = getMatchedKeys(items, value);
      const parentKeys = getParentKeys(items, matchedKeys);
      setExpandedKeys([...matchedKeys, ...parentKeys]);
      setAutoExpandParent(true);
    } else {
      setExpandedKeys([]);
      setAutoExpandParent(false);
    }
    setSearchValue(value);
  };

  const onExpand = (newExpandedKeys: React.Key[]) => {
    setExpandedKeys(newExpandedKeys);
    setAutoExpandParent(false);
  };

  const treeData = useMemo(() => convertToTreeData(items), [items]);

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => showModal()}>
            新增導覽項目
          </Button>
        </Col>
        <Col>
          <Button
            icon={<MenuOutlined />}
            onClick={() => setViewMode(viewMode === 'tree' ? 'table' : 'tree')}
          >
            {viewMode === 'tree' ? '表格檢視' : '樹狀檢視'}
          </Button>
        </Col>
        {viewMode === 'tree' && (
          <Col flex="auto">
            <Input.Search
              placeholder="搜尋導覽項目（標題、鍵值、路徑）"
              allowClear
              enterButton={<SearchOutlined />}
              onSearch={onSearch}
              onChange={(e) => !e.target.value && onSearch('')}
              style={{ maxWidth: 400 }}
            />
          </Col>
        )}
      </Row>

      <Card>
        {viewMode === 'tree' ? (
          <Tree
            showLine
            switcherIcon={<MenuOutlined />}
            treeData={treeData}
            expandedKeys={expandedKeys}
            autoExpandParent={autoExpandParent}
            onExpand={onExpand}
            style={{ minHeight: 400 }}
          />
        ) : (
          <Table
            columns={columns}
            dataSource={flattenTreeData(items)}
            loading={loading}
            rowKey="id"
            pagination={false}
            size="small"
          />
        )}
      </Card>

      <NavigationItemForm
        visible={modalVisible}
        editingItem={editingItem}
        parentOptions={getParentOptions(items)}
        defaultSortOrder={items.length + 1}
        onSubmit={handleSubmit}
        onCancel={() => setModalVisible(false)}
      />
    </div>
  );
};

export default NavigationManagement;
