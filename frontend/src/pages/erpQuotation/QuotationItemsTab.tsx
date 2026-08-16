/**
 * 線上報價單 — 逐項明細
 *
 * 2026-08-16 owner：「線上報價單機制」。
 *
 * 在此之前報價只有一個手填的 `total_price`，78 張裡 **23 張是空的** ——
 * 因為人手上有的是一份逐項的報價內容，系統卻只給他一個空格叫他填總數。
 * 有了明細之後總價由小計加總得出，不再是獨立維護的第二份事實。
 *
 * 取捨：
 *  · **整批儲存**而非逐列 CRUD —— 使用者的心智模型是「改完這張表按儲存」
 *  · 空白列自動略過（表格編輯必然會留下空列）
 *  · **清空明細不會把總價歸零** —— 空明細代表「還沒逐項拆」，不是「0 元」
 */
import React from 'react';
import {
  Table, Button, InputNumber, Input, Space, Typography, App, Alert, Popconfirm,
} from 'antd';
import { PlusOutlined, DeleteOutlined, SaveOutlined, PrinterOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';

const { Text, Title } = Typography;

export interface QuotationItemRow {
  key: string;
  item_name: string;
  spec?: string;
  unit?: string;
  qty: number;
  unit_price: number;
  amount: number;
}

interface Props {
  quotationId: number;
  caseName?: string;
  caseCode?: string;
}

const money = (n: number) => `NT$ ${Math.round(n).toLocaleString()}`;

export const QuotationItemsTab: React.FC<Props> = ({ quotationId, caseName, caseCode }) => {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [rows, setRows] = React.useState<QuotationItemRow[]>([]);
  const [dirty, setDirty] = React.useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['quotation-items', quotationId],
    queryFn: async () => {
      const res = await apiClient.post<{ data: { items: QuotationItemRow[]; subtotal: number; tax_amount: number; total: number; has_items: boolean } }>(
        ERP_ENDPOINTS.QUOTATION_ITEMS_DETAIL, { quotation_id: quotationId },
      );
      return res?.data;
    },
  });

  React.useEffect(() => {
    if (data?.items) {
      setRows(data.items.map((i, n) => ({ ...i, key: String(i.qty) + n })));
      setDirty(false);
    }
  }, [data]);

  const save = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post<{ data: { item_count: number; total_price: number; total_price_updated: boolean } }>(
        ERP_ENDPOINTS.QUOTATION_ITEMS_REPLACE,
        {
          quotation_id: quotationId,
          items: rows.map((r, i) => ({
            item_name: r.item_name, spec: r.spec, unit: r.unit,
            qty: r.qty, unit_price: r.unit_price, sort_order: i,
          })),
        },
      );
      return res?.data;
    },
    onSuccess: (r) => {
      setDirty(false);
      if (r?.total_price_updated) {
        message.success(`已儲存 ${r.item_count} 個工項，報價總價更新為 ${money(r.total_price ?? 0)}`);
      } else {
        // 明細清空時要說清楚「總價沒有被歸零」，否則使用者會以為資料掉了
        message.warning(`明細已清空。報價總價維持 ${money(r?.total_price ?? 0)} 未歸零`);
      }
      qc.invalidateQueries({ queryKey: ['quotation-items', quotationId] });
      qc.invalidateQueries({ queryKey: ['erp-quotation', quotationId] });
    },
    onError: () => message.error('儲存失敗'),
  });

  const update = (key: string, patch: Partial<QuotationItemRow>) => {
    setRows(prev => prev.map(r => {
      if (r.key !== key) return r;
      const next = { ...r, ...patch };
      next.amount = Math.round((next.qty || 0) * (next.unit_price || 0) * 100) / 100;
      return next;
    }));
    setDirty(true);
  };

  const subtotal = rows.reduce((s, r) => s + (r.amount || 0), 0);
  const tax = data?.tax_amount ?? 0;

  const columns = [
    {
      title: '工項', dataIndex: 'item_name', width: '28%',
      render: (v: string, r: QuotationItemRow) => (
        <Input value={v} placeholder="工項名稱" onChange={e => update(r.key, { item_name: e.target.value })} />
      ),
    },
    {
      title: '規格／說明', dataIndex: 'spec', width: '24%',
      render: (v: string, r: QuotationItemRow) => (
        <Input value={v} placeholder="選填" onChange={e => update(r.key, { spec: e.target.value })} />
      ),
    },
    {
      title: '單位', dataIndex: 'unit', width: 80,
      render: (v: string, r: QuotationItemRow) => (
        <Input value={v} placeholder="式" onChange={e => update(r.key, { unit: e.target.value })} />
      ),
    },
    {
      title: '數量', dataIndex: 'qty', width: 100,
      render: (v: number, r: QuotationItemRow) => (
        <InputNumber<number> style={{ width: '100%' }} min={0} value={v}
          onChange={n => update(r.key, { qty: n ?? 0 })} />
      ),
    },
    {
      title: '單價', dataIndex: 'unit_price', width: 130,
      render: (v: number, r: QuotationItemRow) => (
        <InputNumber<number> style={{ width: '100%' }} min={0} value={v}
          formatter={n => `${n ?? ''}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          parser={n => Number((n || '').replace(/,/g, ''))}
          onChange={n => update(r.key, { unit_price: n ?? 0 })} />
      ),
    },
    {
      title: '小計', dataIndex: 'amount', width: 130, align: 'right' as const,
      render: (v: number) => <Text strong>{money(v || 0)}</Text>,
    },
    {
      title: '', width: 50,
      render: (_: unknown, r: QuotationItemRow) => (
        <Button type="text" danger icon={<DeleteOutlined />}
          onClick={() => { setRows(p => p.filter(x => x.key !== r.key)); setDirty(true); }} />
      ),
    },
  ];

  return (
    <div>
      {dirty && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message="尚未儲存" description="明細改動要按「儲存明細」才會回寫報價總價。" />
      )}

      <Space style={{ marginBottom: 12 }} wrap>
        <Button icon={<PlusOutlined />} onClick={() => {
          setRows(p => [...p, {
            key: `new-${Date.now()}-${p.length}`,
            item_name: '', unit: '式', qty: 1, unit_price: 0, amount: 0,
          }]);
          setDirty(true);
        }}>新增工項</Button>

        <Popconfirm title="儲存明細？" description="總價會由小計加總覆寫" onConfirm={() => save.mutate()}>
          <Button type="primary" icon={<SaveOutlined />} loading={save.isPending} disabled={!dirty}>
            儲存明細
          </Button>
        </Popconfirm>

        <Button icon={<PrinterOutlined />} onClick={() => window.print()} disabled={!rows.length}>
          列印報價單
        </Button>
      </Space>

      <Table
        rowKey="key"
        loading={isLoading}
        dataSource={rows}
        columns={columns}
        pagination={false}
        size="small"
        scroll={{ x: 900 }}
        locale={{ emptyText: '尚未逐項拆列。按「新增工項」開始，總價會由小計自動加總。' }}
        summary={() => (
          <Table.Summary fixed>
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={5}><Text type="secondary">小計</Text></Table.Summary.Cell>
              <Table.Summary.Cell index={1} align="right"><Text strong>{money(subtotal)}</Text></Table.Summary.Cell>
              <Table.Summary.Cell index={2} />
            </Table.Summary.Row>
            {tax > 0 && (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={5}><Text type="secondary">稅額</Text></Table.Summary.Cell>
                <Table.Summary.Cell index={1} align="right">{money(tax)}</Table.Summary.Cell>
                <Table.Summary.Cell index={2} />
              </Table.Summary.Row>
            )}
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={5}><Text strong>總計</Text></Table.Summary.Cell>
              <Table.Summary.Cell index={1} align="right">
                <Title level={5} style={{ margin: 0, color: '#1677ff' }}>{money(subtotal + tax)}</Title>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={2} />
            </Table.Summary.Row>
          </Table.Summary>
        )}
        title={() => (
          <Space direction="vertical" size={0}>
            <Text strong>{caseName || '報價單'}</Text>
            {caseCode && <Text type="secondary" style={{ fontSize: 12 }}>{caseCode}</Text>}
          </Space>
        )}
      />
    </div>
  );
};

export default QuotationItemsTab;
