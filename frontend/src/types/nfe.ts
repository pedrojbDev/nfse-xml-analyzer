/**
 * Tipos para dados de NF-e
 */

export interface NFeHeader {
  chave_nfe: string | null;
  numero: number | null;
  serie: number | null;
  data_emissao: string | null;
  natureza_operacao: string | null;
  tipo_nf: number | null;
  ambiente: number | null;
}

export interface NFeParty {
  doc: string | null;
  nome: string | null;
  uf: string | null;
  municipio: string | null;
}

export interface NFeTotals {
  vNF: number | null;
  vProd: number | null;
  vDesc: number | null;
  vFrete: number | null;
  vOutro: number | null;
  vICMS: number | null;
  vICMSST: number | null;
  vIPI: number | null;
  vPIS: number | null;
  vCOFINS: number | null;
}

export interface NFeItem {
  nItem: number | null;
  cProd: string | null;
  xProd: string | null;
  NCM: string | null;
  CFOP: string | null;
  uCom: string | null;
  qCom: number | null;
  vUnCom: number | null;
  vProd: number | null;
  icms_tipo: string | null;
  cst: string | null;
  csosn: string | null;
  vBC: number | null;
  vICMS: number | null;
  pis_tipo: string | null;
  pis_cst: string | null;
  vPIS: number | null;
  cofins_tipo: string | null;
  cofins_cst: string | null;
  vCOFINS: number | null;
}

export interface NFeItemNormalized {
  product_class: string;
  suggested_group: string;
}

export interface NFeItemEnriched {
  item: NFeItem;
  normalized: NFeItemNormalized;
  decision: string;
  reasons: string[];
  norm_flags: Record<string, any>;
  review_level: string;
  review_text_ptbr: string;
  missing_fields: string[];
  confidence: number;
}

export interface NFeDocument {
  document_type: string;
  doc_class: string;
  decision: string;
  review_level: string;
  review_text_ptbr: string;
  reasons: string[];
  next_actions: string[];
  header: NFeHeader;
  emit: NFeParty;
  dest: NFeParty;
  totals: NFeTotals;
  quality: {
    missing_header_keys: string[];
    diff_items_vs_total_vProd: number | null;
    class_meta: Record<string, any>;
    items_review_high: number;
    items_review_medium: number;
    items_incomplete: number;
  };
}

export interface NFeERPProjection {
  movement_type: string;
  filial_code: string | null;
  supplier_doc: string | null;
  note_number: number | null;
  note_serie: number | null;
  issue_datetime: string | null;
  quantity: number;
  unit_value: number | null;
  total_value: number | null;
  product_code: string | null;
  cost_center_suggested: string | null;
  payment_hint: string;
  rm_status_target: string;
}

export interface NFeDocumentSummary {
  doc_class: string;
  decision: string;
  review_level: string;
  review_text_ptbr: string;
  top_reasons: string[];
  kpis: {
    items: number;
    vNF: number | null;
    vProd: number | null;
    diff_items_vs_total_vProd: number | null;
  };
}

export interface NFeSummary {
  count_items: number;
  items_incomplete: number;
  sum_items_vProd: number;
  total_vProd_xml: number | null;
  diff_items_vs_total_vProd: number | null;
  decision_summary: Record<string, number>;
  quality_summary: Record<string, number>;
  review_summary: Record<string, number>;
  document_summary: NFeDocumentSummary | null;
}

export interface NFeExtractResponse {
  received: boolean;
  filename: string;
  sha256: string;
  count: number;
  header: NFeHeader;
  emit: NFeParty;
  dest: NFeParty;
  totals: NFeTotals;
  summary: NFeSummary;
  document: NFeDocument | null;
  erp_projection: NFeERPProjection | null;
  items?: NFeItemEnriched[];
}

/**
 * Status de lançamento da nota
 */
export type NoteLaunchStatus = "pending" | "launched" | "rejected";

/**
 * Informações de lançamento
 */
export interface NoteLaunchInfo {
  status: NoteLaunchStatus;
  launchedAt?: Date;
  launchedBy?: string;
  rejectedAt?: Date;
  rejectedBy?: string;
  rejectionReason?: string;
  notes?: string; // Observações do operador
}

/**
 * Informações da filial associada à nota
 */
export interface NoteFilialInfo {
  codigo: number;         // Código RM da filial
  nome: string;           // Nome fantasia
  cnpj: string;           // CNPJ (apenas dígitos)
  cnpjFormatado: string;  // CNPJ formatado
  municipio: string;
  uf: string;
  tipo: "matriz" | "filial" | "upa" | "aps" | "hospital" | "escritorio" | "clinica";
}

/**
 * Tipo para nota processada na UI
 */
export interface ProcessedNote {
  id: string;
  filename: string;
  data: NFeExtractResponse;
  processedAt: Date;
  // Controle de lançamento
  launchInfo: NoteLaunchInfo;
  // Identificação da filial (baseada no CNPJ do destinatário)
  filial: NoteFilialInfo | null;
}
