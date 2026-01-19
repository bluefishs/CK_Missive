/**
 * 重複檔案處理 Modal
 *
 * 當上傳的檔案與現有附件重名時，顯示確認對話框，
 * 讓使用者選擇覆蓋、保留兩個或取消上傳。
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import React from 'react';
import { Modal, Button, Alert } from 'antd';
import { FileOutlined } from '@ant-design/icons';
import type { DuplicateFileModalProps } from './types';

export const DuplicateFileModal: React.FC<DuplicateFileModalProps> = ({
  visible,
  file,
  existingAttachment,
  onOverwrite,
  onKeepBoth,
  onCancel,
}) => {
  return (
    <Modal
      title={
        <span style={{ color: '#faad14' }}>
          <FileOutlined style={{ marginRight: 8 }} />
          發現重複檔案
        </span>
      }
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消上傳
        </Button>,
        <Button key="keep" onClick={onKeepBoth}>
          保留兩個
        </Button>,
        <Button key="overwrite" type="primary" danger onClick={onOverwrite}>
          覆蓋舊檔
        </Button>,
      ]}
      width={500}
    >
      <div style={{ padding: '16px 0' }}>
        <Alert
          message="已存在相同檔名的附件"
          description={
            <div>
              <p>
                <strong>新檔案：</strong>
                {file?.name}
              </p>
              <p>
                <strong>現有檔案：</strong>
                {existingAttachment?.original_filename || existingAttachment?.filename}
              </p>
              <p style={{ marginTop: 12, color: '#666' }}>請選擇處理方式：</p>
              <ul style={{ marginTop: 8, paddingLeft: 20, color: '#666' }}>
                <li>
                  <strong>覆蓋舊檔</strong>：刪除現有檔案，上傳新檔案
                </li>
                <li>
                  <strong>保留兩個</strong>：新檔案將以不同名稱儲存
                </li>
                <li>
                  <strong>取消上傳</strong>：不上傳此檔案
                </li>
              </ul>
            </div>
          }
          type="warning"
          showIcon
        />
      </div>
    </Modal>
  );
};

export default DuplicateFileModal;
