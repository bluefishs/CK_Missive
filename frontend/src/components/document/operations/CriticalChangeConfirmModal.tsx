/**
 * 關鍵欄位變更確認 Modal
 *
 * 當使用者修改公文的關鍵欄位（主旨、公文字號、發文/受文單位）時，
 * 顯示確認對話框，提醒使用者這些變更會被記錄。
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import React from 'react';
import { Modal, Button, Alert, List, Tag } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import type { CriticalChangeConfirmModalProps } from './types';

export const CriticalChangeConfirmModal: React.FC<CriticalChangeConfirmModalProps> = ({
  visible,
  changes,
  loading,
  onConfirm,
  onCancel,
}) => {
  return (
    <Modal
      title={
        <span style={{ color: '#ff4d4f' }}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          確認修改關鍵欄位
        </span>
      }
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="confirm"
          type="primary"
          danger
          onClick={onConfirm}
          loading={loading}
        >
          確認修改
        </Button>,
      ]}
      width={550}
    >
      <div style={{ padding: '16px 0' }}>
        <Alert
          message="您即將修改以下關鍵欄位"
          description={
            <div>
              <p style={{ marginBottom: 12, color: '#666' }}>
                這些變更將被記錄在審計日誌中。請確認以下修改內容：
              </p>
              <List
                size="small"
                dataSource={changes}
                renderItem={(change) => (
                  <List.Item style={{ padding: '8px 0' }}>
                    <div style={{ width: '100%' }}>
                      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
                        {change.icon} {change.label}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Tag
                          color="red"
                          style={{
                            maxWidth: '45%',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {change.oldValue.length > 30
                            ? change.oldValue.slice(0, 30) + '...'
                            : change.oldValue}
                        </Tag>
                        <span>→</span>
                        <Tag
                          color="green"
                          style={{
                            maxWidth: '45%',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {change.newValue.length > 30
                            ? change.newValue.slice(0, 30) + '...'
                            : change.newValue}
                        </Tag>
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </div>
          }
          type="warning"
          showIcon
        />
      </div>
    </Modal>
  );
};

export default CriticalChangeConfirmModal;
