import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../api/client';
import { logger } from '../../services/logger';

interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code: string;
  business_type: string;
  rating: number;
  contact_person: string;
  phone: string;
  email: string;
}

export const VendorManagement: React.FC = () => {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVendors();
  }, []);

  const fetchVendors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/extended/vendors`);
      const data = await response.json();
      setVendors(data);
    } catch (error) {
      logger.error('Failed to fetch vendors:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>載入中...</div>;
  }

  return (
    <div className="vendor-management">
      <h1>協力廠商管理</h1>
      <div className="vendors-grid">
        {vendors.map(vendor => (
          <div key={vendor.id} className="vendor-card">
            <h3>{vendor.vendor_name}</h3>
            <p>廠商統編: {vendor.vendor_code}</p>
            <p>業務類型: {vendor.business_type}</p>
            <p>評級: {"★".repeat(vendor.rating || 0)}</p>
            {vendor.contact_person && <p>聯絡人: {vendor.contact_person}</p>}
            {vendor.phone && <p>電話: {vendor.phone}</p>}
            {vendor.email && <p>信箱: {vendor.email}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};