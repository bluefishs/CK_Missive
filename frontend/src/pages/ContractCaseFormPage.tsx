import React from 'react';
import {
  Card,
  Checkbox,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Spin,
  Divider,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  PlusOutlined,
} from '@ant-design/icons';

import {
  CATEGORY_OPTIONS,
  CASE_NATURE_OPTIONS,
  STATUS_OPTIONS,
} from './contractCase/tabs/constants';

import { AddAgencyModal } from './contractCase/AddAgencyModal';
import { useContractCaseForm, CLIENT_TYPE_OPTIONS } from './contractCase/useContractCaseForm';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

export const ContractCaseFormPage: React.FC = () => {
  const {
    form,
    isEdit,
    title,
    isMobile,
    loading,
    optionsLoading,
    submitting,
    agencyOptions,
    vendorOptions,
    addAgencyModalVisible,
    setAddAgencyModalVisible,
    addAgencySubmitting,
    handleSubmit,
    handleBack,
    generateYearOptions,
    handleAddAgencySubmit,
  } = useContractCaseForm();

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? 24 : 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: isMobile ? '12px' : undefined }}>
      <Card style={{ marginBottom: isMobile ? 12 : 16 }} size={isMobile ? 'small' : 'medium'}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: isMobile ? 8 : 16 }}>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={handleBack} size={isMobile ? 'small' : 'middle'}>
            {isMobile ? '返回' : '返回列表'}
          </Button>
          <Title level={isMobile ? 4 : 3} style={{ margin: 0 }}>{title}</Title>
        </div>
      </Card>

      <Card size={isMobile ? 'small' : 'medium'} styles={{ body: { padding: isMobile ? 12 : 24 } }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          size={isMobile ? 'middle' : 'large'}
          initialValues={{ year: new Date().getFullYear(), status: '待執行', client_type: 'agency' }}
        >
          <Spin spinning={optionsLoading} description="載入選項中...">
          <Row gutter={[isMobile ? 8 : 16, 0]}>
            <Col span={24}>
              <Form.Item label="案件名稱" name="project_name" rules={[{ required: true, message: '請輸入案件名稱' }]}>
                <Input placeholder="請輸入案件名稱" />
              </Form.Item>
            </Col>

            <Col xs={24} sm={8}>
              <Form.Item label="年度" name="year" rules={[{ required: true, message: '請選擇年度' }]}>
                <Select placeholder="請選擇年度">
                  {generateYearOptions().map(year => (
                    <Option key={year} value={parseInt(year)}>{year}年</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="案件類別" name="category">
                <Select placeholder="請選擇案件類別" allowClear>
                  {CATEGORY_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="案件性質" name="case_nature">
                <Select placeholder="請選擇案件性質" allowClear>
                  {CASE_NATURE_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={4}>
              <Form.Item label="委託來源" name="client_type">
                <Select options={CLIENT_TYPE_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item noStyle shouldUpdate={(prev, cur) => prev.client_type !== cur.client_type}>
                {({ getFieldValue }) => {
                  const clientType = getFieldValue('client_type') || 'agency';
                  if (clientType === 'agency') {
                    return (
                      <Form.Item label="委託單位" name="client_agency" tooltip="從機關單位清單中選擇，或點擊下方新增">
                        <Select
                          placeholder="請選擇委託機關" allowClear showSearch optionFilterProp="label"
                          options={agencyOptions.map(agency => ({
                            value: agency.agency_name,
                            label: agency.agency_short_name
                              ? `${agency.agency_name} (${agency.agency_short_name})`
                              : agency.agency_name,
                          }))}
                          popupRender={(menu) => (
                            <>
                              {menu}
                              <Divider style={{ margin: '8px 0' }} />
                              <Button
                                type="text" icon={<PlusOutlined />}
                                onClick={() => setAddAgencyModalVisible(true)}
                                style={{ width: '100%', textAlign: 'left', color: '#1890ff' }}
                              >
                                新增機關單位
                              </Button>
                            </>
                          )}
                        />
                      </Form.Item>
                    );
                  }
                  if (clientType === 'vendor') {
                    return (
                      <Form.Item label="委託單位" name="client_agency" tooltip="從廠商清單中選擇">
                        <Select
                          placeholder="請選擇委託廠商" allowClear showSearch optionFilterProp="label"
                          options={vendorOptions.map(v => ({
                            value: v.vendor_name,
                            label: v.vendor_code ? `${v.vendor_name} (${v.vendor_code})` : v.vendor_name,
                          }))}
                        />
                      </Form.Item>
                    );
                  }
                  return (
                    <Form.Item label="委託單位" name="client_agency">
                      <Input placeholder="請輸入委託單位名稱" />
                    </Form.Item>
                  );
                }}
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="執行狀態" name="status" rules={[{ required: true, message: '請選擇執行狀態' }]}>
                <Select placeholder="請選擇執行狀態">
                  {STATUS_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={16}>
              <Form.Item label="契約期程" name="contract_period">
                <RangePicker style={{ width: '100%' }} placeholder={['開始日期', '結束日期']} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="完成進度 (%)" name="progress" tooltip="0-100，可留空">
                <InputNumber style={{ width: '100%' }} min={0} max={100} placeholder="0-100" />
              </Form.Item>
            </Col>

            <Col xs={24} sm={12}>
              <Form.Item label="契約金額" name="contract_amount">
                <InputNumber<number>
                  style={{ width: '100%' }}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, ''))}
                  placeholder="請輸入契約金額" min={0} prefix="NT$"
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="得標金額" name="winning_amount">
                <InputNumber<number>
                  style={{ width: '100%' }}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, ''))}
                  placeholder="請輸入得標金額" min={0} prefix="NT$"
                />
              </Form.Item>
            </Col>

            <Col xs={24} sm={12}>
              <Form.Item label="契約文號" name="contract_doc_number">
                <Input placeholder="請輸入契約文號" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="專案路徑" name="project_path">
                <Input placeholder="請輸入專案資料夾路徑 (可選)" />
              </Form.Item>
            </Col>

            <Col span={24}>
              <Form.Item label="專案說明" name="description">
                <TextArea rows={isMobile ? 3 : 4} placeholder="請輸入專案說明" />
              </Form.Item>
            </Col>

            <Col span={24}>
              <Form.Item name="has_dispatch_management" valuePropName="checked">
                <Checkbox>啟用派工管理功能（勾選後此案件可使用派工安排、工程關聯等功能）</Checkbox>
              </Form.Item>
            </Col>

            <Col span={24}>
              <Form.Item label="備註" name="notes">
                <TextArea rows={isMobile ? 2 : 3} placeholder="請輸入備註" />
              </Form.Item>
            </Col>

            <Col span={24}>
              <Form.Item style={{ marginBottom: 0 }}>
                {isMobile ? (
                  <Space vertical style={{ width: '100%' }}>
                    <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={submitting} block>
                      {isEdit ? '更新' : '新增'}
                    </Button>
                    <Button onClick={handleBack} block>取消</Button>
                  </Space>
                ) : (
                  <Space>
                    <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={submitting}>
                      {isEdit ? '更新' : '新增'}
                    </Button>
                    <Button onClick={handleBack}>取消</Button>
                  </Space>
                )}
              </Form.Item>
            </Col>
          </Row>
          </Spin>
        </Form>
      </Card>

      <AddAgencyModal
        open={addAgencyModalVisible}
        onCancel={() => setAddAgencyModalVisible(false)}
        onSubmit={handleAddAgencySubmit}
        submitting={addAgencySubmitting}
        agencyOptions={agencyOptions}
        isMobile={isMobile}
      />
    </div>
  );
};

export default ContractCaseFormPage;
