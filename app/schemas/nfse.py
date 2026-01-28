# app/schemas/nfse.py
"""
Schemas Pydantic para NFS-e (Nota Fiscal de Serviço Eletrônica).

Define modelos de entrada e saída para os endpoints de NFS-e,
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

class ServiceClass(str, Enum):
    """Classes de serviço (nível item)."""
    SERVICO_SAUDE = "SERVICO_SAUDE"
    SERVICO_TECNICO = "SERVICO_TECNICO"
    SERVICO_ADMINISTRATIVO = "SERVICO_ADMINISTRATIVO"
    SERVICO_CONSULTORIA = "SERVICO_CONSULTORIA"
    SERVICO_MANUTENCAO = "SERVICO_MANUTENCAO"
    OUTROS = "OUTROS"


class NfseDocumentClass(str, Enum):
    """Classes de documento NFS-e (nível nota)."""
    SERVICO_SAUDE = "SERVICO_SAUDE"
    SERVICO_TECNICO = "SERVICO_TECNICO"
    SERVICO_ADMINISTRATIVO = "SERVICO_ADMINISTRATIVO"
    SERVICO_CONSULTORIA = "SERVICO_CONSULTORIA"
    SERVICO_MANUTENCAO = "SERVICO_MANUTENCAO"
    OUTROS = "OUTROS"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class NfseDecision(str, Enum):
    """Decisão de processamento."""
    AUTO = "AUTO"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class NfseReviewLevel(str, Enum):
    """Nível de revisão/risco."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# =============================================================================
# Schemas de Tributos
# =============================================================================

class NfseTaxes(BaseModel):
    """Tributos de uma NFS-e."""
    
    iss_retido: Optional[int] = Field(None, description="Flag ISS retido (1=sim, 2=não)")
    base_calculo: Optional[float] = Field(None, description="Base de cálculo do ISS")
    aliquota: Optional[float] = Field(None, description="Alíquota do ISS")
    valor_iss: Optional[float] = Field(None, description="Valor do ISS")
    valor_iss_retido: Optional[float] = Field(None, description="Valor do ISS retido")
    valor_deducoes: Optional[float] = Field(None, description="Valor de deduções")
    valor_pis: Optional[float] = Field(None, description="Valor do PIS")
    valor_cofins: Optional[float] = Field(None, description="Valor do COFINS")
    valor_inss: Optional[float] = Field(None, description="Valor do INSS")
    valor_ir: Optional[float] = Field(None, description="Valor do IR")
    valor_csll: Optional[float] = Field(None, description="Valor do CSLL")
    outras_retencoes: Optional[float] = Field(None, description="Outras retenções")
    desconto_incondicionado: Optional[float] = Field(None, description="Desconto incondicionado")
    desconto_condicionado: Optional[float] = Field(None, description="Desconto condicionado")
    valor_liquido_nfse: Optional[float] = Field(None, description="Valor líquido informado no XML")
    valor_liquido_calculado_politica_b: Optional[float] = Field(None, description="Valor líquido calculado")
    valor_liquido_diff_xml_vs_calc: Optional[float] = Field(None, description="Diferença entre líquido XML e calculado")
    valor_liquido_divergente: bool = Field(False, description="Se há divergência no valor líquido")

    class Config:
        extra = "allow"


# =============================================================================
# Schemas de Item (Serviço)
# =============================================================================

class NfseItemFields(BaseModel):
    """Campos principais de um item/serviço da NFS-e."""
    
    numero_nota: Optional[str] = Field(None, description="Número da nota")
    data_emissao: Optional[str] = Field(None, description="Data/hora de emissão formatada")
    cnpj_fornecedor: Optional[str] = Field(None, description="CNPJ do prestador formatado")
    valor_total: Optional[float] = Field(None, description="Valor total do serviço")
    competencia: Optional[str] = Field(None, description="Competência (MM/YYYY)")
    descricao_servico: Optional[str] = Field(None, description="Descrição resumida do serviço")
    cnae: Optional[str] = Field(None, description="Código CNAE do serviço")

    class Config:
        extra = "allow"


class NfseItemFlags(BaseModel):
    """Flags de qualidade de um item."""
    
    needs_review: bool = Field(False, description="Se precisa revisão")
    incomplete: bool = Field(False, description="Se tem campos faltando")
    missing_critical: bool = Field(False, description="Se faltam campos críticos")

    class Config:
        extra = "allow"


class NfseValidationCnae(BaseModel):
    """Resultado da validação CNAE vs Descrição."""
    
    status: Optional[str] = Field(None, description="Status: ok, alert, unknown")
    reason: Optional[str] = Field(None, description="Razão da validação")
    rule_label: Optional[str] = Field(None, description="Label da regra aplicada")
    severity: Optional[str] = Field(None, description="Severidade: info, warning, error")

    class Config:
        extra = "allow"


