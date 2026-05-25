/**
 * RolePermissionDiff — 兩 role 並列差異比較
 *
 * 設計：
 * - 選擇 role A / role B
 * - 計算：共有 / 僅 A / 僅 B
 * - 三欄並列顯示，按權限分類分組
 * - superuser wildcard 比對：標示「* 為通配，無實際 perm 列表」
 *
 * @version 1.0.0
 * @date 2026-05-07
 */
import React, { useMemo, useState } from 'react';
import {
  Modal, Select, Space, Typography, Tag, Empty, Spin, Card, Row, Col, Alert,
  Statistic,
} from 'antd';
import {
  DiffOutlined, ArrowsAltOutlined, CheckCircleOutlined, MinusCircleOutlined,
} from '@ant-design/icons';
import { useRolePermissionsList, useRolePermissionsDetail } from '../../hooks/system/useRolePermissions';

const { Text, Paragraph } = Typography;

interface Props {
  open: boolean;
  onClose: () => void;
  /** 預選 role A (例如從 list page 帶入點擊的 role) */
  defaultRoleA?: string;
}

const ROLE_ORDER: Record<string, number> = {
  superuser: 0, admin: 1, staff: 2, user: 3, unverified: 4,
};

export const RolePermissionDiff: React.FC<Props> = ({ open, onClose, defaultRoleA }) => {
  const { data: rolesList } = useRolePermissionsList();
  const [roleA, setRoleA] = useState<string>(defaultRoleA || 'admin');
  const [roleB, setRoleB] = useState<string>('staff');

  const { data: detailA, isLoading: loadingA } = useRolePermissionsDetail(open ? roleA : null);
  const { data: detailB, isLoading: loadingB } = useRolePermissionsDetail(open ? roleB : null);

  const roleOptions = useMemo(() => {
    if (!rolesList?.items) return [];
    return [...rolesList.items]
      .sort((a, b) => (ROLE_ORDER[a.role] ?? 99) - (ROLE_ORDER[b.role] ?? 99))
      .map((r) => ({
        value: r.role,
        label: `${r.name_zh || r.role} (${r.permission_count}${r.is_wildcard ? ' / *' : ''})`,
      }));
  }, [rolesList]);

  const diff = useMemo(() => {
    if (!detailA?.role || !detailB?.role) return null;
    const setA = new Set(detailA.role.permissions);
    const setB = new Set(detailB.role.permissions);
    const isWildcardA = detailA.role.is_wildcard;
    const isWildcardB = detailB.role.is_wildcard;

    const both = [...setA].filter((p) => setB.has(p)).sort();
    const onlyA = [...setA].filter((p) => !setB.has(p)).sort();
    const onlyB = [...setB].filter((p) => !setA.has(p)).sort();

    return {
      both, onlyA, onlyB,
      isWildcardA, isWildcardB,
      countA: detailA.role.permission_count,
      countB: detailB.role.permission_count,
    };
  }, [detailA, detailB]);

  const isLoading = loadingA || loadingB;

  // 把 perms 按 prefix 分組（reports:* / admin:* / documents:* 等）
  const groupByPrefix = (perms: string[]): Record<string, string[]> => {
    const grouped: Record<string, string[]> = {};
    for (const p of perms) {
      const prefix = p.split(':')[0] || '_';
      const list = grouped[prefix] || [];
      list.push(p);
      grouped[prefix] = list;
    }
    return grouped;
  };

  const PermList: React.FC<{ perms: string[]; color: string; emptyText: string }> = ({ perms, color, emptyText }) => {
    if (perms.length === 0) {
      return <Empty description={emptyText} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    }
    const grouped = groupByPrefix(perms);
    return (
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {Object.entries(grouped)
          .sort((a, b) => a[0].localeCompare(b[0]))
          .map(([prefix, list]) => (
            <div key={prefix}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {prefix}（{list.length}）
              </Text>
              <div style={{ marginTop: 4 }}>
                <Space wrap size={[4, 4]}>
                  {list.map((p) => (
                    <Tag key={p} color={color} style={{ fontSize: 11 }}>{p}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          ))}
      </Space>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <DiffOutlined />
          <span>角色權限差異比較</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={1100}
    >
      <Space style={{ marginBottom: 16, width: '100%' }} wrap>
        <Space>
          <Text strong>角色 A：</Text>
          <Select
            value={roleA}
            onChange={setRoleA}
            options={roleOptions}
            style={{ width: 200 }}
          />
        </Space>
        <ArrowsAltOutlined rotate={45} style={{ color: '#999', fontSize: 16 }} />
        <Space>
          <Text strong>角色 B：</Text>
          <Select
            value={roleB}
            onChange={setRoleB}
            options={roleOptions}
            style={{ width: 200 }}
          />
        </Space>
      </Space>

      {isLoading ? (
        <Spin />
      ) : !diff ? (
        <Empty description="請選擇兩個角色比較" />
      ) : (
        <>
          {(diff.isWildcardA || diff.isWildcardB) && (
            <Alert
              type="warning"
              showIcon
              message="包含 Wildcard 角色"
              description={
                <span>
                  {diff.isWildcardA && <>角色 A (<Text code>{roleA}</Text>) 為 wildcard <Text code>*</Text>，</>}
                  {diff.isWildcardB && <>角色 B (<Text code>{roleB}</Text>) 為 wildcard <Text code>*</Text>，</>}
                  比對僅顯示 wildcard 字面，實際擁有所有 permissions。
                </span>
              }
              style={{ marginBottom: 16 }}
            />
          )}

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic
                  title={<Space><CheckCircleOutlined style={{ color: '#52c41a' }} />共有</Space>}
                  value={diff.both.length}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic
                  title={<Space><MinusCircleOutlined style={{ color: '#1890ff' }} />僅 A 有</Space>}
                  value={diff.onlyA.length}
                  valueStyle={{ color: '#1890ff' }}
                  suffix={`/ ${diff.countA}`}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic
                  title={<Space><MinusCircleOutlined style={{ color: '#fa8c16' }} />僅 B 有</Space>}
                  value={diff.onlyB.length}
                  valueStyle={{ color: '#fa8c16' }}
                  suffix={`/ ${diff.countB}`}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Card
                title={<Space><CheckCircleOutlined style={{ color: '#52c41a' }} /><Text strong>共有 {diff.both.length}</Text></Space>}
                size="small"
                style={{ height: '100%' }}
              >
                <div style={{ maxHeight: 480, overflowY: 'auto' }}>
                  <PermList perms={diff.both} color="green" emptyText="兩 role 無共同 perm" />
                </div>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card
                title={<Space><MinusCircleOutlined style={{ color: '#1890ff' }} /><Text strong>僅 {roleA} 有 {diff.onlyA.length}</Text></Space>}
                size="small"
                style={{ height: '100%' }}
              >
                <div style={{ maxHeight: 480, overflowY: 'auto' }}>
                  <PermList perms={diff.onlyA} color="blue" emptyText={`${roleA} 比 ${roleB} 無額外 perm`} />
                </div>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card
                title={<Space><MinusCircleOutlined style={{ color: '#fa8c16' }} /><Text strong>僅 {roleB} 有 {diff.onlyB.length}</Text></Space>}
                size="small"
                style={{ height: '100%' }}
              >
                <div style={{ maxHeight: 480, overflowY: 'auto' }}>
                  <PermList perms={diff.onlyB} color="orange" emptyText={`${roleB} 比 ${roleA} 無額外 perm`} />
                </div>
              </Card>
            </Col>
          </Row>

          <Paragraph type="secondary" style={{ fontSize: 11, marginTop: 12, marginBottom: 0 }}>
            提示：「僅 A 有」可協助判斷哪些權限是 {roleA} 角色的專屬授權；「僅 B 有」反向判斷。
            兩者皆少代表角色重疊度高，可能可合併或調整邊界。
          </Paragraph>
        </>
      )}
    </Modal>
  );
};

export default RolePermissionDiff;
