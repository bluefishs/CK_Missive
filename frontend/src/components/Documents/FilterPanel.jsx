import React, { useState, useEffect } from 'react';
import { Card, Form, Row, Col, Input, Select, DatePicker, Button, Space } from 'antd';
import { SearchOutlined, ClearOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { Option } = Select;
const { RangePicker } = DatePicker;

const FilterPanel = ({ onFilter, loading }) => {
  const [form] = Form.useForm();
  const [filters, setFilters] = useState({});

  // 年度選項（最近5年）
  const currentYear = new Date().getFullYear();
  const yearOptions = [];
  for (let i = 0; i < 5; i++) {
    const year = currentYear - i;
    yearOptions.push(year);
  }

  // 表單提交
  const handleSubmit = (values) => {
    const filterData = {
      category: values.category,
      year: values.year,
      doc_word: values.doc_word,
      sender: values.sender,
      receiver: values.receiver,
      contract_case: values.contract_case,
      keyword: values.keyword,
    };

    // 處理日期範圍
    if (values.dateRange && values.dateRange.length === 2) {
      filterData.date_from = values.dateRange[0].format('YYYY-MM-DD');
      filterData.date_to = values.dateRange[1].format('YYYY-MM-DD');
    }

    // 移除空值
    Object.keys(filterData).forEach(key => {
      if (!filterData[key]) {
        delete filterData[key];
      }
    });

    setFilters(filterData);
    onFilter(filterData);
  };

  // 清除篩選
  const handleClear = () => {
    form.resetFields();
    setFilters({});
    onFilter({});
  };

  // 快速篩選按鈕
  const quickFilters = [
    { label: '本年度收文', filters: { category: 'receive', year: currentYear } },
    { label: '本年度發文', filters: { category: 'send', year: currentYear } },
    { label: '本月文件', filters: { date_from: dayjs().startOf('month').format('YYYY-MM-DD'), date_to: dayjs().endOf('month').format('YYYY-MM-DD') } },
  ];

  const handleQuickFilter = (quickFilter) => {
    // 設置表單值
    const formValues = {};
    if (quickFilter.filters.category) formValues.category = quickFilter.filters.category;
    if (quickFilter.filters.year) formValues.year = quickFilter.filters.year;
    if (quickFilter.filters.date_from && quickFilter.filters.date_to) {
      formValues.dateRange = [dayjs(quickFilter.filters.date_from), dayjs(quickFilter.filters.date_to)];
    }
    
    form.setFieldsValue(formValues);
    
    // 執行篩選
    setFilters(quickFilter.filters);
    onFilter(quickFilter.filters);
  };

  return (
    <Card title="篩選查詢" className="filter-panel">
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        autoComplete="off"
      >
        {/* 快速篩選按鈕 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={24}>
            <Space wrap>
              <span style={{ fontWeight: 'bold' }}>快速篩選：</span>
              {quickFilters.map((filter, index) => (
                <Button
                  key={index}
                  size="small"
                  onClick={() => handleQuickFilter(filter)}
                >
                  {filter.label}
                </Button>
              ))}
            </Space>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          {/* 分類 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="分類" name="category">
              <Select placeholder="請選擇分類" allowClear>
                <Option value="receive">收文</Option>
                <Option value="send">發文</Option>
              </Select>
            </Form.Item>
          </Col>

          {/* 年度 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="年度" name="year">
              <Select placeholder="請選擇年度" allowClear>
                {yearOptions.map(year => (
                  <Option key={year} value={year}>{year}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>

          {/* 字號 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="字號" name="doc_word">
              <Input placeholder="請輸入字號" allowClear />
            </Form.Item>
          </Col>

          {/* 發文機關 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="發文機關" name="sender">
              <Input placeholder="請輸入發文機關" allowClear />
            </Form.Item>
          </Col>

          {/* 收文機關 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="收文機關" name="receiver">
              <Input placeholder="請輸入收文機關" allowClear />
            </Form.Item>
          </Col>

          {/* 承攬案件 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="承攬案件" name="contract_case">
              <Input placeholder="請輸入案件名稱" allowClear />
            </Form.Item>
          </Col>

          {/* 日期範圍 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="日期範圍" name="dateRange">
              <RangePicker 
                style={{ width: '100%' }}
                placeholder={['開始日期', '結束日期']}
              />
            </Form.Item>
          </Col>

          {/* 關鍵字搜尋 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="關鍵字" name="keyword">
              <Input placeholder="搜尋主旨、文號等" allowClear />
            </Form.Item>
          </Col>
        </Row>

        {/* 操作按鈕 */}
        <Row>
          <Col span={24}>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SearchOutlined />}
                loading={loading}
              >
                查詢
              </Button>
              <Button
                icon={<ClearOutlined />}
                onClick={handleClear}
              >
                清除
              </Button>
            </Space>
          </Col>
        </Row>
      </Form>
    </Card>
  );
};

export default FilterPanel;