class NfseItemValidations(BaseModel):
    """Validações aplicadas ao item."""
    
    cnae_vs_descricao: NfseValidationCnae = Field(
        default_factory=NfseValidationCnae,
        description="Validação CNAE vs descrição"
    )

    class Config:
        extra = "allow"


class NfseItemNormalized(BaseModel):
    """Resultado da normalização de um serviço."""
    
    service_class: str = Field(..., description="Classe do serviço")
    suggested_group: str = Field(..., description="Grupo sugerido para o ERP")
    cnae_group: Optional[str] = Field(None, description="Grupo do CNAE")


class NfseItemNormFlags(BaseModel):
    """Flags de normalização de um item NFS-e."""
    
    has_minimum_fields: bool = Field(True, description="Se tem campos mínimos")
    has_valid_cnae: bool = Field(True, description="Se CNAE é válido")
    has_valid_valor: bool = Field(True, description="Se valor é válido")
    valor_liquido_divergente: bool = Field(False, description="Se valor líquido diverge")
    requires_review_cnae: bool = Field(False, description="Se CNAE requer revisão")


class NfseItem(BaseModel):
    """Item/serviço de uma NFS-e (formato do extrator)."""
    
    fields: NfseItemFields = Field(default_factory=NfseItemFields, description="Campos principais")
    taxes: NfseTaxes = Field(default_factory=NfseTaxes, description="Tributos")
    missing_fields: list[str] = Field(default_factory=list, description="Campos ausentes")
    confidence: float = Field(1.0, description="Confiança da extração (0-1)")
    flags: NfseItemFlags = Field(default_factory=NfseItemFlags, description="Flags de qualidade")
    field_sources: dict[str, str] = Field(default_factory=dict, description="Origem dos campos")
    tax_sources: dict[str, str] = Field(default_factory=dict, description="Origem dos tributos")
    xml_raw: dict[str, Any] = Field(default_factory=dict, description="Dados brutos do XML")
    validations: NfseItemValidations = Field(default_factory=NfseItemValidations, description="Validações")
    decision: Optional[str] = Field(None, description="Decisão (AUTO/REVIEW/BLOCK)")
    reasons: list[str] = Field(default_factory=list, description="Razões da decisão")

    class Config:
        extra = "allow"


class NfseItemEnriched(BaseModel):
    """Item enriquecido com normalização."""
    
    fields: NfseItemFields = Field(default_factory=NfseItemFields, description="Campos principais")
    taxes: NfseTaxes = Field(default_factory=NfseTaxes, description="Tributos")
    missing_fields: list[str] = Field(default_factory=list, description="Campos ausentes")
    confidence: float = Field(1.0, description="Confiança da extração (0-1)")
    flags: NfseItemFlags = Field(default_factory=NfseItemFlags, description="Flags de qualidade")
    field_sources: dict[str, str] = Field(default_factory=dict, description="Origem dos campos")
    validations: NfseItemValidations = Field(default_factory=NfseItemValidations, description="Validações")
    
    # Campos da normalização
    normalized: NfseItemNormalized = Field(..., description="Dados normalizados")
    norm_flags: NfseItemNormFlags = Field(default_factory=NfseItemNormFlags, description="Flags de normalização")
    review_level: str = Field("LOW", description="Nível de revisão")
    review_text_ptbr: str = Field("", description="Explicação em português")

    class Config:
        extra = "allow"


# =============================================================================
# Schemas de Partes (Prestador/Tomador)
# =============================================================================

class NfsePrestador(BaseModel):
    """Prestador de serviço (emissor da NFS-e)."""
    
    doc: Optional[str] = Field(None, description="CNPJ (apenas dígitos)")
    doc_formatado: Optional[str] = Field(None, description="CNPJ formatado")
    nome: Optional[str] = Field(None, description="Razão social")
    inscricao_municipal: Optional[str] = Field(None, description="Inscrição municipal")
    municipio: Optional[str] = Field(None, description="Município")
    uf: Optional[str] = Field(None, description="UF")

    class Config:
        extra = "allow"


class NfseTomador(BaseModel):
    """Tomador de serviço (destinatário da NFS-e)."""
    
    doc: Optional[str] = Field(None, description="CNPJ/CPF (apenas dígitos)")
    doc_formatado: Optional[str] = Field(None, description="CNPJ/CPF formatado")
    nome: Optional[str] = Field(None, description="Razão social/nome")
    municipio: Optional[str] = Field(None, description="Município")
    uf: Optional[str] = Field(None, description="UF")

    class Config:
        extra = "allow"


# =============================================================================
# Schemas de Totais e Sumário
# =============================================================================

