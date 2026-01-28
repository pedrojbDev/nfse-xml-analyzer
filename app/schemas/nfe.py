# app/schemas/nfe.py
"""
Schemas Pydantic para NF-e.

Define modelos de entrada e saída para os endpoints de NF-e,
garantindo validação e documentação automática no OpenAPI.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class ProductClass(str, Enum):
    """Classes de produto (nível item)."""
    MEDICAMENTO = "MEDICAMENTO"
    MATERIAL_HOSPITALAR = "MATERIAL_HOSPITALAR"
    GENERICO = "GENERICO"


class DocumentClass(str, Enum):
    """Classes de documento (nível nota)."""
    MEDICAMENTO = "MEDICAMENTO"
    MATERIAL_HOSPITALAR = "MATERIAL_HOSPITALAR"
    GENERICO = "GENERICO"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class Decision(str, Enum):
    """Decisão de processamento."""
    AUTO = "AUTO"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class ReviewLevel(str, Enum):
    """Nível de revisão/risco."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# =============================================================================
# Schemas de Item
# =============================================================================

class NFeItemData(BaseModel):
    """Dados brutos de um item da NF-e."""
    
    nItem: Optional[int] = Field(None, description="Número sequencial do item")
    cProd: Optional[str] = Field(None, description="Código do produto")
    xProd: Optional[str] = Field(None, description="Descrição do produto")
    NCM: Optional[str] = Field(None, description="Código NCM")
    CFOP: Optional[str] = Field(None, description="Código CFOP")
    uCom: Optional[str] = Field(None, description="Unidade comercial")
    qCom: Optional[float] = Field(None, description="Quantidade comercial")
    vUnCom: Optional[float] = Field(None, description="Valor unitário comercial")
    vProd: Optional[float] = Field(None, description="Valor total do produto")
    
    # Impostos
    icms_tipo: Optional[str] = Field(None, description="Tipo do grupo ICMS")
    cst: Optional[str] = Field(None, description="CST do ICMS")
    csosn: Optional[str] = Field(None, description="CSOSN (Simples Nacional)")
    vBC: Optional[float] = Field(None, description="Base de cálculo ICMS")
    vICMS: Optional[float] = Field(None, description="Valor ICMS")
    pis_tipo: Optional[str] = Field(None, description="Tipo do grupo PIS")
    pis_cst: Optional[str] = Field(None, description="CST do PIS")
    vPIS: Optional[float] = Field(None, description="Valor PIS")
    cofins_tipo: Optional[str] = Field(None, description="Tipo do grupo COFINS")
    cofins_cst: Optional[str] = Field(None, description="CST do COFINS")
    vCOFINS: Optional[float] = Field(None, description="Valor COFINS")

    class Config:
        extra = "allow"


class NFeItemNormalized(BaseModel):
    """Resultado da normalização de um item."""
    
    product_class: str = Field(..., description="Classe do produto")
    suggested_group: str = Field(..., description="Grupo sugerido para o ERP")


class NFeItemNormFlags(BaseModel):
    """Flags de normalização de um item."""
    
    expected_vProd: Optional[float] = Field(None, description="vProd esperado (qCom × vUnCom)")
    diff_vProd_vs_expected: Optional[float] = Field(None, description="Diferença entre vProd e esperado")
    vProd_invalid: bool = Field(False, description="Se vProd diverge do esperado")
    has_minimum_fiscal_keys: bool = Field(True, description="Se tem NCM e CFOP")
    requires_product_registration: bool = Field(True, description="Se requer cadastro no ERP")


class NFeItemEnriched(BaseModel):
    """Item enriquecido com normalização."""
    
    item: NFeItemData = Field(..., description="Dados originais do item")
    normalized: NFeItemNormalized = Field(..., description="Dados normalizados")
    decision: str = Field(..., description="Decisão (AUTO/REVIEW/BLOCK)")
    reasons: list[str] = Field(default_factory=list, description="Códigos dos motivos")
    norm_flags: NFeItemNormFlags = Field(..., description="Flags de normalização")
    review_level: str = Field(..., description="Nível de revisão")
    review_text_ptbr: str = Field(..., description="Explicação em português")
    
    # Do extrator
    missing_fields: list[str] = Field(default_factory=list, description="Campos ausentes")
    confidence: float = Field(1.0, description="Confiança da extração (0-1)")
    flags: dict[str, Any] = Field(default_factory=dict, description="Flags do extrator")
    field_sources: dict[str, str] = Field(default_factory=dict, description="Origem dos campos")

    class Config:
        extra = "allow"


