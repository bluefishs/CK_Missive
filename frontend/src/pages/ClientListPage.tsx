/**
 * 委託單位管理頁面
 *
 * 複用 VendorList 元件，自動篩選 vendor_type='client'。
 * 與 /vendors (協力廠商) 完全分開顯示。
 *
 * @version 1.0.0
 */
import React from 'react';
import VendorList from '../components/vendor/VendorList';
import { ROUTES } from '../router/types';

const ClientListPage: React.FC = () => {
  return (
    <VendorList
      vendorType="client"
      title="委託單位管理"
      createRoute={ROUTES.CLIENT_CREATE}
    />
  );
};

export default ClientListPage;
