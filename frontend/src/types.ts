export type Box = [number, number, number, number];
export type ExtractedField = {
  name: string;
  value: string | null;
  confidence: number;
  page: number | null;
  quote: string;
  boxes: Box[];
  needs_review: number;
  reviewed: number;
  version: number;
};
export type Document = {
  id: string;
  filename: string;
  status: string;
  stage: string;
  page_count: number;
  processed_pages: number;
  extracted_pages: number;
  attempts: number;
  error: string | null;
  document_type: string;
  fields: ExtractedField[];
  pages?: { number: number; text: string }[];
};
export type Citation = {
  id: number;
  document_id: string;
  filename: string;
  page: number;
  quote: string;
};
export type Answer = { answer: string; citations: Citation[]; mode: string };
export const fieldLabels: Record<string, string> = {
  document_number: "Document number",
  party_a: "Supplier / provider",
  party_b: "Customer",
  total: "Total amount",
  currency: "Currency",
  effective_date: "Issue / effective date",
  due_date: "Due date",
};
