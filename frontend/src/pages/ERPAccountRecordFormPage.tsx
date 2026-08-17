/**
 * ERP 應收／應付填報頁（新增／編輯共用，雙向）
 *
 * 路由：/erp/quotations/:quotationId/accounts/:direction/create
 *      /erp/quotations/:quotationId/accounts/:direction/:recordId/edit
 *      direction ∈ receivable | payable
 *
 * 取代 `AccountRecordTab` 內的 Modal 填報（owner：ERP 填報參考公文設計、減少彈跳視窗）。
 * 獨立頁換到的是 Modal 給不了的：手機完整縱向空間、網址可分享、返回鍵正確、
 * 重新整理不丟填到一半的內容。
 *
 * ⚠️ 為什麼是這一頁而不是先前的 ERPBillingFormPage：
 * 2026-08-02 查證發現 `BillingsTab` / `InvoicesTab` / `VendorPayablesTab` 三個元件
 * **沒有任何頁面在使用**（只在 index.ts re-export），實際渲染的是雙向的 `AccountRecordTab`。
 * 先前針對 BillingsTab 做的 pilot 因此不會出現在畫面上 —— 已改為對真正在用的元件施作。
 *
 * 端點與 payload 刻意與 AccountRecordTab 原本的 Modal 完全一致（同樣走 apiClient
 * 直呼 ERP_ENDPOINTS），避免「換了入口也換了行為」。
 */

