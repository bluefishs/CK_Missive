/**
 * 財政部同步發票選取 Modal
 */
import React, { useState, useMemo } from 'react';
import {
  Modal, Table, Button, Flex, Tag, Input, Row, Col, Alert,
  AutoComplete, Segmented,
} from 'antd';
import { CloudDownloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useEInvoicePendingList } from '../../hooks';
import type { ExpenseInvoice, ExpenseInvoiceStatus } from '../../types/erp';
import { EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS } from '../../types/erp';
import { ROUTES } from '../../router/types';

interface Props {
  open: boolean;
  onClose: () => void;
}

const MofInvoiceModal: React.FC<Props> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'unassigned' | 'all'>('unassigned');
  const { data: pendingData, isLoading } = useEInvoicePendingList({ skip: 0, limit: 200 });

  const allItems = useMemo(() => pendingData?.items ?? [], [pendingData?.items]);

  const filteredItems = useMemo(() => {
    let list = allItems;
    if (filter === 'unassigned') list = list.filter(i => !i.case_code);
    if (search.trim()) {
      const kw = search.trim().toLowerCase();
      list = list.filter(i =>
        i.inv_num?.toLowerCase().includes(kw) ||
        i.seller_ban?.includes(kw) ||
        i.date?.includes(kw) ||
        String(i.amount).includes(kw)
      );
    }
    return list;
  }, [allItems, filter, search]);

  const autoCompleteOptions = useMemo(() => {
    if (!search.trim()) return [];
    const kw = search.trim().toLowerCase();
    const matches = new Set<string>();
    for (const item of allItems) {
      if (item.inv_num && item.inv_num.toLowerCase().includes(kw)) matches.add(item.inv_num);
      if (item.seller_ban && item.seller_ban.includes(kw)) matches.add(item.seller_ban);
    }
    return Array.from(matches).slice(0, 10).map(v => ({ value: v, label: v }));
  }, [allItems, search]);

  const handleClose = () => {
    onClose();
    setSearch('');
  };

  return (
    <Modal
      title={<><CloudDownloadOutlined /> 財政部同步發票 — 選取報帳</>}
      open={open}
      onCancel={handleClose}
      footer={<Button onClick={handleClose}>關閉</Button>}
      width={780}
    >
      <Flex vertical style={{ width: '100%', marginBottom: 16 }}>
        <Alert
          type="info"
          message="財政部自動同步的電子發票。篩選「未指定案號」可快速找出需報帳的發票。"
          showIcon
        />
        <Row gutter={12} align="middle">
          <Col flex="auto">
            <AutoComplete
              options={autoCompleteOptions}
              onSearch={setSearch}
              onSelect={setSearch}
              value={search}
              style={{ width: '100%' }}
            >
              <Input
                prefix={<SearchOutlined />}
                placeholder="搜尋發票號碼 / 賣方統編..."
                allowClear
                onChange={(e) => { if (!e.target.value) setSearch(''); }}
              />
            </AutoComplete>
          </Col>
          <Col>
            <Segmented
              options={[
                { value: 'unassigned', label: `未指定案號 (${allItems.filter(i => !i.case_code).length})` },
                { value: 'all', label: `全部 (${allItems.length})` },
              ]}
              value={filter}
              onChange={(v) => setFilter(v as 'unassigned' | 'all')}
            />
          </Col>
        </Row>
      </Flex>
      <Table<ExpenseInvoice>
        dataSource={filteredItems}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
        columns={[
          { title: '發票號碼', dataIndex: 'inv_num', key: 'inv_num', width: 130 },
          { title: '日期', dataIndex: 'date', key: 'date', width: 100 },
          {
            title: '金額', dataIndex: 'amount', key: 'amount', width: 110, align: 'right',
            render: (v: number) => v?.toLocaleString() ?? '-',
          },
          { title: '賣方統編', dataIndex: 'seller_ban', key: 'seller_ban', width: 100 },
          {
            title: '案號', dataIndex: 'case_code', key: 'case_code', width: 120,
            render: (v: string | null) => v ? <Tag color="green">{v}</Tag> : <Tag color="orange">未指定</Tag>,
          },
          {
            title: '狀態', dataIndex: 'status', key: 'status', width: 90,
            render: (s: ExpenseInvoiceStatus) => <Tag color={EXPENSE_STATUS_COLORS[s]}>{EXPENSE_STATUS_LABELS[s]}</Tag>,
          },
          {
            title: '操作', key: 'action', width: 80,
            render: (_: unknown, record: ExpenseInvoice) => (
              <Button
                type="primary" size="small"
                onClick={() => {
                  handleClose();
                  navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(record.id)));
                }}
              >
                報帳
              </Button>
            ),
          },
        ]}
      />
    </Modal>
  );
};

export default MofInvoiceModal;
