/**
 * ProposalsTab — 結晶提案審批 + 已套用 Crystal 回滾
 *
 * Phase 5 Slice 3 — admin-only 按鈕。非 admin 會收到 403（由後端 require_admin 把關）。
 */
import React, { useState } from 'react';
import {
  Alert, Button, Card, Col, Empty, Modal, Popconfirm, Row, Spin, Table, Tag, Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { CheckOutlined, CloseOutlined, RollbackOutlined } from '@ant-design/icons';

import MarkdownRenderer from '../../components/common/MarkdownRenderer';
import {
  useCrystalRollback,
  useCrystalsList,
  useProposalApprove,
  useProposalReject,
  useProposalsList,
} from '../../hooks/useMemoryData';
import type { CrystalSummary, ProposalSummary } from '../../types/memory';

const ProposalsTab: React.FC = () => {
  const { data: proposals = [], isLoading: loadingP } = useProposalsList({ limit: 100 });
  const { data: crystals = [], isLoading: loadingC } = useCrystalsList({ limit: 100 });
  const approve = useProposalApprove();
  const reject = useProposalReject();
  const rollback = useCrystalRollback();

  const [preview, setPreview] = useState<ProposalSummary | null>(null);

  const proposalColumns: ColumnsType<ProposalSummary> = [
    { title: '檔名', dataIndex: 'filename', key: 'filename', ellipsis: true, width: 220 },
    {
      title: '類型',
      dataIndex: ['meta', 'proposal_kind'],
      key: 'kind',
      render: (v: unknown) => <Tag color="purple">{String(v ?? '-')}</Tag>,
    },
    {
      title: '目標檔',
      dataIndex: ['meta', 'target_file'],
      key: 'target',
      render: (v: unknown) => <Tag>{String(v ?? '-')}</Tag>,
    },
    {
      title: '狀態',
      dataIndex: ['meta', 'status'],
      key: 'status',
      render: (v: unknown) => {
        const s = String(v ?? 'pending');
        const color = s === 'applied' ? 'green' : s === 'rejected' ? 'red' : 'orange';
        return <Tag color={color}>{s}</Tag>;
      },
    },
    { title: '建立時間', dataIndex: ['meta', 'created_at'], key: 'created_at', width: 180 },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render: (_, r) => {
        const proposalId = String(r.meta?.proposal_id ?? r.filename.replace('.md', ''));
        const isPending = (r.meta?.status ?? 'pending') === 'pending';
        return (
          <span>
            <Button size="small" onClick={() => setPreview(r)} style={{ marginRight: 4 }}>
              預覽
            </Button>
            {isPending && (
              <>
                <Popconfirm
                  title="批准並套用此 proposal？"
                  description="會 snapshot + 改 yaml + 寫 crystal 記錄（可回滾）"
                  onConfirm={() => approve.mutate({ proposal_id: proposalId })}
                  okButtonProps={{ loading: approve.isPending }}
                >
                  <Button size="small" type="primary" icon={<CheckOutlined />}>批准</Button>
                </Popconfirm>
                <Popconfirm
                  title="拒絕此 proposal？"
                  onConfirm={() => reject.mutate({ proposal_id: proposalId })}
                  okButtonProps={{ loading: reject.isPending, danger: true }}
                >
                  <Button size="small" danger icon={<CloseOutlined />} style={{ marginLeft: 4 }}>拒絕</Button>
                </Popconfirm>
              </>
            )}
          </span>
        );
      },
    },
  ];

  const crystalColumns: ColumnsType<CrystalSummary> = [
    { title: '檔名', dataIndex: 'filename', key: 'filename', ellipsis: true, width: 220 },
    { title: '目標', dataIndex: ['meta', 'target_file'], key: 'target' },
    { title: 'snapshot', dataIndex: ['meta', 'snapshot'], key: 'snapshot', ellipsis: true },
    { title: '批准人', dataIndex: ['meta', 'approved_by'], key: 'by' },
    { title: '批准時間', dataIndex: ['meta', 'approved_at'], key: 'at', width: 180 },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, r) => {
        const crystalId = String(r.meta?.crystal_id ?? r.filename.replace('.md', ''));
        return (
          <Popconfirm
            title="回滾此 crystal？"
            description="會從 snapshot 還原 yaml 檔案"
            onConfirm={() => rollback.mutate({ crystal_id: crystalId })}
            okButtonProps={{ loading: rollback.isPending, danger: true }}
          >
            <Button size="small" icon={<RollbackOutlined />} danger>回滾</Button>
          </Popconfirm>
        );
      },
    },
  ];

  return (
    <>
      <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
        <Col xs={24}>
          <Card
            size="small"
            title={<span>結晶提案 <Tag color="orange">{proposals.length}</Tag></span>}
          >
            <Alert
              type="warning"
              showIcon
              message="批准 = 改 yaml。系統會 snapshot 原檔並可回滾；僅 admin 可操作"
              style={{ marginBottom: 12 }}
            />
            {loadingP ? (
              <Spin />
            ) : proposals.length === 0 ? (
              <Empty description="尚無待決 proposal（crystallization_scan 04:30 自動掃）" />
            ) : (
              <Table
                size="small"
                rowKey="filename"
                columns={proposalColumns}
                dataSource={proposals}
                pagination={{ pageSize: 10 }}
                scroll={{ x: 'max-content' }}
              />
            )}
          </Card>
        </Col>
        <Col xs={24}>
          <Card
            size="small"
            title={<span>已套用 Crystal <Tag color="gold">{crystals.length}</Tag></span>}
          >
            {loadingC ? (
              <Spin />
            ) : crystals.length === 0 ? (
              <Typography.Text type="secondary">尚無已套用 crystal</Typography.Text>
            ) : (
              <Table
                size="small"
                rowKey="filename"
                columns={crystalColumns}
                dataSource={crystals}
                pagination={{ pageSize: 10 }}
                scroll={{ x: 'max-content' }}
              />
            )}
          </Card>
        </Col>
      </Row>
      <Modal
        open={!!preview}
        title={preview?.filename}
        onCancel={() => setPreview(null)}
        footer={null}
        width={720}
      >
        {preview && <MarkdownRenderer content={preview.body_preview} />}
      </Modal>
    </>
  );
};

export default ProposalsTab;
