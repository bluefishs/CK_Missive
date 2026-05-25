#!/usr/bin/env python3
"""
Phase 2: 前端整合自動化腳本
=============================
工程歷程追蹤（Workflow）前端模組

執行內容:
  Step 1: 新增 TypeScript 型別定義 → types/taoyuan.ts (追加)
  Step 2: 新增常數定義 → constants/taoyuanOptions.ts (追加)
  Step 3: 新增 API 端點 → api/endpoints.ts (追加)
  Step 4: 建立 API 模組 → api/taoyuan/workflow.ts (新檔)
  Step 5: 更新 API 入口 → api/taoyuan/index.ts (修改)
  Step 6: 建立頁面元件 → pages/taoyuanWorkflow/ (新目錄 5 檔)
  Step 7: 更新路由設定 → router/types.ts + router/AppRouter.tsx

執行方式:
  cd C:\\GeminiCli\\CK_Missive
  python claude_plant/project_dispatch_workflow/phase2_execute_frontend.py

日期: 2026-02-12
"""

import os
import sys
import re
import shutil
from datetime import datetime

# ============================================================================
# 基本設定
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_SRC = os.path.join(BASE_DIR, "frontend", "src")
BACKUP_DIR = os.path.join(BASE_DIR, "claude_plant", "project_dispatch_workflow", "backups",
                          f"phase2_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

RESULTS = []

def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "SKIP": "⏭️"}.get(level, "  ")
    print(f"  {prefix} {msg}")
    RESULTS.append((level, msg))

