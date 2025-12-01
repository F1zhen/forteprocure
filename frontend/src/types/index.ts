export interface Tender {
  id: number;
  announce_number: string;
  name: string;
  organizer_name: string;
  total_sum: number;
  status: string;
  publish_date: string;
  is_analyzed: boolean;
  risk_score?: number;
}

export interface RiskItem {
  risk_flag: string;
  severity: number;
  explanation: string;
  justification: string;
}

export interface Supplier {
  id?: number;
  general_name?: string;
  name?: string;
  specialty_description?: string;
  activity_description?: string;
  distance?: number;
  external_id?: string;
  bin?: string;
  source_registry?: string;
}

export interface AnalysisData {
  tender_id: number;
  tender: Tender;
  ai_analysis: {
    summary: string;
    key_fields: Record<string, unknown>;
    risk_analysis: RiskItem[];
    technical_analysis: Record<string, unknown>;
    contract_terms_detail: Record<string, unknown>;
    similar_tenders: Array<{
      tender: Tender;
      similarity_score: number;
    }>;
    final_notes: string;
  };
  similar_tenders: Tender[];
  matching_suppliers: Supplier[];
  risk_suppliers: Supplier[];
}