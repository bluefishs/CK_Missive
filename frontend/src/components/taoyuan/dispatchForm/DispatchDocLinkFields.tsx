import React from 'react';
import {
  Form,
  Input,
  Select,
  Divider,
  Space,
} from 'antd';
import { ResponsiveFormRow } from '../../common/ResponsiveFormRow';
import { FileTextOutlined } from '@ant-design/icons';

import type { OfficialDocument } from '../../../types/api';

interface DispatchDocLinkFieldsProps {
  mode: 'create' | 'edit' | 'quick';
  document?: OfficialDocument | null;
  isReceiveDoc?: boolean;
  agencyDocOptions: Array<{ value: number; label: string }>;
  companyDocOptions: Array<{ value: number; label: string }>;
  onAgencyDocSearch?: (keyword: string) => void;
  onCompanyDocSearch?: (keyword: string) => void;
}

export const DispatchDocLinkFields: React.FC<DispatchDocLinkFieldsProps> = ({
  mode,
  document,
  isReceiveDoc,
  agencyDocOptions,
  companyDocOptions,
  onAgencyDocSearch,
  onCompanyDocSearch,
}) => {
  return (
    <>
      <Divider style={{ margin: '16px 0' }} />
      <div style={{ marginBottom: 16 }}>
        <Space>
          <FileTextOutlined />
          <span style={{ fontWeight: 500 }}>公文關聯</span>
        </Space>
      </div>

      {mode === 'quick' && document ? (
        <ResponsiveFormRow>
          <Form.Item
            label="機關函文號"
            tooltip={isReceiveDoc ? '自動帶入當前公文文號' : '如需關聯機關函文，請至派工紀錄編輯'}
          >
            <Input
              value={isReceiveDoc ? document.doc_number : undefined}
              disabled
              style={{ backgroundColor: '#f5f5f5' }}
              placeholder={isReceiveDoc ? '' : '(非機關來函)'}
            />
          </Form.Item>
          <Form.Item
            label="乾坤函文號"
            tooltip={!isReceiveDoc ? '自動帶入當前公文文號' : '如需關聯乾坤函文，請至派工紀錄編輯'}
          >
            <Input
              value={!isReceiveDoc ? document.doc_number : undefined}
              disabled
              style={{ backgroundColor: '#f5f5f5' }}
              placeholder={!isReceiveDoc ? '' : '(非乾坤發文)'}
            />
          </Form.Item>
        </ResponsiveFormRow>
      ) : (
        <ResponsiveFormRow>
          <Form.Item
            name="agency_doc_id"
            label="機關函文（收文）"
            tooltip="選擇對應的機關來文"
          >
            <Select
              allowClear
              showSearch
              placeholder="搜尋並選擇機關函文"
              filterOption={false}
              onSearch={onAgencyDocSearch}
              popupMatchSelectWidth={false}
              style={{ width: '100%' }}
              notFoundContent={
                agencyDocOptions.length === 0 ? '無符合資料' : '輸入關鍵字搜尋'
              }
              options={agencyDocOptions}
            />
          </Form.Item>
          <Form.Item
            name="company_doc_id"
            label="乾坤函文（發文）"
            tooltip="選擇對應的乾坤發文"
          >
            <Select
              allowClear
              showSearch
              placeholder="搜尋並選擇乾坤函文"
              filterOption={false}
              onSearch={onCompanyDocSearch}
              popupMatchSelectWidth={false}
              style={{ width: '100%' }}
              notFoundContent={
                companyDocOptions.length === 0 ? '無符合資料' : '輸入關鍵字搜尋'
              }
              options={companyDocOptions}
            />
          </Form.Item>
        </ResponsiveFormRow>
      )}
    </>
  );
};