def backup_file(filepath):
    """備份檔案到 BACKUP_DIR"""
    if os.path.exists(filepath):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        rel = os.path.relpath(filepath, FRONTEND_SRC)
        dest = os.path.join(BACKUP_DIR, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(filepath, dest)
        log(f"已備份: {rel}", "INFO")

def write_new_file(filepath, content):
    """建立新檔案"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    rel = os.path.relpath(filepath, FRONTEND_SRC)
    log(f"已建立: {rel}", "OK")

def append_to_file(filepath, content, marker=None):
    """在檔案尾部追加內容 (若有 marker 則追加在 marker 前)"""
    backup_file(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()
    if marker and marker in original:
        updated = original.replace(marker, content + "\n" + marker)
    else:
        updated = original.rstrip() + "\n\n" + content + "\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(updated)
    rel = os.path.relpath(filepath, FRONTEND_SRC)
    log(f"已追加: {rel}", "OK")

def insert_after(filepath, anchor, new_content):
    """在 anchor 所在行之後插入 new_content"""
    backup_file(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and anchor in line:
            out.append(new_content if new_content.endswith("\n") else new_content + "\n")
            inserted = True
    if not inserted:
        log(f"找不到錨點 '{anchor[:50]}...' in {os.path.basename(filepath)}", "WARN")
        return False
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(out)
    rel = os.path.relpath(filepath, FRONTEND_SRC)
    log(f"已插入: {rel} (after: {anchor[:40]}...)", "OK")
    return True


# ============================================================================
# Step 1: 新增 TypeScript 型別定義
# ============================================================================

def step1_add_types():
    print("\n🔹 Step 1: 新增工作歷程型別定義 → types/taoyuan.ts")

    filepath = os.path.join(FRONTEND_SRC, "types", "taoyuan.ts")
    if not os.path.exists(filepath):
        log("types/taoyuan.ts 不存在!", "ERR")
        return False

    # 檢查是否已新增
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if "WorkRecord" in content:
        log("WorkRecord 型別已存在，跳過", "SKIP")
        return True

    type_defs = '''
// ============================================================================
// 工程歷程追蹤 (Workflow) 相關型別
// ============================================================================

/** 里程碑類型 */
export type MilestoneType =
  | 'dispatch'
  | 'survey'
  | 'site_inspection'
  | 'submit_result'
  | 'revision'
  | 'review_meeting'
  | 'negotiation'
  | 'final_approval'
  | 'boundary_survey'
  | 'closed'
  | 'other';

/** 工作紀錄狀態 */
export type WorkRecordStatus = 'pending' | 'in_progress' | 'completed' | 'overdue';

/** 公文簡要資訊 (嵌入 WorkRecord) */
export interface DocBrief {
  id: number;
  doc_number?: string;
  doc_date?: string;
  subject?: string;
}

/** 工作歷程紀錄 */
export interface WorkRecord {
  id: number;
  dispatch_order_id: number;
  taoyuan_project_id?: number;
  incoming_doc_id?: number;
  outgoing_doc_id?: number;
  milestone_type: MilestoneType;
  description?: string;
  submission_type?: string;
  record_date: string;
  deadline_date?: string;
  completed_date?: string;
  status: WorkRecordStatus;
  sort_order: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
  // 嵌套公文資訊
  incoming_doc?: DocBrief;
  outgoing_doc?: DocBrief;
  // 派工單/工程名稱 (列表用)
  dispatch_no?: string;
  project_name?: string;
}

/** 工作歷程建立請求 */
export interface WorkRecordCreate {
  dispatch_order_id: number;
  taoyuan_project_id?: number;
  incoming_doc_id?: number;
  outgoing_doc_id?: number;
  milestone_type: MilestoneType;
  description?: string;
  submission_type?: string;
  record_date: string;
  deadline_date?: string;
  completed_date?: string;
  status?: WorkRecordStatus;
  sort_order?: number;
  notes?: string;
}

/** 工作歷程更新請求 */
export type WorkRecordUpdate = Partial<Omit<WorkRecordCreate, 'dispatch_order_id'>>;

/** 工作歷程列表查詢參數 */
export interface WorkRecordListQuery {
  page?: number;
  limit?: number;
  dispatch_order_id?: number;
  taoyuan_project_id?: number;
  milestone_type?: MilestoneType;
  status?: WorkRecordStatus;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** 工作歷程列表回應 */
export interface WorkRecordListResponse {
  success: boolean;
  items: WorkRecord[];
  pagination: PaginationMeta;
}

/** 工程歷程摘要 */
export interface ProjectWorkflowSummary {
  project_id: number;
  sequence_no?: number;
  project_name: string;
  sub_case_name?: string;
  district?: string;
  batch_close_no?: number;
  case_handler?: string;
  total_records: number;
  total_incoming_docs: number;
  total_outgoing_docs: number;
  current_stage?: string;
  last_record_date?: string;
  records: WorkRecord[];
}

/** 工程歷程摘要列表回應 */
export interface WorkflowSummaryResponse {
  success: boolean;
  items: ProjectWorkflowSummary[];
  pagination: PaginationMeta;
}

/** 里程碑類型定義 (前端常數用) */
export interface MilestoneTypeOption {
  value: MilestoneType;
  label: string;
  color: string;
  order: number;
}

/** 發文類別選項 */
export interface SubmissionTypeOption {
  value: string;
  label: string;
}
'''
    append_to_file(filepath, type_defs)
    return True


# ============================================================================
# Step 2: 新增常數定義
# ============================================================================

def step2_add_constants():
    print("\n🔹 Step 2: 新增工作歷程常數 → constants/taoyuanOptions.ts")

    filepath = os.path.join(FRONTEND_SRC, "constants", "taoyuanOptions.ts")
    if not os.path.exists(filepath):
        log("constants/taoyuanOptions.ts 不存在!", "ERR")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if "MILESTONE_TYPE_OPTIONS" in content:
        log("MILESTONE_TYPE_OPTIONS 已存在，跳過", "SKIP")
        return True

    constants = '''
// ============================================================================
// 工程歷程追蹤常數
// ============================================================================

/**
 * 里程碑類型選項
 * 對應後端 MilestoneType enum
 */
export const MILESTONE_TYPE_OPTIONS = [
  { value: 'dispatch', label: '派工', color: 'green', order: 1 },
  { value: 'survey', label: '會勘', color: 'blue', order: 2 },
  { value: 'site_inspection', label: '查估檢視', color: 'cyan', order: 3 },
  { value: 'submit_result', label: '送件/檢送成果', color: 'gold', order: 4 },
  { value: 'revision', label: '修正成果', color: 'orange', order: 5 },
  { value: 'review_meeting', label: '審查/價審會議', color: 'purple', order: 6 },
  { value: 'negotiation', label: '協議價購', color: 'magenta', order: 7 },
  { value: 'final_approval', label: '定稿核定', color: 'lime', order: 8 },
  { value: 'boundary_survey', label: '土地鑑界', color: 'geekblue', order: 9 },
  { value: 'closed', label: '結案', color: 'red', order: 99 },
  { value: 'other', label: '其他', color: 'default', order: 50 },
] as const;

/** 里程碑 value → label 快查表 */
export const MILESTONE_LABEL_MAP: Record<string, string> = Object.fromEntries(
  MILESTONE_TYPE_OPTIONS.map(o => [o.value, o.label])
);

/** 里程碑 value → color 快查表 */
export const MILESTONE_COLOR_MAP: Record<string, string> = Object.fromEntries(
  MILESTONE_TYPE_OPTIONS.map(o => [o.value, o.color])
);

/**
 * 發文類別選項
 * 公司發文給機關時的類別分類
 */
export const SUBMISSION_TYPE_OPTIONS = [
  { value: '檢送成果(紙本+電子檔)', label: '檢送成果(紙本+電子檔)' },
  { value: '檢送修正後成果(紙本+電子檔)', label: '檢送修正後成果(紙本+電子檔)' },
  { value: '檢修正後成果(協議市價-電子檔)', label: '檢修正後成果(協議市價-電子檔)' },
  { value: '檢送成果(電子檔)', label: '檢送成果(電子檔)' },
  { value: '檢修正後成果', label: '檢修正後成果' },
  { value: '檢送成果定稿版(繳送)', label: '檢送成果定稿版(繳送)' },
] as const;

/** 工作紀錄狀態選項 */
export const WORK_RECORD_STATUS_OPTIONS = [
  { value: 'pending', label: '待處理', color: 'default' },
  { value: 'in_progress', label: '進行中', color: 'processing' },
  { value: 'completed', label: '已完成', color: 'success' },
  { value: 'overdue', label: '已逾期', color: 'error' },
] as const;

/** 結案批次顏色對應 */
export const BATCH_CLOSE_COLORS: Record<number, string> = {
  1: '#52c41a',  // 綠
  2: '#1890ff',  // 藍
  3: '#faad14',  // 黃
  4: '#eb2f96',  // 粉
  5: '#722ed1',  // 紫
};
'''
    append_to_file(filepath, constants)
    return True


# ============================================================================
# Step 3: 新增 API 端點常數
# ============================================================================

def step3_add_endpoints():
    print("\n🔹 Step 3: 新增 Workflow API 端點 → api/endpoints.ts")

    filepath = os.path.join(FRONTEND_SRC, "api", "endpoints.ts")
    if not os.path.exists(filepath):
        log("api/endpoints.ts 不存在!", "ERR")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if "WORKFLOW_CONSTANTS" in content:
        log("Workflow 端點已存在，跳過", "SKIP")
        return True

    # 在 TAOYUAN_DISPATCH_ENDPOINTS 結尾 "} as const;" 前插入
    # 找到最後一個 TAOYUAN 相關的端點塊
    new_endpoints = '''
  // 工程歷程追蹤 (Workflow)
  /** 歷程常數 GET /taoyuan-dispatch/workflow/constants */
  WORKFLOW_CONSTANTS: '/taoyuan-dispatch/workflow/constants',
  /** 歷程紀錄列表 GET /taoyuan-dispatch/workflow/records */
  WORKFLOW_RECORDS_LIST: '/taoyuan-dispatch/workflow/records',
  /** 建立歷程紀錄 POST /taoyuan-dispatch/workflow/records */
  WORKFLOW_RECORDS_CREATE: '/taoyuan-dispatch/workflow/records',
  /** 歷程紀錄詳情 GET /taoyuan-dispatch/workflow/records/:id */
  WORKFLOW_RECORDS_DETAIL: (id: number) => `/taoyuan-dispatch/workflow/records/${id}`,
  /** 更新歷程紀錄 PUT /taoyuan-dispatch/workflow/records/:id */
  WORKFLOW_RECORDS_UPDATE: (id: number) => `/taoyuan-dispatch/workflow/records/${id}`,
  /** 刪除歷程紀錄 DELETE /taoyuan-dispatch/workflow/records/:id */
  WORKFLOW_RECORDS_DELETE: (id: number) => `/taoyuan-dispatch/workflow/records/${id}`,
  /** 工程歷程摘要 GET /taoyuan-dispatch/workflow/project-summary */
  WORKFLOW_PROJECT_SUMMARY: '/taoyuan-dispatch/workflow/project-summary',
  /** 單一工程歷程 GET /taoyuan-dispatch/workflow/projects/:id */
  WORKFLOW_PROJECT_DETAIL: (id: number) => `/taoyuan-dispatch/workflow/projects/${id}`,'''

    # 尋找 TAOYUAN_DISPATCH_ENDPOINTS 的結尾 "} as const;"
    # 往回找 DOCUMENT_LINK_PROJECT 或最後一個端點
    backup_file(filepath)
    # 找到 TAOYUAN_DISPATCH_ENDPOINTS 區塊，在其 "} as const;" 前插入
    # 策略：找到包含 "DOCUMENT_LINK_PROJECT" 的行，向下找到 "}," 或 "} as const;"
    lines = content.split('\n')
    insert_idx = None
    in_taoyuan_block = False
    brace_count = 0

    for i, line in enumerate(lines):
        if 'TAOYUAN_DISPATCH_ENDPOINTS' in line and '=' in line:
            in_taoyuan_block = True
            continue
        if in_taoyuan_block:
            brace_count += line.count('{') - line.count('}')
            if '} as const;' in line and brace_count <= 0:
                insert_idx = i
                break

    if insert_idx is None:
        log("找不到 TAOYUAN_DISPATCH_ENDPOINTS 結尾", "WARN")
        # fallback: 在檔案尾部 export 前插入
        return False

    lines.insert(insert_idx, new_endpoints)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    log("已插入 Workflow 端點到 TAOYUAN_DISPATCH_ENDPOINTS", "OK")
    return True


# ============================================================================
# Step 4: 建立 API 模組
# ============================================================================

def step4_create_api_module():
    print("\n🔹 Step 4: 建立 Workflow API 模組 → api/taoyuan/workflow.ts")

    filepath = os.path.join(FRONTEND_SRC, "api", "taoyuan", "workflow.ts")
    if os.path.exists(filepath):
        log("api/taoyuan/workflow.ts 已存在，跳過", "SKIP")
        return True

    content = '''/**
 * 桃園查估派工 - 工程歷程追蹤 API
 *
 * @version 1.0.0
 * @date 2026-02-12
 */

import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  WorkRecord,
  WorkRecordCreate,
  WorkRecordUpdate,
  WorkRecordListQuery,
  WorkRecordListResponse,
  ProjectWorkflowSummary,
  WorkflowSummaryResponse,
} from '../../types/taoyuan';

const EP = API_ENDPOINTS.TAOYUAN_DISPATCH;

/**
 * 工程歷程追蹤 API 服務
 */
export const workflowApi = {
  // ── 常數 ──────────────────────────────────────────────
  /**
   * 取得歷程相關常數 (里程碑類型、發文類別、批次顏色)
   */
  async getConstants() {
    return apiClient.get<{
      milestone_types: Record<string, { label: string; color: string; order: number }>;
      submission_types: Record<string, string>;
      batch_close_colors: Record<string, string>;
    }>(EP.WORKFLOW_CONSTANTS);
  },

  // ── 歷程紀錄 CRUD ────────────────────────────────────
  /**
   * 取得歷程紀錄列表
   */
  async listRecords(params?: WorkRecordListQuery): Promise<WorkRecordListResponse> {
    return apiClient.get<WorkRecordListResponse>(EP.WORKFLOW_RECORDS_LIST, { params });
  },

  /**
   * 建立歷程紀錄
   */
  async createRecord(data: WorkRecordCreate): Promise<WorkRecord> {
    return apiClient.post<WorkRecord>(EP.WORKFLOW_RECORDS_CREATE, data);
  },

  /**
   * 取得單筆歷程紀錄
   */
  async getRecord(id: number): Promise<WorkRecord> {
    return apiClient.get<WorkRecord>(EP.WORKFLOW_RECORDS_DETAIL(id));
  },

  /**
   * 更新歷程紀錄
   */
  async updateRecord(id: number, data: WorkRecordUpdate): Promise<WorkRecord> {
    return apiClient.put<WorkRecord>(EP.WORKFLOW_RECORDS_UPDATE(id), data);
  },

  /**
   * 刪除歷程紀錄
   */
  async deleteRecord(id: number): Promise<{ success: boolean; message: string }> {
    return apiClient.delete(EP.WORKFLOW_RECORDS_DELETE(id));
  },

  // ── 工程歷程摘要 ─────────────────────────────────────
  /**
   * 取得所有工程的歷程摘要
   */
  async getProjectSummary(params?: {
    contract_project_id?: number;
    batch_close_no?: number;
    district?: string;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<WorkflowSummaryResponse> {
    return apiClient.get<WorkflowSummaryResponse>(EP.WORKFLOW_PROJECT_SUMMARY, { params });
  },

  /**
   * 取得單一工程的完整歷程
   */
  async getProjectWorkflow(projectId: number): Promise<ProjectWorkflowSummary> {
    return apiClient.get<ProjectWorkflowSummary>(EP.WORKFLOW_PROJECT_DETAIL(projectId));
  },
};

export default workflowApi;
'''
    write_new_file(filepath, content)
    return True


# ============================================================================
# Step 5: 更新 API 入口
# ============================================================================

def step5_update_api_index():
    print("\n🔹 Step 5: 更新 API 模組入口 → api/taoyuan/index.ts")

    filepath = os.path.join(FRONTEND_SRC, "api", "taoyuan", "index.ts")
    if not os.path.exists(filepath):
        log("api/taoyuan/index.ts 不存在!", "ERR")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if "workflowApi" in content:
        log("workflowApi 已匯出，跳過", "SKIP")
        return True

    backup_file(filepath)

    # 1) 加入 export
    content = content.replace(
        "export { dispatchAttachmentsApi",
        "export { workflowApi } from './workflow';\nexport { dispatchAttachmentsApi"
    )

    # 2) 加入 import
    content = content.replace(
        "import { dispatchAttachmentsApi } from './attachments';",
        "import { dispatchAttachmentsApi } from './attachments';\nimport { workflowApi } from './workflow';"
    )

    # 3) 加入到統一入口物件
    content = content.replace(
        "  attachments: dispatchAttachmentsApi,",
        "  attachments: dispatchAttachmentsApi,\n  workflow: workflowApi,"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    log("已更新 api/taoyuan/index.ts", "OK")
    return True


# ============================================================================
# Step 6: 建立頁面元件
# ============================================================================

def step6_create_page_components():
    print("\n🔹 Step 6: 建立頁面元件 → pages/taoyuanWorkflow/")

    page_dir = os.path.join(FRONTEND_SRC, "pages", "taoyuanWorkflow")
    os.makedirs(page_dir, exist_ok=True)

    # ── 6a: index.ts ──
    write_new_file(os.path.join(page_dir, "index.ts"), '''/**
 * 工程歷程追蹤模組匯出
 */
export { ProjectWorkflowPage } from './ProjectWorkflowPage';
export { WorkflowTimeline } from './WorkflowTimeline';
export { WorkRecordFormModal } from './WorkRecordFormModal';
export { WorkflowFilters } from './WorkflowFilters';
''')

    # ── 6b: WorkflowFilters.tsx ──
    write_new_file(os.path.join(page_dir, "WorkflowFilters.tsx"), '''/**
 * 工程歷程篩選列元件
 */
import React from 'react';
import { Card, Row, Col, Select, Input, Button, Space } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  MILESTONE_TYPE_OPTIONS,
  DISTRICT_OPTIONS,
  BATCH_CLOSE_COLORS,
  WORK_RECORD_STATUS_OPTIONS,
} from '../../constants/taoyuanOptions';

export interface WorkflowFilterValues {
  search?: string;
  district?: string;
  milestone_type?: string;
  batch_close_no?: number;
  status?: string;
}

interface WorkflowFiltersProps {
  values: WorkflowFilterValues;
  onChange: (values: WorkflowFilterValues) => void;
  onReset: () => void;
  loading?: boolean;
}

export const WorkflowFilters: React.FC<WorkflowFiltersProps> = ({
  values,
  onChange,
  onReset,
  loading,
}) => {
  const handleChange = (key: keyof WorkflowFilterValues, val: any) => {
    onChange({ ...values, [key]: val || undefined });
  };

  return (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Row gutter={[12, 12]} align="middle">
        <Col xs={24} sm={12} md={6}>
          <Input
            placeholder="搜尋工程名稱..."
            prefix={<SearchOutlined />}
            value={values.search}
            onChange={(e) => handleChange('search', e.target.value)}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4}>
          <Select
            placeholder="行政區"
            value={values.district}
            onChange={(v) => handleChange('district', v)}
            options={DISTRICT_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
            allowClear
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={12} sm={6} md={4}>
          <Select
            placeholder="里程碑類型"
            value={values.milestone_type}
            onChange={(v) => handleChange('milestone_type', v)}
            options={MILESTONE_TYPE_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
            allowClear
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Select
            placeholder="結案批次"
            value={values.batch_close_no}
            onChange={(v) => handleChange('batch_close_no', v)}
            options={Object.entries(BATCH_CLOSE_COLORS).map(([k, c]) => ({
              value: Number(k),
              label: `第 ${k} 批`,
            }))}
            allowClear
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Select
            placeholder="狀態"
            value={values.status}
            onChange={(v) => handleChange('status', v)}
            options={WORK_RECORD_STATUS_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
            allowClear
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} sm={6} md={4}>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={onReset} loading={loading}>
              重置
            </Button>
          </Space>
        </Col>
      </Row>
    </Card>
  );
};

export default WorkflowFilters;
''')

    # ── 6c: WorkflowTimeline.tsx ──
    write_new_file(os.path.join(page_dir, "WorkflowTimeline.tsx"), '''/**
 * 工程歷程時間軸元件
 *
 * 以 Ant Design Timeline 呈現單一工程的里程碑歷程
 */
import React from 'react';
import { Timeline, Tag, Typography, Space, Button, Tooltip, Empty } from 'antd';
import { EditOutlined, DeleteOutlined, FileTextOutlined } from '@ant-design/icons';
import type { WorkRecord } from '../../types/taoyuan';
import { MILESTONE_LABEL_MAP, MILESTONE_COLOR_MAP } from '../../constants/taoyuanOptions';

const { Text, Paragraph } = Typography;

interface WorkflowTimelineProps {
  records: WorkRecord[];
  onEdit?: (record: WorkRecord) => void;
  onDelete?: (record: WorkRecord) => void;
  loading?: boolean;
}

export const WorkflowTimeline: React.FC<WorkflowTimelineProps> = ({
  records,
  onEdit,
  onDelete,
  loading,
}) => {
  if (!records || records.length === 0) {
    return <Empty description="尚無歷程紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  // 依 record_date 降序排列 (最新在上)
  const sorted = [...records].sort(
    (a, b) => new Date(b.record_date).getTime() - new Date(a.record_date).getTime()
  );

  return (
    <Timeline
      mode="left"
      items={sorted.map((rec) => ({
        color: MILESTONE_COLOR_MAP[rec.milestone_type] || 'gray',
        children: (
          <div style={{ paddingBottom: 8 }}>
            {/* 標題列: 日期 + 里程碑 Tag */}
            <Space size={8} wrap>
              <Text strong>{rec.record_date}</Text>
              <Tag color={MILESTONE_COLOR_MAP[rec.milestone_type] || 'default'}>
                {MILESTONE_LABEL_MAP[rec.milestone_type] || rec.milestone_type}
              </Tag>
              {rec.status === 'completed' && <Tag color="success">已完成</Tag>}
              {rec.status === 'overdue' && <Tag color="error">已逾期</Tag>}
            </Space>

            {/* 機關來文 */}
            {rec.incoming_doc && (
              <div style={{ marginTop: 4 }}>
                <FileTextOutlined style={{ color: '#1890ff', marginRight: 4 }} />
                <Text type="secondary">
                  機關來文：{rec.incoming_doc.doc_number || '—'}
                  {rec.incoming_doc.doc_date && ` (${rec.incoming_doc.doc_date})`}
                </Text>
              </div>
            )}

            {/* 事項描述 */}
            {rec.description && (
              <Paragraph
                style={{ marginTop: 4, marginBottom: 4 }}
                ellipsis={{ rows: 2, expandable: true, symbol: '展開' }}
              >
                {rec.description}
              </Paragraph>
            )}

            {/* 公司發文 + 發文類別 */}
            {rec.outgoing_doc && (
              <div>
                <FileTextOutlined style={{ color: '#52c41a', marginRight: 4 }} />
                <Text type="secondary">
                  公司發文：{rec.outgoing_doc.doc_number || '—'}
                  {rec.submission_type && ` — ${rec.submission_type}`}
                </Text>
              </div>
            )}

            {/* 備註 */}
            {rec.notes && (
              <div style={{ marginTop: 4 }}>
                <Text type="secondary" italic>備註：{rec.notes}</Text>
              </div>
            )}

            {/* 操作按鈕 */}
            <Space size={4} style={{ marginTop: 6 }}>
              {onEdit && (
                <Tooltip title="編輯">
                  <Button
                    type="link"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => onEdit(rec)}
                  />
                </Tooltip>
              )}
              {onDelete && (
                <Tooltip title="刪除">
                  <Button
                    type="link"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => onDelete(rec)}
                  />
                </Tooltip>
              )}
            </Space>
          </div>
        ),
      }))}
    />
  );
};

export default WorkflowTimeline;
''')

    # ── 6d: WorkRecordFormModal.tsx ──
    write_new_file(os.path.join(page_dir, "WorkRecordFormModal.tsx"), '''/**
 * 工作歷程新增/編輯 Modal
 */
import React, { useEffect } from 'react';
import {
  Modal,
  Form,
  Select,
  Input,
  DatePicker,
  Radio,
  message,
} from 'antd';
import dayjs from 'dayjs';
import type { WorkRecord, WorkRecordCreate, WorkRecordUpdate } from '../../types/taoyuan';
import {
  MILESTONE_TYPE_OPTIONS,
  SUBMISSION_TYPE_OPTIONS,
  WORK_RECORD_STATUS_OPTIONS,
} from '../../constants/taoyuanOptions';

const { TextArea } = Input;

interface WorkRecordFormModalProps {
  open: boolean;
  record?: WorkRecord | null;
  dispatchOrderId?: number;
  projectId?: number;
  onSubmit: (data: WorkRecordCreate | WorkRecordUpdate) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

export const WorkRecordFormModal: React.FC<WorkRecordFormModalProps> = ({
  open,
  record,
  dispatchOrderId,
  projectId,
  onSubmit,
  onCancel,
  loading,
}) => {
  const [form] = Form.useForm();
  const isEdit = !!record;

  useEffect(() => {
    if (open) {
      if (record) {
        form.setFieldsValue({
          ...record,
          record_date: record.record_date ? dayjs(record.record_date) : undefined,
          deadline_date: record.deadline_date ? dayjs(record.deadline_date) : undefined,
          completed_date: record.completed_date ? dayjs(record.completed_date) : undefined,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          dispatch_order_id: dispatchOrderId,
          taoyuan_project_id: projectId,
          status: 'pending',
          record_date: dayjs(),
        });
      }
    }
  }, [open, record, dispatchOrderId, projectId, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        record_date: values.record_date?.format('YYYY-MM-DD'),
        deadline_date: values.deadline_date?.format('YYYY-MM-DD') || null,
        completed_date: values.completed_date?.format('YYYY-MM-DD') || null,
      };
      await onSubmit(payload);
      form.resetFields();
    } catch (err: any) {
      if (err?.errorFields) return; // validation error
      message.error('儲存失敗');
    }
  };

  return (
    <Modal
      title={isEdit ? '編輯歷程紀錄' : '新增歷程紀錄'}
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={640}
      destroyOnClose
    >
      <Form form={form} layout="vertical" size="middle">
        <Form.Item name="dispatch_order_id" hidden>
          <Input />
        </Form.Item>
        <Form.Item name="taoyuan_project_id" hidden>
          <Input />
        </Form.Item>

        <Form.Item
          name="milestone_type"
          label="里程碑類型"
          rules={[{ required: true, message: '請選擇里程碑類型' }]}
        >
          <Select
            placeholder="請選擇里程碑類型"
            options={MILESTONE_TYPE_OPTIONS.map(o => ({
              value: o.value,
              label: `${o.label}`,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="record_date"
          label="紀錄日期"
          rules={[{ required: true, message: '請選擇日期' }]}
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="description" label="事項描述">
          <TextArea rows={3} placeholder="輸入事項描述..." />
        </Form.Item>

        <Form.Item name="submission_type" label="發文類別">
          <Select
            placeholder="選擇發文類別 (選填)"
            options={SUBMISSION_TYPE_OPTIONS.map(o => ({
              value: o.value,
              label: o.label,
            }))}
            allowClear
          />
        </Form.Item>

        <Form.Item name="deadline_date" label="期限日期">
          <DatePicker style={{ width: '100%' }} placeholder="選擇期限日期 (選填)" />
        </Form.Item>

        <Form.Item name="completed_date" label="完成日期">
          <DatePicker style={{ width: '100%' }} placeholder="選擇完成日期 (選填)" />
        </Form.Item>

        <Form.Item name="status" label="狀態">
          <Radio.Group>
            {WORK_RECORD_STATUS_OPTIONS.map(o => (
              <Radio key={o.value} value={o.value}>{o.label}</Radio>
            ))}
          </Radio.Group>
        </Form.Item>

        <Form.Item name="notes" label="備註">
          <TextArea rows={2} placeholder="備註 (選填)" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default WorkRecordFormModal;
''')

    # ── 6e: ProjectWorkflowPage.tsx (主頁面) ──
    write_new_file(os.path.join(page_dir, "ProjectWorkflowPage.tsx"), '''/**
 * 工程歷程追蹤主頁面
 *
 * 以 Collapse 卡片呈現各工程的歷程，
 * 展開後以 Tabs 切換「歷程時間軸」與「公文明細」。
 *
 * @version 1.0.0
 * @date 2026-02-12
 */
import React, { useState, useCallback } from 'react';
import {
  Typography,
  Card,
  Collapse,
  Tabs,
  Tag,
  Space,
  Button,
  Spin,
  Empty,
  Popconfirm,
  message,
  Steps,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  HistoryOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { workflowApi } from '../../api/taoyuan/workflow';
import { TAOYUAN_CONTRACT, MILESTONE_LABEL_MAP, MILESTONE_COLOR_MAP, BATCH_CLOSE_COLORS } from '../../constants/taoyuanOptions';
import { useResponsive } from '../../hooks';

import { WorkflowFilters, type WorkflowFilterValues } from './WorkflowFilters';
import { WorkflowTimeline } from './WorkflowTimeline';
import { WorkRecordFormModal } from './WorkRecordFormModal';
import type { WorkRecord, WorkRecordCreate, WorkRecordUpdate, ProjectWorkflowSummary } from '../../types/taoyuan';

const { Title, Text } = Typography;

// ── 主頁面元件 ────────────────────────────────────────────
export const ProjectWorkflowPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // 篩選
  const [filters, setFilters] = useState<WorkflowFilterValues>({});
  const resetFilters = () => setFilters({});

  // Modal 狀態
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<WorkRecord | null>(null);
  const [activeProject, setActiveProject] = useState<{ dispatchOrderId?: number; projectId?: number }>({});

  // ── 資料查詢 ──
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['workflow-summary', filters],
    queryFn: () => workflowApi.getProjectSummary({
      contract_project_id: TAOYUAN_CONTRACT.PROJECT_ID,
      district: filters.district,
      search: filters.search,
      batch_close_no: filters.batch_close_no,
    }),
    staleTime: 30_000,
  });

  const summaries: ProjectWorkflowSummary[] = data?.items ?? [];

  // ── 建立 / 更新 / 刪除 Mutations ──
  const createMut = useMutation({
    mutationFn: (d: WorkRecordCreate) => workflowApi.createRecord(d),
    onSuccess: () => {
      message.success('歷程紀錄已建立');
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
      setModalOpen(false);
    },
    onError: () => message.error('建立失敗'),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: WorkRecordUpdate }) =>
      workflowApi.updateRecord(id, data),
    onSuccess: () => {
      message.success('歷程紀錄已更新');
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
      setModalOpen(false);
      setEditingRecord(null);
    },
    onError: () => message.error('更新失敗'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => workflowApi.deleteRecord(id),
    onSuccess: () => {
      message.success('歷程紀錄已刪除');
      queryClient.invalidateQueries({ queryKey: ['workflow-summary'] });
    },
    onError: () => message.error('刪除失敗'),
  });

  // ── 事件處理 ──
  const handleAdd = useCallback((projectId?: number, dispatchOrderId?: number) => {
    setEditingRecord(null);
    setActiveProject({ projectId, dispatchOrderId });
    setModalOpen(true);
  }, []);

  const handleEdit = useCallback((rec: WorkRecord) => {
    setEditingRecord(rec);
    setActiveProject({
      projectId: rec.taoyuan_project_id,
      dispatchOrderId: rec.dispatch_order_id,
    });
    setModalOpen(true);
  }, []);

  const handleDelete = useCallback((rec: WorkRecord) => {
    deleteMut.mutate(rec.id);
  }, [deleteMut]);

  const handleSubmit = async (payload: WorkRecordCreate | WorkRecordUpdate) => {
    if (editingRecord) {
      await updateMut.mutateAsync({ id: editingRecord.id, data: payload as WorkRecordUpdate });
    } else {
      await createMut.mutateAsync(payload as WorkRecordCreate);
    }
  };

  // ── 渲染 ──
  return (
    <div style={{ padding: pagePadding }}>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <Space>
          <HistoryOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          <Title level={4} style={{ margin: 0 }}>工程歷程追蹤</Title>
          <Tag color="blue">{TAOYUAN_CONTRACT.NAME.substring(0, 20)}...</Tag>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isLoading}>
            重新整理
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAdd()}>
            新增歷程
          </Button>
        </Space>
      </div>

      {/* 篩選列 */}
      <WorkflowFilters values={filters} onChange={setFilters} onReset={resetFilters} loading={isLoading} />

      {/* 主體列表 */}
      <Spin spinning={isLoading}>
        {summaries.length === 0 ? (
          <Card>
            <Empty description="尚無工程歷程資料" />
          </Card>
        ) : (
          <Collapse
            accordion
            size="large"
            items={summaries.map((proj) => ({
              key: String(proj.project_id),
              label: (
                <Space size={8} wrap>
                  <Text strong>
                    {proj.sequence_no ? `${proj.sequence_no}. ` : ''}
                    {proj.project_name}
                  </Text>
                  {proj.sub_case_name && <Text type="secondary">({proj.sub_case_name})</Text>}
                  {proj.batch_close_no && (
                    <Tag
                      color={BATCH_CLOSE_COLORS[proj.batch_close_no] || '#888'}
                      style={{ borderRadius: 10 }}
                    >
                      第 {proj.batch_close_no} 批
                    </Tag>
                  )}
                  {proj.district && <Tag>{proj.district}</Tag>}
                  <Text type="secondary">
                    歷程 {proj.total_records} | 來文 {proj.total_incoming_docs} | 發文 {proj.total_outgoing_docs}
                  </Text>
                  {proj.current_stage && (
                    <Tag color={MILESTONE_COLOR_MAP[proj.current_stage] || 'default'}>
                      {MILESTONE_LABEL_MAP[proj.current_stage] || proj.current_stage}
                    </Tag>
                  )}
                </Space>
              ),
              extra: (
                <Button
                  type="link"
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAdd(proj.project_id);
                  }}
                >
                  新增
                </Button>
              ),
              children: (
                <Tabs
                  defaultActiveKey="timeline"
                  size="small"
                  items={[
                    {
                      key: 'timeline',
                      label: '歷程時間軸',
                      children: (
                        <WorkflowTimeline
                          records={proj.records || []}
                          onEdit={handleEdit}
                          onDelete={handleDelete}
                        />
                      ),
                    },
                    {
                      key: 'info',
                      label: '工程資訊',
                      children: (
                        <div>
                          <Text type="secondary">
                            承辦人：{proj.case_handler || '—'} ｜
                            最後紀錄：{proj.last_record_date || '—'}
                          </Text>
                        </div>
                      ),
                    },
                  ]}
                />
              ),
            }))}
          />
        )}
      </Spin>

      {/* 新增/編輯 Modal */}
      <WorkRecordFormModal
        open={modalOpen}
        record={editingRecord}
        dispatchOrderId={activeProject.dispatchOrderId}
        projectId={activeProject.projectId}
        onSubmit={handleSubmit}
        onCancel={() => { setModalOpen(false); setEditingRecord(null); }}
        loading={createMut.isPending || updateMut.isPending}
      />
    </div>
  );
};

export default ProjectWorkflowPage;
''')

    log(f"已建立 5 個頁面元件於 pages/taoyuanWorkflow/", "OK")
    return True


# ============================================================================
# Step 7: 更新路由設定
# ============================================================================

def step7_update_router():
    print("\n🔹 Step 7: 更新路由設定")

    # 7a: router/types.ts — 加入 ROUTES
    types_file = os.path.join(FRONTEND_SRC, "router", "types.ts")
    with open(types_file, "r", encoding="utf-8") as f:
        content = f.read()

    if "TAOYUAN_WORKFLOW" in content:
        log("TAOYUAN_WORKFLOW 路由已存在，跳過", "SKIP")
    else:
        backup_file(types_file)
        # 在 TAOYUAN_PROJECT_DETAIL 後插入
        content = content.replace(
            "  TAOYUAN_PROJECT_DETAIL: '/taoyuan/project/:id',",
            "  TAOYUAN_PROJECT_DETAIL: '/taoyuan/project/:id',\n  TAOYUAN_WORKFLOW: '/taoyuan/workflow',"
        )
        # 在 ROUTE_META 中加入
        meta_insert = '''  [ROUTES.TAOYUAN_WORKFLOW]: {
    title: '工程歷程',
    description: '桃園查估專區 - 工程歷程追蹤',
    icon: 'HistoryOutlined',
  },'''
        content = content.replace(
            "  [ROUTES.TAOYUAN_DISPATCH_CREATE]: {",
            meta_insert + "\n  [ROUTES.TAOYUAN_DISPATCH_CREATE]: {"
        )
        with open(types_file, "w", encoding="utf-8") as f:
            f.write(content)
        log("已更新 router/types.ts", "OK")

    # 7b: router/AppRouter.tsx — 加入懶載入 + Route
    router_file = os.path.join(FRONTEND_SRC, "router", "AppRouter.tsx")
    with open(router_file, "r", encoding="utf-8") as f:
        content = f.read()

    if "ProjectWorkflowPage" in content:
        log("ProjectWorkflowPage 路由已存在，跳過", "SKIP")
    else:
        backup_file(router_file)

        # 加入 lazy import (在桃園查估專區區塊後)
        content = content.replace(
            "const TaoyuanProjectDetailPage = lazy(() => import('../pages/TaoyuanProjectDetailPage'));",
            "const TaoyuanProjectDetailPage = lazy(() => import('../pages/TaoyuanProjectDetailPage'));\nconst ProjectWorkflowPage = lazy(() => import('../pages/taoyuanWorkflow/ProjectWorkflowPage'));"
        )

        # 加入 Route (在桃園查估路由區塊後)
        content = content.replace(
            "          <Route path={ROUTES.TAOYUAN_PROJECT_DETAIL} element={<ProtectedRoute><TaoyuanProjectDetailPage /></ProtectedRoute>} />",
            "          <Route path={ROUTES.TAOYUAN_PROJECT_DETAIL} element={<ProtectedRoute><TaoyuanProjectDetailPage /></ProtectedRoute>} />\n          <Route path={ROUTES.TAOYUAN_WORKFLOW} element={<ProtectedRoute><ProjectWorkflowPage /></ProtectedRoute>} />"
        )

        with open(router_file, "w", encoding="utf-8") as f:
            f.write(content)
        log("已更新 router/AppRouter.tsx", "OK")

    return True


# ============================================================================
# Step 8: 驗證
# ============================================================================

def step8_verify():
    print("\n🔹 Step 8: 驗證檔案完整性")
    checks = [
        ("types/taoyuan.ts 含 WorkRecord", "types/taoyuan.ts", "WorkRecord"),
        ("constants 含 MILESTONE_TYPE_OPTIONS", "constants/taoyuanOptions.ts", "MILESTONE_TYPE_OPTIONS"),
        ("endpoints 含 WORKFLOW_CONSTANTS", "api/endpoints.ts", "WORKFLOW_CONSTANTS"),
        ("api/taoyuan/workflow.ts 存在", "api/taoyuan/workflow.ts", None),
        ("api/taoyuan/index.ts 含 workflowApi", "api/taoyuan/index.ts", "workflowApi"),
        ("pages/taoyuanWorkflow/index.ts 存在", "pages/taoyuanWorkflow/index.ts", None),
        ("pages/taoyuanWorkflow/ProjectWorkflowPage.tsx 存在", "pages/taoyuanWorkflow/ProjectWorkflowPage.tsx", None),
        ("pages/taoyuanWorkflow/WorkflowTimeline.tsx 存在", "pages/taoyuanWorkflow/WorkflowTimeline.tsx", None),
        ("pages/taoyuanWorkflow/WorkRecordFormModal.tsx 存在", "pages/taoyuanWorkflow/WorkRecordFormModal.tsx", None),
        ("pages/taoyuanWorkflow/WorkflowFilters.tsx 存在", "pages/taoyuanWorkflow/WorkflowFilters.tsx", None),
        ("router/types.ts 含 TAOYUAN_WORKFLOW", "router/types.ts", "TAOYUAN_WORKFLOW"),
        ("AppRouter.tsx 含 ProjectWorkflowPage", "router/AppRouter.tsx", "ProjectWorkflowPage"),
    ]

    ok_count = 0
    for label, rel_path, keyword in checks:
        fpath = os.path.join(FRONTEND_SRC, rel_path)
        if not os.path.exists(fpath):
            log(f"✗ {label} — 檔案不存在", "ERR")
            continue
        if keyword:
            with open(fpath, "r", encoding="utf-8") as f:
                if keyword not in f.read():
                    log(f"✗ {label} — 關鍵字 '{keyword}' 未找到", "ERR")
                    continue
        log(f"✓ {label}", "OK")
        ok_count += 1

    print(f"\n  驗證結果: {ok_count}/{len(checks)} 通過")
    return ok_count == len(checks)


# ============================================================================
# 主程序
# ============================================================================

def main():
    print("=" * 60)
    print("  Phase 2: 前端整合自動化腳本")
    print("  工程歷程追蹤 (Workflow) 前端模組")
    print(f"  執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 確認路徑
    if not os.path.isdir(FRONTEND_SRC):
        print(f"\n❌ 前端目錄不存在: {FRONTEND_SRC}")
        sys.exit(1)

    print(f"\n📂 前端目錄: {FRONTEND_SRC}")
    print(f"📂 備份目錄: {BACKUP_DIR}")

    steps = [
        ("Step 1: 新增型別定義", step1_add_types),
        ("Step 2: 新增常數定義", step2_add_constants),
        ("Step 3: 新增 API 端點", step3_add_endpoints),
        ("Step 4: 建立 API 模組", step4_create_api_module),
        ("Step 5: 更新 API 入口", step5_update_api_index),
        ("Step 6: 建立頁面元件", step6_create_page_components),
        ("Step 7: 更新路由設定", step7_update_router),
        ("Step 8: 驗證完整性", step8_verify),
    ]

    for name, func in steps:
        try:
            result = func()
            if not result:
                log(f"{name} 未完全成功", "WARN")
        except Exception as e:
            log(f"{name} 執行失敗: {e}", "ERR")
            import traceback
            traceback.print_exc()

    # 統計
    ok = sum(1 for l, _ in RESULTS if l == "OK")
    warn = sum(1 for l, _ in RESULTS if l == "WARN")
    err = sum(1 for l, _ in RESULTS if l == "ERR")
    skip = sum(1 for l, _ in RESULTS if l == "SKIP")

    print("\n" + "=" * 60)
    print("  執行結果總結")
    print("=" * 60)
    print(f"  ✅ 成功: {ok}")
    print(f"  ⏭️ 跳過: {skip}")
    print(f"  ⚠️ 警告: {warn}")
    print(f"  ❌ 錯誤: {err}")
    print()

    if err == 0:
        print("  🎉 Phase 2 前端整合完成！")
        print()
        print("  📌 後續步驟:")
        print("    1. cd frontend && npm run build  (確認編譯通過)")
        print("    2. 開啟 http://localhost:3000/taoyuan/workflow 確認頁面")
        print("    3. 確認先執行 Phase 1 後端腳本 (API 端點需存在)")
        print()
        print("  📂 新增/修改檔案:")
        print("    [修改] types/taoyuan.ts")
        print("    [修改] constants/taoyuanOptions.ts")
        print("    [修改] api/endpoints.ts")
        print("    [新增] api/taoyuan/workflow.ts")
        print("    [修改] api/taoyuan/index.ts")
        print("    [新增] pages/taoyuanWorkflow/ (5 個檔案)")
        print("    [修改] router/types.ts")
        print("    [修改] router/AppRouter.tsx")
    else:
        print("  ⚠️ 有錯誤發生，請檢查上方訊息")

    print()


if __name__ == "__main__":
    main()
