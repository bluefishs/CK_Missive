/**
 * ERP 報價/成本管理列表頁面
 */
import React, { useState } from 'react';
import { Card, Button, Space, Input, Select, Typography, Row, Col, Alert, App, Upload, Tag } from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import { PlusOutlined, ReloadOutlined, DownloadOutlined, UploadOutlined, FileExcelOutlined, DollarOutlined, FundOutlined, BankOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { erpQuotationsApi } from '../api/erp';
import { useNavigate } from 'react-router-dom';
import { useERPQuotations, useERPProfitSummary, useAuthGuard } from '../hooks';
import type { ERPQuotation, ERPQuotationListParams } from '../types/erp';
import { erpQuotationStatusLabel, erpQuotationStatusColor } from '../types/erp';
import type { ResponsiveColumn } from '../components/common/EnhancedTable';
import { ROUTES } from '../router/types';
import { ClickableStatCard } from '../components/common';
import { getErrorMessage } from '../utils/apiErrorParser';

const { Title, Text } = Typography;

// development-rules §2.6 ③：列表以**當年度**為統計基準；§2.5：紀年一律西元。
// 2026-08-29 複查發現本頁**完全沒有年度篩選 UI** —— `params.year` 只在匯出時
// 用得到，於是列表把所有年度混在一起，統計卡也是歷年總和。
const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = [
  { value: 0, label: '全部年度' },
  ...Array.from({ length: 5 }, (_, i) => {
    const y = CURRENT_YEAR - i;
    return { value: y, label: `${y} 年` };
  }),
];

export const ERPQuotationListPage: React.FC = () => {
  const navigate = useNavigate();
  const { message, modal } = App.useApp();
  const { hasPermission } = useAuthGuard();
  // 2026-08-27：原本用 `projects:write` 守著，而那個名字**不存在於任何地方**
  //   （沒有角色擁有、兩份 SSOT 都沒有）⇒ 只有 superuser 看得到這些按鈕，
  //   admin 與業務同仁都看不到。
  //
  //   ⚠️ 改成 `projects:edit` **不會放寬任何 API 存取** ——
  //   這一頁對應的後端端點全部只有 `require_auth`（實測：quotations 5 支、
  //   pm/cases 1 支，零個 require_admin／require_permission）
  //   ⇒ 任何登入者本來就打得到那些 API。前端的守衛只是在隱藏入口，
  //   而它隱藏的對象包含本來就有權限的人。
  //
  //   為什麼是 `projects:edit`：它是最接近的**既有**權限（admin／staff／ops 擁有），
  //   而報價單與 PM 案件在資料模型上都掛在承攬案件之下（case_code 橋接）。
  //   「新增」動作刻意用同一個守衛而不是 `projects:create`（admin 專屬）——
  //   因為後端沒有做這個區分，前端多做一層會再製造一次「前後端不一致」。
  //
  //   ⚠️ 這是**過渡對齊**，不是最終答案。正解是 `quotations:*` / `pm:*` 自己的
  //   權限詞彙，那需要 owner 決定（A23 後續）。在那之前，這個對齊讓畫面
  //   與後端說同一件事。
  const canWrite = hasPermission('projects:edit');
  const [statFilter, setStatFilter] = useState<string | null>(null);
  const [params, setParams] = useState<ERPQuotationListParams>({ page: 1, limit: 20, sort_by: 'year', sort_order: 'desc', year: CURRENT_YEAR });
  const { data, isLoading, isError, refetch } = useERPQuotations(params);
  // ⚠️ 統計卡必須跟著年度篩選走，否則會出現「列表 92 筆／卡片 257 筆」的
  // 不一致 —— 那比沒有年度篩選更糟：兩個數字都在畫面上，而使用者無從
  // 判斷哪一個才是他要的。後端 get_profit_summary 本來就收 year，
  // 是前端沒傳（同「送出的與收到的不一致」家族）。
  const { data: profitSummary } = useERPProfitSummary({ year: params.year });
  // 2026-08-15：刪除改由詳情頁提供（對照 /documents 的導航設計），
  // 列表不再持有刪除能力，故 useDeleteERPQuotation 與 handleDelete 一併移除。

  // 前端過濾：僅顯示已承攬

  const columns: ResponsiveColumn<ERPQuotation>[] = [
    { title: '案號', key: 'project_code', width: 160, render: (_: unknown, r: ERPQuotation) => r.project_code || r.case_code },
    {
      title: '案名',
      dataIndex: 'case_name',
      key: 'case_name',
      ellipsis: true,
      render: (text: string | null) => <strong>{text ?? '-'}</strong>,
    },
    // 2026-08-19 owner：「報價單要能對應填報者」。
    //
    // `created_by` 一直存在於資料表，但**77 張全是 NULL**（端點建立時
    // 沒把使用者傳進去，08-19 已修 ⇒ 之後新建的才有），而且它只是一個
    // user id —— 就算顯示也只是個數字。後端補了 `created_by_name`，
    // 這裡才看得到人。
    //
    // 舊資料顯示「—」是誠實的：那些是修法之前建立的，系統當時沒有記錄
    // 是誰填的，寫任何名字上去都是編的。
    // 承辦同仁在填報者前面：找案子時問的是「這是誰的案子」，
    // 而不是「誰把它打進系統」。（owner 2026-08-21：服務人員＝承辦同仁）
    {
      title: '承辦同仁',
      dataIndex: 'staff_name',
      key: 'staff_name',
      width: 110,
      render: (v: string | null) => v || <span style={{ color: '#999' }}>—</span>,
    },
    {
      title: '填報者',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
      width: 110,
      render: (v: string | null) => v || <span style={{ color: '#999' }}>—</span>,
    },
    // 舊案號（個人管理時期，B114-B002）—— 與紙本、回簽 PDF 檔名對得起來的那組編號
    {
      title: '舊案號',
      dataIndex: 'legacy_quotation_no',
      key: 'legacy_quotation_no',
      width: 130,
      render: (v: string | null) => v || <span style={{ color: '#999' }}>—</span>,
    },
    // 2026-08-15：補上「狀態」欄。
    // owner 回報「表格無提供篩選」—— 實測排序圖示 12 個、篩選漏斗 **0 個**。
    // 真因不是 enhanceColumns 沒生效，是**列表根本沒有狀態欄**：
    // enhanceColumns 只對 STATUS_KEYS 類欄位自動加篩選，沒有那個欄位就沒有篩選。
    // 而狀態（草稿／已確認／修訂中／已結案）是主要業務屬性，看不到本來就不合理。
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 100, align: 'center',
      render: (v?: string) => <Tag color={erpQuotationStatusColor(v)}>{erpQuotationStatusLabel(v)}</Tag>,
    },
    { title: '年度', hideOnMobile: true, dataIndex: 'year', key: 'year', width: 80, align: 'center', render: (v?: number) => v ? (v < 1911 ? v + 1911 : v) : '-' },
    {
      title: '總價',
      dataIndex: 'total_price',
      key: 'total_price',
      width: 120,
      align: 'right',
      render: (v: string | null) => v ? Number(v).toLocaleString() : '-',
    },
    {
      title: '毛利',
      hideOnMobile: true, dataIndex: 'gross_profit',
      key: 'gross_profit',
      width: 120,
      align: 'right',
      render: (v: string) => {
        const num = Number(v);
        return <span style={{ color: num >= 0 ? '#52c41a' : '#ff4d4f' }}>{num.toLocaleString()}</span>;
      },
    },
    {
      title: '毛利率',
      hideOnMobile: true, dataIndex: 'gross_margin',
      key: 'gross_margin',
      width: 90,
      align: 'right',
      render: (v: string | null) => v ? `${Number(v).toFixed(1)}%` : '-',
    },
    // 2026-08-15 移除「操作」欄（詳情／編輯／刪除）。
    // 對照 `/documents` 列表：它沒有操作欄 —— 點列進詳情，所有操作在詳情頁。
    // 這三顆在報價詳情頁本來就有，列表這一欄是重複的；
    // 而且每一顆都要 stopPropagation 才不會和點列進詳情打架，
    // 那個 stopPropagation 本身就是「這一欄不該在這裡」的訊號。
    // 點列進詳情由下方 onRow 提供。
  ];

  const grossProfit = profitSummary ? Number(profitSummary.total_gross_profit) : 0;

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          {/* 2026-08-27 階段 1（QUOTATION_PHASE_POSITIONING §5）：
              標題原本是「財務管理 (ERP)」，而這一頁七成的內容是**還沒確認承攬**的報價
              （256 張裡 178 張對應的 PM 案件沒有 project_code）。
              ERP 是確認承攬「之後」的程序，用它當標題等於把位階講反了。
              選單同步移到「專案管理」底下並更名為「報價單總覽」。
              ⚠️ 路由與 API 前綴**刻意不動**（階段 2 才處理，且需 owner 先定階段 0 判準）。*/}
          <Col>
            <Title level={3} style={{ margin: 0 }}>報價單總覽</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              跨案件檢視 —— 建立與線上填寫明細請至各案件的「邀標報價」頁
            </Text>
          </Col>
          <Col>
            {/* 2026-08-27 owner：「/erp/quotations 首頁也不應該有新增報價鈕，
                都要在邀標報價程序」⇒ 建立入口只留在 PM 案件頁。

                ⚠️ 刻意留一個**指路**而不是整個拿掉：這一頁一直是大家找報價的地方，
                按鈕忽然不見會變成「功能沒了」而不是「換地方了」——
                本專案已經有過同型（空清單退化成數字、標案查無資料沒說出真正原因）。
                它是連結不是動作，不受 canWrite 影響（找路不需要權限）。 */}
            <Button
              type="link"
              icon={<PlusOutlined />}
              onClick={() => navigate(ROUTES.PM_CASES)}
            >
              新增報價請至「邀標報價案件」
            </Button>
          </Col>
        </Row>
        {profitSummary && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="營收總額"
                value={Number(profitSummary.total_revenue).toLocaleString()}
                icon={<DollarOutlined />}
                color="#1890ff"
                active={statFilter === 'revenue'}
                onClick={() => setStatFilter(statFilter === 'revenue' ? null : 'revenue')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="成本總額"
                value={Number(profitSummary.total_cost).toLocaleString()}
                icon={<BankOutlined />}
                color="#faad14"
                active={statFilter === 'cost'}
                onClick={() => setStatFilter(statFilter === 'cost' ? null : 'cost')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="毛利"
                value={grossProfit.toLocaleString()}
                icon={<FundOutlined />}
                color={grossProfit >= 0 ? '#3f8600' : '#cf1322'}
                active={statFilter === 'profit'}
                onClick={() => setStatFilter(statFilter === 'profit' ? null : 'profit')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="應收未收"
                value={Number(profitSummary.total_outstanding).toLocaleString()}
                icon={<ExclamationCircleOutlined />}
                color="#ff4d4f"
                active={statFilter === 'outstanding'}
                onClick={() => setStatFilter(statFilter === 'outstanding' ? null : 'outstanding')}
              />
            </Col>
          </Row>
        )}
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜尋案號/案名"
            allowClear
            onSearch={(v) => setParams((p) => ({ ...p, search: v || undefined, page: 1 }))}
            style={{ width: 240 }}
          />
          <Select
            value={params.year ?? 0}
            onChange={(v) => setParams((p) => ({ ...p, year: v || undefined, page: 1 }))}
            options={YEAR_OPTIONS}
            style={{ width: 130 }}
            aria-label="年度"
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
          <Button
            icon={<FileExcelOutlined />}
            onClick={async () => {
              try {
                const blob = await erpQuotationsApi.exportExcel({ year: params.year });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'erp_quotations.xlsx';
                a.click();
                URL.revokeObjectURL(url);
                message.success('匯出成功');
              } catch (e) { message.error(getErrorMessage(e, '匯出失敗'), 8); }
            }}
          >匯出 Excel</Button>
          {canWrite && (
            <>
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    const result = await erpQuotationsApi.importExcel(file);
                    message.success(`匯入完成: 新增 ${result.created} 筆, 更新 ${result.updated} 筆`);
                    if (result.errors?.length) {
                      message.warning(`${result.errors.length} 筆匯入失敗`);
                    }
                    refetch();
                  } catch (e) { message.error(getErrorMessage(e, '匯入失敗'), 8); }
                  return false;
                }}
              >
                <Button icon={<UploadOutlined />}>匯入 Excel</Button>
              </Upload>
              {/* owner 2026-08-19：「若線上產出報價單未完全上線前，如何匯入與管理
                  既有 XLS 為目前階段重點」「新增與更新整合為一個按鍵鈕」。
                  依舊案號（B114-B002）upsert —— 有就更新、沒有就新增，
                  使用者不需要先知道 277 列裡哪些已在系統。
                  按下去**先預覽再確認**：這是第一次把數百筆業務資料寫進系統。 */}
              <Upload
                accept=".xlsx"
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    message.loading({ content: '解析中...', key: 'legacy' });
                    const p = await erpQuotationsApi.importLegacy(file, true);
                    message.destroy('legacy');
                    modal.confirm({
                      title: '匯入既有報價單彙整',
                      width: 560,
                      content: (
                        <div>
                          <p>共讀到 <b>{p.total_rows}</b> 列：</p>
                          <ul>
                            <li>將<b>新增 {p.will_create}</b> 筆</li>
                            <li>將<b>更新 {p.will_update}</b> 筆（依舊案號比對到既有資料）</li>
                            {p.skipped > 0 && <li>略過 {p.skipped} 筆（檔案內重複或缺案名）</li>}
                          </ul>
                          {/* 2026-08-27：08-20 那次匯入靜靜建出 26 件分身 ——
                              既有 `B114-B003`、彙整表帶 `B114-B003-0`，
                              case_code 不同故判為「不存在」而再建一件。
                              事後查證那 26 組兩側**案名完全相同**，且有碼那一側全部都有金流。
                              ⚠️ 只提醒不阻擋：實測另有 4 組同形態但案名完全不同
                              （B114-B026「平鎮區查估」vs B114-B026-0「永翠76透地雷達」），
                              合併與否要看案名與金額語意，是人的判斷。 */}
                          {(p.duplicate_candidate_count ?? 0) > 0 && (
                            <Alert
                              type="warning"
                              showIcon
                              style={{ marginBottom: 8 }}
                              message={`有 ${p.duplicate_candidate_count} 筆可能是既有案件的分身`}
                              description={
                                <div>
                                  <div style={{ marginBottom: 4 }}>
                                    這些新案號與既有案件<b>只差版次尾碼，且案名完全相同</b>：
                                  </div>
                                  {(p.duplicate_candidates ?? []).slice(0, 5).map((d) => (
                                    <div key={d.new_case_code} style={{ fontSize: 12 }}>
                                      · <b>{d.new_case_code}</b> ← 既有 {d.existing_case_code}
                                      {' '}— {d.case_name}
                                    </div>
                                  ))}
                                  {(p.duplicate_candidate_count ?? 0) > 5 && (
                                    <div style={{ fontSize: 12 }}>
                                      …其餘 {(p.duplicate_candidate_count ?? 0) - 5} 筆
                                    </div>
                                  )}
                                  <div style={{ marginTop: 4 }}>
                                    仍會建立（系統不自動合併）——確認是同一件的話，匯入後請自行處理。
                                  </div>
                                </div>
                              }
                            />
                          )}
                          {(p.skipped_detail?.length ?? 0) > 0 && (
                            <Alert type="warning" showIcon message="略過明細"
                              description={p.skipped_detail!.slice(0, 5)
                                .map(x => `${x.legacy_no}：${x.reason}`).join('；')} />
                          )}
                        </div>
                      ),
                      okText: '確認寫入', cancelText: '取消',
                      onOk: async () => {
                        const r = await erpQuotationsApi.importLegacy(file, false);
                        message.success(`匯入完成：新增 ${r.created} 筆、更新 ${r.updated} 筆`);
                        refetch();
                      },
                    });
                  } catch {
                    message.destroy('legacy');
                    message.error('彙整表解析失敗');
                  }
                  return false;
                }}
              >
                <Button icon={<FileExcelOutlined />}>匯入彙整表（舊案號）</Button>
              </Upload>
              {/* owner 2026-08-19：「產生報價單只是步驟一，其需將客戶回簽檔案
                  上傳確認才正式完成邀標報價承攬」。
                  檔名就是對應關係：回簽報價單_<舊案號>_<客戶>_<標的>_<項目>.pdf
                  ⚠️ 相依：要先匯入彙整表（系統才有舊案號可比對），
                  否則會全部回報「找不到舊案號」—— 訊息會講清楚，不會靜靜跳過。 */}
              <Upload
                accept=".pdf"
                multiple
                showUploadList={false}
                beforeUpload={() => false}
                onChange={async (info) => {
                  // AntD 的 originFileObj 型別是 RcFile（File 的子型別，多了 uid），
                  // 這裡只需要當成 File 傳給 FormData
                  const files: File[] = info.fileList
                    .map((f) => f.originFileObj)
                    .filter(Boolean) as unknown as File[];
                  if (files.length !== info.fileList.length) return;
                  try {
                    message.loading({ content: '比對中...', key: 'signed' });
                    const p = await erpQuotationsApi.importSigned(files, true);
                    message.destroy('signed');
                    modal.confirm({
                      title: '匯入客戶回簽報價單',
                      width: 620,
                      content: (
                        <div>
                          <p>共 <b>{p.total_files}</b> 個檔案：</p>
                          <ul>
                            <li>可掛回 <b>{p.will_attach}</b> 份</li>
                            {p.unmatched > 0 && <li>對不上 {p.unmatched} 份</li>}
                          </ul>
                          {(p.unmatched_detail?.length ?? 0) > 0 && (
                            <Alert type="warning" showIcon message="對不上的檔案"
                              description={
                                <ul style={{ margin: 0, paddingLeft: 18 }}>
                                  {p.unmatched_detail!.slice(0, 5).map((u) => (
                                    <li key={u.file_name}>{u.file_name}：{u.reason}</li>
                                  ))}
                                </ul>
                              } />
                          )}
                        </div>
                      ),
                      okText: '確認掛回', cancelText: '取消',
                      okButtonProps: { disabled: p.will_attach === 0 },
                      onOk: async () => {
                        const r = await erpQuotationsApi.importSigned(files, false);
                        message.success(`回簽掛回完成：${r.attached} 份`);
                        refetch();
                      },
                    });
                  } catch {
                    message.destroy('signed');
                    message.error('回簽檔解析失敗');
                  }
                }}
              >
                <Button icon={<UploadOutlined />}>匯入客戶回簽</Button>
              </Upload>
              <Button
                icon={<DownloadOutlined />}
                onClick={async () => {
                  try {
                    const blob = await erpQuotationsApi.downloadTemplate();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'erp_quotation_template.xlsx';
                    a.click();
                    URL.revokeObjectURL(url);
                  } catch (e) { message.error(getErrorMessage(e, '下載範本失敗'), 8); }
                }}
              >下載範本</Button>
            </>
          )}
        </Space>

        <EnhancedTable<ERPQuotation>
          columns={columns}
          dataSource={data?.items ?? []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: params.page,
            pageSize: params.limit,
            total: data?.pagination?.total ?? 0,
            onChange: (page, pageSize) => setParams((p) => ({ ...p, page, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.id))),
            style: { cursor: 'pointer' },
          })}
          size="middle"
          scroll={{ x: 1000 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPQuotationListPage;
