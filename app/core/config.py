# app/core/config.py
"""
Configurações centralizadas da aplicação.

Usa pydantic-settings para carregar variáveis de ambiente de forma tipada.
Todas as configurações devem ser definidas aqui para evitar valores hardcoded.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações da aplicação.
    
    Variáveis podem ser definidas via:
    - Arquivo .env na raiz do projeto
    - Variáveis de ambiente do sistema
    - Valores padrão definidos aqui
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ==========================================================================
    # App Info
    # ==========================================================================
    app_name: str = "NF-e Analyzer API"
    app_version: str = "0.3.0"
    debug: bool = False
    environment: str = "development"  # development, staging, production
    
    # ==========================================================================
    # Paths
    # ==========================================================================
    audit_log_path: str = "data/audit.jsonl"
    upload_temp_dir: str = "data/uploads"
    
    # ==========================================================================
    # Thresholds - Normalização de Itens
    # ==========================================================================
    # Tolerância para divergência entre vProd calculado e informado (em R$)
    item_vprod_tolerance: float = 0.05
    
    # ==========================================================================
    # Thresholds - Análise de Documento
    # ==========================================================================
    # Tolerância absoluta para divergência de totais (em R$)
    doc_vprod_abs_threshold: float = 0.10
    # Tolerância percentual para divergência de totais
    doc_vprod_pct_threshold: float = 0.001
    
    # ==========================================================================
    # ERP - Códigos Padrão para Projeção (NF-e)
    # ==========================================================================
    erp_movement_type: str = "1.2.01"
    erp_product_code_medicamento: str = "00007"
    erp_product_code_material: str = "00008"
    erp_product_code_generico: str = "00008"
    
    # ==========================================================================
    # ERP - Códigos Padrão para Projeção (NFS-e)
    # ==========================================================================
    erp_nfse_movement_type: str = "2.1.01"
    erp_service_code_saude: str = "00010"
    erp_service_code_tecnico: str = "00011"
    erp_service_code_outros: str = "00012"
    
    # ==========================================================================
    # Thresholds - NFS-e
    # ==========================================================================
    # Tolerância absoluta para divergência de valor líquido (em R$)
    nfse_liquido_abs_threshold: float = 0.10
    # Tolerância percentual para divergência de valor líquido
    nfse_liquido_pct_threshold: float = 0.001
    
    # ==========================================================================
    # Classificação - Keywords (pode ser sobrescrito via env como JSON)
    # ==========================================================================
    # Keywords que indicam material hospitalar (separadas por vírgula no .env)
    material_keywords: str = (
        # Seringas e agulhas
        "SERINGA,AGULHA,SCALP,JELCO,BUTTERFLY,"
        # Cateteres e sondas
        "CATETER,SONDA,FOLLEY,FOLEY,NASOGASTRICA,VESICAL,URETRAL,RETAL,ASPIRACAO,"
        # Luvas e proteção
        "LUVA,LUVAS,PROCEDIMENTO,LATEX,NITRILA,VINIL,CIRURGICA,"
        # Curativos e coberturas
        "GAZE,GAZES,CURATIVO,ESPARADRAPO,MICROPORE,ATADURA,COMPRESSA,ALGODAO,"
        "BANDAGEM,FITA ADESIVA,TEGADERM,HIDROCOLOIDE,FILME TRANSPARENTE,"
        # Equipos e extensores
        "EQUIPO,EXTENSOR,TORNEIRA,TORNEIRINHA,THREE WAY,TREEWAY,INFUSAO,"
        "MULTIVIAS,POLIFIX,BURETA,PERFUSOR,"
        # Drenos e tubos
        "DRENO,TUBO,TRAQUEOSTOMIA,CANULA,ENDOTRAQUEAL,OROTRAQUEAL,ASPIRADOR,"
        # Instrumentais e cirúrgicos
        "BISTURI,LAMINA,SUTURA,FIO CIRURGICO,FIO NYLON,FIO SEDA,FIO CATGUT,"
        "FIO VICRYL,FIO PROLENE,PINÇA,TESOURA,PORTA AGULHA,AFASTADOR,"
        # Máscaras e proteção respiratória
        "MASCARA,MASCARAS,N95,PFF2,CIRURGICA,DESCARTAVEL,PROTETOR FACIAL,"
        # Aventais e campos
        "AVENTAL,CAMPO,CAMPO CIRURGICO,CAMPO ESTERIL,LENCOL,PROPAPE,"
        # Oxigenoterapia
        "OXIGENIO,UMIDIFICADOR,NEBULIZADOR,INALADOR,RESERVATORIO,"
        # Coleta e exames
        "TUBO COLETA,VACUTAINER,LANCETA,COLETOR,FRASCO COLETA,SWAB,"
        # Diversos materiais
        "ABAIXADOR,ESPECULO,TERMOMETRO,ESFIGMO,ESTETOSCOPIO,OTOSCOPIO,"
        "BOLSA,COLETORA,OSTOMIA,UROSTOMIA,COLOSTOMIA,"
        "FIXADOR,FIXACAO,IMOBILIZADOR,TALA,COLAR CERVICAL,"
        "FRALDA,ABSORVENTE,COXIM,ALMOFADA,"
        # Esterilização
        "ESTERIL,ESTERILIZADO,AUTOCLAVE,INDICADOR BIOLOGICO,"
        # Outros
        "DISPOSITIVO,HOSPITALAR,MEDICO,PROCEDIMENTO,DESC,DESCARTAVEL"
    )
    
    # Keywords que indicam medicamentos (separadas por vírgula no .env)
    medicamento_keywords: str = (
        # Formas farmacêuticas
        "COMPRIMIDO,CAPSULA,AMPOLA,FRASCO,SOLUCAO,XAROPE,SUSPENSAO,"
        "INJETAVEL,POMADA,CREME,GEL,GOTAS,SPRAY,AEROSOL,SUPOSITORIO,"
        "PATCH,ADESIVO TRANSDERMICO,COLÍRIO,COLIRIO,"
        # Sufixos e prefixos comuns
        "MG,MCG,ML,UI,UND,DOSE,"
        # Termos indicativos
        "FARMACEUTICO,DROGA,PRINCIPIO ATIVO,GENERICO,REFERENCIA,"
        "SIMILAR,VACINA,SORO,ANTIBIOTICO,ANALGESICO,ANTI-INFLAMATORIO,"
        "ANTIINFLAMATORIO,ANTITERMICO,ANTIPIRETICO,"
        # Classes terapêuticas
        "DIPIRONA,PARACETAMOL,IBUPROFENO,DICLOFENACO,OMEPRAZOL,RANITIDINA,"
        "AMOXICILINA,AZITROMICINA,CEFALEXINA,CIPROFLOXACINO,"
        "METFORMINA,GLIBENCLAMIDA,INSULINA,"
        "LOSARTANA,ENALAPRIL,CAPTOPRIL,ATENOLOL,PROPRANOLOL,"
        "SINVASTATINA,ATORVASTATINA,"
        "CLONAZEPAM,DIAZEPAM,RIVOTRIL,"
        "DEXAMETASONA,PREDNISONA,PREDNISOLONA,HIDROCORTISONA,"
        "TRAMADOL,MORFINA,CODEINA,FENTANIL,"
        "ONDANSETRONA,METOCLOPRAMIDA,BROMOPRIDA,"
        "FUROSEMIDA,HIDROCLOROTIAZIDA,ESPIRONOLACTONA,"
        "HEPARINA,ENOXAPARINA,CLEXANE,WARFARINA,"
        "ADRENALINA,EPINEFRINA,NORADRENALINA,DOPAMINA,DOBUTAMINA,"
        "FISIOLOGICO,RINGER,GLICOSADO,MANITOL,"
        "LIDOCAINA,BUPIVACAINA,ROPIVACAINA,"
        "MIDAZOLAM,PROPOFOL,KETAMINA,ETOMIDATO,"
        "ATROPINA,NEOSTIGMINA,"
        "CLOREXIDINA,IODOPOVIDONA,PVPI"
    )
    
    @property
    def material_keywords_list(self) -> list[str]:
        """Retorna keywords de material hospitalar como lista."""
        return [k.strip().upper() for k in self.material_keywords.split(",") if k.strip()]
    
    @property
    def medicamento_keywords_list(self) -> list[str]:
        """Retorna keywords de medicamentos como lista."""
        return [k.strip().upper() for k in self.medicamento_keywords.split(",") if k.strip()]
    
    # ==========================================================================
    # API
    # ==========================================================================
    api_prefix: str = ""
    cors_origins: str = "*"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna CORS origins como lista."""
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Retorna instância cacheada das configurações.
    
    Usar esta função ao invés de instanciar Settings diretamente
    para evitar recarregar o .env múltiplas vezes.
    """
    return Settings()


# Instância global para imports diretos
settings = get_settings()
