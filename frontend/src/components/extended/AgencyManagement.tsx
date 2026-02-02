import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../api/client';
import { logger } from '../../services/logger';

interface Agency {
  id: number;
  agency_name: string;
  agency_code: string;
  agency_type: string;
  contact_person: string;
  phone: string;
  email: string;
}

export const AgencyManagement: React.FC = () => {
  const [agencies, setAgencies] = useState<Agency[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAgencies();
  }, []);

  const fetchAgencies = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/extended/agencies`);
      const data = await response.json();
      setAgencies(data);
    } catch (error) {
      logger.error('Failed to fetch agencies:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>載入中...</div>;
  }

  return (
    <div className="agency-management">
      <h1>機關單位管理</h1>
      <div className="agencies-grid">
        {agencies.map(agency => (
          <div key={agency.id} className="agency-card">
            <h3>{agency.agency_name}</h3>
            <p>機關代碼: {agency.agency_code}</p>
            <p>機關類型: {agency.agency_type}</p>
            {agency.contact_person && <p>聯絡人: {agency.contact_person}</p>}
            {agency.phone && <p>電話: {agency.phone}</p>}
            {agency.email && <p>信箱: {agency.email}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};