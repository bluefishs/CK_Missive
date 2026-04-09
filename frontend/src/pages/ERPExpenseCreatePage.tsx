/**
 * 新增核銷頁面 — 統一入口
 *
 * 三種輸入方式填入同一張表單：
 *   1. 手動填寫
 *   2. 智慧掃描 (拍照/選圖 → QR+OCR 自動填入)
 *   3. 財政部發票 (選取已同步的電子發票填入)
 *
 * v3.0.0 — 行動優先重構：手機端步驟式單流程，桌面端保持雙欄
 */
import React, { useState, useMemo, useEffect } from 'react';
import {
  Button, Card, Form, Input, InputNumber, Select, DatePicker,
  Row, Col, Typography, App, Segmented, Alert, Divider, Space, Tag, Steps,
} from 'antd';
import {
  ArrowLeftOutlined, SaveOutlined,
  ScanOutlined, CloudDownloadOutlined, EditOutlined,
} from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useResponsive } from '../hooks/utility/useResponsive';
import { useCreateExpense, usePMCases, useEInvoicePendingList } from '../hooks';
import type { ExpenseInvoiceCreate, VoucherType } from '../types/erp';
import { EXPENSE_CATEGORY_OPTIONS, CURRENCY_OPTIONS, VOUCHER_TYPE_OPTIONS } from '../types/erp';
import { ROUTES } from '../router/types';
import { ERP_ENDPOINTS } from '../api/endpoints';
import { expensesApi } from '../api/erp';
import apiClient from '../api/client';
import type { SmartScanResult } from '../api/erp/expensesApi';
import ExpenseScanPanel from './erpExpense/ExpenseScanPanel';
import { compressImage } from './erpExpense/imageUtils';

type InputMethod = '智慧掃描' | '手動填寫' | '財政部發票';

const ERPExpenseCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createMutation = useCreateExpense();
  const { data: pmCasesData } = usePMCases({ page: 1, page_size: 200 });
  const { data: mofData } = useEInvoicePendingList({ skip: 0, limit: 50 });
  const mofInvoices = (mofData as { items?: Array<{ id: number; inv_num: string; date: string; amount: number; seller_ban?: string; status: string }> })?.items ?? [];
  const { isMobile } = useResponsive();

  // Multi-currency auto-calculation
  const watchCurrency = Form.useWatch('currency', form);
  const watchOriginalAmount = Form.useWatch('original_amount', form);
  const watchExchangeRate = Form.useWatch('exchange_rate', form);
  const isForeignCurrency = watchCurrency && watchCurrency !== 'TWD';

  useEffect(() => {
    if (isForeignCurrency && watchOriginalAmount && watchExchangeRate) {
      const calculated = Math.round(watchOriginalAmount * watchExchangeRate);
      form.setFieldValue('amount', calculated);
    }
  }, [isForeignCurrency, watchOriginalAmount, watchExchangeRate, form]);

  const urlCaseCode = searchParams.get('case_code');
  const [method, setMethod] = useState<InputMethod>('智慧掃描');
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<SmartScanResult | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [scanImageFile, setScanImageFile] = useState<File | null>(null);
  const [attrType, setAttrType] = useState<'project' | 'operational' | 'none'>(urlCaseCode ? 'project' : 'none');
  const [voucherType, setVoucherType] = useState<VoucherType>('invoice');
  const [mobileStep, setMobileStep] = useState(0);

  const caseOptions = useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pmCases = (pmCasesData as any)?.items ?? (pmCasesData as any)?.data?.items ?? [];
    return (Array.isArray(pmCases) ? pmCases : []).map((c: { case_code: string; project_code?: string; case_name: string; status: string }) => ({
      value: c.case_code,
      label: c.project_code ? `${c.project_code} ${c.case_name}` : `${c.case_code} ${c.case_name} (未成案)`,
      status: c.status,
      project_code: c.project_code,
    }));
  }, [pmCasesData]);

  // --- 智慧掃描 (含圖片壓縮) ---
  const doScan = async (file: File) => {
    if (file.size > 10 * 1024 * 1024) { message.error('檔案過大，上限 10MB'); return; }
    setScanning(true);
    const compressed = await compressImage(file);
    setScanImageFile(compressed);
    setPreviewUrl(URL.createObjectURL(compressed));
    setScanResult(null);
    try {
      const res = await expensesApi.smartScan(compressed, { auto_create: false });
      const data = res.data ?? null;
      setScanResult(data);
      if (data?.success && data.inv_num) {
        form.setFieldsValue({
          inv_num: data.inv_num, date: data.date ? dayjs(data.date) : dayjs(),
          amount: data.amount, tax_amount: data.tax_amount,
          buyer_ban: data.buyer_ban, seller_ban: data.seller_ban,
          source: `smart_${data.method}`,
        });
        message.success(`辨識成功 (${data.method === 'qr' ? 'QR Code' : 'OCR'} ${Math.round(data.confidence * 100)}%)`);
        // AI 自動分類
        const itemName = data.items?.[0]?.name || '';
        if (itemName || data.seller_ban) {
          apiClient.post<{ data: { category?: string } }>(
            ERP_ENDPOINTS.EXPENSES_SUGGEST_CATEGORY,
            { item_name: itemName, seller: data.seller_ban || '' },
          ).then(r => { const cat = r.data?.category; if (cat) { form.setFieldValue('category', cat); message.info(`AI 建議分類：${cat}`); } }).catch(() => {});
        }
        if (isMobile) setMobileStep(1);
      } else {
        message.warning('未辨識出發票資訊，請手動填寫');
        if (isMobile) setMobileStep(1);
      }
    } catch { message.error('辨識失敗'); }
    finally { setScanning(false); }
  };

  const handleMofSelect = (inv: { inv_num: string; date: string; amount: number; seller_ban?: string }) => {
    form.setFieldsValue({ inv_num: inv.inv_num, date: dayjs(inv.date), amount: inv.amount, seller_ban: inv.seller_ban, source: 'mof_sync' });
    message.success(`已填入 ${inv.inv_num}`);
    if (isMobile) setMobileStep(1);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        date: values.date ? dayjs(values.date as string).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
        source: values.source || 'manual', voucher_type: voucherType, attribution_type: attrType,
        case_code: attrType === 'none' ? undefined : values.case_code,
        inv_num: values.inv_num || (voucherType !== 'invoice' ? `AUTO-${Date.now()}` : undefined),
      } as unknown as ExpenseInvoiceCreate;
      const result = await createMutation.mutateAsync(payload);

      // 上傳掃描/拍照圖片作為收據附件
      if (scanImageFile) {
        try {
          // result 可能是 {data: {id}} 或 {id} (視 API wrapper 結構)
          const rd = result as { data?: { id?: number }; id?: number };
          const expenseId = rd?.data?.id ?? rd?.id;
          if (expenseId) {
            await apiClient.upload(
              ERP_ENDPOINTS.EXPENSES_UPLOAD_RECEIPT,
              scanImageFile,
              'file',
              { invoice_id: String(expenseId) },
            );
          }
        } catch {
          message.warning('紀錄已建立，但收據圖片上傳失敗');
        }
      }

      message.success('核銷紀錄已建立');
      navigate(ROUTES.ERP_EXPENSES);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || '建立失敗');
    }
  };

  // --- 共用元素 ---
  const methodSelector = (
    <Segmented
      block size={isMobile ? 'middle' : 'large'} value={method}
      onChange={(v) => setMethod(v as InputMethod)}
      options={[
        { value: '智慧掃描', icon: <ScanOutlined />, label: isMobile ? '掃描' : '智慧掃描' },
        { value: '手動填寫', icon: <EditOutlined />, label: isMobile ? '手動' : '手動填寫' },
        { value: '財政部發票', icon: <CloudDownloadOutlined />, label: isMobile ? '電子發票' : '財政部發票' },
      ]}
    />
  );

  const scanPanel = (
    <ExpenseScanPanel
      method={method} scanning={scanning} scanResult={scanResult} previewUrl={previewUrl}
      isMobile={isMobile} mofInvoices={mofInvoices} onScan={doScan}
      onReset={() => { setScanResult(null); setPreviewUrl(null); }}
      onMofSelect={handleMofSelect} onGoToForm={() => setMobileStep(1)}
    />
  );

  const expenseForm = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ currency: 'TWD', source: 'manual', case_code: urlCaseCode || undefined }}>
      <Form.Item name="source" hidden><Input /></Form.Item>
      <Form.Item label="憑證類型">
        <Select value={voucherType} onChange={(v) => { setVoucherType(v); if (v !== 'invoice') form.setFieldValue('inv_num', ''); }} options={VOUCHER_TYPE_OPTIONS} />
      </Form.Item>
      <Row gutter={12}>
        <Col xs={24} sm={12}>
          <Form.Item name="inv_num" label={voucherType === 'invoice' ? '發票號碼' : '憑證編號'}
            rules={[{ required: voucherType === 'invoice', message: '請輸入發票號碼' }, ...(voucherType === 'invoice' ? [{ pattern: /^[A-Z]{2}\d{8}$/, message: '格式: AB12345678' }] : [])]}
            extra={voucherType !== 'invoice' ? '選填，留空自動產生' : undefined}>
            <Input placeholder={voucherType === 'invoice' ? 'AB12345678' : '選填'} maxLength={voucherType === 'invoice' ? 10 : 50} />
          </Form.Item>
        </Col>
        <Col xs={24} sm={12}>
          <Form.Item name="date" label="開立日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col xs={24} sm={12}>
          <Form.Item name="amount" label="含稅總額" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} prefix="NT$"
              formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(v) => Number(v!.replace(/,/g, '')) as unknown as 0} />
          </Form.Item>
        </Col>
        <Col xs={24} sm={12}>
          <Form.Item name="tax_amount" label="稅額">
            <InputNumber style={{ width: '100%' }} min={0} prefix="NT$" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col xs={24} sm={12}>
          <Form.Item name="buyer_ban" label="買方統編"><Input placeholder="8碼 (個人留空)" maxLength={8} /></Form.Item>
        </Col>
        <Col xs={24} sm={12}>
          <Form.Item name="seller_ban" label="賣方統編"><Input placeholder="8碼" maxLength={8} /></Form.Item>
        </Col>
      </Row>

      <Divider style={{ margin: '8px 0 16px' }}>核銷歸屬</Divider>
      <Form.Item label="歸屬類型">
        <Segmented block size={isMobile ? 'middle' : 'large'} value={attrType}
          onChange={(v) => { setAttrType(v as typeof attrType); if (v === 'none') form.setFieldValue('case_code', undefined); }}
          options={[{ value: 'project', label: '專案費用' }, { value: 'operational', label: '營運費用' }, { value: 'none', label: '未歸屬' }]} />
      </Form.Item>
      {attrType === 'project' && (
        <Form.Item name="case_code" label="關聯案件" extra={isMobile ? undefined : '已成案顯示成案編號'}>
          <Select showSearch allowClear optionFilterProp="label" placeholder="選擇案件" options={caseOptions}
            optionRender={(option) => (<Space><span>{option.label}</span>{!(option.data as { project_code?: string }).project_code && <Tag color="orange" style={{ fontSize: 11 }}>未成案</Tag>}</Space>)} />
        </Form.Item>
      )}
      {attrType === 'operational' && <Alert type="info" showIcon message="營運費用將自動歸入營運帳目" style={{ marginBottom: 16 }} />}
      <Row gutter={12}>
        <Col xs={24} sm={12}>
          <Form.Item name="category" label="費用分類" rules={[{ required: true, message: '請選擇分類' }]}>
            <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} />
          </Form.Item>
        </Col>
        {!isMobile && <Col sm={6}><Form.Item name="currency" label="幣別"><Select options={CURRENCY_OPTIONS} /></Form.Item></Col>}
      </Row>
      {isForeignCurrency && (
        <Row gutter={12}>
          <Col xs={24} sm={8}>
            <Form.Item name="original_amount" label="原幣金額" rules={[{ required: true, message: '請輸入原幣金額' }]}>
              <InputNumber style={{ width: '100%' }} min={0}
                formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(v) => Number(v!.replace(/,/g, '')) as unknown as 0} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name="exchange_rate" label="匯率" rules={[{ required: true, message: '請輸入匯率' }]}>
              <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={4} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item label="折算台幣">
              <InputNumber style={{ width: '100%' }} value={watchOriginalAmount && watchExchangeRate ? Math.round(watchOriginalAmount * watchExchangeRate) : undefined}
                disabled prefix="NT$"
                formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
            </Form.Item>
          </Col>
        </Row>
      )}
      <Form.Item name="notes" label="備註"><Input.TextArea rows={isMobile ? 1 : 2} maxLength={500} /></Form.Item>
      {isMobile && <Form.Item name="currency" hidden initialValue="TWD"><Input /></Form.Item>}

      <div style={{ display: 'flex', gap: 8, flexDirection: isMobile ? 'column' : 'row' }}>
        <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={createMutation.isPending} size="large" block={isMobile}>建立核銷</Button>
        {isMobile && mobileStep === 1 && <Button block onClick={() => setMobileStep(0)}>返回掃描</Button>}
        {!isMobile && <Button onClick={() => navigate(ROUTES.ERP_EXPENSES)}>取消</Button>}
      </div>
    </Form>
  );

  // =========================================================================
  return (
    <ResponsiveContent>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.ERP_EXPENSES)} size={isMobile ? 'middle' : 'large'}>{isMobile ? '' : '返回'}</Button>
          <Typography.Title level={isMobile ? 5 : 4} style={{ margin: 0, flex: 1 }}>新增核銷</Typography.Title>
        </div>

        {isMobile ? (
          <>
            <Steps size="small" current={mobileStep} items={[{ title: '輸入方式' }, { title: '填寫送出' }]} style={{ marginBottom: 4 }} />
            {mobileStep === 0 && <Card size="small" styles={{ body: { padding: 12 } }}><div style={{ marginBottom: 12 }}>{methodSelector}</div>{scanPanel}</Card>}
            {mobileStep === 1 && (
              <Card size="small" styles={{ body: { padding: 12 } }}>
                {scanResult?.success && <Alert type="success" showIcon message={`已辨識 ${scanResult.inv_num} — NT$ ${scanResult.amount?.toLocaleString()}`} style={{ marginBottom: 12 }} closable />}
                {expenseForm}
              </Card>
            )}
          </>
        ) : (
          <>
            <Card size="small">{methodSelector}</Card>
            <Row gutter={16}>
              <Col md={10}><Card title={method} style={{ minHeight: 300 }}>{scanPanel}</Card></Col>
              <Col md={14}><Card title="核銷資訊">{expenseForm}</Card></Col>
            </Row>
          </>
        )}
      </div>
    </ResponsiveContent>
  );
};

export default ERPExpenseCreatePage;
