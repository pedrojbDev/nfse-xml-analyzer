// Tipos para NFS-e (Nota Fiscal de Serviço Eletrônica)

export interface NfseTaxes {
  iss_retido?: number | null;
  base_calculo?: number | null;
  aliquota?: number | null;
  valor_iss?: number | null;
  valor_iss_retido?: number | null;
  valor_deducoes?: number | null;
  valor_pis?: number | null;
  valor_cofins?: number | null;
  valor_inss?: number | null;
  valor_ir?: number | null;
  valor_csll?: number | null;
  outras_retencoes?: number | null;
  desconto_incondicionado?: number | null;
  desconto_condicionado?: number | null;
  valor_liquido_nfse?: number | null;
  valor_liquido_calculado_politica_b?: number | null;
  valor_liquido_diff_xml_vs_calc?: number | null;
  valor_liquido_divergente?: boolean;
}

export interface NfseItemFields {
  numero_nota?: string | null;
  data_emissao?: string | null;
  cnpj_fornecedor?: string | null;
  valor_total?: number | null;
  competencia?: string | null;
  descricao_servico?: string | null;
  cnae?: string | null;
}

export interface NfseItemFlags {
  needs_review?: boolean;
  incomplete?: boolean;
  missing_critical?: boolean;
}

export interface NfseValidationCnae {
  status?: string | null;
  reason?: string | null;
  rule_label?: string | null;
  severity?: string | null;
}

export interface NfseItemValidations {
  cnae_vs_descricao?: NfseValidationCnae;
}

export interface NfseItemNormalized {
  service_class: string;
  suggested_group: string;
  cnae_group?: string | null;
}

export interface NfseItemNormFlags {
  has_minimum_fields?: boolean;
  has_valid_cnae?: boolean;
  has_valid_valor?: boolean;
  valor_liquido_divergente?: boolean;
  requires_review_cnae?: boolean;
}

export interface NfseItem {
  fields: NfseItemFields;
  taxes: NfseTaxes;
  missing_fields?: string[];
  confidence?: number;
  flags?: NfseItemFlags;
  field_sources?: Record<string, string>;
  tax_sources?: Record<string, string>;
  xml_raw?: Record<string, any>;
  validations?: NfseItemValidations;
  decision?: string;
  reasons?: string[];
  
  // Campos da normalização
  normalized?: NfseItemNormalized;
  norm_flags?: NfseItemNormFlags;
  review_level?: string;
  review_text_ptbr?: string;
}

export interface NfsePrestador {
  doc?: string | null;
  doc_formatado?: string | null;
  nome?: string | null;
  razao_social?: string | null;
  nome_fantasia?: string | null;
  inscricao_municipal?: string | null;
  endereco?: string | null;
  municipio?: string | null;
  uf?: string | null;
}

export interface NfseTomador {
  doc?: string | null;
  doc_formatado?: string | null;
  nome?: string | null;
  municipio?: string | null;
  uf?: string | null;
}

export interface NfseTotals {
  valor_servicos?: number | null;
  valor_deducoes?: number | null;
  valor_pis?: number | null;
  valor_cofins?: number | null;
  valor_inss?: number | null;
  valor_ir?: number | null;
  valor_csll?: number | null;
  valor_iss?: number | null;
  valor_iss_retido?: number | null;
  valor_liquido?: number | null;
}

export interface NfseDocumentQuality {
  missing_fields?: string[];
  diff_liquido_vs_calculated?: number | null;
  class_meta?: Record<string, any>;
  items_review_high?: number;
  items_review_medium?: number;
  items_incomplete?: number;
  cnae_alerts?: number;
}

export interface NfseDocument {
  document_type: string;
  doc_class: string;
  decision: string;
  review_level: string;
  review_text_ptbr: string;
  reasons?: string[];
  next_actions?: string[];
  prestador?: Record<string, any>;
  tomador?: Record<string, any>;
  totals?: Record<string, any>;
  quality?: NfseDocumentQuality;
}

export interface NfseERPProjection {
  movement_type: string;
  filial_code?: string | null;
  supplier_doc?: string | null;
  note_number?: string | null;
  competencia?: string | null;
  issue_datetime?: string | null;
  valor_bruto?: number | null;
  valor_liquido?: number | null;
  service_code?: string | null;
  cost_center_suggested?: string | null;
  payment_hint?: string;
  rm_status_target?: string;
  retencoes?: Record<string, number>;
}

