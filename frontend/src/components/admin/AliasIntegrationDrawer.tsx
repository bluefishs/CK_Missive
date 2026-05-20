/**
 * AliasIntegrationDrawer — 使用者認證方式整合 UI（ADR-0025 Identity Unification）
 *
 * 解決同一人因不同認證方式（Google / LINE / Email）建多個 user records 的整合議題。
 *
 * 功能：
 * - Tab 1: 潛在分身 clusters（同 full_name 多筆）+ merge 操作
 * - Tab 2: 合併歷史（user_merge_log 最近 100 筆）
 *
 * 對應後端：backend/app/api/endpoints/user_alias_admin.py
 *
 * @version 1.0.0
 * @date 2026-04-28
 */
import React, { useState, useCallback } from 'react';
import {
  Drawer, Tabs, Card, Tag, Button, Space, Empty, Spin, Modal, Radio,
  Switch, Input, Typography, message, Descriptions, Alert,
} from 'antd';
import { UserSwitchOutlined, HistoryOutlined, MergeCellsOutlined, CrownOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ADMIN_USER_MANAGEMENT_ENDPOINTS } from '../../api/endpoints/users';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface AliasUser {
  id: number;
  username: string;
  email: string;
  role: string;
  is_admin: boolean;
  is_superuser: boolean;
  auth_provider: string;
  canonical_user_id: number | null;
  is_active: boolean;
  is_canonical: boolean;
}

interface AliasCluster {
  full_name: string;
  users: AliasUser[];
  already_merged: boolean;
}

interface AliasCandidatesResponse {
  success: boolean;
  total_clusters: number;
  clusters: AliasCluster[];
}

interface MergeHistoryItem {
  id: number;
  canonical_id: number;
  alias_id: number;
  canonical_role: string;
  alias_role: string;
  role_harmonized: boolean;
  merged_by: number;
  merged_at: string;
  notes: string | null;
  reversed_at: string | null;
}

interface MergeHistoryResponse {
  success: boolean;
  total: number;
  items: MergeHistoryItem[];
}

interface Props {
  open: boolean;
  onClose: () => void;
}

const providerColor: Record<string, string> = {
  google: 'red',
  line: 'green',
  email: 'blue',
  password: 'orange',
};

