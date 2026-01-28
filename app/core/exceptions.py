# app/core/exceptions.py
"""
Exceções customizadas da aplicação.

Hierarquia:
- NFeAnalyzerError (base)
  - XMLParseError (erros de parse)
  - ValidationError (erros de validação de dados)
  - ClassificationError (erros de classificação)
  - AuditError (erros de auditoria)
"""
from __future__ import annotations

from typing import Any, Optional


class NFeAnalyzerError(Exception):
    """
    Exceção base da aplicação.
    
    Todas as exceções customizadas devem herdar desta classe.
    """
    
    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> dict[str, Any]:
        """Converte exceção para dicionário (útil para respostas HTTP)."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class XMLParseError(NFeAnalyzerError):
    """Erro ao fazer parse de XML."""
    
    def __init__(
        self,
        message: str = "Falha ao processar XML",
        *,
        filename: Optional[str] = None,
        line: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        _details = details or {}
        if filename:
            _details["filename"] = filename
        if line:
            _details["line"] = line
        
        super().__init__(message, code="XML_PARSE_ERROR", details=_details)


class XMLEmptyError(XMLParseError):
    """XML vazio ou nulo."""
    
    def __init__(self, filename: Optional[str] = None):
        super().__init__(
            message="XML vazio ou não fornecido",
            filename=filename,
        )
        self.code = "XML_EMPTY"


class XMLInvalidStructureError(XMLParseError):
    """Estrutura do XML não corresponde ao esperado (NF-e, NFSe)."""
    
    def __init__(
        self,
        message: str = "Estrutura do XML não corresponde ao formato esperado",
        *,
        expected: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        details = {}
        if expected:
            details["expected_format"] = expected
        
        super().__init__(message, filename=filename, details=details)
        self.code = "XML_INVALID_STRUCTURE"


class ValidationError(NFeAnalyzerError):
    """Erro de validação de dados."""
    
    def __init__(
        self,
        message: str,
        *,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[dict[str, Any]] = None,
    ):
        _details = details or {}
        if field:
            _details["field"] = field
        if value is not None:
            _details["value"] = str(value)[:100]  # Trunca valores muito longos
        
        super().__init__(message, code="VALIDATION_ERROR", details=_details)


class MissingRequiredFieldError(ValidationError):
    """Campo obrigatório ausente."""
    
    def __init__(self, field: str, context: Optional[str] = None):
        message = f"Campo obrigatório ausente: {field}"
        if context:
            message += f" ({context})"
        
        super().__init__(message, field=field)
        self.code = "MISSING_REQUIRED_FIELD"


class ClassificationError(NFeAnalyzerError):
    """Erro durante classificação de item/documento."""
    
    def __init__(
        self,
        message: str = "Erro ao classificar item ou documento",
        *,
        item_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        _details = details or {}
        if item_id:
            _details["item_id"] = item_id
        
        super().__init__(message, code="CLASSIFICATION_ERROR", details=_details)


class AuditError(NFeAnalyzerError):
    """Erro ao registrar evento de auditoria."""
    
    def __init__(
        self,
        message: str = "Erro ao registrar auditoria",
        *,
        event_kind: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        _details = details or {}
        if event_kind:
            _details["event_kind"] = event_kind
        
        super().__init__(message, code="AUDIT_ERROR", details=_details)


class ConfigurationError(NFeAnalyzerError):
    """Erro de configuração da aplicação."""
    
    def __init__(
        self,
        message: str,
        *,
        setting: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        _details = details or {}
        if setting:
            _details["setting"] = setting
        
        super().__init__(message, code="CONFIGURATION_ERROR", details=_details)