export interface NfseSummary {
  count?: number;
  numero_nota?: string | null;
  competencia?: string | null;
  is_cancelada?: boolean;
  decision_summary?: Record<string, number>;
  sum_valor_total_politica_a?: number;
  sum_valor_liquido_politica_b?: number;
  count_liquido_politica_b?: number;
  count_valor_liquido_informado_xml?: number;
  count_valor_liquido_divergente?: number;
  missing_valor_total?: number;
  missing_competencia?: number;
  items_with_missing_critical?: number;
  tax_totals?: {
    sum_valor_iss?: number;
    sum_valor_iss_retido?: number;
    sum_valor_pis?: number;
    sum_valor_cofins?: number;
    sum_valor_inss?: number;
    sum_valor_ir?: number;
    sum_valor_csll?: number;
  };
  validation_summary?: {
    cnae_vs_descricao?: {
      ok?: number;
      alert?: number;
      unknown?: number;
    };
  };
  // Campos da normalização
  service_class_summary?: Record<string, number>;
  review_summary?: Record<string, number>;
  quality_summary?: Record<string, number>;
  document_summary?: {
    doc_class?: string;
    decision?: string;
    review_level?: string;
    review_text_ptbr?: string;
    top_reasons?: string[];
    kpis?: Record<string, any>;
  };
}

// Dados específicos da nota individual
export interface NfseNoteData {
  numero_nota?: string | null;
  codigo_verificacao?: string | null;
  data_emissao?: string | null;
  competencia?: string | null;
  is_cancelada?: boolean;
  servico?: {
    discriminacao?: string | null;
    descricao_resumida?: string | null;
    codigo_tributacao?: string | null;
    item_lista_servico?: string | null;
    cnae?: string | null;
  };
}

export interface NfseExtractResponse {
  received: boolean;
  filename: string;
  sha256: string;
  count: number;
  
  prestador?: NfsePrestador | null;
  tomador?: NfseTomador | null;
  totals?: NfseTotals | null;
  summary?: NfseSummary | null;
  
  document?: NfseDocument | null;
  erp_projection?: NfseERPProjection | null;
  
  items?: NfseItem[];
  
  // Dados extras da nota individual
  _noteData?: NfseNoteData;
}

export interface ProcessedNfse {
  id: string;
  filename: string;
  data: NfseExtractResponse;
  processedAt: Date;
}

// Enums para consistência
export type NfseServiceClass = 
  | "SERVICO_SAUDE"
  | "SERVICO_TECNICO"
  | "SERVICO_ADMINISTRATIVO"
  | "SERVICO_CONSULTORIA"
  | "SERVICO_MANUTENCAO"
  | "OUTROS";

export type NfseDocumentClass = 
  | "SERVICO_SAUDE"
  | "SERVICO_TECNICO"
  | "SERVICO_ADMINISTRATIVO"
  | "SERVICO_CONSULTORIA"
  | "SERVICO_MANUTENCAO"
  | "OUTROS"
  | "MIXED"
  | "UNKNOWN";

export type NfseDecision = "AUTO" | "REVIEW" | "BLOCK";

export type NfseReviewLevel = "LOW" | "MEDIUM" | "HIGH";

// Helpers para tradução
export const SERVICE_CLASS_LABELS: Record<NfseServiceClass, string> = {
  SERVICO_SAUDE: "Serviço de Saúde",
  SERVICO_TECNICO: "Serviço Técnico",
  SERVICO_ADMINISTRATIVO: "Serviço Administrativo",
  SERVICO_CONSULTORIA: "Consultoria",
  SERVICO_MANUTENCAO: "Manutenção",
  OUTROS: "Outros",
};

export const DOCUMENT_CLASS_LABELS: Record<NfseDocumentClass, string> = {
  SERVICO_SAUDE: "Serviço de Saúde",
  SERVICO_TECNICO: "Serviço Técnico",
  SERVICO_ADMINISTRATIVO: "Serviço Administrativo",
  SERVICO_CONSULTORIA: "Consultoria",
  SERVICO_MANUTENCAO: "Manutenção",
  OUTROS: "Outros",
  MIXED: "Tipos Misturados",
  UNKNOWN: "Não Identificado",
};

export function translateServiceClass(serviceClass: string): string {
  return SERVICE_CLASS_LABELS[serviceClass as NfseServiceClass] || serviceClass;
}

export function translateDocumentClass(docClass: string): string {
  return DOCUMENT_CLASS_LABELS[docClass as NfseDocumentClass] || docClass;
}

export function getServiceClassColor(serviceClass: string): string {
  const colors: Record<string, string> = {
    SERVICO_SAUDE: "bg-red-100 text-red-800",
    SERVICO_TECNICO: "bg-blue-100 text-blue-800",
    SERVICO_ADMINISTRATIVO: "bg-gray-100 text-gray-800",
    SERVICO_CONSULTORIA: "bg-purple-100 text-purple-800",
    SERVICO_MANUTENCAO: "bg-orange-100 text-orange-800",
    OUTROS: "bg-gray-100 text-gray-600",
    MIXED: "bg-yellow-100 text-yellow-800",
    UNKNOWN: "bg-gray-200 text-gray-500",
  };
  return colors[serviceClass] || "bg-gray-100 text-gray-600";
}
