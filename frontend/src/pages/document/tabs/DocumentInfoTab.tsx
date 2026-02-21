/**
 * 公文資訊 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Form,
  Input,
  Select,
  Divider,
  Descriptions,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
import dayjs from 'dayjs';
import type { DocumentInfoTabProps } from './types';
import { DOC_TYPE_OPTIONS, DELIVERY_METHOD_OPTIONS } from './constants';

const { TextArea } = Input;
const { Option } = Select;

export const DocumentInfoTab: React.FC<DocumentInfoTabProps> = ({
  form,
  document,
  isEditing,
}) => {
  return (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      <ResponsiveFormRow>
        {/* 根據文件類別顯示不同欄位：發文用發文形式，收文用文件類型 */}
        {document?.category === '發文' ? (
          <Form.Item
            label="發文形式"
            name="delivery_method"
            rules={[{ required: true, message: '請選擇發文形式' }]}
          >
            <Select placeholder="請選擇發文形式">
              {DELIVERY_METHOD_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <Form.Item
            label="文件類型"
            name="doc_type"
            rules={[{ required: true, message: '請選擇文件類型' }]}
          >
            <Select placeholder="請選擇文件類型">
              {DOC_TYPE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        )}
        <Form.Item
          label="公文字號"
          name="doc_number"
          rules={[{ required: true, message: '請輸入公文字號' }]}
        >
          <Input placeholder="如：乾坤字第1130001號" />
        </Form.Item>
      </ResponsiveFormRow>

      <ResponsiveFormRow>
        <Form.Item
          label="發文機關"
          name="sender"
          rules={[{ required: true, message: '請輸入發文機關' }]}
        >
          <Input placeholder="請輸入發文機關" />
        </Form.Item>
        <Form.Item label="受文者" name="receiver">
          <Input placeholder="請輸入受文者" />
        </Form.Item>
      </ResponsiveFormRow>

      <Form.Item
        label="主旨"
        name="subject"
        rules={[{ required: true, message: '請輸入主旨' }]}
      >
        <TextArea rows={2} placeholder="請輸入公文主旨" maxLength={200} showCount />
      </Form.Item>

      <Form.Item label="說明" name="content">
        <TextArea rows={4} placeholder="請輸入公文內容說明" maxLength={1000} showCount />
      </Form.Item>

      <Form.Item label="備註" name="notes">
        <TextArea rows={3} placeholder="請輸入備註" maxLength={500} showCount />
      </Form.Item>

      <Form.Item label="簡要說明(乾坤備註)" name="ck_note">
        <TextArea rows={3} placeholder="請輸入乾坤內部簡要說明或備註" maxLength={1000} showCount />
      </Form.Item>

      {/* 唯讀模式下顯示系統資訊 */}
      {!isEditing && document && (
        <>
          <Divider />
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="建立時間">
              {document.created_at ? dayjs(document.created_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="更新時間">
              {document.updated_at ? dayjs(document.updated_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="建立者">
              {document.creator || '系統'}
            </Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Form>
  );
};

export default DocumentInfoTab;