# =============================================================================
# Schemas de Header/Partes
# =============================================================================

class NFeHeader(BaseModel):
    """Cabeçalho da NF-e."""
    
    chave_nfe: Optional[str] = Field(None, description="Chave de acesso (44 dígitos)")
    numero: Optional[int] = Field(None, description="Número da nota")
    serie: Optional[int] = Field(None, description="Série da nota")
    data_emissao: Optional[str] = Field(None, description="Data/hora de emissão")
    natureza_operacao: Optional[str] = Field(None, description="Natureza da operação")
    tipo_nf: Optional[int] = Field(None, description="Tipo (0=entrada, 1=saída)")
    ambiente: Optional[int] = Field(None, description="Ambiente (1=prod, 2=homolog)")

    class Config:
        extra = "allow"


class NFeParty(BaseModel):
    """Emitente ou Destinatário."""
    
    doc: Optional[str] = Field(None, description="CNPJ/CPF (apenas dígitos)")
    nome: Optional[str] = Field(None, description="Razão social/nome")
    uf: Optional[str] = Field(None, description="UF")
    municipio: Optional[str] = Field(None, description="Município")

    class Config:
        extra = "allow"


class NFeTotals(BaseModel):
    """Totais da NF-e."""
    
    vNF: Optional[float] = Field(None, description="Valor total da NF")
    vProd: Optional[float] = Field(None, description="Valor total dos produtos")
    vDesc: Optional[float] = Field(None, description="Valor total de descontos")
    vFrete: Optional[float] = Field(None, description="Valor do frete")
    vOutro: Optional[float] = Field(None, description="Outras despesas")
    vICMS: Optional[float] = Field(None, description="Valor total ICMS")
    vICMSST: Optional[float] = Field(None, description="Valor total ICMS ST")
    vIPI: Optional[float] = Field(None, description="Valor total IPI")
    vPIS: Optional[float] = Field(None, description="Valor total PIS")
    vCOFINS: Optional[float] = Field(None, description="Valor total COFINS")

    class Config:
        extra = "allow"


# =============================================================================
# Schemas de Sumário e Documento
# =============================================================================

class NFeNormSummary(BaseModel):
    """Sumário da normalização de itens."""
    
    decision_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Contagem por decisão"
    )
    quality_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Contagem de problemas de qualidade"
    )
    review_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Contagem por nível de revisão"
    )


class NFeDocumentQuality(BaseModel):
    """Qualidade do documento."""
    
    missing_header_keys: list[str] = Field(default_factory=list)
    diff_items_vs_total_vProd: Optional[float] = None
    class_meta: dict[str, Any] = Field(default_factory=dict)
    items_review_high: int = 0
    items_review_medium: int = 0
    items_incomplete: int = 0


class NFeDocument(BaseModel):
    """Análise do documento (nível nota)."""
    
    document_type: str = Field("NFE", description="Tipo do documento")
    doc_class: str = Field(..., description="Classe do documento")
    decision: str = Field(..., description="Decisão")
    review_level: str = Field(..., description="Nível de revisão")
    review_text_ptbr: str = Field(..., description="Explicação em português")
    reasons: list[str] = Field(default_factory=list, description="Motivos")
    next_actions: list[str] = Field(default_factory=list, description="Próximas ações sugeridas")
    
    header: dict[str, Any] = Field(default_factory=dict)
    emit: dict[str, Any] = Field(default_factory=dict)
    dest: dict[str, Any] = Field(default_factory=dict)
    totals: dict[str, Any] = Field(default_factory=dict)
    quality: NFeDocumentQuality = Field(default_factory=NFeDocumentQuality)

    class Config:
        extra = "allow"


