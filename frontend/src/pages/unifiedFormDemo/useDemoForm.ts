/**
 * UnifiedFormDemo - 表單邏輯 Hook
 * 管理 demo 數據狀態、表單提交、CSV 導出
 */
import { useState } from 'react';
import { Form } from 'antd';
import type { DemoRecord } from './constants';
import { INITIAL_DEMO_DATA } from './constants';

interface FormValues {
  title: string;
  category: string;
  status?: string;
  priority?: string;
  amount?: number;
}

export function useDemoForm(messageApi: { success: (msg: string) => void; warning: (msg: string) => void }) {
  const [form] = Form.useForm();
  const [demoData, setDemoData] = useState<DemoRecord[]>(INITIAL_DEMO_DATA);
  const [formSequenceNumber, setFormSequenceNumber] = useState('');
  const [formRemarks, setFormRemarks] = useState('');

  const handleFormSubmit = (values: FormValues) => {
    const newRecord: DemoRecord = {
      id: demoData.length + 1,
      sequence_number: formSequenceNumber || '',
      title: values.title,
      category: values.category,
      status: values.status || '待開始',
      priority: values.priority || '中',
      created_date: new Date().toISOString().split('T')[0] ?? '',
      created_by: '當前使用者',
      amount: values.amount ? Number(values.amount) : undefined,
      remarks: formRemarks,
    };

    setDemoData([...demoData, newRecord]);
    form.resetFields();
    setFormSequenceNumber('');
    setFormRemarks('');
    messageApi.success('記錄已新增');
  };

  const handleExport = (filteredData: DemoRecord[]) => {
    const exportData = filteredData.map((item) => ({
      流水號: item.sequence_number,
      標題: item.title,
      類別: item.category,
      狀態: item.status,
      優先級: item.priority,
      金額: item.amount || 0,
      建立日期: item.created_date,
      建立者: item.created_by,
      備註: item.remarks || '',
    }));

    if (exportData.length === 0) {
      messageApi.warning('沒有數據可導出');
      return;
    }
    const csvContent = [
      Object.keys(exportData[0]!).join(','),
      ...exportData.map((row) => Object.values(row).join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `統一表單數據_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    messageApi.success('CSV 文件已導出');
  };

  return {
    form,
    demoData,
    formSequenceNumber,
    setFormSequenceNumber,
    formRemarks,
    setFormRemarks,
    handleFormSubmit,
    handleExport,
  };
}
