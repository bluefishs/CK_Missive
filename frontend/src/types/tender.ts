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
  award_details?: TenderAwardDetails;
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

/** 決標品項明細 */
export interface TenderAwardItem {
  item_no: number;
  winner: string | null;
  amount: number | null;
}

/** 決標/價格詳情 (嵌入 TenderDetailEvent) */
export interface TenderAwardDetails {
  award_date: string | null;
  total_award_amount: number | null;
  floor_price: number | null;
  award_items: TenderAwardItem[];
}

/** 底價分析結果 */
export interface TenderPriceAnalysis {
  tender: {
    title: string;
    unit_id: string;
    job_number: string;
    unit_name: string;
  };
  prices: {
    budget: number | null;
    floor_price: number | null;
    award_amount: number | null;
    award_date: string | null;
  };
  analysis: {
    budget_award_variance_pct: number | null;
    floor_award_variance_pct: number | null;
    budget_floor_variance_pct: number | null;
    savings_rate_pct: number | null;
  };
  award_items: TenderAwardItem[];
}

/** 價格統計彙整 */
export interface TenderPriceAgg {
  count: number;
  min: number | null;
  max: number | null;
  avg: number | null;
  median: number | null;
}

/** 價格趨勢結果 */
export interface TenderPriceTrends {
  query: string;
  total: number;
  samples: number;
  stats: {
    budget: TenderPriceAgg;
    floor_price: TenderPriceAgg;
    award_amount: TenderPriceAgg;
    award_rate_pct: number | null;
  };
  distribution: Array<{ range: string; count: number }>;
  entries: Array<{
    title: string;
    date: string;
    unit_name: string;
    budget: number | null;
    floor_price: number | null;
    award_amount: number | null;
  }>;
}