import React, { useEffect, useMemo } from 'react';
import { Form, Input, InputNumber, DatePicker, Select, App, Button, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { apiClient } from '../api/client';
import { ERP_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
// 期別詞彙表 —— 唯一定義處在後端 `schemas/erp/billing.py: BillingPeriod`
import { BILLING_PERIOD_OPTIONS } from '../types/erp';
import { useResponsive } from '../hooks';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';

const amountFormatter = (v: unknown) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

const ERPAccountRecordFormPage: React.FC = () => {
  const { quotationId, direction, recordId } =
    useParams<{ quotationId: string; direction: string; recordId?: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const { isMobile } = useResponsive();
  const queryClient = useQueryClient();

  const qid = Number(quotationId);
  const rid = recordId ? Number(recordId) : null;
  const isEdit = rid !== null;
  const isReceivable = direction !== 'payable';

  const dirLabel = isReceivable ? '應收' : '應付';
  const paymentLabel = isReceivable ? '收款' : '付款';
  const listEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_LIST : ERP_ENDPOINTS.VENDOR_PAYABLES_LIST;
  const createEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_CREATE : ERP_ENDPOINTS.VENDOR_PAYABLES_CREATE;
  const deleteEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_DELETE : ERP_ENDPOINTS.VENDOR_PAYABLES_DELETE;
  const updateEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_UPDATE : ERP_ENDPOINTS.VENDOR_PAYABLES_UPDATE;
  const queryKey = useMemo(
    () => (isReceivable ? ['erp-billings', qid] : ['erp-vendor-payables', qid]),
    [isReceivable, qid],
  );

  // 編輯時自列表取單筆（與 Tab 相同的資料來源，多數情況命中既有快取）
  const { data: rawData, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      apiClient.post<{ data: Record<string, unknown>[] }>(listEndpoint, { erp_quotation_id: qid }),
    enabled: isEdit,
  });

  const record = useMemo(() => {
    if (!isEdit) return undefined;
    const rows = (rawData?.data ?? (rawData as unknown as Record<string, unknown>[]) ?? []) as Record<string, unknown>[];
    return rows.find((r) => Number(r.id) === rid);
  }, [rawData, rid, isEdit]);

  useEffect(() => {
    if (!record) return;
    if (isReceivable) {
      form.setFieldsValue({
        billing_period: record.billing_period,
        billing_date: record.billing_date ? dayjs(record.billing_date as string) : null,
        billing_amount: record.billing_amount != null ? Number(record.billing_amount) : null,
        payment_status: record.payment_status ?? 'pending',
        payment_date: record.payment_date ? dayjs(record.payment_date as string) : null,
        payment_amount: record.payment_amount != null ? Number(record.payment_amount) : null,
        notes: record.notes,
      });
    } else {
      form.setFieldsValue({
        vendor_name: record.vendor_name,
        payable_amount: record.payable_amount != null ? Number(record.payable_amount) : null,
        // 2026-08-17：補上 description —— 原本表單沒有這一欄，
        // 於是編輯既有紀錄時它的說明**不會被載入**，儲存後就被清空了
        // （比「看不到」更糟：看不到只是不知道，載不到會靜靜刪掉既有資料）。
        description: record.description,
        invoice_number: record.invoice_number,
        due_date: record.due_date ? dayjs(record.due_date as string) : null,
        payment_status: record.payment_status ?? 'unpaid',
        paid_date: record.paid_date ? dayjs(record.paid_date as string) : null,
        paid_amount: record.paid_amount != null ? Number(record.paid_amount) : null,
        notes: record.notes,
      });
    }
  }, [record, isReceivable, form]);

  const backToQuotation = () => {
    navigate(`${ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(qid))}?tab=${isReceivable ? 'receivable' : 'payable'}`);
  };

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ['erp-quotations'] });
    queryClient.invalidateQueries({ queryKey: ['erp-quotations', 'detail'] });
  };

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      isEdit
        ? apiClient.post(updateEndpoint, { id: rid, data: payload })
        : apiClient.post(createEndpoint, payload),
    onSuccess: () => {
      message.success(isEdit ? '更新成功' : '新增成功');
      invalidate();
      backToQuotation();
    },
    onError: () => message.error(isEdit ? '更新失敗' : '新增失敗'),
  });

  // 端點與原本表格操作欄用的是同一支（deleteEndpoint），避免「換了入口也換了行為」。
  const deleteMutation = useMutation({
    mutationFn: () => apiClient.post(deleteEndpoint, { id: rid }),
    onSuccess: () => { message.success('已刪除'); invalidate(); backToQuotation(); },
    onError: () => message.error('刪除失敗'),
  });

  const handleSubmit = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return; // 欄位已自行標紅
    }
    const payload = isReceivable
      ? {
          erp_quotation_id: qid,
          billing_period: values.billing_period,
          billing_date: values.billing_date?.format('YYYY-MM-DD'),
          billing_amount: values.billing_amount,
          payment_status: values.payment_status || 'pending',
          payment_date: values.payment_date?.format('YYYY-MM-DD'),
          payment_amount: values.payment_amount,
          notes: values.notes,
        }
      : {
          erp_quotation_id: qid,
          vendor_name: values.vendor_name,
          payable_amount: values.payable_amount,
          description: values.description,
          invoice_number: values.invoice_number,
          due_date: values.due_date?.format('YYYY-MM-DD'),
          payment_status: values.payment_status || 'unpaid',
          paid_date: values.paid_date?.format('YYYY-MM-DD'),
          paid_amount: values.paid_amount,
          notes: values.notes,
        };
    mutation.mutate(payload);
  };

  return (
    <ErpFormPageShell
      title={`${isEdit ? '編輯' : '新增'}${dirLabel}`}
      backText="返回報價單"
      onBack={backToQuotation}
      onSubmit={handleSubmit}
      submitting={mutation.isPending}
      isEdit={isEdit}
      submitText={isEdit ? '儲存變更' : `新增${dirLabel}`}
      loading={isEdit && isLoading}
      notFoundMessage={isEdit && !isLoading && !record ? `找不到這筆${dirLabel}紀錄（可能已被刪除）。` : undefined}
      /* 刪除原本在報價頁的表格操作欄。該欄依「詳情頁 tab 只呈現不操作」移除後，
         刪除若不搬到這裡就沒有任何入口了。 */
      headerExtra={isEdit ? (
        <Popconfirm
          title={`確定刪除這筆${dirLabel}紀錄？`}
          okText="刪除" cancelText="取消"
          onConfirm={() => deleteMutation.mutate()}
        >
          <Button danger icon={<DeleteOutlined />} loading={deleteMutation.isPending}>刪除</Button>
        </Popconfirm>
      ) : undefined}
    >
      <Form
        form={form}
        layout="vertical"
        size={isMobile ? 'middle' : 'large'}
        preserve={false}
        initialValues={{ payment_status: isReceivable ? 'pending' : 'unpaid' }}
      >
        {isReceivable ? (
          <>
            {/* 2026-08-17 owner：「建議期別採下拉選單，避免不同專案不一致，如 第一期款」。
                原本是 `<Input placeholder="如 第1期" />` —— 51 筆已漂成三種寫法表達
                同一件事（第一期 47／第一期款項 3／資訊系統第一期款 1），任何以期別
                分組的統計都會算成三種，而沒有任何一方會報錯。
                詞彙表唯一定義處在後端 `schemas/erp/billing.py: BillingPeriod`。 */}
            <Form.Item name="billing_period" label="期別">
              <Select
                allowClear
                placeholder="請選擇期別（不分期選「一次請領」）"
                options={BILLING_PERIOD_OPTIONS.map((v) => ({ label: v, value: v }))}
              />
            </Form.Item>
            <Form.Item name="billing_date" label="請款日期" rules={[{ required: true, message: '請選擇請款日期' }]}>
              <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
            </Form.Item>
            <Form.Item name="billing_amount" label="請款金額" rules={[{ required: true, message: '請輸入請款金額' }]}>
              <InputNumber style={{ width: '100%' }} min={0} inputMode="numeric" formatter={amountFormatter} />
            </Form.Item>
          </>
        ) : (
          <>
            <Form.Item name="vendor_name" label="協力廠商" rules={[{ required: true, message: '請輸入廠商名稱' }]}>
              <Input placeholder="廠商名稱" />
            </Form.Item>
            <Form.Item name="payable_amount" label="應付金額" rules={[{ required: true, message: '請輸入應付金額' }]}>
              <InputNumber style={{ width: '100%' }} min={0} inputMode="numeric" formatter={amountFormatter} />
            </Form.Item>
            {/* 2026-08-17 owner 回報「編輯無期別可修改，有藏欄位或標準化問題」——
                期別在應付端**資料模型就沒有**（見下方說明），但這一查揪出真正的
                藏欄位就是這個 `description`：

                  · DB 有這一欄，37 筆裡 32 筆有值（都是匯入來的，格式「案名 外包費用」）
                  · 表單從來沒有這一欄 ⇒ **凡是從表單建的必然空白**
                  · 實測那 5 筆空白全是 2026-07 之後建立的，匯入的 32 筆都有值

                症狀是「應付列表看不出這筆是做什麼的」，而不會有任何錯誤 ——
                欄位在、資料型別對、只是沒有入口。同「發票關聯整條鏈都建好只缺一顆按鈕」
                （CROSS_LAYER_CONTRACT_INTEGRITY.md 家族三）。 */}
            <Form.Item
              name="description"
              label="說明"
              extra="這筆應付是做什麼的（如「XX 案 外包費用」）—— 列表只看得到廠商與金額，沒有說明就分不出同廠商的多筆"
            >
              <Input placeholder="選填，建議填寫" />
            </Form.Item>
            <Form.Item name="invoice_number" label="廠商發票號碼">
              <Input placeholder="選填" />
            </Form.Item>
            <Form.Item name="due_date" label="應付日期">
              <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
            </Form.Item>
          </>
        )}

        {/* 2026-08-17 owner：「請款金額為何需要填列兩次？」
            兩欄語意本來不同（開出去的 vs 實際收到的，`partial` 部分收款就是為此），
            **但實測 36 筆有填收款金額的全部與請款金額相同、0 筆不同** ——
            也就是這個區分在實務裡從來沒用到，只剩「同一個數字打兩次」。

            改為狀態切到「已收款／已付款」時**自動帶入**，仍可手改
            （真的部分收款時填不同值），而不是移除欄位 —— 移除會讓
            部分收款無法表達，那是把一個罕見情境變成不可能。 */}
        <Form.Item name="payment_status" label={`${paymentLabel}狀態`}>
          <Select
            onChange={(v) => {
              const amtField = isReceivable ? 'payment_amount' : 'paid_amount';
              const srcField = isReceivable ? 'billing_amount' : 'payable_amount';
              if (v === 'paid' && !form.getFieldValue(amtField)) {
                form.setFieldValue(amtField, form.getFieldValue(srcField));
              }
            }}
            options={
              isReceivable
                ? [
                    { value: 'pending', label: '待收款' },
                    { value: 'partial', label: '部分收款' },
                    { value: 'paid', label: '已收款' },
                    { value: 'overdue', label: '逾期' },
                  ]
                : [
                    { value: 'unpaid', label: '未付款' },
                    { value: 'partial', label: '部分付款' },
                    { value: 'paid', label: '已付款' },
                  ]
            }
          />
        </Form.Item>

        <Form.Item name={isReceivable ? 'payment_date' : 'paid_date'} label={`${paymentLabel}日期`}>
          <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
        </Form.Item>

        <Form.Item
          name={isReceivable ? 'payment_amount' : 'paid_amount'}
          label={`${paymentLabel}金額`}
          extra={
            <span>
              狀態改為「{isReceivable ? '已收款' : '已付款'}」時會自動帶入
              {isReceivable ? '請款' : '應付'}金額；金額不同時（部分{paymentLabel}）再手改。
            </span>
          }
        >
          <InputNumber style={{ width: '100%' }} min={0} inputMode="numeric" formatter={amountFormatter} />
        </Form.Item>

        <Form.Item name="notes" label="備註">
          <Input.TextArea rows={isMobile ? 3 : 2} />
        </Form.Item>
      </Form>
    </ErpFormPageShell>
  );
};

export default ERPAccountRecordFormPage;
