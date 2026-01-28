import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formata valor para moeda brasileira
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

/**
 * Traduz códigos de reason para português
 */
export function translateReason(code: string): string {
  const translations: Record<string, string> = {
    // Documento
    DOC_NO_ITEMS: "Nenhum item encontrado na nota",
    DOC_MISSING_HEADER_KEYS: "Campos obrigatórios ausentes no cabeçalho",
    DOC_TOTAL_DIVERGENCE: "Divergência entre total da nota e soma dos itens",
    DOC_ITEMS_MIXED_CLASSES: "Mistura de classes de produtos",
    DOC_ITEMS_INCOMPLETE: "Itens com dados incompletos",
    DOC_CANNOT_CLASSIFY: "Não foi possível classificar automaticamente",
    DOC_ITEMS_HAVE_REVIEW_HIGH: "Itens com pendências críticas",
    DOC_ITEMS_HAVE_REVIEW_MEDIUM: "Itens com pendências moderadas",
    
    // Item - Classificação
    CLASS_MEDICAMENTO_BY_NCM_30XX: "Identificado como medicamento pelo NCM",
    CLASS_MATERIAL_BY_NCM_90XX: "Identificado como material hospitalar pelo NCM",
    CLASS_MATERIAL_BY_KEYWORD: "Identificado como material pela descrição",
    CLASS_GENERIC_FALLBACK: "Classificado como genérico",
    
    // Item - Qualidade
    NCM_MISSING: "NCM não informado",
    CFOP_MISSING: "CFOP não informado",
    PRODUCT_CODE_MISSING: "Código do produto ausente",
    PRODUCT_DESC_MISSING: "Descrição do produto ausente",
    QTY_OR_PRICE_MISSING: "Quantidade ou preço ausente",
    ITEM_TOTAL_INVALID: "Total do item diverge do cálculo",
  };
  
  return translations[code] || code;
}

/**
 * Traduz classe de produto para português amigável
 */
export function translateProductClass(cls: string): string {
  const translations: Record<string, string> = {
    MEDICAMENTO: "Medicamento",
    MATERIAL_HOSPITALAR: "Material Hospitalar",
    GENERICO: "Genérico",
    MIXED: "Misto",
    UNKNOWN: "Não Identificado",
  };
  
  return translations[cls] || cls;
}

/**
 * Traduz nível de revisão
 */
export function translateReviewLevel(level: string): string {
  const translations: Record<string, string> = {
    HIGH: "Alto",
    MEDIUM: "Médio",
    LOW: "Baixo",
  };
  
  return translations[level] || level;
}

/**
 * Retorna cor do badge baseado no nível de revisão
 */
export function getReviewLevelColor(level: string): string {
  const colors: Record<string, string> = {
    HIGH: "bg-red-100 text-red-800 border-red-200",
    MEDIUM: "bg-yellow-100 text-yellow-800 border-yellow-200",
    LOW: "bg-green-100 text-green-800 border-green-200",
  };
  
  return colors[level] || "bg-gray-100 text-gray-800 border-gray-200";
}

/**
 * Retorna cor do badge baseado na classe do produto
 */
export function getProductClassColor(cls: string): string {
  const colors: Record<string, string> = {
    MEDICAMENTO: "bg-blue-100 text-blue-800 border-blue-200",
    MATERIAL_HOSPITALAR: "bg-purple-100 text-purple-800 border-purple-200",
    GENERICO: "bg-gray-100 text-gray-800 border-gray-200",
    MIXED: "bg-orange-100 text-orange-800 border-orange-200",
    UNKNOWN: "bg-gray-100 text-gray-500 border-gray-200",
  };
  
  return colors[cls] || "bg-gray-100 text-gray-800 border-gray-200";
}
