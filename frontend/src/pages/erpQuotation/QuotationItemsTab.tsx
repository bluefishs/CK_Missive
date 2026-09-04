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
  Card, Row, Col, Divider,
} from 'antd';
import type { ColumnType } from 'antd/es/table';
import { useResponsive } from '../../hooks';
import { PlusOutlined, DeleteOutlined, SaveOutlined, } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { queryKeys } from '../../config/queryConfig';
import { erpQuotationsApi } from '../../api/erp/quotationsApi';
// 型別 SSOT 在 types/erp.ts —— 這裡若自己宣告一份，後端欄位一改就會靜默錯位
import type { QuotationItemRow, QuotationItemsDetail } from '../../types/erp';

const { Text, Title } = Typography;


interface Props {
  quotationId: number;
  caseName?: string;
  caseCode?: string;
  /**
   * 唯讀（2026-09-02 owner：「已承攬不應有報價明細編輯機制」）。
   * 成案後明細是合約的依據，改它會讓報價單與承攬案、請款對不上；
   * 要改要走版次（revision+1）或變更單，不是在這裡直接改。
   */
  readOnly?: boolean;
}

const money = (n: number) => `NT$ ${Math.round(n).toLocaleString()}`;

export const QuotationItemsTab: React.FC<Props> = ({ quotationId, caseName, caseCode, readOnly = false }) => {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [rows, setRows] = React.useState<QuotationItemRow[]>([]);
  const [dirty, setDirty] = React.useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.erpQuotations.items(quotationId),
    queryFn: async () => {
      const res = await apiClient.post<{ data: QuotationItemsDetail }>(
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
      const res = await apiClient.post<{ data: { item_count: number; total_price: number; total_price_updated: boolean; documents_refreshed?: string[]; documents_error?: string } }>(
        ERP_ENDPOINTS.QUOTATION_ITEMS_REPLACE,
        {
          quotation_id: quotationId,
          items: rows.map((r, i) => ({
            item_no: r.item_no?.trim() || undefined, item_name: r.item_name, spec: r.spec, unit: r.unit,
            qty: r.qty, unit_price: r.unit_price, amount: r.amount, sort_order: i, notes: r.notes || undefined,
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
      qc.invalidateQueries({ queryKey: queryKeys.erpQuotations.items(quotationId) });
      // 2026-09-04：已輸出的 XLS／PDF 由後端重新產出並覆蓋；沒有輸出過就不動
      if (r?.documents_refreshed?.length) {
        message.info(`已同步更新本案附件裡的 ${r.documents_refreshed.join('、')}`);
        void qc.invalidateQueries({ queryKey: ['pm-case-attachments'] });
      } else if (r?.documents_error) {
        message.warning(`明細已存，但已輸出的報價單檔更新失敗：${r.documents_error}`, 8);
      }
      // ⚠️ 原本寫 `['erp-quotation', ...]`（單數）—— 不存在。
      //    報價單家族的首 token 是 `erp-quotations`（見 useERPQuotations 的 erpKeys），
      //    用前綴一次涵蓋詳情與清單：改明細會動到總價，兩邊都該重載。
      qc.invalidateQueries({ queryKey: ['erp-quotations'] });
    },
    onError: () => message.error('儲存失敗'),
  });

  const update = (key: string, patch: Partial<QuotationItemRow>) => {
    setRows(prev => prev.map(r => {
      if (r.key !== key) return r;
      const next = { ...r, ...patch };
      // 2026-09-04 owner「項目填寫彈性」：複價可直接改（專案優惠等）。改數量／單價時，
      // 只在複價還等於原乘積（沒被手動改過）時才跟著重算；手動改過的複價保留。
      if ('amount' in patch) {
        next.amount_manual = true;
      } else if (!r.amount_manual) {
        next.amount = Math.round((next.qty || 0) * (next.unit_price || 0) * 100) / 100;
      }
      return next;
    }));
    setDirty(true);
  };

  // ⚠️ 2026-08-29：這裡原本一律 `小計 = 明細加總`、`總計 = 小計 + 稅額`，
  // 於是**沒有明細的報價單顯示的總計是錯的** —— 案件 509（35,000 元）
  // 畫面顯示「小計 0／稅額 1,750／總計 1,750」，而後端 `data.total` 回的是 35,000。
  //
  // 後端算對了，前端拿到後又自己算了一次。而本檔檔頭寫著
  // 「**清空明細不會把總價歸零** —— 空明細代表『還沒逐項拆』，不是『0 元』」：
  // 儲存邏輯守住了這條，**顯示沒有**。
  //
  // 判準：**有明細時以明細為準**（編輯中要即時反映改動，那是這個畫面的用途），
  // **沒有明細時以報價單本身的金額為準**（那是唯一的事實來源）。
  const itemsSubtotal = rows.reduce((s, r) => s + (r.amount || 0), 0);
  const tax = data?.tax_amount ?? 0;
  const noItems = rows.length === 0;
  const storedTotal = data?.total ?? 0;
  const subtotal = noItems ? Math.max(storedTotal - tax, 0) : itemsSubtotal;
  const total = noItems ? storedTotal : itemsSubtotal + tax;

  const { isMobile, isTablet } = useResponsive();
  const isNarrow = isMobile || isTablet;

  // 範本容量取自後端 —— 這裡原本也有一份手抄的 `5`，
  // 後端 08-29 提到 10 之後它會繼續叫使用者去合併輸出得出來的工項。
  // 同一個檔案裡的第二份手抄常數，與建單頁那份是同一天的同一個病。
  const { data: tplMeta } = useQuery({
    queryKey: ['quotation-template-meta'],
    queryFn: () => erpQuotationsApi.getTemplateMeta(),
    staleTime: 60 * 60 * 1000,
  });
  const capacity = tplMeta?.item_capacity ?? 5;

  // 2026-08-29：窄螢幕（含平板）收掉選填欄並降低強制寬度。
  // 實測 390px 下本表外溢 584px —— 而它是**可編輯**表格（每格是 Input），
  // 收掉必填欄會讓人改不了價，所以只收「規格／說明」（選填）。
  //
  // ⚠️ 這是**減災不是解決**：六欄價目表在 390px 上仍需橫向捲（降到約 230px）。
  // 真正的解是窄螢幕改一列一卡的編輯器，那是另一個工作量級；
  // 在那之前不要把這裡的數字下降讀成「手機可以順順地編報價單了」。
  const CN = '一二三四五六七八九十';
  const anyCustomNo = rows.some(r => (r.item_no ?? '').trim());
  const autoNo = (i: number) => (anyCustomNo ? `${i + 1}` : (i < CN.length ? `${CN[i]}、` : `${i + 1}、`));
  const columns = ([
    {
      // 2026-09-04 owner「小項 1.1／1.2」：項次可自填；空白就照列序自動 一、二、三
      title: '項次', dataIndex: 'item_no', width: 72, align: 'center' as const,
      render: (v: string, r: QuotationItemRow, i: number) => readOnly ? <Text>{v || autoNo(i)}</Text> : (
        <Input value={v} placeholder={autoNo(i)} onChange={e => update(r.key, { item_no: e.target.value })} />
      ),
    },
    {
      title: '工項', dataIndex: 'item_name', width: '28%',
      render: (v: string, r: QuotationItemRow) => readOnly ? <Text>{v || '—'}</Text> : (
        <Input value={v} placeholder="工項名稱" onChange={e => update(r.key, { item_name: e.target.value })} />
      ),
    },
    {
      title: '規格／說明', dataIndex: 'spec', width: '24%', _optionalOnNarrow: true,
      render: (v: string, r: QuotationItemRow) => readOnly ? <Text type="secondary">{v || '—'}</Text> : (
        <Input value={v} placeholder="選填" onChange={e => update(r.key, { spec: e.target.value })} />
      ),
    },
    {
      title: '單位', dataIndex: 'unit', width: 80,
      render: (v: string, r: QuotationItemRow) => readOnly ? <Text>{v || '式'}</Text> : (
        <Input value={v} placeholder="式" onChange={e => update(r.key, { unit: e.target.value })} />
      ),
    },
    {
      title: '數量', dataIndex: 'qty', width: 100,
      render: (v: number, r: QuotationItemRow) => readOnly ? <Text>{v}</Text> : (
        <InputNumber<number> style={{ width: '100%' }} min={0} value={v}
          onChange={n => update(r.key, { qty: n ?? 0 })} />
      ),
    },
    {
      title: '單價', dataIndex: 'unit_price', width: 130,
      render: (v: number, r: QuotationItemRow) => readOnly ? <Text>{money(v || 0)}</Text> : (
        <InputNumber<number> style={{ width: '100%' }} min={0} value={v}
          formatter={n => `${n ?? ''}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          parser={n => Number((n || '').replace(/,/g, ''))}
          onChange={n => update(r.key, { unit_price: n ?? 0 })} />
      ),
    },
    {
      title: '複價', dataIndex: 'amount', width: 130, align: 'right' as const,
      render: (v: number, r: QuotationItemRow) => readOnly ? <Text strong>{money(v || 0)}</Text> : (
        <InputNumber<number> style={{ width: '100%' }} min={0} value={v}
          formatter={n => `${n ?? ''}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          parser={n => Number((n || '').replace(/,/g, ''))}
          onChange={n => update(r.key, { amount: n ?? 0 })} />
      ),
    },
    {
      title: '備註', dataIndex: 'notes', width: 160, _optionalOnNarrow: true,
      render: (v: string, r: QuotationItemRow) => readOnly ? <Text type="secondary">{v || '—'}</Text> : (
        <Input value={v} placeholder="印在文件備註欄" onChange={e => update(r.key, { notes: e.target.value })} />
      ),
    },
    ...(readOnly ? [] : [{
      title: '', width: 50,
      render: (_: unknown, r: QuotationItemRow) => (
        <Button type="text" danger icon={<DeleteOutlined />}
          onClick={() => { setRows(p => p.filter(x => x.key !== r.key)); setDirty(true); }} />
      ),
    }]),
  ] as (ColumnType<QuotationItemRow> & { _optionalOnNarrow?: boolean })[])
    .filter((c) => !(isNarrow && c._optionalOnNarrow));

  // ── 窄螢幕：一列一卡（<992px）──────────────────────────────
  //
  // 六欄價目表每格都是 Input，390px 下即使收掉選填欄仍外溢約 230px ——
  // 而**編輯**時的橫向捲比瀏覽時更難用：手指捲動會誤觸輸入框。
  // 卡片版把同一列的六個欄位疊成三行，寬度由容器決定，**不需要橫向捲**。
  //
  // 刻意不共用 columns 定義：那六個 render 是為 <td> 寫的（無標籤、靠表頭
  // 說明語意），搬進卡片後每格都需要自己的標籤 —— 硬共用會得到一排無名輸入框。
  const narrowCards = (
    <div>
      {rows.length === 0 && (
        <Card size="small" style={{ marginBottom: 12 }}>
          <Text type="secondary">尚未逐項拆列。按「新增工項」開始，總價會由小計自動加總。</Text>
        </Card>
      )}
      {rows.map((r, i) => (
        <Card
          key={r.key}
          size="small"
          style={{ marginBottom: 8 }}
          title={<Text type="secondary" style={{ fontSize: 12 }}>第 {i + 1} 項</Text>}
          extra={readOnly ? null : (
            <Button type="text" danger size="small" icon={<DeleteOutlined />}
              onClick={() => { setRows(p => p.filter(x => x.key !== r.key)); setDirty(true); }} />
          )}
        >
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>工項</Text>
              <Input value={r.item_name} placeholder="工項名稱"
                onChange={e => update(r.key, { item_name: e.target.value })} />
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>規格／說明</Text>
              <Input value={r.spec} placeholder="選填"
                onChange={e => update(r.key, { spec: e.target.value })} />
            </div>
            <Row gutter={8}>
              <Col span={7}>
                <Text type="secondary" style={{ fontSize: 12 }}>單位</Text>
                <Input value={r.unit} placeholder="式"
                  onChange={e => update(r.key, { unit: e.target.value })} />
              </Col>
              <Col span={8}>
                <Text type="secondary" style={{ fontSize: 12 }}>數量</Text>
                <InputNumber<number> style={{ width: '100%' }} min={0} value={r.qty}
                  onChange={n => update(r.key, { qty: n ?? 0 })} />
              </Col>
              <Col span={9}>
                <Text type="secondary" style={{ fontSize: 12 }}>單價</Text>
                <InputNumber<number> style={{ width: '100%' }} min={0} value={r.unit_price}
                  formatter={n => `${n ?? ''}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={n => Number((n || '').replace(/,/g, ''))}
                  onChange={n => update(r.key, { unit_price: n ?? 0 })} />
              </Col>
            </Row>
            <div style={{ textAlign: 'right' }}>
              <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>小計</Text>
              <Text strong>{money(r.amount || 0)}</Text>
            </div>
          </Space>
        </Card>
      ))}

      {/* 合計 —— 卡片版沒有 Table.Summary，要自己給，否則窄螢幕看不到總價 */}
      <Card size="small">
        <Row justify="space-between">
          <Col><Text type="secondary">小計{noItems && '（報價單金額）'}</Text></Col>
          <Col><Text strong>{money(subtotal)}</Text></Col></Row>
        {tax > 0 && (
          <Row justify="space-between" style={{ marginTop: 4 }}>
            <Col><Text type="secondary">稅額</Text></Col><Col>{money(tax)}</Col></Row>
        )}
        <Divider style={{ margin: '8px 0' }} />
        <Row justify="space-between" align="middle">
          <Col><Text strong>總計</Text></Col>
          <Col><Title level={5} style={{ margin: 0, color: '#1677ff' }}>{money(total)}</Title></Col>
        </Row>
      </Card>
    </div>
  );

  return (
    <div>
      {dirty && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message="尚未儲存" description="明細改動要按「儲存明細」才會回寫報價總價。" />
      )}

      {isNarrow && (
        <Space direction="vertical" size={0} style={{ marginBottom: 8 }}>
          <Text strong>{caseName || '報價單'}</Text>
          {caseCode && <Text type="secondary" style={{ fontSize: 12 }}>{caseCode}</Text>}
        </Space>
      )}

      {readOnly && (
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
          message="此報價單已承攬，明細已鎖定"
          description="成案後的明細是合約與請款的依據。需要調整請以新版次或變更單處理，不在此直接修改。" />
      )}
      <Space style={{ marginBottom: 12 }} wrap>
        {!readOnly && <Button icon={<PlusOutlined />} onClick={() => {
          // 資料層存得下所以不擋，但要在**填的當下**說，
          // 不是走到輸出那一步才被 400 打回來合併工項。
          if (rows.length >= capacity) {
            message.warning(`正式文件範本目前僅容 ${capacity} 項，超出的項目輸出時需先合併`);
          }
          setRows(p => [...p, {
            key: `new-${Date.now()}-${p.length}`,
            item_name: '', unit: '式', qty: 1, unit_price: 0, amount: 0,
          }]);
          setDirty(true);
        }}>新增工項</Button>}

        {!readOnly && <Popconfirm title="儲存明細？" description="總價會由小計加總覆寫" onConfirm={() => save.mutate()}>
          <Button type="primary" icon={<SaveOutlined />} loading={save.isPending} disabled={!dirty}>
            儲存明細
          </Button>
        </Popconfirm>}

      </Space>

      {isNarrow ? narrowCards : (
      <Table
        tableLayout="fixed"
        rowKey="key"
        loading={isLoading}
        dataSource={rows}
        columns={columns}
        pagination={false}
        size="small"
        scroll={{ x: isNarrow ? 620 : 900 }}
        locale={{ emptyText: '尚未逐項拆列。按「新增工項」開始，總價會由小計自動加總。' }}
        summary={() => (
          <Table.Summary fixed>
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={5}>
                <Text type="secondary">小計{noItems && '（報價單金額，尚未逐項拆列）'}</Text>
              </Table.Summary.Cell>
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
                <Title level={5} style={{ margin: 0, color: '#1677ff' }}>{money(total)}</Title>
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
      )}
    </div>
  );
};

export default QuotationItemsTab;
