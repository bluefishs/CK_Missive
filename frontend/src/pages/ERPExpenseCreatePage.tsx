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
  Row, Col, Typography, App, Segmented, Alert, Divider, Space, Tag, Steps, Tooltip, Collapse,
} from 'antd';
import {
  ArrowLeftOutlined, SaveOutlined,
  ScanOutlined, CloudDownloadOutlined, EditOutlined, QrcodeOutlined,
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
import { ExpenseQRButton } from '../components/common/ExpenseQRCode';
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
  // 手機端控制項放大到 40px：實測這頁的輸入框/下拉高度只有 22–32px（AntD 預設 size），
  // 用滑鼠沒問題，用拇指就很容易點歪。桌面維持原尺寸不動。
  const ctrlSize = isMobile ? 'large' as const : 'middle' as const;

  // Multi-currency auto-calculation
  const watchCaseCode = Form.useWatch('case_code', form);
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
  // 手機端把「憑證類型」與「備註」收進更多（預設收合、一鍵展開，兩者都仍可填）。
  // 不是刪欄位 —— 核銷資料僅 9 筆，不足以用分佈當隱藏依據；這是版面取捨：
  // 憑證類型絕大多數情況維持預設值、備註可事後在詳情頁補，兩者都不必佔開頭的位置。
  const [showMoreFields, setShowMoreFields] = useState(false);
  // 批次連續建立（2026-07-31）：以 ref 記住本次送出要不要留在頁面，
  // 避免用 state 造成 submit 與狀態更新的時序競態。
  const continueRef = React.useRef(false);
  const [createdCount, setCreatedCount] = useState(0);

  // 最近使用的案件 (localStorage 記錄，工地人員通常反覆報同一案件)
  const RECENT_KEY = 'ck_expense_recent_cases';
  const recentCodes: string[] = useMemo(() => {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch { return []; }
  }, []);

  const caseOptions = useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pmCases = (pmCasesData as any)?.items ?? (pmCasesData as any)?.data?.items ?? [];
    const all = (Array.isArray(pmCases) ? pmCases : []).map((c: { case_code: string; project_code?: string; case_name: string; status: string }) => ({
      value: c.case_code,
      label: c.project_code ? `${c.project_code} ${c.case_name}` : `${c.case_code} ${c.case_name} (未成案)`,
      status: c.status,
      project_code: c.project_code,
    }));
    // 最近使用的排前面
    if (recentCodes.length > 0) {
      const recentSet = new Set(recentCodes);
      const recent = all.filter((c: { value: string }) => recentSet.has(c.value));
      const rest = all.filter((c: { value: string }) => !recentSet.has(c.value));
      return [...recent, ...rest];
    }
    return all;
  }, [pmCasesData, recentCodes]);

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

      message.success(`核銷紀錄已建立${continueRef.current ? '，可接著掃下一張' : ''}`);
      // 記住最近使用的案件 (行動端快速選擇)
      const usedCase = values.case_code as string | undefined;
      if (usedCase) {
        try {
          const prev: string[] = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
          const updated = [usedCase, ...prev.filter(c => c !== usedCase)].slice(0, 5);
          localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
        } catch { /* ignore */ }
      }
      // 2026-07-31（owner：行動裝置批次掃描會被中斷導回清單，無法接續作業）：
      // 原本每建立一筆就 navigate 到清單頁 → 手機上要一張一張重新進來。
      // 改為「建立並繼續」時留在本頁、重置表單回到掃描步驟，並保留案件歸屬。
      if (continueRef.current) {
        const keepCase = values.case_code as string | undefined;
        form.resetFields();
        form.setFieldsValue({
          currency: 'TWD', source: 'manual',
          case_code: keepCase,
        });
        setScanResult(null);
        setPreviewUrl(null);
        setScanImageFile(null);
        setCreatedCount((n) => n + 1);
        if (isMobile) setMobileStep(0);
        continueRef.current = false;
        return;
      }
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

  // 桌機 → 手機交接用：以「目前實際選定的案件」為準（手動選案也適用），退回 URL 參數
  const handoffCaseCode = (watchCaseCode as string | undefined) || urlCaseCode || null;
  const handoffCaseName = caseOptions.find(
    (c: { value: string; label: string }) => c.value === handoffCaseCode,
  )?.label;

  const scanPanel = (
    <ExpenseScanPanel
      method={method} scanning={scanning} scanResult={scanResult} previewUrl={previewUrl}
      isMobile={isMobile} mofInvoices={mofInvoices} onScan={doScan}
      onReset={() => { setScanResult(null); setPreviewUrl(null); }}
      onMofSelect={handleMofSelect} onGoToForm={() => setMobileStep(1)}
    />
  );

  /**
   * 行動版重點摘要（2026-07-31，owner：「對應行端如何呈現重點資訊與填報」）
   * 手機螢幕窄，表單一路捲下去容易漏看金額。掃描完成後先用大字把
   * 「發票號碼 / 金額 / 日期」攤在最上面供核對，其餘欄位仍在下方可改。
   * QR 金額有矛盾時（如 DC-09761665）這裡會直接標紅，避免存錯。
   */
  const mobileScanSummary = isMobile && scanResult ? (
    <Card size="small" style={{ marginBottom: 12 }} styles={{ body: { padding: 12 } }}>
      <Row gutter={8} align="middle">
        <Col span={14}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>發票號碼</Typography.Text>
          <div style={{ fontSize: 18, fontWeight: 600 }}>{scanResult.inv_num || '—'}</div>
        </Col>
        <Col span={10} style={{ textAlign: 'right' }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>金額</Typography.Text>
          <div style={{
            fontSize: 22, fontWeight: 700,
            color: scanResult.warnings?.length ? '#fa8c16' : '#1890ff',
          }}>
            NT$ {scanResult.amount != null ? scanResult.amount.toLocaleString() : '—'}
          </div>
        </Col>
      </Row>
      {scanResult.warnings?.length > 0 && (
        <Alert
          type="warning" showIcon style={{ marginTop: 8 }}
          message="金額與紙本可能不同，請核對後修改"
          description={<div style={{ fontSize: 12 }}>{scanResult.warnings[0]}</div>}
        />
      )}
    </Card>
  ) : null;

  const expenseForm = (
    <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ currency: 'TWD', source: 'manual', case_code: urlCaseCode || undefined }}>
      {mobileScanSummary}
      <Form.Item name="source" hidden><Input /></Form.Item>
      {(!isMobile || showMoreFields) && (
        <Form.Item label="憑證類型">
          <Select value={voucherType} size={ctrlSize} onChange={(v) => { setVoucherType(v); if (v !== 'invoice') form.setFieldValue('inv_num', ''); }} options={VOUCHER_TYPE_OPTIONS} />
        </Form.Item>
      )}
      <Row gutter={12}>
        <Col xs={24} sm={12}>
          <Form.Item name="inv_num" label={voucherType === 'invoice' ? '發票號碼' : '憑證編號'}
            rules={[{ required: voucherType === 'invoice', message: '請輸入發票號碼' }, ...(voucherType === 'invoice' ? [{ pattern: /^[A-Z]{2}\d{8}$/, message: '格式: AB12345678' }] : [])]}
            extra={voucherType !== 'invoice' ? '選填，留空自動產生' : undefined}
            /* 用 normalize 而非 onChange+setFieldValue：後者改得了值卻不會重跑驗證，
               實測會留下「值已是 AB12345678、欄位仍紅字報格式錯誤」的過期錯誤。
               normalize 在值進入 form store 前就轉換，驗證看到的就是轉換後的值。 */
            normalize={(v) => (voucherType === 'invoice' && typeof v === 'string' ? v.toUpperCase() : v)}>
            {/* 發票號碼規則是 ^[A-Z]{2}\d{8}$ —— 手機打前兩碼字母得先按 shift，
                打成小寫還會被驗證擋下。改為輸入時自動轉大寫（桌面同樣受惠）。 */}
            <Input
              placeholder={voucherType === 'invoice' ? 'AB12345678' : '選填'}
              maxLength={voucherType === 'invoice' ? 10 : 50}
              size={ctrlSize}
              autoCapitalize="characters"
              autoCorrect="off"
              spellCheck={false}
            />
          </Form.Item>
        </Col>
        <Col xs={24} sm={12}>
          <Form.Item name="date" label="開立日期" rules={[{ required: true }]}>
            {/* 刻意**不預設今天**：這是財務憑證的日期，猜錯而使用者沒發現就是髒資料。
                改為給一鍵捷徑 —— 省掉點日曆的功夫，但仍是使用者明確選的。 */}
            <DatePicker
              style={{ width: '100%' }} size={ctrlSize} inputReadOnly={isMobile}
              presets={[
                { label: '今天', value: dayjs() },
                { label: '昨天', value: dayjs().add(-1, 'd') },
              ]}
            />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col xs={24} sm={12}>
          <Form.Item name="amount" label="含稅總額" rules={[{ required: true }]}>
            {/* inputMode 缺席時手機跳的是全鍵盤而不是數字鍵盤（實測 inputmode 為空）。 */}
            <InputNumber style={{ width: '100%' }} min={0} prefix="NT$" size={ctrlSize} inputMode="decimal"
              formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(v) => Number(v!.replace(/,/g, '')) as unknown as 0} />
          </Form.Item>
        </Col>
      </Row>

      {/* 2026-08-16 核銷簡化（owner）。
          量測：9 筆核銷裡 **6 筆走 QR 掃描**（會自動帶入稅額與統編），
          而 **外幣三欄從來沒有被用過**（非 TWD 0 筆、匯率 0 筆）。
          瓶頸其實不在填報而在審核（6 筆卡著、其中 4 筆 16 天沒動），
          但把「掃了就有」與「從沒用過」的欄位一直攤在畫面上，
          會讓這張表看起來比實際需要填的多一倍。
          → 收進可展開區。**值仍然會被 QR 帶入並送出**，只是預設不占版面。 */}
      {!isMobile && (
        <Collapse
          ghost
          size="small"
          style={{ marginBottom: 8 }}
          items={[{
            key: 'adv',
            label: <Typography.Text type="secondary" style={{ fontSize: 13 }}>進階（稅額、統編、幣別）— QR 掃描會自動帶入</Typography.Text>,
            children: (
              <Row gutter={12}>
                <Col sm={6}>
                  <Form.Item name="tax_amount" label="稅額">
                    <InputNumber style={{ width: '100%' }} min={0} prefix="NT$" />
                  </Form.Item>
                </Col>
                <Col sm={6}>
                  <Form.Item name="buyer_ban" label="買方統編"><Input placeholder="8碼 (個人留空)" maxLength={8} /></Form.Item>
                </Col>
                <Col sm={6}>
                  <Form.Item name="seller_ban" label="賣方統編"><Input placeholder="8碼" maxLength={8} /></Form.Item>
                </Col>
                <Col sm={6}>
                  <Form.Item name="currency" label="幣別"><Select options={CURRENCY_OPTIONS} /></Form.Item>
                </Col>
              </Row>
            ),
          }]}
        />
      )}

      <Divider style={{ margin: '8px 0 16px' }}>核銷歸屬</Divider>
      <Form.Item label="歸屬類型">
        <Segmented block size="large" value={attrType}
          onChange={(v) => { setAttrType(v as typeof attrType); if (v === 'none') form.setFieldValue('case_code', undefined); }}
          options={[{ value: 'project', label: '專案費用' }, { value: 'operational', label: '營運費用' }, { value: 'none', label: '未歸屬' }]} />
      </Form.Item>
      {attrType === 'project' && (
        <Form.Item name="case_code" label="關聯案件" extra={isMobile ? undefined : '已成案顯示成案編號，最近使用的排前面'}>
          <Select showSearch allowClear optionFilterProp="label" size={ctrlSize}
            placeholder={isMobile ? '搜尋案件名稱或編號' : '選擇案件'}
            options={caseOptions}
            listHeight={isMobile ? 200 : 256}
            optionRender={(option) => {
              const isRecent = recentCodes.includes(option.value as string);
              return (
                <Space>
                  {isRecent && <Tag color="blue" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>近期</Tag>}
                  <span>{option.label}</span>
                  {!(option.data as { project_code?: string }).project_code && <Tag color="orange" style={{ fontSize: 11 }}>未成案</Tag>}
                </Space>
              );
            }} />
        </Form.Item>
      )}
      {attrType === 'operational' && <Alert type="info" showIcon message="營運費用將自動歸入營運帳目" style={{ marginBottom: 16 }} />}
      <Row gutter={12}>
        <Col xs={24} sm={12}>
          <Form.Item name="category" label="費用分類" rules={[{ required: true, message: '請選擇分類' }]}>
            <Select placeholder="選擇分類" size={ctrlSize} options={EXPENSE_CATEGORY_OPTIONS} />
          </Form.Item>
        </Col>
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
      {(!isMobile || showMoreFields) && (
        <Form.Item name="notes" label="備註"><Input.TextArea rows={isMobile ? 1 : 2} maxLength={500} size={ctrlSize} /></Form.Item>
      )}
      {isMobile && !showMoreFields && (
        <Button type="link" size="small" style={{ paddingLeft: 0, marginBottom: 8 }}
          onClick={() => setShowMoreFields(true)}>
          更多欄位（憑證類型、備註）
        </Button>
      )}
      {isMobile && <Form.Item name="currency" hidden initialValue="TWD"><Input /></Form.Item>}

      <div style={{ display: 'flex', gap: 8, flexDirection: isMobile ? 'column' : 'row' }}>
        <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={createMutation.isPending} size="large" block={isMobile}
          onClick={() => { continueRef.current = false; }}>
          建立核銷{createdCount > 0 ? `（本次已建 ${createdCount} 筆）` : ''}
        </Button>
        {/* 批次連續：建立後不離開本頁，直接回到掃描步驟接續下一張 */}
        <Button htmlType="submit" icon={<ScanOutlined />} size="large" block={isMobile}
          loading={createMutation.isPending}
          onClick={() => { continueRef.current = true; }}>
          建立並繼續掃下一張
        </Button>
        {/* 「返回掃描」原為第三個全寬大按鈕（約 48px）。它是三個動作裡最次要的，
            且捲到底時正好被浮動助理鈕蓋住 → 降級為文字連結，版面少一整列。 */}
        {isMobile && mobileStep === 1 && (
          <Button type="link" onClick={() => setMobileStep(0)} style={{ alignSelf: 'center' }}>返回掃描</Button>
        )}
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
              <Col md={10}>
                <Card
                  title={method}
                  style={{ minHeight: 300 }}
                  /* 2026-07-30（owner）：桌機沒有相機，發票要用手機拍。
                     此處提供「電腦 → 手機」交接 QR：掃了就在手機開同一案的核銷頁
                     （URL 帶 case_code），直接用手機相機拍照上傳。
                     原本 QR 只在案件詳情頁 → 人已經在建立頁時得退回去找，流程斷。 */
                  extra={handoffCaseCode ? (
                    <ExpenseQRButton
                      caseCode={handoffCaseCode}
                      caseName={handoffCaseName}
                      label="用手機拍照上傳"
                      tooltip="用手機掃描此 QR，即可在手機開啟同一案件的核銷頁並用相機拍發票"
                      type="primary"
                    />
                  ) : (
                    <Tooltip title="請先選擇關聯案件，才能產生手機專用連結">
                      <Button icon={<QrcodeOutlined />} disabled>用手機拍照上傳</Button>
                    </Tooltip>
                  )}
                >
                  {scanPanel}
                </Card>
              </Col>
              <Col md={14}><Card title="核銷資訊">{expenseForm}</Card></Col>
            </Row>
          </>
        )}
      </div>
    </ResponsiveContent>
  );
};

export default ERPExpenseCreatePage;
