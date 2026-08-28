/**
 * 新增報價 — 範本式一頁建單（2026-08-28 owner：「erp/quotations/create 仍是 mis 非 xls 樣板」）
 *
 * 版面依正式報價單範本（`backend/app/templates/quotation_template.xlsx`）的結構：
 * 案首（案名／委託單位／年度）→ 逐項明細（工作內容／單位／數量／單價／複價）
 * → 小計／營業稅 5%／總計 → 備註。**不是** MIS 欄位表單。
 *
 * 兩個入口共用本頁：
 *  · 列表頁「新增報價」（無參數）＝快速建單 —— 送出時**先走授權路徑建 PM 案件**
 *    （委託單位寫進 pm_cases.client_name，輸出文件的客戶欄才有來源；
 *    entity_creation_ssot：PMCase 只能經 /pm/cases/create 建構），
 *    再建報價、再存明細，最後導向該案件的報價單分頁（唯一輸出入口）。
 *  · PM 案件詳情頁「新增報價」（帶 case_code）＝案件已存在，只建報價＋明細。
 *
 * 財務成本欄位（外包費／人事費等）**刻意不在本頁** —— 那是 ERP 財務視角，
 * 編輯路徑仍在 `/erp/quotations/:id/edit`（ERPQuotationFormPage）。
 */
import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card, Table, Button, Input, InputNumber, Space, Typography, App, Row, Col, Form, Modal,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, SaveOutlined, ArrowLeftOutlined, FileTextOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS, PM_ENDPOINTS } from '../../api/endpoints';
import { erpQuotationsApi as quotationsApi } from '../../api/erp/quotationsApi';
import { ROUTES } from '../../router/types';
import { ResponsiveContent } from '@ck-shared/ui-components';
import type { SuccessResponse } from '../../api/types';
import type { PMCase } from '../../types/pm';

const { Text, Title } = Typography;

const money = (n: number) => `NT$ ${Math.round(n).toLocaleString()}`;

/** 範本明細列（本頁為建立期的本地列，尚無 quotation_id） */
interface DraftItemRow {
  key: string;
  item_name: string;
  spec?: string;
  unit?: string;
  qty: number;
  unit_price: number;
}

/** 正式範本的明細容量 —— 超過的輸出時會被擋（quotation_document.py ITEM_LAST_ROW） */
const TEMPLATE_ITEM_CAPACITY = 5;

let _keySeq = 0;
const newRow = (): DraftItemRow => ({
  key: `draft-${++_keySeq}`, item_name: '', spec: '', unit: '式', qty: 1, unit_price: 0,
});

const QuotationTemplateCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchParams] = useSearchParams();

  // 入口 2（PM 案件詳情頁）帶進來的既有案件
  const presetCaseCode = searchParams.get('case_code') || undefined;
  const presetPmCaseId = searchParams.get('pm_case_id') || undefined;

  const [caseName, setCaseName] = React.useState(searchParams.get('case_name') ?? '');
  const [clientName, setClientName] = React.useState('');
  const [year, setYear] = React.useState<number>(
    Number(searchParams.get('year')) || new Date().getFullYear(),
  );
  const [notes, setNotes] = React.useState('');
  const [rows, setRows] = React.useState<DraftItemRow[]>([newRow(), newRow(), newRow()]);
  const [saving, setSaving] = React.useState(false);
  const [tplUrl, setTplUrl] = React.useState<string | null>(null);
  const [tplLoading, setTplLoading] = React.useState(false);

  // owner 2026-08-29：「xls 樣本報價單無法呈現嗎」——可以：
  // 空白範本經後端同一條 LibreOffice 鏈轉 PDF，建單前就能看到正式版面
  // （輸出 PDF 的預覽要先有單，這顆不用）。
  const showTemplate = async () => {
    setTplLoading(true);
    try {
      const res = await apiClient.post(
        ERP_ENDPOINTS.QUOTATION_TEMPLATE_PREVIEW, {}, { responseType: 'blob' },
      );
      const raw = res as unknown as { data?: Blob } | Blob;
      const blob = raw instanceof Blob ? raw : (raw.data as Blob);
      setTplUrl(URL.createObjectURL(blob));
    } catch {
      message.error('範本預覽產生失敗，請稍後再試');
    } finally {
      setTplLoading(false);
    }
  };

  const patch = (key: string, part: Partial<DraftItemRow>) =>
    setRows(rs => rs.map(r => (r.key === key ? { ...r, ...part } : r)));

  const filled = rows.filter(r => r.item_name.trim());
  const subtotal = filled.reduce((s, r) => s + r.qty * r.unit_price, 0);
  const tax = Math.round(subtotal * 0.05);
  const total = subtotal + tax;

  const addRow = () => {
    if (rows.length >= TEMPLATE_ITEM_CAPACITY) {
      // 不擋（資料層存得下），但要在**填的當下**說，不是輸出那一步才 400
      message.warning(
        `正式文件範本目前僅容 ${TEMPLATE_ITEM_CAPACITY} 項，超出的項目輸出時需先合併`,
      );
    }
    setRows(rs => [...rs, newRow()]);
  };

  const handleSubmit = async () => {
    if (!caseName.trim()) { message.error('請填寫案名'); return; }
    if (!presetCaseCode && !clientName.trim()) {
      message.error('請填寫委託單位 —— 輸出的報價單需要客戶抬頭'); return;
    }
    setSaving(true);
    try {
      // ① 案件：入口 1 需先建案（授權路徑），入口 2 已有
      let caseCode = presetCaseCode;
      let pmCaseId = presetPmCaseId;
      if (!caseCode) {
        const res = await apiClient.post<SuccessResponse<PMCase>>(PM_ENDPOINTS.CASES_CREATE, {
          case_name: caseName.trim(),
          client_name: clientName.trim(),
          year,
          category: '02', // 承攬報價 —— 本頁就是報價流程的入口
          status: 'planning',
        });
        const created = res.data!;
        caseCode = created.case_code ?? undefined;
        pmCaseId = String(created.id);
        if (!caseCode) throw new Error('建案成功但未取得建案案號');
      }

      // ② 報價單
      const quotation = await quotationsApi.create({
        case_code: caseCode,
        case_name: caseName.trim(),
        year,
        notes: notes.trim() || undefined,
      });

      // ③ 明細（有填才存；total_price 由後端小計回寫，不另填第二份事實）
      if (filled.length > 0) {
        await apiClient.post(ERP_ENDPOINTS.QUOTATION_ITEMS_REPLACE, {
          quotation_id: quotation.id,
          items: filled.map((r, i) => ({
            item_name: r.item_name.trim(), spec: r.spec?.trim() || undefined,
            unit: r.unit?.trim() || undefined, qty: r.qty, unit_price: r.unit_price,
            sort_order: i,
          })),
        });
      }

      message.success(`報價單已建立（${caseCode}）`);
      // ④ 直達唯一的輸出入口 —— 該案件的報價單分頁（明細編輯器＋輸出 PDF 都在那裡）
      if (pmCaseId) {
        navigate(`${ROUTES.PM_CASE_DETAIL.replace(':id', pmCaseId)}?tab=quotations`);
      } else {
        navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(quotation.id)));
      }
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || (e as Error).message || '建立失敗');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      title: '項次', width: 56, align: 'center' as const,
      render: (_: unknown, __: DraftItemRow, i: number) => i + 1,
    },
    {
      title: '工作內容', dataIndex: 'item_name',
      render: (_: unknown, r: DraftItemRow) => (
        <Input value={r.item_name} placeholder="例：地上物查估作業"
          onChange={e => patch(r.key, { item_name: e.target.value })} />
      ),
    },
    {
      title: '規格', dataIndex: 'spec', width: 140,
      render: (_: unknown, r: DraftItemRow) => (
        <Input value={r.spec} onChange={e => patch(r.key, { spec: e.target.value })} />
      ),
    },
    {
      title: '單位', dataIndex: 'unit', width: 80,
      render: (_: unknown, r: DraftItemRow) => (
        <Input value={r.unit} onChange={e => patch(r.key, { unit: e.target.value })} />
      ),
    },
    {
      title: '數量', dataIndex: 'qty', width: 90,
      render: (_: unknown, r: DraftItemRow) => (
        <InputNumber min={0} value={r.qty} style={{ width: '100%' }}
          onChange={v => patch(r.key, { qty: Number(v ?? 0) })} />
      ),
    },
    {
      title: '單價', dataIndex: 'unit_price', width: 120,
      render: (_: unknown, r: DraftItemRow) => (
        <InputNumber min={0} value={r.unit_price} style={{ width: '100%' }}
          formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          onChange={v => patch(r.key, { unit_price: Number(v ?? 0) })} />
      ),
    },
    {
      title: '複價', width: 120, align: 'right' as const,
      render: (_: unknown, r: DraftItemRow) => (
        <Text>{money(r.qty * r.unit_price)}</Text>
      ),
    },
    {
      title: '', width: 44,
      render: (_: unknown, r: DraftItemRow) => (
        <Button type="text" danger icon={<DeleteOutlined />} size="small"
          onClick={() => setRows(rs => rs.filter(x => x.key !== r.key))} />
      ),
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
            <Title level={4} style={{ margin: 0 }}>
              <FileTextOutlined style={{ marginRight: 8 }} />新增報價單
            </Title>
          </Space>
          <Button icon={<EyeOutlined />} loading={tplLoading} onClick={showTemplate}>
            檢視 XLS 範本樣式
          </Button>
        </Space>

        <Modal
          title="報價單範本樣式（輸出時即為此版面）"
          open={!!tplUrl}
          onCancel={() => { if (tplUrl) URL.revokeObjectURL(tplUrl); setTplUrl(null); }}
          footer={null}
          width="80%"
        >
          {tplUrl && (
            <iframe src={tplUrl} title="quotation-template-preview"
              style={{ width: '100%', height: '70vh', border: 'none' }} />
          )}
        </Modal>

        {/* 案首 —— 對應範本抬頭下方的案件資訊區 */}
        <Card size="small" title="案件資訊">
          <Form layout="vertical">
            <Row gutter={16}>
              <Col xs={24} md={presetCaseCode ? 16 : 10}>
                <Form.Item label="案名" required style={{ marginBottom: 8 }}>
                  <Input value={caseName} placeholder="工程／作業名稱"
                    onChange={e => setCaseName(e.target.value)} />
                </Form.Item>
              </Col>
              {!presetCaseCode && (
                <Col xs={24} md={8}>
                  <Form.Item label="委託單位（客戶抬頭）" required style={{ marginBottom: 8 }}>
                    <Input value={clientName} placeholder="輸出報價單的客戶名稱"
                      onChange={e => setClientName(e.target.value)} />
                  </Form.Item>
                </Col>
              )}
              <Col xs={12} md={4}>
                <Form.Item label="年度" style={{ marginBottom: 8 }}>
                  <InputNumber value={year} style={{ width: '100%' }}
                    onChange={v => setYear(Number(v ?? new Date().getFullYear()))} />
                </Form.Item>
              </Col>
              {presetCaseCode && (
                <Col xs={12} md={4}>
                  <Form.Item label="建案案號" style={{ marginBottom: 8 }}>
                    <Text code>{presetCaseCode}</Text>
                  </Form.Item>
                </Col>
              )}
            </Row>
          </Form>
          {!presetCaseCode && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              送出時會自動建立邀標案件並產生建案案號（CK{'{'}年{'}'}_PM_02_…），
              後續成案、附件、費用都掛在同一個案號下。
            </Text>
          )}
        </Card>

        {/* 明細 —— 對應範本第 16~20 列 */}
        <Card size="small" title="報價明細"
          extra={<Button icon={<PlusOutlined />} size="small" onClick={addRow}>新增項目</Button>}>
          <Table<DraftItemRow>
            columns={columns} dataSource={rows} rowKey="key"
            size="small" pagination={false}
            scroll={{ x: 760 }}
          />
          <Row justify="end" style={{ marginTop: 12 }}>
            <Col>
              <Space direction="vertical" size={2} style={{ textAlign: 'right' }}>
                <Text>小計：{money(subtotal)}</Text>
                <Text>營業稅 5%：{money(tax)}</Text>
                <Title level={5} style={{ margin: 0 }}>總計：{money(total)}</Title>
              </Space>
            </Col>
          </Row>
        </Card>

        <Card size="small" title="備註">
          <Input.TextArea rows={2} value={notes} placeholder="付款條件、有效期限等"
            onChange={e => setNotes(e.target.value)} />
        </Card>

        <Space>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSubmit}>
            建立報價單
          </Button>
          <Text type="secondary" style={{ fontSize: 12 }}>
            建立後即進入報價單分頁，可繼續編輯明細並輸出正式 XLS／PDF（自動存入本案附件）
          </Text>
        </Space>
      </Space>
    </ResponsiveContent>
  );
};

export default QuotationTemplateCreatePage;
