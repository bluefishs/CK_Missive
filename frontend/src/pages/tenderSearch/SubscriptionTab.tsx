/**
 * 訂閱 Tab - 關鍵字自動監控訂閱管理
 */
import React from 'react';
import {
  Input, Tag, Select, Button, Typography, Row, Col,
  Empty, Card, Space, Popconfirm, Flex,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, BellOutlined,
} from '@ant-design/icons';
import type { UseMutationResult } from '@tanstack/react-query';

const { Text } = Typography;

const CATEGORY_OPTIONS = [
  { value: '', label: '全部類別' },
  { value: '工程', label: '工程類' },
  { value: '勞務', label: '勞務類' },
  { value: '財物', label: '財物類' },
];

interface Subscription {
  id: number;
  keyword: string;
  category: string | null;
  is_active: boolean;
  last_checked_at: string | null;
  last_count: number;
  last_diff: number;
  last_new_titles: string[];
}

export interface SubscriptionTabProps {
  subscriptions: Subscription[] | undefined;
  subKeyword: string;
  setSubKeyword: (v: string) => void;
  subCategory: string;
  setSubCategory: (v: string) => void;
  editingSubId: number | null;
  setEditingSubId: (v: number | null) => void;
  editingKeyword: string;
  setEditingKeyword: (v: string) => void;
  createSub: UseMutationResult<{ id: number; keyword: string }, Error, { keyword: string; category?: string }>;
  updateSub: UseMutationResult<{ id: number; keyword: string }, Error, { id: number; keyword?: string; category?: string; is_active?: boolean }>;
  deleteSub: UseMutationResult<void, Error, number>;
  handleSubSearch: (keyword: string, category?: string | null) => void;
  message: { success: (msg: string) => void; error: (msg: string) => void; warning: (msg: string) => void };
}

const SubscriptionTab: React.FC<SubscriptionTabProps> = ({
  subscriptions, subKeyword, setSubKeyword, subCategory, setSubCategory,
  editingSubId, setEditingSubId, editingKeyword, setEditingKeyword,
  createSub, updateSub, deleteSub, handleSubSearch, message,
}) => {
  const handleCreate = () => {
    if (!subKeyword.trim()) return;
    createSub.mutate(
      { keyword: subKeyword.trim(), category: subCategory || undefined },
      { onSuccess: () => { message.success('訂閱已建立'); setSubKeyword(''); setSubCategory(''); } },
    );
  };

  const handleSaveEdit = (id: number) => {
    if (!editingKeyword.trim()) return;
    updateSub.mutate(
      { id, keyword: editingKeyword.trim() },
      { onSuccess: () => { message.success('已更新'); setEditingSubId(null); } },
    );
  };

  return (
    <div>
      <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Input placeholder="輸入訂閱關鍵字（如：測量、空拍、地籍）" value={subKeyword} onChange={e => setSubKeyword(e.target.value)}
            onPressEnter={handleCreate} />
        </Col>
        <Col>
          <Select style={{ width: 100 }} options={CATEGORY_OPTIONS} value={subCategory}
            onChange={setSubCategory} placeholder="類別" />
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} loading={createSub.isPending}
            onClick={handleCreate}>新增</Button>
        </Col>
      </Row>
      {!subscriptions?.length ? <Empty description="尚無訂閱，新增關鍵字即可自動追蹤新標案" /> : (
        <Flex vertical gap={8}>
          {subscriptions.map((s) => (
            <Card key={s.id} size="small"
              hoverable={editingSubId !== s.id}
              extra={
                <Space onClick={e => e.stopPropagation()}>
                  {editingSubId === s.id ? (
                    <Button type="link" size="small" onClick={() => handleSaveEdit(s.id)}>儲存</Button>
                  ) : (
                    <Button type="link" size="small" onClick={() => { setEditingSubId(s.id); setEditingKeyword(s.keyword); }}>編輯</Button>
                  )}
                  <Popconfirm title="取消訂閱？" onConfirm={() => deleteSub.mutate(s.id)}>
                    <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              }
            >
              {editingSubId === s.id ? (
                <Space style={{ width: '100%' }} onClick={e => e.stopPropagation()}>
                  <Input size="small" value={editingKeyword} onChange={e => setEditingKeyword(e.target.value)}
                    onPressEnter={() => handleSaveEdit(s.id)}
                    style={{ width: 200 }} />
                  <Select size="small" value={s.category || ''} style={{ width: 100 }}
                    options={CATEGORY_OPTIONS}
                    onChange={(v) => updateSub.mutate({ id: s.id, category: v || '' })} />
                  <Button size="small" onClick={() => setEditingSubId(null)}>取消</Button>
                </Space>
              ) : (
                <div>
                  <Row justify="space-between" align="middle">
                    <Col>
                      <Space>
                        <BellOutlined />
                        <strong>{s.keyword}</strong>
                        {s.category && <Tag>{s.category}</Tag>}
                        {!s.is_active && <Tag color="default">已停用</Tag>}
                        {s.last_diff > 0 && <Tag color="red">+{s.last_diff} 新增</Tag>}
                      </Space>
                    </Col>
                    <Col>
                      <Space>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {s.last_checked_at
                            ? new Date(s.last_checked_at).toLocaleString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                            : '等待排程'}
                        </Text>
                        <Button type="primary" size="small"
                          onClick={() => handleSubSearch(s.keyword, s.category)}>
                          搜尋 {s.last_count.toLocaleString()} 筆
                        </Button>
                      </Space>
                    </Col>
                  </Row>
                  {s.last_new_titles?.length > 0 && (
                    <div style={{ marginTop: 8, paddingLeft: 22 }}>
                      {s.last_new_titles.slice(0, 3).map((title, i) => (
                        <div key={i} style={{ fontSize: 12, color: '#595959', marginBottom: 2 }}>
                          • {title}
                        </div>
                      ))}
                      {s.last_new_titles.length > 3 && (
                        <Button type="link" size="small" style={{ padding: 0, fontSize: 11 }}
                          onClick={() => handleSubSearch(s.keyword, s.category)}>
                          ...還有 {s.last_new_titles.length - 3} 筆，查看全部 →
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
        </Flex>
      )}
    </div>
  );
};

export default SubscriptionTab;
