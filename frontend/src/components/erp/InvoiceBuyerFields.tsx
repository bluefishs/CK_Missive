/**
 * 發票買受人欄位（抬頭 ＋ 統編）——委託單位主檔下拉 ＋ 就地新增
 *
 * ⭐ 2026-09-08 owner：「發票抬頭（買受人）及買受人統編 是否對應 /clients 提供
 * 下拉選單選取，若無對應則可新增（原頁面填列不要轉跳頁面）」。
 *
 * 與協力廠商那一側同型（`ERPAccountRecordFormPage` 的 `vendor_name`）：
 * 自由輸入的後果是**同一個買受人會有多種寫法**（有無「股份」「有限公司」、全半形），
 * 而發票要對回委託單位主檔靠的就是名稱與統編 ⇒ 打不一樣就對不起來，
 * 而兩邊都不會報錯。
 *
 * ⚠️ **買受人不等於委託單位**：09-08 那五案的委託單位是「鎮泓有限公司」，
 * 而發票抬頭有「蔡蕙宇」（個人）與「樂昱建設有限公司」。
 * 所以這個下拉**不強制**只能從清單挑 —— 既有的自由值必須顯示得出來，
 * 並且明白標成「不在委託單位主檔」，讓那件事是**看得見的事實**而不是畫面異常。
 *
 * ⚠️ 做成共用元件而不是兩邊各寫一份：這一頁的欄位同時出現在
 * 報價單詳情的「開立發票」Modal 與獨立填報頁，
 * 兩份宣告分家正是本 repo 反覆出事的形狀（L145 家族）。
 */
import React, { useMemo, useState } from 'react';
import { Form, Input, Select, Divider, Space, Button, App } from 'antd';
import type { FormInstance } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';

import { useClientOptions } from '../../hooks/business/useDropdownData';
import { usePermissions } from '../../hooks/utility/usePermissions';
import { extractApiMessage } from '../../utils/apiMessage';

interface Props {
  /** 需要 form 實例：挑主檔時要一併帶入統編、就地新增後要回填抬頭 */
  form: FormInstance;
}

export const InvoiceBuyerFields: React.FC<Props> = ({ form }) => {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const { hasPermission } = usePermissions();
  const { clients, isLoading } = useClientOptions();
  const [newName, setNewName] = useState('');

  // 一般同仁按下去必然 403（`POST /api/vendors` 要 `vendors:create`）——
  // 不給必然失敗的按鈕（同 ContractCaseVendorFormPage）。
  const canCreate = hasPermission('vendors:create');

  const watched = Form.useWatch('buyer_name', form) as string | undefined;
  const options = useMemo(() => {
    const opts = clients.map((c) => ({
      label: c.tax_id ? `${c.vendor_name}（${c.tax_id}）` : c.vendor_name,
      value: c.vendor_name,
    }));
    if (watched && !clients.some((c) => c.vendor_name === watched)) {
      opts.unshift({ label: `${watched}（不在委託單位主檔）`, value: watched });
    }
    return opts;
  }, [clients, watched]);

  const handleAdd = async () => {
    const name = newName.trim();
    if (!name) return;
    try {
      const { vendorsApi } = await import('../../api/vendorsApi');
      // 統編一起帶進主檔：這裡是唯一同時知道「名稱」與「統編」的時點，
      // 分兩次做的話主檔會留下一堆沒有統編的委託單位。
      const taxId = String(form.getFieldValue('buyer_tax_id') || '').trim();
      await vendorsApi.createVendor({
        vendor_name: name,
        vendor_type: 'client',
        ...(taxId ? { tax_id: taxId } : {}),
      });
      await qc.invalidateQueries({ queryKey: ['clients-dropdown'] });
      form.setFieldValue('buyer_name', name);
      setNewName('');
      message.success('已新增委託單位');
    } catch (e) {
      message.error(extractApiMessage(e, '新增委託單位失敗'));
    }
  };

  return (
    <>
      <Form.Item
        name="buyer_name"
        label="發票抬頭（買受人）"
        extra="從委託單位主檔挑；買受人可能與委託單位不同（實例：委託單位鎮泓、抬頭樂昱建設），找不到可就地新增"
      >
        <Select
          showSearch
          allowClear
          placeholder="選擇或新增買受人"
          optionFilterProp="label"
          loading={isLoading}
          options={options}
          // 挑了主檔就把統編一起帶進來 —— 這一欄此前要人自己抄，
          // 抄錯了發票對不回主檔，而畫面上看不出來。
          onChange={(v?: string) => {
            const hit = clients.find((c) => c.vendor_name === v);
            if (hit?.tax_id) form.setFieldValue('buyer_tax_id', hit.tax_id);
          }}
          notFoundContent={isLoading ? '載入中…' : '沒有相符的委託單位'}
          dropdownRender={!canCreate ? undefined : (menu) => (
            <>
              {menu}
              <Divider style={{ margin: '8px 0' }} />
              <Space style={{ padding: '0 8px 4px' }}>
                <Input
                  placeholder="輸入新委託單位名稱"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.stopPropagation()}
                  size="small"
                />
                <Button type="link" icon={<PlusOutlined />} size="small" onClick={handleAdd}>
                  新增
                </Button>
              </Space>
            </>
          )}
        />
      </Form.Item>
      <Form.Item
        name="buyer_tax_id"
        label="買受人統編"
        rules={[{ pattern: /^[0-9]{8}$/, message: '統一編號為 8 碼數字' }]}
        extra="挑選主檔會自動帶入；三聯式必填，二聯式（機關／個人）可留空"
      >
        <Input maxLength={8} placeholder="12345678" />
      </Form.Item>
    </>
  );
};

export default InvoiceBuyerFields;
