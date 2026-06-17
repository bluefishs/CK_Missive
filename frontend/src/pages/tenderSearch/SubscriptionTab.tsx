/**
 * 訂閱 Tab - 關鍵字自動監控訂閱管理
 */
import React, { useState, useEffect } from 'react';
import {
  Input, Tag, Select, Button, Typography, Row, Col,
  Empty, Card, Space, Popconfirm, Flex, Divider, Tooltip,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, BellOutlined, FilterOutlined, ApartmentOutlined, SaveOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseMutationResult } from '@tanstack/react-query';
import { tenderApi } from '../../api/tenderApi';

const { Text } = Typography;

/**
 * 推薦規則設定面板（L75.4）— owner 自維「同義詞」+「排除關鍵字」，即時生效、不需 rebuild。
 * 解「每發現一個誤判（公廁抽水肥/血壓機/復建工程…）就要找工程師改碼」的反覆修正。
 */
const KeywordRulesPanel: React.FC<{
  message: { success: (m: string) => void; error: (m: string) => void };
}> = ({ message }) => {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ['tender', 'keyword-rules'],
    queryFn: () => tenderApi.getKeywordRules(),
    staleTime: 5 * 60 * 1000,
  });
  const [exclusions, setExclusions] = useState<string[]>([]);
  const [synonyms, setSynonyms] = useState<string[][]>([]);
  const [newExc, setNewExc] = useState('');
  const [newTerm, setNewTerm] = useState<Record<number, string>>({});

  useEffect(() => {
    if (data) { setExclusions(data.exclusions ?? []); setSynonyms(data.synonyms ?? []); }
  }, [data]);

  const save = useMutation({
    mutationFn: () => tenderApi.saveKeywordRules({ synonyms, exclusions }),
    onSuccess: () => {
      message.success('規則已儲存，業務推薦即時生效');
      qc.invalidateQueries({ queryKey: ['tender', 'recommend'] });
      qc.invalidateQueries({ queryKey: ['tender', 'keyword-rules'] });
    },
    onError: () => message.error('儲存失敗'),
  });

  const addExc = () => {
    const t = newExc.trim();
    if (t && !exclusions.includes(t)) setExclusions([...exclusions, t]);
    setNewExc('');
  };
  const addTermToGroup = (gi: number) => {
    const t = (newTerm[gi] || '').trim();
    if (!t) return;
    setSynonyms(synonyms.map((g, i) => (i === gi && !g.includes(t) ? [...g, t] : g)));
    setNewTerm({ ...newTerm, [gi]: '' });
  };

  return (
    <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}
      title={<Space><FilterOutlined />推薦規則設定（同義詞 / 排除關鍵字）</Space>}
      extra={<Button type="primary" size="small" icon={<SaveOutlined />} loading={save.isPending}
        onClick={() => save.mutate()}>儲存（即時生效）</Button>}
    >
      <Text strong>排除關鍵字</Text>
      <Tooltip title="標題含這些詞的標案不進業務推薦（如：血壓機、復建工程、抽水肥、儀器…非公司職能）">
        <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>非公司職能案件 → 自動排除</Text>
      </Tooltip>
      <div style={{ margin: '8px 0' }}>
        {exclusions.map((e) => (
          <Tag key={e} closable color="red" onClose={() => setExclusions(exclusions.filter((x) => x !== e))}
            style={{ marginBottom: 4 }}>{e}</Tag>
        ))}
      </div>
      <Space.Compact style={{ width: 320, maxWidth: '100%' }}>
        <Input size="small" placeholder="新增排除詞（如：血壓機、復建工程）" value={newExc}
          onChange={(e) => setNewExc(e.target.value)} onPressEnter={addExc} />
        <Button size="small" icon={<PlusOutlined />} onClick={addExc}>加入</Button>
      </Space.Compact>

      <Divider style={{ margin: '12px 0' }} />
      <Text strong><ApartmentOutlined /> 同義詞群組</Text>
      <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>訂閱主詞自動展開整組（如 UAV → 無人機/空拍機）</Text>
      <Flex vertical gap={4} style={{ marginTop: 8 }}>
        {synonyms.map((g, gi) => (
          <div key={gi}>
            {g.map((t) => (
              <Tag key={t} closable color="blue" style={{ marginBottom: 4 }}
                onClose={() => setSynonyms(synonyms.map((gg, i) => (i === gi ? gg.filter((x) => x !== t) : gg)).filter((gg) => gg.length))}>
                {t}
              </Tag>
            ))}
            <Space.Compact style={{ width: 200 }}>
              <Input size="small" placeholder="加同義詞" value={newTerm[gi] || ''}
                onChange={(e) => setNewTerm({ ...newTerm, [gi]: e.target.value })}
                onPressEnter={() => addTermToGroup(gi)} />
              <Button size="small" icon={<PlusOutlined />} onClick={() => addTermToGroup(gi)} />
            </Space.Compact>
          </div>
        ))}
        <Button size="small" type="dashed" icon={<PlusOutlined />} style={{ width: 140 }}
          onClick={() => setSynonyms([...synonyms, ['新群組']])}>新增同義群組</Button>
      </Flex>
    </Card>
  );
};

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
      <KeywordRulesPanel message={message} />
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
