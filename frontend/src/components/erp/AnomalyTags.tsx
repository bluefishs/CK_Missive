/**
 * 金流異常標籤 ＋ 判讀（解除待辦）
 *
 * ⭐ 2026-09-08 owner：「5 筆的『已收 17,850』已付清、發票多開 ——
 * 是否異常案件標註機制並增列篩選查詢，以利解除或處理異常費用之案件機制」。
 *
 * ⚠️ 這裡**不判斷什麼算異常** —— 判準的唯一定義在後端
 * `app/services/erp/finance_anomaly.py`。前端抄一份就是第二份宣告，
 * 而那正是本 repo 反覆出事的形狀（L145 家族）。
 *
 * ⚠️ 「判讀」解除的是**待辦**不是事實：判讀後標籤仍在（轉灰、標「已判讀」），
 * 因為數字還是那樣。若判讀會讓標籤消失，這個機制就變成
 * 「一鍵讓問題從畫面上消失」—— 比沒有這個機制更糟。
 */
import React, { useState } from 'react';
import { Tag, Tooltip, Space, Modal, Input, App, Typography } from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '../../api/client';
import { extractApiMessage } from '../../utils/apiMessage';
import type { FinanceAnomaly } from '../../types/erp';

const { Text } = Typography;

interface Props {
  quotationId: number;
  anomalies?: FinanceAnomaly[];
  /** 唯讀（例如列表只想顯示不想給操作） */
  readOnly?: boolean;
}

export const AnomalyTags: React.FC<Props> = ({ quotationId, anomalies, readOnly }) => {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [target, setTarget] = useState<FinanceAnomaly | null>(null);
  const [reason, setReason] = useState('');

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['erp-quotations'] });
    qc.invalidateQueries({ queryKey: ['erp-anomalies'] });
  };

  const ack = useMutation({
    mutationFn: (v: { code: string; reason: string }) =>
      apiClient.post('/erp/anomalies/ack', {
        quotation_id: quotationId, anomaly_type: v.code, reason: v.reason,
      }),
    onSuccess: () => { message.success('已記錄判讀'); setTarget(null); setReason(''); invalidate(); },
    onError: (e) => message.error(extractApiMessage(e, '記錄判讀失敗')),
  });

  const unack = useMutation({
    mutationFn: (code: string) =>
      apiClient.post('/erp/anomalies/unack', { quotation_id: quotationId, anomaly_type: code }),
    onSuccess: () => { message.success('已退回待處理'); invalidate(); },
    onError: (e) => message.error(extractApiMessage(e, '退回失敗')),
  });

  if (!anomalies?.length) return <Text type="secondary">—</Text>;

  return (
    <>
      <Space size={[4, 4]} wrap onClick={(e) => e.stopPropagation()}>
        {anomalies.map((a) => (
          <Tooltip
            key={a.code}
            title={
              <div>
                <div>{a.explain}</div>
                <div style={{ marginTop: 4 }}>{a.detail}</div>
                {a.acknowledged && a.ack && (
                  <div style={{ marginTop: 4 }}>
                    已判讀：{a.ack.reason}
                    {a.ack.acked_by ? `（${a.ack.acked_by}）` : ''}
                  </div>
                )}
                {!readOnly && <div style={{ marginTop: 4 }}>點擊{a.acknowledged ? '退回待處理' : '記錄判讀'}</div>}
              </div>
            }
          >
            <Tag
              color={a.acknowledged ? 'default' : a.severity === 'red' ? 'red' : 'gold'}
              style={{ margin: 0, cursor: readOnly ? 'default' : 'pointer' }}
              onClick={readOnly ? undefined : () => {
                if (a.acknowledged) unack.mutate(a.code);
                else { setTarget(a); setReason(''); }
              }}
            >
              {a.acknowledged ? `${a.label}（已判讀）` : a.label}
            </Tag>
          </Tooltip>
        ))}
      </Space>

      <Modal
        title={`判讀：${target?.label ?? ''}`}
        open={!!target}
        onCancel={() => setTarget(null)}
        okText="記錄判讀"
        confirmLoading={ack.isPending}
        okButtonProps={{ disabled: reason.trim().length < 2 }}
        onOk={() => target && ack.mutate({ code: target.code, reason: reason.trim() })}
      >
        <p style={{ marginTop: 0 }}>{target?.detail}</p>
        <p><Text type="secondary">{target?.explain}</Text></p>
        {/* 原因必填：沒有原因的判讀等於把問題藏起來，下一個人看到「已判讀」
            卻不知道當初判了什麼，只能再判一次。 */}
        <Input.TextArea
          rows={3}
          maxLength={500}
          showCount
          placeholder="判讀原因（必填）——例：已付清，發票多開 840 元屬追加項目，客戶同意不另補請款"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <p style={{ marginBottom: 0, marginTop: 8 }}>
          <Text type="secondary">
            判讀不會更動任何金額 —— 數字仍然是現在這樣，只是這一筆從「待處理」移到「已判讀」。
          </Text>
        </p>
      </Modal>
    </>
  );
};

export default AnomalyTags;