class NfseTotals(BaseModel):
    """Totais da NFS-e."""
    
    valor_servicos: Optional[float] = Field(None, description="Valor total dos serviços")
    valor_deducoes: Optional[float] = Field(None, description="Valor total de deduções")
    valor_pis: Optional[float] = Field(None, description="Valor total PIS")
    valor_cofins: Optional[float] = Field(None, description="Valor total COFINS")
    valor_inss: Optional[float] = Field(None, description="Valor total INSS")
    valor_ir: Optional[float] = Field(None, description="Valor total IR")
    valor_csll: Optional[float] = Field(None, description="Valor total CSLL")
    valor_iss: Optional[float] = Field(None, description="Valor total ISS")
    valor_iss_retido: Optional[float] = Field(None, description="Valor total ISS retido")
    valor_liquido: Optional[float] = Field(None, description="Valor líquido total")

    class Config:
        extra = "allow"


class NfseTaxTotals(BaseModel):
    """Totais tributários agregados."""
    
    sum_valor_iss: float = Field(0.0)
    sum_valor_iss_retido: float = Field(0.0)
    sum_valor_pis: float = Field(0.0)
    sum_valor_cofins: float = Field(0.0)
    sum_valor_inss: float = Field(0.0)
    sum_valor_ir: float = Field(0.0)
    sum_valor_csll: float = Field(0.0)


class NfseValidationSummary(BaseModel):
    """Sumário das validações CNAE."""
    
    cnae_vs_descricao: dict[str, int] = Field(
        default_factory=lambda: {"ok": 0, "alert": 0, "unknown": 0}
    )


class NfseSummary(BaseModel):
    """Sumário da extração/normalização."""
    
    count: int = Field(0, description="Total de itens")
    decision_summary: dict[str, int] = Field(
        default_factory=lambda: {"auto": 0, "review": 0, "block": 0}
    )
    sum_valor_total_politica_a: float = Field(0.0, description="Soma ValorServicos")
    sum_valor_liquido_politica_b: float = Field(0.0, description="Soma valor líquido calculado")
    count_liquido_politica_b: int = Field(0)
    count_valor_liquido_informado_xml: int = Field(0)
    count_valor_liquido_divergente: int = Field(0)
    missing_valor_total: int = Field(0)
    missing_competencia: int = Field(0)
    items_with_missing_critical: int = Field(0)
    tax_totals: NfseTaxTotals = Field(default_factory=NfseTaxTotals)
    validation_summary: NfseValidationSummary = Field(default_factory=NfseValidationSummary)
    policy: str = Field("A (valor_total := ValorServicos)")

    class Config:
        extra = "allow"


class NfseNormSummary(BaseModel):
    """Sumário da normalização de serviços."""
    
    decision_summary: dict[str, int] = Field(default_factory=dict)
    quality_summary: dict[str, int] = Field(default_factory=dict)
    review_summary: dict[str, int] = Field(default_factory=dict)
    service_class_summary: dict[str, int] = Field(default_factory=dict)


# =============================================================================
# Schemas de Documento
# =============================================================================

class NfseDocumentQuality(BaseModel):
    """Qualidade do documento NFS-e."""
    
    missing_fields: list[str] = Field(default_factory=list)
    diff_liquido_vs_calculated: Optional[float] = None
    class_meta: dict[str, Any] = Field(default_factory=dict)
    items_review_high: int = 0
    items_review_medium: int = 0
    items_incomplete: int = 0
    cnae_alerts: int = 0


class NfseDocument(BaseModel):
    """Análise do documento NFS-e (nível nota)."""
    
    document_type: str = Field("NFSE", description="Tipo do documento")
    doc_class: str = Field(..., description="Classe do documento")
    decision: str = Field(..., description="Decisão")
    review_level: str = Field(..., description="Nível de revisão")
    review_text_ptbr: str = Field(..., description="Explicação em português")
    reasons: list[str] = Field(default_factory=list, description="Motivos")
    next_actions: list[str] = Field(default_factory=list, description="Próximas ações sugeridas")
    
    prestador: dict[str, Any] = Field(default_factory=dict)
    tomador: dict[str, Any] = Field(default_factory=dict)
    totals: dict[str, Any] = Field(default_factory=dict)
    quality: NfseDocumentQuality = Field(default_factory=NfseDocumentQuality)

    class Config:
        extra = "allow"


