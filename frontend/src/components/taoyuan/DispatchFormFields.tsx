/**
 * 派工表單共用欄位元件
 *
 * 統一管理派工表單欄位，避免重複維護。
 * 支援三種模式：
 * - create: 完整新增模式（獨立新增頁面）
 * - edit: 編輯模式（派工詳情頁面）
 * - quick: 快速新增模式（公文內新增派工）
 *
 * @version 1.3.0 - 分案名稱/履約期限/聯絡備註/雲端資料夾/專案資料夾改為 TextArea 支援多行
 * @date 2026-01-29
 */

import React, { useMemo, useState } from 'react';
import {
  Form,
  Input,
  Select,
  Row,
  Col,
  AutoComplete,
  InputNumber,
  Divider,
  Space,
  Typography,
  Alert,
  Button,
} from 'antd';
import { ResponsiveFormRow } from '../common/ResponsiveFormRow';
import type { FormInstance } from 'antd';
import { FileTextOutlined, PlusOutlined } from '@ant-design/icons';

import type { TaoyuanProject, OfficialDocument } from '../../types/api';
import { TAOYUAN_WORK_TYPES } from '../../types/api';
import type { ProjectAgencyContact } from '../../api/projectAgencyContacts';
import type { ProjectVendor } from '../../api/projectVendorsApi';

const { Option } = Select;
const { Text } = Typography;

// =============================================================================
// 常數定義
// =============================================================================

/** 作業類別與金額欄位的對應表 */
const WORK_TYPE_AMOUNT_MAPPING: Record<
  string,
  { amountField: string; label: string }
> = {
  '01.地上物查估作業': { amountField: 'work_01_amount', label: '01.地上物查估' },
  '02.土地協議市價查估作業': { amountField: 'work_02_amount', label: '02.土地協議市價查估' },
  '03.土地徵收市價查估作業': { amountField: 'work_03_amount', label: '03.土地徵收市價查估' },
  '04.相關計畫書製作': { amountField: 'work_04_amount', label: '04.相關計畫書製作' },
  '05.測量作業': { amountField: 'work_05_amount', label: '05.測量作業' },
  '06.樁位測釘作業': { amountField: 'work_06_amount', label: '06.樁位測釘作業' },
  '07.辦理教育訓練': { amountField: 'work_07_amount', label: '07.辦理教育訓練' },
};

// =============================================================================
// Props 介面定義
// =============================================================================

export interface DispatchFormFieldsProps {
  /** Ant Design Form 實例 */
  form: FormInstance;

  /**
   * 表單模式
   * - create: 完整新增模式（顯示所有欄位）
   * - edit: 編輯模式（不顯示公文關聯，使用獨立 Tab）
   * - quick: 快速新增模式（精簡欄位，用於公文內新增）
   */
  mode: 'create' | 'edit' | 'quick';

  /** 可選擇的工程列表（用於工程名稱 AutoComplete） */
  availableProjects?: TaoyuanProject[];

  /** 機關承辦清單 */
  agencyContacts?: ProjectAgencyContact[];

  /** 協力廠商清單（查估單位） */
  projectVendors?: ProjectVendor[];

  /** 選擇工程時的回調（用於混合模式自動關聯） */
  onProjectSelect?: (projectId: number, projectName: string) => void;

  /** 新增工程的回調（輸入的工程名稱不在清單中時，提供快速新增） */
  onCreateProject?: (projectName: string) => void;

  /** 是否正在建立工程中 */
  creatingProject?: boolean;

  // === 契金相關（edit 模式專用） ===

  /** 是否顯示契金欄位（預設 create/edit 顯示，quick 不顯示） */
  showPaymentFields?: boolean;

  /** 監聽的作業類別（用於動態顯示契金欄位） */
  watchedWorkTypes?: string[];

  // === 公文關聯相關（create/quick 模式專用） ===

  /** 是否顯示公文關聯欄位 */
  showDocLinkFields?: boolean;

  /** 當前公文（quick 模式用於自動帶入） */
  document?: OfficialDocument | null;

  /** 是否為收文（quick 模式用於判斷自動帶入哪個欄位） */
  isReceiveDoc?: boolean;

  /** 機關函文選項（create 模式用） */
  agencyDocOptions?: Array<{ value: number; label: string }>;

  /** 乾坤函文選項（create 模式用） */
  companyDocOptions?: Array<{ value: number; label: string }>;

  /** 搜尋機關函文回調 */
  onAgencyDocSearch?: (keyword: string) => void;

  /** 搜尋乾坤函文回調 */
  onCompanyDocSearch?: (keyword: string) => void;

  // === 工程關聯相關（create 模式專用） ===

  /** 是否顯示工程關聯欄位 */
  showProjectLinkFields?: boolean;

