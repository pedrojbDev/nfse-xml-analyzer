from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CnaeRule:
    cnae: str              # dígitos ou "*" (wildcard)
    match_type: str        # "contains" | "regex"
    pattern: str
    label: str
    severity: str          # "info" | "warning" | "error"


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def _digits_only(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    d = re.sub(r"\D+", "", str(s))
    return d or None


def _default_rules_path() -> str:
    # Permite configurar via env (caminho absoluto ou relativo)
    env_path = os.getenv("CNAE_RULES_PATH")
    if env_path:
        return env_path

    # Default: rules_cnae.csv dentro da pasta "app"
    # cnae_rules.py está em app/services/ -> parents[1] == app/
    base_app_dir = Path(__file__).resolve().parents[1]
    return str(base_app_dir / "rules_cnae.csv")



@lru_cache(maxsize=1)
def load_cnae_rules(path: Optional[str] = None) -> List[CnaeRule]:
    """
    Carrega regras de CNAE a partir de CSV (;).
    Cacheado em memória para não reler arquivo a cada request.
    """
    path_str = (path or _default_rules_path()).strip()
    p = Path(path_str)

    if not p.exists():
        return []

    rules: List[CnaeRule] = []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cnae = _norm(row.get("cnae")) or "*"
            match_type = _norm(row.get("match_type")).lower() or "contains"
            pattern = _norm(row.get("pattern"))
            label = _norm(row.get("label")) or "Regra CNAE"
            severity = _norm(row.get("severity")).lower() or "info"

            if not pattern:
                continue

            rules.append(
                CnaeRule(
                    cnae=cnae,
                    match_type=match_type,
                    pattern=pattern,
                    label=label,
                    severity=severity,
                )
            )

    return rules


def reload_cnae_rules() -> None:
    """Força recarregar regras (limpa cache)."""
    load_cnae_rules.cache_clear()


def validate_cnae_vs_descricao(
    cnae: Optional[str],
    descricao: Optional[str],
    rules_path: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """
    Retorna um dict padronizado para anexar no item:
      status: "ok" | "alert" | "unknown"
      rule_label, severity, rule_pattern, rule_cnae
      reason (texto curto)
    """
    cnae_norm = _digits_only(cnae)
    desc = (descricao or "").strip()

    if not cnae_norm or not desc:
        return {
            "status": "unknown",
            "rule_label": None,
            "severity": None,
            "rule_pattern": None,
            "rule_cnae": None,
            "reason": "CNAE ou descrição ausente",
        }

    rules = load_cnae_rules(rules_path)
    if not rules:
        return {
            "status": "unknown",
            "rule_label": None,
            "severity": None,
            "rule_pattern": None,
            "rule_cnae": None,
            "reason": "Sem arquivo de regras configurado",
        }

    desc_up = desc.upper()

    # Regras específicas do CNAE primeiro + wildcard depois
    scoped = [r for r in rules if r.cnae == cnae_norm]
    wild = [r for r in rules if r.cnae == "*"]
    candidates = scoped + wild

    for r in candidates:
        if r.match_type == "contains":
            if r.pattern.upper() in desc_up:
                return {
                    "status": "ok",
                    "rule_label": r.label,
                    "severity": r.severity,
                    "rule_pattern": r.pattern,
                    "rule_cnae": r.cnae,
                    "reason": "Descrição compatível com regra",
                }
        elif r.match_type == "regex":
            if re.search(r.pattern, desc, flags=re.IGNORECASE):
                return {
                    "status": "ok",
                    "rule_label": r.label,
                    "severity": r.severity,
                    "rule_pattern": r.pattern,
                    "rule_cnae": r.cnae,
                    "reason": "Descrição compatível com regex",
                }

    # Se existem regras específicas para o CNAE e nenhuma bateu => ALERTA
    if scoped:
        return {
            "status": "alert",
            "rule_label": None,
            "severity": "warning",
            "rule_pattern": None,
            "rule_cnae": cnae_norm,
            "reason": "Nenhuma regra do CNAE bateu com a descrição",
        }

    # Sem regra específica para esse CNAE => unknown (para não gerar falso positivo)
    return {
        "status": "unknown",
        "rule_label": None,
        "severity": None,
        "rule_pattern": None,
        "rule_cnae": cnae_norm,
        "reason": "Sem regra cadastrada para este CNAE",
    }