class NfseERPProjection(BaseModel):
    """Projeção para o ERP."""
    
    movement_type: str = Field(..., description="Tipo de movimento")
    filial_code: Optional[str] = Field(None, description="Código da filial")
    supplier_doc: Optional[str] = Field(None, description="CNPJ do prestador")
    note_number: Optional[str] = Field(None, description="Número da nota")
    competencia: Optional[str] = Field(None, description="Competência")
    issue_datetime: Optional[str] = Field(None, description="Data de emissão")
    valor_bruto: Optional[float] = Field(None, description="Valor bruto (ValorServicos)")
    valor_liquido: Optional[float] = Field(None, description="Valor líquido")
    service_code: Optional[str] = Field(None, description="Código do serviço sugerido")
    cost_center_suggested: Optional[str] = Field(None, description="Centro de custo sugerido")
    payment_hint: str = Field("BOLETO", description="Dica de pagamento")
    rm_status_target: str = Field("PENDENTE", description="Status alvo no RM")
    retencoes: dict[str, float] = Field(default_factory=dict, description="Retenções a considerar")

    class Config:
        extra = "allow"


class NfseDocumentSummary(BaseModel):
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

class NfseExtractResponse(BaseModel):
    """Resposta do endpoint /nfse-xml-extract."""
    
    received: bool = Field(..., description="Se o XML foi recebido com sucesso")
    filename: str = Field(..., description="Nome do arquivo")
    sha256: str = Field(..., description="Hash SHA256 do conteúdo")
    
    count: int = Field(0, description="Total de itens (compatibilidade)")
    count_total: int = Field(0, description="Total de itens")
    count_page: int = Field(0, description="Itens na página atual")
    page: int = Field(1, description="Página atual")
    page_size: int = Field(50, description="Tamanho da página")
    pages: int = Field(0, description="Total de páginas")
    
    items: list[dict[str, Any]] = Field(default_factory=list, description="Itens da página")
    summary: dict[str, Any] = Field(default_factory=dict, description="Sumário")
    
    # Campos adicionados pela normalização/análise
    prestador: Optional[NfsePrestador] = Field(None, description="Dados do prestador")
    tomador: Optional[NfseTomador] = Field(None, description="Dados do tomador")
    totals: Optional[NfseTotals] = Field(None, description="Totais")
    document: Optional[NfseDocument] = Field(None, description="Análise do documento")
    erp_projection: Optional[NfseERPProjection] = Field(None, description="Projeção ERP")

    class Config:
        extra = "allow"


class NfseExtractSummaryResponse(BaseModel):
    """Resposta do endpoint /nfse-xml-extract/summary."""
    
    received: bool = Field(...)
    filename: str = Field(...)
    sha256: str = Field(...)
    count: int = Field(0)
    
    prestador: Optional[NfsePrestador] = None
    tomador: Optional[NfseTomador] = None
    totals: Optional[NfseTotals] = None
    summary: NfseSummary = Field(default_factory=NfseSummary)
    
    document: Optional[NfseDocument] = None
    erp_projection: Optional[NfseERPProjection] = None
    
    # Itens enriquecidos (para uso no frontend)
    items: list[dict[str, Any]] = Field(default_factory=list, description="Itens normalizados")

    class Config:
        extra = "allow"


class NfseBatchFileResult(BaseModel):
    """Resultado de um arquivo no processamento batch."""
    
    file: str = Field(..., description="Nome do arquivo")
    xml_sha256: str = Field(..., description="Hash do XML")
    received: bool = Field(True)
    count_items: int = Field(0)
    
    prestador: Optional[NfsePrestador] = None
    tomador: Optional[NfseTomador] = None
    totals: Optional[NfseTotals] = None
    summary: dict[str, Any] = Field(default_factory=dict)
    document: Optional[NfseDocument] = None
    erp_projection: Optional[NfseERPProjection] = None
    items: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        extra = "allow"


class NfseBatchSummary(BaseModel):
    """Sumário do processamento batch."""
    
    count_files_ok: int = Field(0)
    count_files_error: int = Field(0)
    count_total_items: int = Field(0)
    sum_valor_servicos: float = Field(0.0)
    sum_valor_liquido: float = Field(0.0)
    decision_summary: dict[str, int] = Field(default_factory=dict)
    quality_summary: dict[str, int] = Field(default_factory=dict)


class NfseBatchResponse(BaseModel):
    """Resposta do endpoint /nfse-xml-batch/summary."""
    
    received: bool = Field(...)
    filename: str = Field(...)
    sha256_zip: str = Field(...)
    
    count_files_ok: int = Field(0)
    count_files_error: int = Field(0)
    
    files: list[NfseBatchFileResult] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    batch_summary: NfseBatchSummary = Field(default_factory=NfseBatchSummary)

    class Config:
        extra = "allow"


class NfseErrorResponse(BaseModel):
    """Resposta de erro."""
    
    received: bool = Field(False)
    error: str = Field(..., description="Código do erro")
    message: str = Field(..., description="Mensagem de erro")
    details: dict[str, Any] = Field(default_factory=dict, description="Detalhes adicionais")