  /** 工程選項（用於關聯工程多選） */
  projectLinkOptions?: Array<{ value: number; label: string }>;
}

// =============================================================================
// 主元件
// =============================================================================

export const DispatchFormFields: React.FC<DispatchFormFieldsProps> = ({
  form: _form,
  mode,
  availableProjects = [],
  agencyContacts = [],
  projectVendors = [],
  onProjectSelect,
  onCreateProject,
  creatingProject = false,
  showPaymentFields,
  watchedWorkTypes = [],
  showDocLinkFields,
  document,
  isReceiveDoc,
  agencyDocOptions = [],
  companyDocOptions = [],
  onAgencyDocSearch,
  onCompanyDocSearch,
  showProjectLinkFields,
  projectLinkOptions = [],
}) => {
  // 根據模式決定預設顯示
  const shouldShowPayment = showPaymentFields ?? (mode !== 'quick');
  const shouldShowDocLink = showDocLinkFields ?? (mode === 'create' || mode === 'quick');
  const shouldShowProjectLink = showProjectLinkFields ?? (mode === 'create');

  // 追蹤使用者輸入的工程名稱（用於判斷是否顯示「新增工程」按鈕）
  const [projectInputText, setProjectInputText] = useState('');

  // 判斷輸入的名稱是否已存在於工程清單中
  const isNewProjectName = useMemo(() => {
    if (!projectInputText.trim()) return false;
    return !availableProjects.some(
      (p) => p.project_name.toLowerCase() === projectInputText.trim().toLowerCase()
    );
  }, [projectInputText, availableProjects]);

  // 建立 AutoComplete 選項（工程列表）
  const projectOptions = useMemo(() => {
    return availableProjects.map((proj) => ({
      value: proj.project_name,
      label: (
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>{proj.project_name}</span>
          <span style={{ color: '#999', fontSize: '12px' }}>
            {[proj.district, proj.sequence_no ? `#${proj.sequence_no}` : null]
              .filter(Boolean)
              .join(' ')}
          </span>
        </div>
      ),
      projectId: proj.id,
    }));
  }, [availableProjects]);

  // 處理 AutoComplete 選擇
  const handleProjectSelect = (value: string, option: { projectId?: number }) => {
    if (option.projectId && onProjectSelect) {
      onProjectSelect(option.projectId, value);
    }
  };

  // 過濾有效的作業類別（用於契金欄位）
  const validWorkTypes = watchedWorkTypes.filter(
    (wt) => WORK_TYPE_AMOUNT_MAPPING[wt]
  );

  return (
    <>
      {/* ================================================================= */}
      {/* 第一行：派工單號 + 工程名稱/派工事項 */}
      {/* ================================================================= */}
      <ResponsiveFormRow>
        <Form.Item
          name="dispatch_no"
          label="派工單號"
          rules={[{ required: true, message: '請輸入派工單號' }]}
        >
          <Input placeholder="例: TY-2026-001" />
        </Form.Item>
        <Form.Item
          name="project_name"
          label="工程名稱/派工事項"
          tooltip="可從工程列表選擇或直接輸入（如：教育訓練）"
        >
          <AutoComplete
            options={projectOptions}
            onSelect={handleProjectSelect}
            onSearch={setProjectInputText}
            onChange={(value) => {
              if (!value) setProjectInputText('');
            }}
            placeholder="輸入或選擇工程名稱/派工事項"
            allowClear
            filterOption={(inputValue, option) =>
              option?.value?.toLowerCase().includes(inputValue.toLowerCase()) ?? false
            }
            dropdownRender={(menu) => (
              <>
                {menu}
                {onCreateProject && isNewProjectName && (
                  <>
                    <Divider style={{ margin: '4px 0' }} />
                    <Button
                      type="link"
                      icon={<PlusOutlined />}
                      onClick={() => onCreateProject(projectInputText.trim())}
                      loading={creatingProject}
                      style={{ width: '100%', textAlign: 'left' }}
                    >
                      新增工程「{projectInputText.trim()}」
                    </Button>
                  </>
                )}
              </>
            )}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* ================================================================= */}
      {/* 第二行：作業類別 + 分案名稱 + 履約期限 */}
      {/* ================================================================= */}
      <ResponsiveFormRow>
        <Form.Item name="work_type" label="作業類別">
          <Select
            mode="multiple"
            allowClear
            placeholder="選擇作業類別（可多選）"
            maxTagCount={2}
          >
            {TAOYUAN_WORK_TYPES.map((type) => (
              <Option key={type} value={type}>
                {type}
              </Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="sub_case_name" label="分案名稱/派工備註">
          <Input.TextArea
            rows={2}
            placeholder="輸入分案名稱或備註"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
        <Form.Item name="deadline" label="履約期限">
          <Input.TextArea
            rows={2}
            placeholder="例: 114/12/31"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* ================================================================= */}
      {/* 第三行：案件承辦 + 查估單位 + 聯絡備註 */}
      {/* ================================================================= */}
      <ResponsiveFormRow>
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
                <div style={{ lineHeight: 1.4 }}>
                  <div>{contact.contact_name}</div>
                  {(contact.position || contact.department) && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {[contact.position, contact.department].filter(Boolean).join(' / ')}
                    </Text>
                  )}
                </div>
              </Option>
            ))}
          </Select>
        </Form.Item>
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
            {projectVendors.map((vendor) => (
              <Option
                key={vendor.vendor_id}
                value={vendor.vendor_name}
                label={vendor.vendor_name}
              >
                <div style={{ lineHeight: 1.4 }}>
                  <div>{vendor.vendor_name}</div>
                  {(vendor.role || vendor.vendor_business_type) && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {[vendor.role, vendor.vendor_business_type].filter(Boolean).join(' / ')}
                    </Text>
                  )}
                </div>
              </Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="contact_note" label="聯絡備註">
          <Input.TextArea
            rows={2}
            placeholder="輸入聯絡備註"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* ================================================================= */}
      {/* 第四行：雲端資料夾 + 專案資料夾 */}
      {/* ================================================================= */}
      <ResponsiveFormRow>
        <Form.Item name="cloud_folder" label="雲端資料夾">
          <Input.TextArea
            rows={2}
            placeholder="Google Drive 連結"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
        <Form.Item name="project_folder" label="專案資料夾">
          <Input.TextArea
            rows={2}
            placeholder="本地路徑"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* ================================================================= */}
      {/* 公文關聯區塊 */}
      {/* ================================================================= */}
      {shouldShowDocLink && (
        <>
          <Divider style={{ margin: '16px 0' }} />
          <div style={{ marginBottom: 16 }}>
            <Space>
              <FileTextOutlined />
              <span style={{ fontWeight: 500 }}>公文關聯</span>
            </Space>
          </div>

          {mode === 'quick' && document ? (
            // quick 模式：自動帶入當前公文
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
            // create 模式：可搜尋選擇公文
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
                  notFoundContent={
                    companyDocOptions.length === 0 ? '無符合資料' : '輸入關鍵字搜尋'
                  }
                  options={companyDocOptions}
                />
              </Form.Item>
            </ResponsiveFormRow>
          )}
        </>
      )}

      {/* ================================================================= */}
      {/* 契金資訊區塊 */}
      {/* ================================================================= */}
      {shouldShowPayment && (
        <>
          <Divider orientation="left">契金資訊</Divider>

          {mode === 'edit' ? (
            // edit 模式：根據選擇的作業類別動態顯示金額欄位
            validWorkTypes.length > 0 ? (
              <Row gutter={16}>
                {validWorkTypes.map((wt) => {
                  const mapping = WORK_TYPE_AMOUNT_MAPPING[wt];
                  if (!mapping) return null;
                  return (
                    <Col span={8} key={wt}>
                      <Form.Item
                        name={mapping.amountField}
                        label={`${mapping.label} 金額`}
                      >
                        <InputNumber
                          style={{ width: '100%' }}
                          min={0}
                          precision={0}
                          formatter={(value) =>
                            `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                          }
                          parser={(value) =>
                            Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as unknown as 0
                          }
                          placeholder="輸入金額"
                        />
                      </Form.Item>
                    </Col>
                  );
                })}
              </Row>
            ) : (
              <Alert
                message="請先選擇作業類別"
                description="選擇作業類別後，將顯示對應的金額輸入欄位"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )
          ) : (
            // create 模式：顯示所有 7 種金額欄位
            <Row gutter={[16, 16]}>
              {Object.entries(WORK_TYPE_AMOUNT_MAPPING).map(([, mapping]) => (
                <Col span={6} key={mapping.amountField}>
                  <Form.Item name={mapping.amountField} label={mapping.label}>
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0}
                      precision={0}
                      formatter={(value) =>
                        `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                      }
                      parser={(value) =>
                        Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as unknown as 0
                      }
                      placeholder="輸入金額"
                    />
                  </Form.Item>
                </Col>
              ))}
            </Row>
          )}
        </>
      )}

      {/* ================================================================= */}
      {/* 工程關聯區塊（僅 create 模式） */}
      {/* ================================================================= */}
      {shouldShowProjectLink && (
        <>
          <Divider orientation="left">工程關聯</Divider>
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
              options={projectLinkOptions}
            />
          </Form.Item>
        </>
      )}
    </>
  );
};

export default DispatchFormFields;
