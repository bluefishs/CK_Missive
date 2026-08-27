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

import React, { useEffect, useMemo, useState } from 'react';
import { Form, Input, InputNumber, DatePicker, Select, App, Button, Popconfirm, Divider, Space } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { apiClient } from '../api/client';
import { ERP_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
// 期別詞彙表 —— 唯一定義處在後端 `schemas/erp/billing.py: BillingPeriod`
import { BILLING_PERIOD_OPTIONS } from '../types/erp';
import type { ERPBilling, ERPVendorPayable } from '../types/erp';
import { useResponsive } from '../hooks';
import { useSubcontractorOptions } from '../hooks/business/useDropdownData';
import { extractApiMessage } from '../utils/apiMessage';
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

  // 2026-08-18：`record` 由 `Record<string, unknown>` 改為兩個方向的聯集型別。
  //
  // 原本每個欄位靠 `record.xxx` 取值而不受檢查 —— 於是我在後端補了
  // `payable_period` 卻漏了前端型別，tsc 完全沒有機會發現。
  // 同一次比對還揪出前端 `ERPVendorPayable` 少了 7 個後端一直有回傳的欄位。
  //
  // 用 `Partial<A & B>`：這一頁本來就同時處理兩種紀錄，而編輯時
  // 只有其中一組欄位有值。**繞過型別的地方，型別就守不住那個欄位。**
  const record = useMemo((): Partial<ERPBilling & ERPVendorPayable> | undefined => {
    if (!isEdit) return undefined;
    const rows = (rawData?.data ?? (rawData as unknown as Record<string, unknown>[]) ?? []) as Record<string, unknown>[];
    return rows.find((r) => Number(r.id) === rid) as
      | Partial<ERPBilling & ERPVendorPayable>
      | undefined;
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
        payable_period: record.payable_period,
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


  // 協力廠商下拉（2026-08-18）—— 值用 vendor_name 以維持後端欄位不變。
  const { subcontractors, isLoading: subLoading, isError: subFailed } = useSubcontractorOptions();
  const [newVendorName, setNewVendorName] = useState('');
  const qc = useQueryClient();
  const handleAddVendor = async () => {
    const name = newVendorName.trim();
    if (!name) return;
    try {
      const { vendorsApi } = await import('../api/vendorsApi');
      await vendorsApi.createVendor({ vendor_name: name, vendor_type: 'subcontractor' });
      // 讓下拉立刻看得到新廠商 —— 不重整清單的話使用者會以為沒新增成功
      await qc.invalidateQueries({ queryKey: ['subcontractors-dropdown'] });
      form.setFieldValue('vendor_name', name);
      setNewVendorName('');
      message.success('已新增協力廠商');
    } catch (e) {
      message.error(extractApiMessage(e, '新增廠商失敗'));
    }
  };

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
          billing_period: values.billing_period,
          billing_date: values.billing_date?.format('YYYY-MM-DD'),
          billing_amount: values.billing_amount,
          payment_status: values.payment_status || 'pending',
          payment_date: values.payment_date?.format('YYYY-MM-DD'),
          payment_amount: values.payment_amount,
          notes: values.notes,
        }
      : {
          payable_period: values.payable_period,
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
    // ⚠️ 2026-08-18：`erp_quotation_id` **只在建立時送**。
    //
    // 原本它寫在 payload 本體裡，Create 與 Update 共用 —— 而 Update schema
    // 沒有這一欄，08-17 開 `extra='forbid'` 之後，編輯任何一筆應收/應付都 422。
    //
    // 語意上也不該送：帳款不能改掛到另一張報價（那不是「編輯」是「搬移」，
    // 真要做得刪掉重建）。
    //
    // 第一版修法是在 mutate 前解構掉它。行為正確，但 payload 字面值裡
    // 仍然看得到那一欄 —— **讀程式碼的人（與檢核）都會以為更新時會送**。
    // 改為本體不含、建立時才補：讓寫法本身說出規則。
    //
    // 我 08-17 開 forbid 前有掃前端 payload，但那支腳本用「欄位交集最大」
    // 找對應 schema —— 這個 payload 交集最大的是 **Create**，
    // 於是 Update 缺的欄位沒有被看見。**掃描找錯了比對對象，就等於沒掃。**
    // 現由 `write_payload_schema_audit` 以端點常數為錨比對，不再用猜的。
    mutation.mutate(isEdit ? payload : { erp_quotation_id: qid, ...payload });
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
        {/* 期別 —— **兩個方向共用**（2026-08-18 owner：「應收與應付兩者設計不一致」）。
            原本只有應收有，而應付的資料模型連欄位都沒有；同一個表單切換方向時
            欄位就少一個，而沒有任何理由。已補 `erp_vendor_payables.payable_period`。

            2026-08-17：由自由輸入 `<Input placeholder="如 第1期" />` 改為下拉。
            51 筆曾漂成三種寫法表達同一件事（第一期 47／第一期款項 3／
            資訊系統第一期款 1），任何以期別分組的統計都會算成三種，
            而沒有任何一方會報錯。
            詞彙表唯一定義處在後端 `schemas/erp/billing.py: BillingPeriod`，
            應收與應付共用同一份 —— 分期就是分期。 */}
        <Form.Item name={isReceivable ? 'billing_period' : 'payable_period'} label="期別">
          <Select
            allowClear
            placeholder="請選擇期別（不分期選「一次請領」）"
            options={BILLING_PERIOD_OPTIONS.map((v) => ({ label: v, value: v }))}
          />
        </Form.Item>

        {isReceivable ? (
          <>
            <Form.Item name="billing_date" label="請款日期" rules={[{ required: true, message: '請選擇請款日期' }]}>
              <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
            </Form.Item>
            <Form.Item name="billing_amount" label="請款金額" rules={[{ required: true, message: '請輸入請款金額' }]}>
              <InputNumber style={{ width: '100%' }} min={0} inputMode="numeric" formatter={amountFormatter} />
            </Form.Item>
          </>
        ) : (
          <>
            {/* 2026-08-18 owner：「其協力廠商應對應資料庫提供下拉選單，非自行填列」。

                原本是自由輸入 —— 後果是同一家廠商會有多種寫法（有無「股份」
                「有限公司」、全半形），而後端 `_resolve_vendor_id` 是**靠名稱**
                去配對 `partner_vendors` 的：名字打不一樣就配不到，
                應付與廠商主檔從此對不起來，而**兩邊都不會報錯**。

                沿用專案既有規約：Select 找不到選項時由 `dropdownRender` 提供
                即時新增（同 `ContractCaseVendorFormPage`），
                不逼使用者離開這一頁去建廠商。

                送出的仍是 `vendor_name`（後端欄位沒變），只是值改為從清單挑。 */}
            <Form.Item name="vendor_name" label="協力廠商" rules={[{ required: true, message: '請選擇協力廠商' }]}>
              <Select
                showSearch
                allowClear
                placeholder="選擇或新增協力廠商"
                optionFilterProp="label"
                loading={subLoading}
                options={subcontractors.map((v) => ({
                  label: v.vendor_name,
                  value: v.vendor_name,
                }))}
                // 2026-08-27：這個下拉自 08-18 上線起就一直是空的 ——
                // `useSubcontractorOptions` 送 limit=200 而後端上限是 100 ⇒ 422 ⇒
                // useQuery 失敗 ⇒ `?? []`。422 在本專案屬「業務錯誤、元件自理」，
                // 不會被 GlobalApiErrorNotifier 接走，所以**沒有任何一層出聲**。
                // limit 已修，但真正要治的是**空清單長什麼樣**：
                // 「沒有選項」與「公司沒有協力廠商」在畫面上必須分得出來。
                notFoundContent={
                  subFailed ? '廠商清單載入失敗，請重新整理'
                    : subLoading ? '載入中…'
                    : '沒有可選的協力廠商'
                }
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <Divider style={{ margin: '8px 0' }} />
                    <Space style={{ padding: '0 8px 4px' }}>
                      <Input
                        placeholder="輸入新廠商名稱"
                        value={newVendorName}
                        onChange={(e) => setNewVendorName(e.target.value)}
                        onKeyDown={(e) => e.stopPropagation()}
                        size="small"
                      />
                      <Button type="link" icon={<PlusOutlined />} size="small" onClick={handleAddVendor}>
                        新增
                      </Button>
                    </Space>
                  </>
                )}
              />
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
