/**
 * 新增核銷頁面 — 統一入口
 *
 * 三種輸入方式填入同一張表單：
 *   1. 手動填寫
 *   2. 智慧掃描 (拍照/選圖 → QR+OCR 自動填入)
 *   3. 財政部發票 (選取已同步的電子發票填入)
 *
 * 使用者確認/補充分類、案號後送出建檔。
 *
 * @version 2.0.0
 */
import React, { useState, useRef, useMemo } from 'react';
import {
  Button, Card, Form, Input, InputNumber, Select, DatePicker,
  Row, Col, Typography, App, Segmented, Upload, Spin, Alert,
  Descriptions, Tag, Divider, Space, Image,
} from 'antd';
import {
  ArrowLeftOutlined, SaveOutlined, CameraOutlined,
  ScanOutlined, CloudDownloadOutlined, EditOutlined,
  PictureOutlined,
} from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useCreateExpense, usePMCases, useEInvoicePendingList } from '../hooks';
import type { ExpenseInvoiceCreate } from '../types/erp';
import { EXPENSE_CATEGORY_OPTIONS, CURRENCY_OPTIONS } from '../types/erp';
import { ROUTES } from '../router/types';
import { ERP_ENDPOINTS } from '../api/endpoints';
import { expensesApi } from '../api/erp';
import apiClient from '../api/client';
import type { SmartScanResult } from '../api/erp/expensesApi';

const { Text } = Typography;

type InputMethod = '手動填寫' | '智慧掃描' | '財政部發票';

const ERPExpenseCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createMutation = useCreateExpense();
  const { data: pmCasesData } = usePMCases({ page: 1, page_size: 200 });
  const { data: mofData } = useEInvoicePendingList({ skip: 0, limit: 50 });
  const mofInvoices = (mofData as { items?: Array<{ id: number; inv_num: string; date: string; amount: number; seller_ban?: string; status: string }> })?.items ?? [];
  const cameraRef = useRef<HTMLInputElement>(null);

  // 從 URL 讀取預設案件 (PM Case 費用 Tab 點「新增」帶入)
  const urlCaseCode = searchParams.get('case_code');

  const [method, setMethod] = useState<InputMethod>('智慧掃描');
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<SmartScanResult | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [attrType, setAttrType] = useState<'project' | 'operational' | 'none'>(urlCaseCode ? 'project' : 'none');

  // 案件下拉 — 區分已成案/未成案
  const caseOptions = useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pmCases = (pmCasesData as any)?.items ?? (pmCasesData as any)?.data?.items ?? [];
    return (Array.isArray(pmCases) ? pmCases : []).map((c: { case_code: string; project_code?: string; case_name: string; status: string }) => ({
      value: c.case_code,
      label: c.project_code
        ? `${c.project_code} ${c.case_name}`
        : `${c.case_code} ${c.case_name} (未成案)`,
      status: c.status,
      project_code: c.project_code,
    }));
  }, [pmCasesData]);

  // --- 智慧掃描 ---
  const doScan = async (file: File) => {
    if (file.size > 10 * 1024 * 1024) {
      message.error('檔案過大，上限 10MB');
      return;
    }
    setScanning(true);
    setPreviewUrl(URL.createObjectURL(file));
    setScanResult(null);

    try {
      // auto_create=false: 只辨識不建檔，讓使用者補充分類後再送出
      const res = await expensesApi.smartScan(file, { auto_create: false });
      const data = res.data ?? null;
      setScanResult(data);

      if (data?.success && data.inv_num) {
        // 自動填入表單
        form.setFieldsValue({
          inv_num: data.inv_num,
          date: data.date ? dayjs(data.date) : dayjs(),
          amount: data.amount,
          tax_amount: data.tax_amount,
          buyer_ban: data.buyer_ban,
          seller_ban: data.seller_ban,
          source: `smart_${data.method}`,
        });
        message.success(`辨識成功 (${data.method === 'qr' ? 'QR Code' : 'OCR'} ${Math.round(data.confidence * 100)}%)，請確認後送出`);

        // AI 自動分類建議
        const itemName = data.items?.[0]?.name || '';
        if (itemName || data.seller_ban) {
          apiClient.post<{ data: { category?: string } }>(
            ERP_ENDPOINTS.EXPENSES_SUGGEST_CATEGORY,
            { item_name: itemName, seller: data.seller_ban || '' },
          ).then(res => {
            const cat = res.data?.category;
            if (cat) {
              form.setFieldValue('category', cat);
              message.info(`AI 建議分類：${cat}`);
            }
          }).catch(() => {/* ignore */});
        }
      } else {
        message.warning('未辨識出發票資訊，請手動填寫');
      }
    } catch {
      message.error('辨識失敗');
    } finally {
      setScanning(false);
    }
  };

  // --- 送出 ---
  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        date: values.date ? dayjs(values.date as string).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
        source: values.source || 'manual',
        attribution_type: attrType,
        // attrType='none' 時清除 case_code
        case_code: attrType === 'none' ? undefined : values.case_code,
      } as unknown as ExpenseInvoiceCreate;
      await createMutation.mutateAsync(payload);
      message.success('核銷紀錄已建立');
      navigate(ROUTES.ERP_EXPENSES);
    } catch {
      message.error('建立失敗');
    }
  };

  return (
    <ResponsiveContent>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.ERP_EXPENSES)}>返回</Button>
          <Typography.Title level={4} style={{ margin: 0 }}>新增核銷</Typography.Title>
        </div>

        {/* 輸入方式切換 */}
        <Card size="small">
          <Segmented
            block
            size="large"
            value={method}
            onChange={(v) => setMethod(v as InputMethod)}
            options={[
              { value: '智慧掃描', icon: <ScanOutlined /> },
              { value: '手動填寫', icon: <EditOutlined /> },
              { value: '財政部發票', icon: <CloudDownloadOutlined /> },
            ]}
          />
        </Card>

        <Row gutter={16}>
          {/* 左欄：輸入方式面板 */}
          <Col xs={24} md={10}>
            <Card title={method} style={{ minHeight: 300 }}>
              {method === '智慧掃描' && (
                <>
                  {!scanning && !scanResult && (
                    <>
                      <Button
                        type="primary" icon={<CameraOutlined />} block size="large"
                        onClick={() => cameraRef.current?.click()}
                        style={{ height: 56, fontSize: 18, marginBottom: 12 }}
                      >
                        拍照掃描
                      </Button>
                      <input
                        ref={cameraRef}
                        type="file" accept="image/*" capture="environment"
                        style={{ display: 'none' }}
                        onChange={(e) => { const f = e.target.files?.[0]; if (f) doScan(f); if (cameraRef.current) cameraRef.current.value = ''; }}
                      />
                      <Upload.Dragger
                        accept="image/jpeg,image/png,image/webp,image/heic"
                        maxCount={1} showUploadList={false}
                        beforeUpload={(file) => { doScan(file); return false; }}
                      >
                        <PictureOutlined style={{ fontSize: 32, color: '#8c8c8c' }} />
                        <p style={{ color: '#8c8c8c', margin: '8px 0 0' }}>或選擇已有照片</p>
                      </Upload.Dragger>
                    </>
                  )}

                  {scanning && (
                    <div style={{ textAlign: 'center', padding: '40px 0' }}>
                      <Spin size="large" />
                      <div style={{ marginTop: 12 }}><Text type="secondary">辨識中...</Text></div>
                    </div>
                  )}

                  {scanResult && (
                    <div>
                      {previewUrl && (
                        <div style={{ textAlign: 'center', marginBottom: 12 }}>
                          <Image src={previewUrl} alt="發票" width={200} style={{ borderRadius: 8 }} />
                        </div>
                      )}
                      <Descriptions size="small" column={1} bordered>
                        <Descriptions.Item label="辨識方式">
                          <Tag color={scanResult.method === 'qr' ? 'green' : 'orange'}>
                            {scanResult.method === 'qr' ? 'QR Code' : scanResult.method === 'ocr' ? 'OCR' : scanResult.method}
                          </Tag>
                          <Tag>{Math.round(scanResult.confidence * 100)}%</Tag>
                        </Descriptions.Item>
                        {scanResult.inv_num && <Descriptions.Item label="發票號碼">{scanResult.inv_num}</Descriptions.Item>}
                        {scanResult.amount != null && <Descriptions.Item label="金額">NT$ {scanResult.amount.toLocaleString()}</Descriptions.Item>}
                      </Descriptions>
                      {scanResult.items && scanResult.items.length > 0 && (
                        <>
                          <Divider style={{ margin: '8px 0' }}>品項 ({scanResult.items.length})</Divider>
                          {scanResult.items.map((item, i) => (
                            <div key={i} style={{ fontSize: 12, color: '#666' }}>
                              {item.name} ×{item.qty} = ${item.amount}
                            </div>
                          ))}
                        </>
                      )}
                      <Button block style={{ marginTop: 12 }} onClick={() => { setScanResult(null); setPreviewUrl(null); }}>
                        重新掃描
                      </Button>
                    </div>
                  )}
                </>
              )}

              {method === '手動填寫' && (
                <Alert type="info" showIcon message="直接在右側表單填寫發票資訊" />
              )}

              {method === '財政部發票' && (
                <>
                  {mofInvoices.length === 0 ? (
                    <Alert type="warning" showIcon message="尚無待核銷的財政部發票" description="請先至 ERP Hub → 電子發票 同步後再選取。" />
                  ) : (
                    <div style={{ maxHeight: 350, overflow: 'auto' }}>
                      {mofInvoices.map((inv) => (
                        <Card
                          key={inv.id} size="small" hoverable
                          style={{ marginBottom: 8, cursor: 'pointer' }}
                          onClick={() => {
                            form.setFieldsValue({
                              inv_num: inv.inv_num,
                              date: dayjs(inv.date),
                              amount: inv.amount,
                              seller_ban: inv.seller_ban,
                              source: 'mof_sync',
                            });
                            message.success(`已填入 ${inv.inv_num}`);
                          }}
                        >
                          <Space>
                            <Tag color="blue">{inv.inv_num}</Tag>
                            <Text type="secondary">{inv.date}</Text>
                            <Text strong>NT$ {Number(inv.amount).toLocaleString()}</Text>
                          </Space>
                        </Card>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Card>
          </Col>

          {/* 右欄：核銷表單 (三種方式共用) */}
          <Col xs={24} md={14}>
            <Card title="核銷資訊">
              <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ currency: 'TWD', source: 'manual', case_code: urlCaseCode || undefined }}>
                <Form.Item name="source" hidden><Input /></Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="inv_num" label="發票號碼" rules={[{ required: true, pattern: /^[A-Z]{2}\d{8}$/, message: '格式: AB12345678' }]}>
                      <Input placeholder="AB12345678" maxLength={10} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="date" label="開立日期" rules={[{ required: true }]}>
                      <DatePicker style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="amount" label="含稅總額" rules={[{ required: true }]}>
                      <InputNumber style={{ width: '100%' }} min={0} prefix="NT$"
                        formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                        parser={(v) => Number(v!.replace(/,/g, '')) as unknown as 0}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="tax_amount" label="稅額">
                      <InputNumber style={{ width: '100%' }} min={0} prefix="NT$" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="buyer_ban" label="買方統編">
                      <Input placeholder="8碼 (個人留空)" maxLength={8} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="seller_ban" label="賣方統編">
                      <Input placeholder="8碼" maxLength={8} />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider style={{ margin: '8px 0 16px' }}>核銷歸屬</Divider>

                <Form.Item label="歸屬類型">
                  <Segmented
                    block
                    value={attrType}
                    onChange={(v) => {
                      setAttrType(v as typeof attrType);
                      if (v === 'none') form.setFieldValue('case_code', undefined);
                    }}
                    options={[
                      { value: 'project', label: '專案/案件費用' },
                      { value: 'operational', label: '營運費用' },
                      { value: 'none', label: '未歸屬' },
                    ]}
                  />
                </Form.Item>

                {attrType === 'project' && (
                  <Form.Item name="case_code" label="關聯案件" extra="已成案顯示成案編號，未成案顯示案件代碼">
                    <Select
                      showSearch allowClear optionFilterProp="label"
                      placeholder="選擇案件"
                      options={caseOptions}
                      optionRender={(option) => (
                        <Space>
                          <span>{option.label}</span>
                          {!(option.data as { project_code?: string }).project_code && (
                            <Tag color="orange" style={{ fontSize: 11 }}>未成案</Tag>
                          )}
                        </Space>
                      )}
                    />
                  </Form.Item>
                )}

                {attrType === 'operational' && (
                  <Alert type="info" showIcon message="營運費用將自動歸入營運帳目，無需選擇案件" style={{ marginBottom: 16 }} />
                )}

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="category" label="費用分類" rules={[{ required: true, message: '請選擇分類' }]}>
                      <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} />
                    </Form.Item>
                  </Col>
                  <Col span={6}>
                    <Form.Item name="currency" label="幣別">
                      <Select options={CURRENCY_OPTIONS} />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item name="notes" label="備註">
                  <Input.TextArea rows={2} maxLength={500} />
                </Form.Item>

                <Space>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={createMutation.isPending} size="large">
                    建立核銷
                  </Button>
                  <Button onClick={() => navigate(ROUTES.ERP_EXPENSES)}>取消</Button>
                </Space>
              </Form>
            </Card>
          </Col>
        </Row>
      </div>
    </ResponsiveContent>
  );
};

export default ERPExpenseCreatePage;