export const AliasIntegrationDrawer: React.FC<Props> = ({ open, onClose }) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('candidates');
  const [mergingCluster, setMergingCluster] = useState<AliasCluster | null>(null);
  const [canonicalId, setCanonicalId] = useState<number | null>(null);
  const [aliasIds, setAliasIds] = useState<number[]>([]);
  const [harmonizeRole, setHarmonizeRole] = useState(false);
  const [mergeNotes, setMergeNotes] = useState('');

  const { data: candidatesData, isLoading: candidatesLoading } = useQuery({
    queryKey: ['user-alias-candidates'],
    queryFn: () => apiClient.post<AliasCandidatesResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ALIAS_CANDIDATES, {},
    ),
    enabled: open,
    staleTime: 30_000,
    refetchOnMount: 'always',
  });

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['user-merge-history'],
    queryFn: () => apiClient.post<MergeHistoryResponse>(
      ADMIN_USER_MANAGEMENT_ENDPOINTS.ALIAS_MERGE_HISTORY, {},
    ),
    enabled: open && activeTab === 'history',
    staleTime: 30_000,
  });

  const mergeMutation = useMutation({
    mutationFn: (req: { canonical_id: number; alias_id: number; harmonize_role: boolean; notes?: string }) =>
      apiClient.post(ADMIN_USER_MANAGEMENT_ENDPOINTS.ALIAS_MERGE, req),
    onSuccess: () => {
      message.success('分身已合併');
      queryClient.invalidateQueries({ queryKey: ['user-alias-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['user-merge-history'] });
      // v6.10.1 L39 修：原 ['admin-users'] 與 adminUserKeys.list = ['admin','users',...] 不重疊 (silent dead)
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
    onError: (e: Error) => message.error(`合併失敗: ${e.message}`),
  });

  const handleStartMerge = useCallback((cluster: AliasCluster) => {
    setMergingCluster(cluster);
    // 預設 canonical 選 is_canonical=true 第一個（若沒有則挑第一個 user）
    const def = cluster.users.find((u) => u.is_canonical) ?? cluster.users[0];
    setCanonicalId(def?.id ?? null);
    setAliasIds([]);
    setHarmonizeRole(false);
    setMergeNotes('');
  }, []);

  const handleConfirmMerge = useCallback(async () => {
    if (!canonicalId || aliasIds.length === 0) {
      message.warning('請選 canonical 與至少一個 alias');
      return;
    }
    for (const aid of aliasIds) {
      // eslint-disable-next-line no-await-in-loop
      await mergeMutation.mutateAsync({
        canonical_id: canonicalId,
        alias_id: aid,
        harmonize_role: harmonizeRole,
        notes: mergeNotes || undefined,
      });
    }
    setMergingCluster(null);
  }, [canonicalId, aliasIds, harmonizeRole, mergeNotes, mergeMutation]);

  return (
    <>
      <Drawer
        title={<Space><UserSwitchOutlined /> 使用者認證方式整合（ADR-0025）</Space>}
        width={760}
        open={open}
        onClose={onClose}
      >
        <Alert
          type="info"
          showIcon
          message="同一人若用不同認證方式（Google / LINE / Email）登入會建立多個 user records。本工具偵測同名分身並提供合併。"
          style={{ marginBottom: 16 }}
        />
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'candidates',
              label: (
                <span><MergeCellsOutlined /> 潛在分身{candidatesData?.total_clusters ? ` (${candidatesData.total_clusters})` : ''}</span>
              ),
              children: candidatesLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
              ) : !candidatesData?.clusters?.length ? (
                <Empty description="無潛在分身（所有同名用戶皆已合併或無重複）" />
              ) : (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  {candidatesData.clusters.map((cluster) => (
                    <Card
                      key={cluster.full_name}
                      size="small"
                      title={<Space><Text strong>{cluster.full_name}</Text>{cluster.already_merged && <Tag color="green">已合併</Tag>}</Space>}
                      extra={!cluster.already_merged && (
                        <Button size="small" type="primary" icon={<MergeCellsOutlined />} onClick={() => handleStartMerge(cluster)}>合併</Button>
                      )}
                    >
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {cluster.users.map((u) => (
                          <div key={u.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {u.is_canonical && <CrownOutlined style={{ color: '#faad14' }} title="canonical" />}
                            <Text code>#{u.id}</Text>
                            <Text>{u.email}</Text>
                            <Tag color={providerColor[u.auth_provider] ?? 'default'}>{u.auth_provider}</Tag>
                            <Tag>{u.role}</Tag>
                            {!u.is_active && <Tag color="red">停用</Tag>}
                            {!u.is_canonical && u.canonical_user_id && (
                              <Text type="secondary">→ #{u.canonical_user_id}</Text>
                            )}
                          </div>
                        ))}
                      </Space>
                    </Card>
                  ))}
                </Space>
              ),
            },
            {
              key: 'history',
              label: <span><HistoryOutlined /> 合併歷史</span>,
              children: historyLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
              ) : !historyData?.items?.length ? (
                <Empty description="尚無合併紀錄" />
              ) : (
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {historyData.items.map((item) => (
                    <Card key={item.id} size="small">
                      <Descriptions size="small" column={2}>
                        <Descriptions.Item label="canonical">#{item.canonical_id}</Descriptions.Item>
                        <Descriptions.Item label="alias">#{item.alias_id}</Descriptions.Item>
                        <Descriptions.Item label="canonical role">{item.canonical_role}</Descriptions.Item>
                        <Descriptions.Item label="alias role">
                          {item.alias_role}{item.role_harmonized && <Tag color="purple" style={{ marginLeft: 8 }}>已統一</Tag>}
                        </Descriptions.Item>
                        <Descriptions.Item label="merged_by">#{item.merged_by}</Descriptions.Item>
                        <Descriptions.Item label="merged_at">{new Date(item.merged_at).toLocaleString('zh-TW')}</Descriptions.Item>
                        {item.notes && <Descriptions.Item label="備註" span={2}>{item.notes}</Descriptions.Item>}
                        {item.reversed_at && (
                          <Descriptions.Item label="撤銷" span={2}>
                            <Tag color="red">已撤銷 {new Date(item.reversed_at).toLocaleString('zh-TW')}</Tag>
                          </Descriptions.Item>
                        )}
                      </Descriptions>
                    </Card>
                  ))}
                </Space>
              ),
            },
          ]}
        />
      </Drawer>

      {/* 合併確認 Modal */}
      <Modal
        title={`合併分身 — ${mergingCluster?.full_name ?? ''}`}
        open={!!mergingCluster}
        onCancel={() => setMergingCluster(null)}
        onOk={handleConfirmMerge}
        confirmLoading={mergeMutation.isPending}
        okText={`合併 ${aliasIds.length} 個 alias`}
        okButtonProps={{ disabled: !canonicalId || aliasIds.length === 0 }}
        width={620}
      >
        {mergingCluster && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Title level={5} style={{ marginBottom: 8 }}>1. 選 Canonical（保留為主帳號）</Title>
              <Radio.Group value={canonicalId} onChange={(e) => { setCanonicalId(e.target.value); setAliasIds([]); }}>
                <Space direction="vertical">
                  {mergingCluster.users.map((u) => (
                    <Radio key={u.id} value={u.id}>
                      #{u.id} {u.email}{' '}
                      <Tag color={providerColor[u.auth_provider] ?? 'default'}>{u.auth_provider}</Tag>
                      <Tag>{u.role}</Tag>
                    </Radio>
                  ))}
                </Space>
              </Radio.Group>
            </div>

            <div>
              <Title level={5} style={{ marginBottom: 8 }}>2. 選要合併為 alias 的帳號（多選）</Title>
              <Space direction="vertical">
                {mergingCluster.users.filter((u) => u.id !== canonicalId).map((u) => {
                  const checked = aliasIds.includes(u.id);
                  return (
                    <label key={u.id} style={{ cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => setAliasIds((prev) => checked ? prev.filter((x) => x !== u.id) : [...prev, u.id])}
                        style={{ marginRight: 8 }}
                      />
                      #{u.id} {u.email}{' '}
                      <Tag color={providerColor[u.auth_provider] ?? 'default'}>{u.auth_provider}</Tag>
                      <Tag>{u.role}</Tag>
                    </label>
                  );
                })}
              </Space>
            </div>

            <div>
              <Space>
                <Switch checked={harmonizeRole} onChange={setHarmonizeRole} />
                <Text>同步 role（規則 B：預設關閉，alias 保留自己 role）</Text>
              </Space>
            </div>

            <div>
              <Text type="secondary">備註（可選）</Text>
              <TextArea rows={2} value={mergeNotes} onChange={(e) => setMergeNotes(e.target.value)} maxLength={500} />
            </div>
          </Space>
        )}
      </Modal>
    </>
  );
};

export default AliasIntegrationDrawer;
