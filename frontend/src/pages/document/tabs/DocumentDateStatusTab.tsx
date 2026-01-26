/**
 * 日期狀態 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Form,
  Select,
  DatePicker,
  Row,
  Col,
  Tag,
} from 'antd';
import type { DocumentDateStatusTabProps } from './types';
import { PRIORITY_OPTIONS, STATUS_OPTIONS } from './constants';

const { Option } = Select;

export const DocumentDateStatusTab: React.FC<DocumentDateStatusTabProps> = ({
  form,
  isEditing,
}) => {
  return (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="發文日期" name="doc_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇發文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="收文日期" name="receive_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇收文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="發送日期" name="send_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇發送日期" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="優先等級" name="priority">
            <Select placeholder="請選擇優先等級">
              {PRIORITY_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>
                  <Tag color={opt.color}>{opt.label}</Tag>
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="處理狀態" name="status">
            <Select placeholder="請選擇處理狀態">
              {STATUS_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );
};

export default DocumentDateStatusTab;