class NFeERPProjection(BaseModel):
    """Projeção para o ERP."""
    
    movement_type: str = Field(..., description="Tipo de movimento")
    filial_code: Optional[str] = Field(None, description="Código da filial")
    supplier_doc: Optional[str] = Field(None, description="CNPJ do fornecedor")
    note_number: Optional[int] = Field(None, description="Número da nota")
    note_serie: Optional[int] = Field(None, description="Série da nota")
    issue_datetime: Optional[str] = Field(None, description="Data de emissão")
    quantity: int = Field(1, description="Quantidade (sempre 1 no modo genérico)")
    unit_value: Optional[float] = Field(None, description="Valor unitário")
    total_value: Optional[float] = Field(None, description="Valor total")
    product_code: Optional[str] = Field(None, description="Código do produto sugerido")
    cost_center_suggested: Optional[str] = Field(None, description="Centro de custo sugerido")
    payment_hint: str = Field("BOLETO", description="Dica de pagamento")
    rm_status_target: str = Field("PENDENTE", description="Status alvo no RM")

    class Config:
        extra = "allow"


class NFeDocumentSummary(BaseModel):
    """Sumário do documento para dashboards."""
    
    doc_class: str = Field(..., description="Classe do documento")
    decision: str = Field(..., description="Decisão")
    review_level: str = Field(..., description="Nível de revisão")
    review_text_ptbr: str = Field("", description="Explicação")
    top_reasons: list[str] = Field(default_factory=list, description="Principais motivos")
    kpis: dict[str, Any] = Field(default_factory=dict, description="KPIs")


# =============================================================================
# Schemas de Resposta dos Endpoints
# =============================================================================

class NFeExtractSummary(BaseModel):
    """Sumário da extração."""
    
    count_items: int = Field(0, description="Total de itens")
    items_incomplete: int = Field(0, description="Itens incompletos")
    sum_items_vProd: float = Field(0.0, description="Soma vProd dos itens")
    total_vProd_xml: Optional[float] = Field(None, description="vProd total do XML")
    diff_items_vs_total_vProd: Optional[float] = Field(None, description="Diferença")
    
    # Mesclado do normalizador
    decision_summary: dict[str, int] = Field(default_factory=dict)
    quality_summary: dict[str, int] = Field(default_factory=dict)
    review_summary: dict[str, int] = Field(default_factory=dict)
    document_summary: Optional[NFeDocumentSummary] = None

    class Config:
        extra = "allow"


class NFeExtractResponse(BaseModel):
    """Resposta do endpoint /nfe-xml-extract."""
    
    received: bool = Field(..., description="Se o XML foi recebido com sucesso")
    filename: str = Field(..., description="Nome do arquivo")
    sha256: str = Field(..., description="Hash SHA256 do conteúdo")
    
    count_total: int = Field(0, description="Total de itens")
    count_page: int = Field(0, description="Itens na página atual")
    page: int = Field(1, description="Página atual")
    page_size: int = Field(50, description="Tamanho da página")
    pages: int = Field(0, description="Total de páginas")
    
    header: NFeHeader = Field(default_factory=NFeHeader)
    emit: NFeParty = Field(default_factory=NFeParty)
    dest: NFeParty = Field(default_factory=NFeParty)
    totals: NFeTotals = Field(default_factory=NFeTotals)
    
    items: list[dict[str, Any]] = Field(default_factory=list, description="Itens da página")
    summary: NFeExtractSummary = Field(default_factory=NFeExtractSummary)
    
    document: Optional[NFeDocument] = Field(None, description="Análise do documento")
    erp_projection: Optional[NFeERPProjection] = Field(None, description="Projeção ERP")

    class Config:
        extra = "allow"


class NFeExtractSummaryResponse(BaseModel):
    """Resposta do endpoint /nfe-xml-extract/summary."""
    
    received: bool = Field(...)
    filename: str = Field(...)
    sha256: str = Field(...)
    count: int = Field(0)
    
    header: NFeHeader = Field(default_factory=NFeHeader)
    emit: NFeParty = Field(default_factory=NFeParty)
    dest: NFeParty = Field(default_factory=NFeParty)
    totals: NFeTotals = Field(default_factory=NFeTotals)
    summary: NFeExtractSummary = Field(default_factory=NFeExtractSummary)
    
    document: Optional[NFeDocument] = None
    erp_projection: Optional[NFeERPProjection] = None

    class Config:
        extra = "allow"


class NFeErrorResponse(BaseModel):
    """Resposta de erro."""
    
    received: bool = Field(False)
    error: str = Field(..., description="Código do erro")
    message: str = Field(..., description="Mensagem de erro")
    details: dict[str, Any] = Field(default_factory=dict, description="Detalhes adicionais")
