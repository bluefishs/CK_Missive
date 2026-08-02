/**
 * ERP 請款填報頁（新增／編輯共用）
 *
 * 路由：/erp/quotations/:quotationId/billings/create
 *      /erp/quotations/:quotationId/billings/:billingId/edit
 *
 * 為什麼從 Modal 改成獨立頁（2026-08-02 pilot）：
 * 原本請款新增/編輯是 BillingsTab 內的 Modal（04-06 以 ACCEPTED EXCEPTION 保留，
 * 理由是欄位少＋緊耦合 context，在桌面確實成立）。改採公文既有的「填報＝獨立路由」模式，
 * 取得的是 Modal 給不了的東西：手機有完整縱向空間、網址可分享/可書籤、
 * 瀏覽器返回鍵行為正確、重新整理不會丟掉填到一半的內容。
 *
 * 刻意**不動**「開立發票」「確認收款」兩個 3 欄位快速動作 —— 它們仍是 Tab 內的 Modal。
 * 欄位少、緊接在某一列的動作之後，導頁反而讓人失去所在位置。
 *
 * RWD：沿用 ERP 模組既有的 ResponsiveContent（容器級 padding/maxWidth）
 *      ＋公文頁的 isMobile 細節控制（DocumentCreatePage 有 18 處可參照）。
 */

import React, { useEffect, useMemo } from 'react';
import {
  Card, Form, Input, InputNumber, DatePicker, Select, Button, Space, App, Typography, Spin,
} from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

import { useResponsive } from '../hooks';
import { ROUTES } from '../router/types';
import {
  useERPBillings,
  useCreateERPBilling,
  useUpdateERPBilling,
} from '../hooks/business/useERPQuotations';
import { ERP_BILLING_STATUS_LABELS } from '../types/erp';
import type { ERPBillingCreate, ERPBillingUpdate, ERPBillingStatus } from '../types/erp';

const { Title, Text } = Typography;

const ERPBillingFormPage: React.FC = () => {
  const { quotationId, billingId } = useParams<{ quotationId: string; billingId?: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const { isMobile } = useResponsive();

  const qid = Number(quotationId);
  const bid = billingId ? Number(billingId) : null;
  const isEdit = bid !== null;

  // 編輯時從既有列表查詢取單筆，不另開端點（列表已在快取中，多數情況零額外請求）
  const { data: billings, isLoading } = useERPBillings(qid);
  const record = useMemo(
    () => (isEdit && Array.isArray(billings) ? billings.find((b) => b.id === bid) : undefined),
    [billings, bid, isEdit],
  );

  const createMutation = useCreateERPBilling();
  const updateMutation = useUpdateERPBilling(qid);

  useEffect(() => {
    if (record) {
      form.setFieldsValue({
        ...record,
        billing_date: record.billing_date ? dayjs(record.billing_date) : null,
        billing_amount: record.billing_amount != null ? Number(record.billing_amount) : null,
      });
    }
  }, [record, form]);

  const backToQuotation = () => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(qid)));

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        billing_date: values.billing_date?.format('YYYY-MM-DD'),
        billing_amount: String(values.billing_amount),
      };

      if (isEdit && bid) {
        await updateMutation.mutateAsync({ id: bid, data: payload as ERPBillingUpdate });
        message.success('請款紀錄已更新');
      } else {
        await createMutation.mutateAsync({ ...payload, erp_quotation_id: qid } as ERPBillingCreate);
        message.success('請款紀錄已新增');
      }
      backToQuotation();
    } catch (err) {
      // validateFields 失敗會走到這裡（欄位已自行標紅），不另外彈訊息；
      // API 失敗由全域 GlobalApiErrorNotifier 呈現，此處不吞掉真錯誤。
      if (err && typeof err === 'object' && !('errorFields' in err)) {
        message.error(isEdit ? '更新失敗' : '新增失敗');
      }
    }
  };

  const submitting = createMutation.isPending || updateMutation.isPending;

  if (isEdit && isLoading) {
    return (
      <ResponsiveContent maxWidth="md">
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      </ResponsiveContent>
    );
  }

  if (isEdit && !isLoading && !record) {
    return (
      <ResponsiveContent maxWidth="md">
        <Card>
          <Text type="secondary">找不到這筆請款紀錄（可能已被刪除）。</Text>
          <div style={{ marginTop: 16 }}>
            <Button icon={<ArrowLeftOutlined />} onClick={backToQuotation}>返回報價單</Button>
          </div>
        </Card>
      </ResponsiveContent>
    );
  }

  return (
    <ResponsiveContent maxWidth="md">
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: isMobile ? 8 : 16,
        marginBottom: isMobile ? 16 : 24,
      }}>
        <Button
          icon={<ArrowLeftOutlined />}
          size={isMobile ? 'small' : 'middle'}
          onClick={backToQuotation}
        >
          {isMobile ? '返回' : '返回報價單'}
        </Button>
        <Title level={isMobile ? 5 : 4} style={{ margin: 0 }}>
          {isEdit ? '編輯請款' : '新增請款'}
        </Title>
      </div>

      <Card size={isMobile ? 'small' : 'default'} styles={{ body: { padding: isMobile ? 12 : 24 } }}>
        <Form
          form={form}
          layout="vertical"
          size={isMobile ? 'middle' : 'large'}
          preserve={false}
          initialValues={{ payment_status: 'pending' }}
        >
          <Form.Item name="billing_period" label="請款期別">
            <Input placeholder="例：第 1 期" />
          </Form.Item>

          <Form.Item
            name="billing_date"
            label="請款日期"
            rules={[{ required: true, message: '請選擇請款日期' }]}
          >
            <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
          </Form.Item>

          <Form.Item
            name="billing_amount"
            label="請款金額"
            rules={[{ required: true, message: '請輸入請款金額' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              // 手機叫出數字鍵盤，省去在小螢幕上切換輸入法
              inputMode="numeric"
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number((value ?? '').replace(/,/g, '')) as 0}
            />
          </Form.Item>

          <Form.Item name="payment_status" label="收款狀態">
            <Select
              options={(Object.entries(ERP_BILLING_STATUS_LABELS) as [ERPBillingStatus, string][])
                .map(([value, label]) => ({ value, label }))}
            />
          </Form.Item>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={isMobile ? 3 : 2} />
          </Form.Item>

          <Space
            direction={isMobile ? 'vertical' : 'horizontal'}
            style={{ width: isMobile ? '100%' : undefined }}
          >
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={submitting}
              onClick={handleSubmit}
              block={isMobile}
            >
              {isEdit ? '儲存變更' : '新增請款'}
            </Button>
            <Button onClick={backToQuotation} block={isMobile} disabled={submitting}>
              取消
            </Button>
          </Space>
        </Form>
      </Card>
    </ResponsiveContent>
  );
};

export default ERPBillingFormPage;
