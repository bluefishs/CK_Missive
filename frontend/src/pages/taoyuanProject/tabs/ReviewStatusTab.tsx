/**
 * 審議狀態 Tab
 */

import React from 'react';
import {
  Form,
  Input,
  Select,
  Row,
  Col,
  Tag,
  Divider,
  Badge,
  DatePicker,
  Card,
  Descriptions,
} from 'antd';
import type { FormInstance } from 'antd';

import type { TaoyuanProject } from '../../../types/api';
import { PROGRESS_STATUS_OPTIONS } from '../../../constants/taoyuanOptions';

const { Option } = Select;

interface ReviewStatusTabProps {
  form: FormInstance;
  isEditing: boolean;
  project: TaoyuanProject | undefined;
}

export const ReviewStatusTab: React.FC<ReviewStatusTabProps> = ({
  form,
  isEditing,
  project,
}) => (
  <Form form={form} layout="vertical" disabled={!isEditing}>
    <Row gutter={16}>
      <Col span={8}>
        <Form.Item name="review_result" label="審議結果">
          <Input />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name="completion_date" label="完工日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
    </Row>

    <Form.Item name="remark" label="備註">
      <Input.TextArea rows={3} />
    </Form.Item>

    <Divider>進度追蹤</Divider>

    <Row gutter={16}>
      <Col span={6}>
        <Form.Item name="land_agreement_status" label="土地協議進度">
          <Select allowClear>
            {PROGRESS_STATUS_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                <Badge status={opt.color as any} text={opt.label} />
              </Option>
            ))}
          </Select>
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="land_expropriation_status" label="土地徵收進度">
          <Select allowClear>
            {PROGRESS_STATUS_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                <Badge status={opt.color as any} text={opt.label} />
              </Option>
            ))}
          </Select>
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="building_survey_status" label="地上物查估進度">
          <Select allowClear>
            {PROGRESS_STATUS_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                <Badge status={opt.color as any} text={opt.label} />
              </Option>
            ))}
          </Select>
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="acceptance_status" label="驗收狀態">
          <Select allowClear>
            <Option value="未驗收">
              <Badge status="default" text="未驗收" />
            </Option>
            <Option value="已驗收">
              <Badge status="success" text="已驗收" />
            </Option>
          </Select>
        </Form.Item>
      </Col>
    </Row>

    {!isEditing && project && (
      <>
        <Divider />
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="土地協議">
                  {project.land_agreement_status ? (
                    <Tag color="blue">{project.land_agreement_status}</Tag>
                  ) : (
                    <Tag>未設定</Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="土地徵收">
                  {project.land_expropriation_status ? (
                    <Tag color="orange">{project.land_expropriation_status}</Tag>
                  ) : (
                    <Tag>未設定</Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="地上物查估">
                  {project.building_survey_status ? (
                    <Tag color="green">{project.building_survey_status}</Tag>
                  ) : (
                    <Tag>未設定</Tag>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="驗收狀態">
                  {project.acceptance_status === '已驗收' ? (
                    <Badge status="success" text="已驗收" />
                  ) : (
                    <Badge status="default" text="未驗收" />
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        </Row>
      </>
    )}
  </Form>
);
