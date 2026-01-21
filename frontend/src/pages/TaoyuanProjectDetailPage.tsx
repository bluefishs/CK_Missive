/**
 * 桃園轄管工程詳情頁面
 *
 * 使用通用 DetailPageLayout 元件，採用 Tab 架構對應 Excel「1.轄管工程清單」：
 * - 基本資訊：項次、審議年度、案件類型、行政區、工程名稱、分案名稱、承辦人、查估單位、提案人
 * - 工程範圍：工程起點、工程迄點、道路長度、現況路寬、計畫路寬、都市計畫
 * - 土地建物：公有土地、私有土地、RC數量、鐵皮屋數量
 * - 經費估算：工程費、用地費、補償費、總經費
 * - 審議狀態：審議結果、完工日期、備註、進度追蹤
 * - 派工關聯：關聯的派工紀錄
 *
 * @version 2.0.0
 * @date 2026-01-21
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Form,
  Input,
  Select,
  Button,
  App,
  Space,
  Row,
  Col,
  Tag,
  Spin,
  Empty,
  Descriptions,
  Divider,
  Popconfirm,
  List,
  Card,
  InputNumber,
  Badge,
  DatePicker,
  Statistic,
  Typography,
} from 'antd';
import {
  ProjectOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DeleteOutlined,
  SendOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  EnvironmentOutlined,
  HomeOutlined,
  DollarOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import {
  DetailPageLayout,
  createTabItem,
} from '../components/common/DetailPage';
import { taoyuanProjectsApi, projectLinksApi, dispatchOrdersApi } from '../api/taoyuanDispatchApi';
import { getProjectAgencyContacts, type ProjectAgencyContact } from '../api/projectAgencyContacts';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
import type { TaoyuanProject, TaoyuanProjectUpdate, DispatchOrder } from '../types/api';
import { useAuthGuard } from '../hooks';
import {
  CASE_TYPE_OPTIONS,
  DISTRICT_OPTIONS,
  PROGRESS_STATUS_OPTIONS,
  TAOYUAN_CONTRACT,
} from '../constants/taoyuanOptions';

const { Option } = Select;
const { Text } = Typography;

export const TaoyuanProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 權限控制
  const { hasPermission } = useAuthGuard();
  const canEdit = hasPermission('documents:edit');
  const canDelete = hasPermission('documents:delete');

  // 狀態
  const [activeTab, setActiveTab] = useState('basic');
  const [isEditing, setIsEditing] = useState(false);

  // 派工關聯狀態
  const [selectedDispatchId, setSelectedDispatchId] = useState<number>();

  // 查詢工程詳情
  const {
    data: project,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['taoyuan-project-detail', id],
    queryFn: () => taoyuanProjectsApi.getDetail(parseInt(id || '0', 10)),
    enabled: !!id,
  });

  // 查詢關聯派工
  const { data: linkedDispatchesData, refetch: refetchDispatchLinks } = useQuery({
    queryKey: ['project-dispatch-links', id],
    queryFn: () => projectLinksApi.getDispatchLinks(parseInt(id || '0', 10)),
    enabled: !!id,
  });
  const linkedDispatches = linkedDispatchesData?.dispatch_orders || [];

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

  // 查詢可用派工紀錄（用於關聯選擇）
  const { data: availableDispatchesData } = useQuery({
    queryKey: ['dispatch-orders-for-project', project?.contract_project_id],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: project?.contract_project_id,
        limit: 100,
      }),
    enabled: !!project?.contract_project_id && isEditing,
  });
  const availableDispatches = availableDispatchesData?.items || [];

  // 已關聯的派工 ID
  const linkedDispatchIds = linkedDispatches.map((d) => d.dispatch_order_id);
  // 過濾已關聯的
  const filteredDispatches = availableDispatches.filter(
    (d: DispatchOrder) => !linkedDispatchIds.includes(d.id)
  );

  // 更新 mutation
  const updateMutation = useMutation({
    mutationFn: (data: TaoyuanProjectUpdate) =>
      taoyuanProjectsApi.update(parseInt(id || '0', 10), data),
    onSuccess: () => {
      message.success('工程更新成功');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['taoyuan-projects'] });
      setIsEditing(false);
    },
    onError: () => message.error('更新失敗'),
  });

  // 刪除 mutation
  const deleteMutation = useMutation({
    mutationFn: () => taoyuanProjectsApi.delete(parseInt(id || '0', 10)),
    onSuccess: () => {
      message.success('工程刪除成功');
      queryClient.invalidateQueries({ queryKey: ['taoyuan-projects'] });
      navigate('/taoyuan/dispatch');
    },
    onError: () => message.error('刪除失敗'),
  });

  // 關聯派工 mutation
  const linkDispatchMutation = useMutation({
    mutationFn: (dispatchOrderId: number) =>
      projectLinksApi.linkDispatch(parseInt(id || '0', 10), dispatchOrderId),
    onSuccess: () => {
      message.success('派工關聯成功');
      setSelectedDispatchId(undefined);
      refetchDispatchLinks();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
    },
    onError: () => message.error('關聯失敗'),
  });

  // 移除派工關聯 mutation
  const unlinkDispatchMutation = useMutation({
    mutationFn: (linkId: number) => {
      // 防禦性檢查
      if (linkId === undefined || linkId === null) {
        console.error('[unlinkDispatchMutation] linkId 無效:', linkId);
        return Promise.reject(new Error('關聯 ID 無效'));
      }
      const projectId = parseInt(id || '0', 10);
      if (!projectId || projectId === 0) {
        console.error('[unlinkDispatchMutation] projectId 無效:', id);
        return Promise.reject(new Error('工程 ID 無效'));
      }
      console.debug('[unlinkDispatchMutation] 準備移除:', { projectId, linkId });
      return projectLinksApi.unlinkDispatch(projectId, linkId);
    },
    onSuccess: () => {
      message.success('已移除派工關聯');
      refetchDispatchLinks();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
    },
    onError: (error: Error) => message.error(error.message || '移除關聯失敗'),
  });

  // 設定表單初始值
  useEffect(() => {
    if (project) {
      form.setFieldsValue({
        // 基本資訊
        project_name: project.project_name,
        review_year: project.review_year,
        case_type: project.case_type,
        district: project.district,
        sub_case_name: project.sub_case_name,
        case_handler: project.case_handler,
        survey_unit: project.survey_unit,
        proposer: project.proposer,
        // 工程範圍
        start_point: project.start_point,
        start_coordinate: project.start_coordinate,
        end_point: project.end_point,
        end_coordinate: project.end_coordinate,
        road_length: project.road_length,
        current_width: project.current_width,
        planned_width: project.planned_width,
        urban_plan: project.urban_plan,
        // 土地建物
        public_land_count: project.public_land_count,
        private_land_count: project.private_land_count,
        rc_count: project.rc_count,
        iron_sheet_count: project.iron_sheet_count,
        // 經費估算
        construction_cost: project.construction_cost,
        land_cost: project.land_cost,
        compensation_cost: project.compensation_cost,
        total_cost: project.total_cost,
        // 審議狀態
        review_result: project.review_result,
        completion_date: project.completion_date ? dayjs(project.completion_date) : null,
        remark: project.remark,
        // 進度追蹤
        land_agreement_status: project.land_agreement_status,
        land_expropriation_status: project.land_expropriation_status,
        building_survey_status: project.building_survey_status,
        acceptance_status: project.acceptance_status,
      });
    }
  }, [project, form]);

  // 儲存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      // 轉換日期格式
      const data: TaoyuanProjectUpdate = {
        ...values,
        completion_date: values.completion_date?.format('YYYY-MM-DD') || null,
      };
      updateMutation.mutate(data);
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  // 取消編輯
  const handleCancelEdit = () => {
    setIsEditing(false);
    if (project) {
      form.setFieldsValue({
        project_name: project.project_name,
        review_year: project.review_year,
        case_type: project.case_type,
        district: project.district,
        sub_case_name: project.sub_case_name,
        case_handler: project.case_handler,
        survey_unit: project.survey_unit,
        proposer: project.proposer,
        start_point: project.start_point,
        start_coordinate: project.start_coordinate,
        end_point: project.end_point,
        end_coordinate: project.end_coordinate,
        road_length: project.road_length,
        current_width: project.current_width,
        planned_width: project.planned_width,
        urban_plan: project.urban_plan,
        public_land_count: project.public_land_count,
        private_land_count: project.private_land_count,
        rc_count: project.rc_count,
        iron_sheet_count: project.iron_sheet_count,
        construction_cost: project.construction_cost,
        land_cost: project.land_cost,
        compensation_cost: project.compensation_cost,
        total_cost: project.total_cost,
        review_result: project.review_result,
        completion_date: project.completion_date ? dayjs(project.completion_date) : null,
        remark: project.remark,
        land_agreement_status: project.land_agreement_status,
        land_expropriation_status: project.land_expropriation_status,
        building_survey_status: project.building_survey_status,
        acceptance_status: project.acceptance_status,
      });
    }
  };

  // 關聯派工
  const handleLinkDispatch = useCallback(() => {
    if (!selectedDispatchId) {
      message.warning('請先選擇要關聯的派工紀錄');
      return;
    }
    linkDispatchMutation.mutate(selectedDispatchId);
  }, [selectedDispatchId, linkDispatchMutation, message]);

  // Tab 1: 基本資訊
  const renderBasicTab = () => (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      {/* 工程名稱 */}
      <Form.Item
        name="project_name"
        label="工程名稱"
        rules={[{ required: true, message: '請輸入工程名稱' }]}
      >
        <Input placeholder="請輸入工程名稱" />
      </Form.Item>

      {/* 審議年度 + 案件類型 + 行政區 */}
      <Row gutter={16}>
        <Col span={6}>
          <Form.Item name="review_year" label="審議年度">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="case_type" label="案件類型">
            <Select placeholder="選擇案件類型" allowClear>
              {CASE_TYPE_OPTIONS.map((opt) => (
                <Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="district" label="行政區">
            <Select placeholder="選擇行政區" allowClear showSearch>
              {DISTRICT_OPTIONS.map((opt) => (
                <Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="sub_case_name" label="分案名稱">
            <Input />
          </Form.Item>
        </Col>
      </Row>

      {/* 承辦人 + 查估單位 + 提案人 */}
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
          <Form.Item name="proposer" label="提案人">
            <Input />
          </Form.Item>
        </Col>
      </Row>

      {/* 唯讀模式下顯示系統資訊 */}
      {!isEditing && project && (
        <>
          <Divider />
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="項次">
              {project.sequence_no || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="建立時間">
              {project.created_at ? dayjs(project.created_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="更新時間">
              {project.updated_at ? dayjs(project.updated_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Form>
  );

  // Tab 2: 工程範圍
  const renderScopeTab = () => (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="start_point" label="工程起點">
            <Input placeholder="例: 永安路與中山路口" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="start_coordinate" label="起點坐標(經緯度)">
            <Input placeholder="例: 24.9876,121.1234" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="end_point" label="工程迄點">
            <Input placeholder="例: 永安路與民生路口" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="end_coordinate" label="迄點坐標(經緯度)">
            <Input placeholder="例: 24.9888,121.1256" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="road_length" label="道路長度(公尺)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="current_width" label="現況路寬(公尺)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="planned_width" label="計畫路寬(公尺)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="urban_plan" label="都市計畫">
            <Input />
          </Form.Item>
        </Col>
      </Row>

      {/* 唯讀模式顯示摘要卡片 */}
      {!isEditing && project && (
        <>
          <Divider />
          <Row gutter={16}>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="道路長度"
                  value={project.road_length || 0}
                  suffix="公尺"
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="現況路寬"
                  value={project.current_width || 0}
                  suffix="公尺"
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="計畫路寬"
                  value={project.planned_width || 0}
                  suffix="公尺"
                />
              </Card>
            </Col>
          </Row>
        </>
      )}
    </Form>
  );

  // Tab 3: 土地建物
  const renderLandTab = () => (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      <Row gutter={16}>
        <Col span={6}>
          <Form.Item name="public_land_count" label="公有土地(筆)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="private_land_count" label="私有土地(筆)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="rc_count" label="RC數量(棟)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="iron_sheet_count" label="鐵皮屋數量(棟)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Col>
      </Row>

      {/* 唯讀模式顯示摘要卡片 */}
      {!isEditing && project && (
        <>
          <Divider />
          <Row gutter={16}>
            <Col span={6}>
              <Card size="small">
                <Statistic title="公有土地" value={project.public_land_count || 0} suffix="筆" />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="私有土地" value={project.private_land_count || 0} suffix="筆" />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="RC數量" value={project.rc_count || 0} suffix="棟" />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="鐵皮屋" value={project.iron_sheet_count || 0} suffix="棟" />
              </Card>
            </Col>
          </Row>
        </>
      )}
    </Form>
  );

  // Tab 4: 經費估算
  const renderCostTab = () => (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      <Row gutter={16}>
        <Col span={6}>
          <Form.Item name="construction_cost" label="工程費(元)">
            <InputNumber style={{ width: '100%' }} min={0} formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="land_cost" label="用地費(元)">
            <InputNumber style={{ width: '100%' }} min={0} formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="compensation_cost" label="補償費(元)">
            <InputNumber style={{ width: '100%' }} min={0} formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item name="total_cost" label="總經費(元)">
            <InputNumber style={{ width: '100%' }} min={0} formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
        </Col>
      </Row>

      {/* 唯讀模式顯示摘要卡片 */}
      {!isEditing && project && (
        <>
          <Divider />
          <Row gutter={16}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="工程費"
                  value={project.construction_cost || 0}
                  prefix="$"
                  precision={0}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="用地費"
                  value={project.land_cost || 0}
                  prefix="$"
                  precision={0}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="補償費"
                  value={project.compensation_cost || 0}
                  prefix="$"
                  precision={0}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="總經費"
                  value={project.total_cost || 0}
                  prefix="$"
                  precision={0}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}
    </Form>
  );

  // Tab 5: 審議狀態
  const renderStatusTab = () => (
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

      {/* 唯讀模式顯示進度摘要 */}
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

  // Tab 6: 派工關聯
  const renderDispatchLinksTab = () => (
    <Spin spinning={isLoading}>
      {/* 新增關聯區塊 */}
      {canEdit && isEditing && (
        <Card size="small" style={{ marginBottom: 16 }} title="新增派工關聯">
          <Row gutter={[12, 12]} align="middle">
            <Col span={16}>
              <Select
                showSearch
                allowClear
                placeholder="搜尋派工單號..."
                style={{ width: '100%' }}
                value={selectedDispatchId}
                onChange={setSelectedDispatchId}
                filterOption={(input, option) =>
                  String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={filteredDispatches.map((d: DispatchOrder) => ({
                  value: d.id,
                  label: `${d.dispatch_no} - ${d.project_name || '(無工程名稱)'}`,
                }))}
                notFoundContent={
                  filteredDispatches.length === 0 ? (
                    <Empty description="無可關聯的派工紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : undefined
                }
              />
            </Col>
            <Col span={8}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleLinkDispatch}
                loading={linkDispatchMutation.isPending}
                disabled={!selectedDispatchId}
              >
                建立關聯
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 已關聯派工列表 */}
      {linkedDispatches.length > 0 ? (
        <List
          dataSource={linkedDispatches}
          renderItem={(dispatch: any) => (
            <Card size="small" style={{ marginBottom: 12 }}>
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="派工單號">
                  <Tag color="blue">{dispatch.dispatch_no}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="作業類別">
                  {dispatch.work_type || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="工程名稱" span={2}>
                  {dispatch.project_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="履約期限">
                  {dispatch.deadline || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="案件承辦">
                  {dispatch.case_handler || '-'}
                </Descriptions.Item>
              </Descriptions>
              <Space style={{ marginTop: 8 }}>
                <Button
                  type="link"
                  size="small"
                  onClick={() => navigate(`/taoyuan/dispatch/${dispatch.dispatch_order_id}`)}
                >
                  查看派工詳情
                </Button>
                {canEdit && isEditing && dispatch.link_id !== undefined && (
                  <Popconfirm
                    title="確定要移除此關聯嗎？"
                    onConfirm={() => unlinkDispatchMutation.mutate(dispatch.link_id)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button
                      type="link"
                      size="small"
                      danger
                      loading={unlinkDispatchMutation.isPending}
                    >
                      移除關聯
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            </Card>
          )}
        />
      ) : (
        <Empty description="此工程尚無關聯派工紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE}>
          {!canEdit && (
            <Button type="link" onClick={() => navigate('/taoyuan/dispatch')}>
              返回派工管理
            </Button>
          )}
        </Empty>
      )}
    </Spin>
  );

  // Tab 配置
  const tabs = [
    createTabItem(
      'basic',
      { icon: <ProjectOutlined />, text: '基本資訊' },
      renderBasicTab()
    ),
    createTabItem(
      'scope',
      { icon: <EnvironmentOutlined />, text: '工程範圍' },
      renderScopeTab()
    ),
    createTabItem(
      'land',
      { icon: <HomeOutlined />, text: '土地建物' },
      renderLandTab()
    ),
    createTabItem(
      'cost',
      { icon: <DollarOutlined />, text: '經費估算' },
      renderCostTab()
    ),
    createTabItem(
      'status',
      { icon: <FileTextOutlined />, text: '審議狀態' },
      renderStatusTab()
    ),
    createTabItem(
      'dispatch-links',
      { icon: <SendOutlined />, text: '派工關聯', count: linkedDispatches.length },
      renderDispatchLinksTab()
    ),
  ];

  // Header 配置
  const headerConfig = {
    title: project?.project_name || '工程詳情',
    icon: <ProjectOutlined />,
    backText: '返回派工管理',
    backPath: '/taoyuan/dispatch',
    tags: project
      ? [
          ...(project.district
            ? [{ text: project.district, color: 'green' as const }]
            : []),
          ...(project.case_type
            ? [{ text: project.case_type, color: 'blue' as const }]
            : []),
          ...(project.acceptance_status === '已驗收'
            ? [{ text: '已驗收', color: 'success' as const }]
            : []),
        ]
      : [],
    extra: (
      <Space>
        {isEditing ? (
          <>
            <Button icon={<CloseOutlined />} onClick={handleCancelEdit}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={updateMutation.isPending}
              onClick={handleSave}
            >
              儲存
            </Button>
          </>
        ) : (
          <>
            {canEdit && (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setIsEditing(true)}
              >
                編輯
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="確定要刪除此工程嗎？"
                description="刪除後將無法復原，請確認是否繼續。"
                onConfirm={() => deleteMutation.mutate()}
                okText="確定刪除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<DeleteOutlined />}>
                  刪除
                </Button>
              </Popconfirm>
            )}
          </>
        )}
      </Space>
    ),
  };

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      loading={isLoading}
      hasData={!!project}
    />
  );
};

export default TaoyuanProjectDetailPage;
