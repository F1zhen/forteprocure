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

export interface TechnicalSpec {
  parameter: string;
  value: string;
  notes: string;
}

export interface AIAnalysis {
  summary: string;
  key_fields: {
    title?: string;
    customer?: string;
    budget?: string;
    deadline?: string;
    subject?: string;
    evaluation_criteria?: string;
    technical_requirements?: string;
    qualification_requirements?: string;
    contract_terms?: string;
    previous_suppliers?: string;
  };
  risk_analysis: RiskItem[];
  technical_analysis: {
    document_structure?: string;
    kpi?: string[];
    technical_spec_table?: TechnicalSpec[];
  };
  contract_terms_detail: {
    penalties?: string;
    warranties?: string;
    deadlines?: string;
    other_terms?: string;
  };
  similar_tenders: Array<{
    title?: string;
    price?: string;
    customer?: string;
    status?: string;
    notes?: string;
  }>;
  final_notes: string;
}

export interface Supplier {
  id?: number;
  general_name?: string;
  name?: string;
  first_name?: string;
  last_name?: string;
  middle_name?: string;
  specialty_description?: string;
  activity_description?: string;
  distance?: number;
  external_id?: string;
  bin?: string;
  source_registry?: string;
  reason_code?: string;
  reason_text?: string;
  legal_address?: string;
  register_type?: string;
}

export interface AnalysisData {
  tender_id: number;
  tender: Tender;
  ai_analysis: AIAnalysis;
  similar_tenders: Tender[];
  matching_suppliers: Supplier[];
  risk_suppliers: Supplier[];
}