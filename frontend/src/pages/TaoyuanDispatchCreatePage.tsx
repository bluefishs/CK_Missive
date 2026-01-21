/**
 * 桃園派工單新增頁面
 *
 * 導航式新增頁面，提供完整表單讓使用者建立新派工單
 * 欄位對應原始需求的 12 個欄位
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Form,
  Input,
  Select,
  Button,
  App,
  Card,
  Row,
  Col,
  Typography,
  Space,
  Divider,
} from 'antd';
import {
  SendOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  FileTextOutlined,
  LinkOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { dispatchOrdersApi, taoyuanProjectsApi } from '../api/taoyuanDispatchApi';
import { documentsApi } from '../api/documentsApi';
import { getProjectAgencyContacts, type ProjectAgencyContact } from '../api/projectAgencyContacts';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
import type { DispatchOrderCreate } from '../types/api';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';
import { TAOYUAN_WORK_TYPES } from '../types/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

export const TaoyuanDispatchCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 公文搜尋狀態
  const [agencyDocSearch, setAgencyDocSearch] = useState('');
  const [companyDocSearch, setCompanyDocSearch] = useState('');

  // 查詢可關聯的工程
  const { data: projectsData } = useQuery({
    queryKey: ['taoyuan-projects-for-dispatch', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () =>
      taoyuanProjectsApi.getList({
        contract_project_id: TAOYUAN_CONTRACT.PROJECT_ID,
        limit: 500,
      }),
  });
  const projects = projectsData?.items ?? [];

  // 查詢機關承辦清單（來自承攬案件 /contract-cases/21）
  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const agencyContacts = agencyContactsData?.items ?? [];

  // 查詢協力廠商清單（用於查估單位，來自承攬案件）
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const projectVendors = vendorsData?.associations ?? [];

  // 查詢機關函文（收文）- 限定桃園專案
  const { data: agencyDocsData } = useQuery({
    queryKey: ['agency-docs-for-dispatch-create', agencyDocSearch, TAOYUAN_CONTRACT.CODE],
    queryFn: () =>
      documentsApi.getDocuments({
        contract_case: TAOYUAN_CONTRACT.CODE,
        category: 'receive', // 機關發給乾坤 = 乾坤收文
        search: agencyDocSearch || undefined,
        limit: 50,
      }),
  });

  // 查詢乾坤函文（發文）- 限定桃園專案
  const { data: companyDocsData } = useQuery({
    queryKey: ['company-docs-for-dispatch-create', companyDocSearch, TAOYUAN_CONTRACT.CODE],
    queryFn: () =>
      documentsApi.getDocuments({
        contract_case: TAOYUAN_CONTRACT.CODE,
        category: 'send', // 乾坤發文
        search: companyDocSearch || undefined,
        limit: 50,
      }),
  });

  // 新增 mutation
  const createMutation = useMutation({
    mutationFn: (data: DispatchOrderCreate) => dispatchOrdersApi.create(data),
    onSuccess: (result) => {
      message.success('派工單新增成功');
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
      // 導航到新建立的派工單詳情頁
      navigate(`/taoyuan/dispatch/${result.id}`);
    },
    onError: (error: any) => {
      message.error(error?.message || '新增失敗');
    },
  });

  // 頁面載入時自動獲取下一個派工單號
  useEffect(() => {
    const loadNextDispatchNo = async () => {
      try {
        const result = await dispatchOrdersApi.getNextDispatchNo();
        if (result.success && result.next_dispatch_no) {
          form.setFieldsValue({
            dispatch_no: result.next_dispatch_no,
          });
        }
      } catch (error) {
        console.error('載入派工單號失敗:', error);
      }
    };
    loadNextDispatchNo();
  }, [form]);

  // 儲存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const data: DispatchOrderCreate = {
        dispatch_no: values.dispatch_no,
        contract_project_id: TAOYUAN_CONTRACT.PROJECT_ID,
        project_name: values.project_name,
        work_type: values.work_type,
        sub_case_name: values.sub_case_name,
        deadline: values.deadline,
        case_handler: values.case_handler,
        survey_unit: values.survey_unit,
        cloud_folder: values.cloud_folder,
        project_folder: values.project_folder,
        contact_note: values.contact_note,
        agency_doc_id: values.agency_doc_id || undefined,
        company_doc_id: values.company_doc_id || undefined,
        linked_project_ids: values.linked_project_ids || [],
      };
      createMutation.mutate(data);
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  // 返回列表
  const handleCancel = () => {
    navigate('/taoyuan/dispatch');
  };

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleCancel}>
              返回
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              <SendOutlined /> 新增派工單
            </Title>
          </Space>
          <Space>
            <Button onClick={handleCancel}>取消</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={createMutation.isPending}
              onClick={handleSave}
            >
              儲存
            </Button>
          </Space>
        </div>
      </Card>

      <Form form={form} layout="vertical">
        {/* 基本資訊 */}
        <Card
          title={
            <Space>
              <SendOutlined />
              <span>派工基本資訊</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="dispatch_no"
                label="派工單號"
                rules={[{ required: true, message: '請輸入派工單號' }]}
              >
                <Input placeholder="例: TY-2026-001" />
              </Form.Item>
            </Col>
            <Col span={16}>
              <Form.Item name="project_name" label="工程名稱/派工事項">
                <Input placeholder="派工事項說明" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="work_type" label="作業類別">
                <Select allowClear placeholder="選擇作業類別">
                  {TAOYUAN_WORK_TYPES.map((type) => (
                    <Option key={type} value={type}>
                      {type}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sub_case_name" label="分案名稱/派工備註">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="deadline" label="履約期限">
                <Input placeholder="例: 114/12/31" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 承辦資訊 */}
        <Card
          title={
            <Space>
              <UserOutlined />
              <span>承辦資訊</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="case_handler"
                label="案件承辦"
                tooltip="從機關承辦清單選擇（來源：承攬案件機關承辦）"
              >
                <Select
                  placeholder="選擇案件承辦"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                >
                  {agencyContacts.map((contact) => (
                    <Option
                      key={contact.id}
                      value={contact.contact_name}
                      label={contact.contact_name}
                    >
                      <div style={{ lineHeight: 1.3 }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {contact.contact_name}
                        </div>
                        {(contact.position || contact.department) && (
                          <div style={{ fontSize: 11, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {[contact.position, contact.department].filter(Boolean).join(' / ')}
                          </div>
                        )}
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="survey_unit"
                label="查估單位"
                tooltip="從協力廠商清單選擇（來源：承攬案件協力廠商）"
              >
                <Select
                  placeholder="選擇查估單位"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                >
                  {projectVendors.map((vendor: ProjectVendor) => (
                    <Option
                      key={vendor.vendor_id}
                      value={vendor.vendor_name}
                      label={vendor.vendor_name}
                    >
                      <div style={{ lineHeight: 1.3 }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {vendor.vendor_name}
                        </div>
                        {(vendor.role || vendor.vendor_business_type) && (
                          <div style={{ fontSize: 11, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {[vendor.role, vendor.vendor_business_type].filter(Boolean).join(' / ')}
                          </div>
                        )}
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="contact_note" label="聯絡備註">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 資料夾路徑 */}
        <Card
          title={
            <Space>
              <LinkOutlined />
              <span>資料夾路徑</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="cloud_folder" label="雲端資料夾">
                <Input placeholder="Google Drive 連結" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="project_folder" label="專案資料夾">
                <Input placeholder="本地路徑" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 公文關聯 */}
        <Card
          title={
            <Space>
              <FileTextOutlined />
              <span>公文關聯</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Row gutter={16}>
            <Col span={12}>
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
                  onSearch={setAgencyDocSearch}
                  notFoundContent={
                    agencyDocsData?.items?.length === 0 ? '無符合資料' : '輸入關鍵字搜尋'
                  }
                  options={(agencyDocsData?.items ?? []).map((doc) => ({
                    value: doc.id,
                    label: `${doc.doc_number || '(無字號)'} - ${doc.subject?.substring(0, 20) || '(無主旨)'}...`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
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
                  onSearch={setCompanyDocSearch}
                  notFoundContent={
                    companyDocsData?.items?.length === 0 ? '無符合資料' : '輸入關鍵字搜尋'
                  }
                  options={(companyDocsData?.items ?? []).map((doc) => ({
                    value: doc.id,
                    label: `${doc.doc_number || '(無字號)'} - ${doc.subject?.substring(0, 20) || '(無主旨)'}...`,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 工程關聯 */}
        <Card
          title={
            <Space>
              <LinkOutlined />
              <span>工程關聯</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Form.Item
            name="linked_project_ids"
            label="關聯工程"
            tooltip="可選擇多個相關工程進行關聯"
          >
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="搜尋並選擇要關聯的工程"
              filterOption={(input, option) =>
                String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={projects.map((p) => ({
                value: p.id,
                label: `${p.project_name}${p.district ? ` (${p.district})` : ''}`,
              }))}
            />
          </Form.Item>
        </Card>

        {/* 底部操作按鈕 */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button onClick={handleCancel}>取消</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={createMutation.isPending}
              onClick={handleSave}
            >
              儲存並查看
            </Button>
          </div>
        </Card>
      </Form>
    </div>
  );
};

export default TaoyuanDispatchCreatePage;
