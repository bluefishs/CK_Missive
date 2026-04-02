/**
 * 標案檢索型別定義
 */

export interface TenderRecord {
  date: string;
  raw_date: number;
  title: string;
  type: string;
  category: string;
  unit_id: string;
  unit_name: string;
  job_number: string;
  company_names: string[];
  company_ids: string[];
  winner_names: string[];
  bidder_names: string[];
  tender_api_url: string;
  matched_keyword?: string;
}

export interface TenderSearchResult {
  query: string;
  page: number;
  total_records: number;
  total_pages: number;
  records: TenderRecord[];
}

export interface TenderDetailEvent {
  date: number;
  type: string;
  title: string;
  category: string;
  job_number: string;
  detail: {
    agency_name: string;
    agency_unit: string;
    agency_address: string;
    contact_person: string;
    contact_phone: string;
    contact_email: string;
    budget: string;
    procurement_type: string;
    method: string;
    award_method: string;
    announce_date: string;
    deadline: string;
    open_date: string;
    status: string;
    pcc_url: string;
  };
  companies: string[];
}

export interface TenderDetail {
  unit_name: string;
  job_number: string;
  title: string;
  events: TenderDetailEvent[];
  latest: TenderDetailEvent | null;
}

export interface TenderRecommendResult {
  keywords: string[];
  total: number;
  records: TenderRecord[];
}

export interface TenderSearchParams {
  query: string;
  page?: number;
  category?: string;
}
