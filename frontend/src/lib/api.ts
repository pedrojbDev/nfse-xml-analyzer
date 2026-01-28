import { NFeExtractResponse } from "@/types/nfe";
import { NfseExtractResponse } from "@/types/nfse";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// Helpers
// ============================================================================

function isZipFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".zip");
}

// ============================================================================
// NF-e API
// ============================================================================

interface NfeBatchResponse {
  received: boolean;
  filename: string;
  sha256: string;
  count_files_ok: number;
  count_files_error: number;
  batch_summary: {
    count_total_items: number;
    sum_vNF: number;
    sum_vProd: number;
  };
  files: Array<{
    file: string;
    xml_sha256: string;
    received: boolean;
    count_items: number;
    header: any;
    emit: any;
    dest: any;
    totals: any;
    summary: any;
    document?: any;
    erp_projection?: any;
    items?: any[];
  }>;
  errors: Array<{
    file: string;
    error: string;
  }>;
}

/**
 * Envia arquivo XML de NF-e para extração e análise
 */
export async function extractNFe(file: File): Promise<NFeExtractResponse> {
  const response = await fetch(`${API_BASE}/nfe-xml-extract/summary`, {
    method: "POST",
    headers: {
      "Content-Type": "application/xml",
      "x-filename": file.name,
    },
    body: await file.arrayBuffer(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Erro ao processar arquivo: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Envia arquivo ZIP de NF-e e retorna lista de notas extraídas
 */
export async function extractNFeFromZip(file: File): Promise<NFeExtractResponse[]> {
  const response = await fetch(`${API_BASE}/nfe-xml-batch/summary`, {
    method: "POST",
    headers: {
      "Content-Type": "application/zip",
      "x-filename": file.name,
    },
    body: await file.arrayBuffer(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Erro ao processar arquivo: ${response.statusText}`);
  }

  const batchResult: NfeBatchResponse = await response.json();
  
  return batchResult.files.map((f) => ({
    received: f.received,
    filename: f.file,
    sha256: f.xml_sha256,
    count: f.count_items,
    header: f.header || {},
    emit: f.emit || {},
    dest: f.dest || {},
    totals: f.totals || {},
    summary: f.summary || {},
    document: f.document || null,
    erp_projection: f.erp_projection || null,
    items: f.items || [],
  }));
}

/**
 * Envia arquivo NF-e (XML ou ZIP) e retorna lista de notas
 */
export async function extractFile(file: File): Promise<NFeExtractResponse[]> {
  if (isZipFile(file)) {
    return extractNFeFromZip(file);
  } else {
    const result = await extractNFe(file);
    return [result];
  }
}

/**
 * Exporta NF-e para CSV
 */
export async function exportNfeToCsv(file: File): Promise<Blob> {
  const isZip = isZipFile(file);
  const endpoint = isZip
    ? `${API_BASE}/nfe-xml-batch/export-csv`
    : `${API_BASE}/nfe-xml-extract/export-csv`;
  
  const contentType = isZip ? "application/zip" : "application/xml";

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": contentType,
      "x-filename": file.name,
    },
    body: await file.arrayBuffer(),
  });

  if (!response.ok) {
    throw new Error(`Erro ao exportar: ${response.statusText}`);
  }

  return response.blob();
}

// Alias para compatibilidade
export const extractToCsv = exportNfeToCsv;
export const exportToCsv = exportNfeToCsv;

// ============================================================================
// NFS-e API
// ============================================================================

// Interface para a nova resposta com múltiplas notas
interface NfseMultiResponse {
  received: boolean;
  filename: string;
  sha256: string;
  count: number;
  notes: Array<{
    index: number;
    received: boolean;
    numero_nota?: string | null;
    codigo_verificacao?: string | null;
    data_emissao?: string | null;
    data_emissao_iso?: string | null;
    competencia?: string | null;
    is_cancelada?: boolean;
    prestador: any;
    tomador: any;
    totals: any;
    taxes: any;
    servico: any;
    validations: any;
    decision: string;
    reasons: string[];
    normalized?: any;
    review_level?: string;
    review_text_ptbr?: string;
    document?: any;
    erp_projection?: any;
  }>;
  batch_summary: {
    count_total: number;
    count_ativas: number;
    count_canceladas: number;
    sum_valor_servicos: number;
    sum_valor_liquido: number;
    decision_summary: Record<string, number>;
    prestadores_distintos: number;
    top_prestadores: any[];
  };
}

interface NfseBatchResponse {
  received: boolean;
  filename: string;
  sha256_zip: string;
  count_files_ok: number;
  count_files_error: number;
  batch_summary: {
    count_total_items: number;
    sum_valor_servicos: number;
    sum_valor_liquido: number;
  };
  files: Array<{
    file: string;
    xml_sha256: string;
    received: boolean;
    count_items: number;
    prestador?: any;
    tomador?: any;
    totals?: any;
    summary?: any;
    document?: any;
    erp_projection?: any;
    items?: any[];
  }>;
  errors: Array<{
    file: string;
    error: string;
  }>;
}

/**
 * Envia arquivo XML de NFS-e e extrai MÚLTIPLAS notas individuais.
 * Cada <CompNfse> no XML é tratado como uma nota separada.
 */
export async function extractNfse(file: File): Promise<NfseExtractResponse[]> {
  const response = await fetch(`${API_BASE}/nfse-xml-extract/summary`, {
    method: "POST",
    headers: {
      "Content-Type": "application/xml",
      "x-filename": file.name,
    },
    body: await file.arrayBuffer(),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Erro ao processar arquivo: ${response.statusText}`);
  }

  const result: NfseMultiResponse = await response.json();
  
  // Converte cada nota individual para o formato NfseExtractResponse
  return result.notes.map((note, idx) => ({
    received: note.received,
    filename: `${result.filename}_nota_${note.numero_nota || idx + 1}`,
    sha256: `${result.sha256}_${idx}`,
    count: 1,  // Cada nota é individual
    prestador: note.prestador || null,
    tomador: note.tomador || null,
    totals: note.totals || null,
    summary: {
      numero_nota: note.numero_nota,
      competencia: note.competencia,
      is_cancelada: note.is_cancelada,
    },
    document: note.document || null,
    erp_projection: note.erp_projection || null,
    items: [{
      fields: {
        numero_nota: note.numero_nota,
        data_emissao: note.data_emissao,
        cnpj_fornecedor: note.prestador?.doc_formatado,
        valor_total: note.totals?.valor_servicos,
        competencia: note.competencia,
        descricao_servico: note.servico?.descricao_resumida,
        cnae: note.servico?.cnae,
      },
      taxes: note.taxes || {},
      validations: note.validations || {},
      normalized: note.normalized,
      review_level: note.review_level,
      review_text_ptbr: note.review_text_ptbr,
      decision: note.decision,
      reasons: note.reasons,
    }],
    // Campos extras específicos da nota
    _noteData: {
      numero_nota: note.numero_nota,
      codigo_verificacao: note.codigo_verificacao,
      data_emissao: note.data_emissao,
      competencia: note.competencia,
      is_cancelada: note.is_cancelada,
      servico: note.servico,
    },
  }));
}

/**
 * Envia arquivo ZIP de NFS-e e retorna lista de notas extraídas
 */
export async function extractNfseFromZip(file: File): Promise<NfseExtractResponse[]> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/nfse-xml-batch/summary`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Erro ao processar arquivo: ${response.statusText}`);
  }

  const batchResult: NfseBatchResponse = await response.json();
  
  return batchResult.files.map((f) => ({
    received: f.received,
    filename: f.file,
    sha256: f.xml_sha256,
    count: f.count_items,
    prestador: f.prestador || null,
    tomador: f.tomador || null,
    totals: f.totals || null,
    summary: f.summary || null,
    document: f.document || null,
    erp_projection: f.erp_projection || null,
    items: f.items || [],
  }));
}

/**
 * Envia arquivo NFS-e (XML ou ZIP) e retorna lista de notas individuais
 */
export async function extractNfseFile(file: File): Promise<NfseExtractResponse[]> {
  if (isZipFile(file)) {
    return extractNfseFromZip(file);
  } else {
    // XML único pode conter múltiplas notas
    return extractNfse(file);
  }
}

/**
 * Exporta NFS-e para CSV
 */
export async function exportNfseToCsv(file: File): Promise<Blob> {
  const response = await fetch(`${API_BASE}/nfse-xml-extract/export-csv`, {
    method: "POST",
    headers: {
      "Content-Type": "application/xml",
      "x-filename": file.name,
    },
    body: await file.arrayBuffer(),
  });

  if (!response.ok) {
    throw new Error(`Erro ao exportar: ${response.statusText}`);
  }

  return response.blob();
}

// ============================================================================
// Health Check
// ============================================================================

/**
 * Verifica status da API
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// ============================================================================
// Funções auxiliares NF-e (para compatibilidade)
// ============================================================================

export async function extractNFeWithItems(
  file: File,
  page: number = 1,
  pageSize: number = 100
): Promise<NFeExtractResponse & { items: any[] }> {
  const response = await fetch(
    `${API_BASE}/nfe-xml-extract?page=${page}&page_size=${pageSize}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/xml",
        "x-filename": file.name,
      },
      body: await file.arrayBuffer(),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Erro ao processar arquivo: ${response.statusText}`);
  }

  return response.json();
}

export async function extractMultipleFiles(
  files: File[]
): Promise<NFeExtractResponse[]> {
  const allResults: NFeExtractResponse[] = [];
  
  for (const file of files) {
    try {
      const results = await extractFile(file);
      allResults.push(...results);
    } catch (error) {
      console.error(`Erro ao processar ${file.name}:`, error);
    }
  }

  return allResults;
}
