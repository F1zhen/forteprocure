import { Tender, AnalysisData, Supplier } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

interface SearchResponse {
  tenders: Tender[];
  count: number;
}

interface UploadResponse {
  tender_id: number;
  result: {
    summary: string;
    key_fields: Record<string, unknown>;
    risk_analysis: Array<{
      risk_flag: string;
      severity: number;
      explanation: string;
      justification: string;
    }>;
    technical_analysis: Record<string, unknown>;
    contract_terms_detail: Record<string, unknown>;
    similar_tenders: unknown[];
    final_notes: string;
  };
}

interface SupplierRiskResponse {
  bin: string;
  is_risky: boolean;
  registries: Supplier[];
}

export const searchTenders = async (
  keyword: string,
  dateFrom: string,
  dateTo: string
): Promise<Tender[]> => {
  const response = await fetch(
    `${API_URL}/api/tenders/search?query=${keyword}&limit=50`
  );

  if (!response.ok) throw new Error('Failed to search tenders');

  const data: SearchResponse = await response.json();
  let tenders = data.tenders || [];

  if (dateFrom || dateTo) {
    tenders = tenders.filter((t) => {
      const pubDate = new Date(t.publish_date);
      if (dateFrom && pubDate < new Date(dateFrom)) return false;
      if (dateTo && pubDate > new Date(dateTo)) return false;
      return true;
    });
  }

  return tenders;
};

export const analyzeTender = async (tenderId: number): Promise<AnalysisData> => {
  const response = await fetch(
    `${API_URL}/api/tenders/${tenderId}/complete`
  );

  if (!response.ok) throw new Error('Failed to analyze tender');

  return response.json();
};

export const uploadTenderFile = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    `${API_URL}/api/analyze-tender-file`,
    {
      method: 'POST',
      body: formData
    }
  );

  if (!response.ok) throw new Error('Failed to upload file');

  return response.json();
};

export const checkSupplierRisk = async (bin: string): Promise<SupplierRiskResponse> => {
  const response = await fetch(
    `${API_URL}/api/suppliers/check-risk/${encodeURIComponent(bin)}`
  );

  if (!response.ok) throw new Error('Failed to check supplier');

  return response.json();
};