from __future__ import annotations
from pathlib import Path
import csv
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CnaeRule:
    cnae: str              # ex: "8610101", "8610*", "*" (wildcard global)
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
    """
    Resolve o caminho do CSV de regras de forma robusta.

    Estrutura do projeto:
      app/
        rules_cnae.csv
        services/
          cnae_rules.py

    Logo, a pasta "app" é o parent da pasta "services".
    """
    env = os.getenv("CNAE_RULES_PATH")
    if env and env.strip():
        return env.strip()

    app_dir = Path(__file__).resolve().parents[1]  # .../app
    return str(app_dir / "rules_cnae.csv")


def _rule_applies(rule_cnae: str, cnae_norm: str) -> bool:
    """
    Matching de escopo de CNAE:
      - "*" aplica a tudo
      - "8610101" aplica exato
      - "8610*" aplica por prefixo (8610...)
    """
    rc = (rule_cnae or "").strip()
    if not rc:
        return False

    if rc == "*":
        return True

    # prefix wildcard
    if rc.endswith("*"):
        prefix = _digits_only(rc[:-1]) or ""
        return bool(prefix) and cnae_norm.startswith(prefix)

    # exact
    return _digits_only(rc) == cnae_norm


def _rule_specificity(rule_cnae: str) -> int:
    """
    Quanto maior, mais específica:
      - CNAE exato: 3
      - prefixo (ex: 8610*): 2
      - wildcard "*": 1
    """
    rc = (rule_cnae or "").strip()
    if rc == "*":
        return 1
    if rc.endswith("*"):
        return 2
    return 3


@lru_cache(maxsize=1)
def load_cnae_rules(path: Optional[str] = None) -> List[CnaeRule]:
    path = path or _default_rules_path()
    if not os.path.exists(path):
        return []

    rules: List[CnaeRule] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
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

    # ordena por especificidade (exato > prefixo > wildcard)
    rules.sort(key=lambda r: _rule_specificity(r.cnae), reverse=True)
    return rules


def reload_cnae_rules() -> None:
    load_cnae_rules.cache_clear()


def validate_cnae_vs_descricao(
    cnae: Optional[str],
    descricao: Optional[str],
    rules_path: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    cnae_norm = _digits_only(cnae)
    desc = (descricao or "").strip()

    if not cnae_norm or not desc:
        return {
            "status": "unknown",
            "rule_label": None,
            "severity": None,
            "rule_pattern": None,
            "rule_cnae": cnae_norm,
            "reason": "CNAE ou descrição ausente",
        }

    rules = load_cnae_rules(rules_path)
    if not rules:
        return {
            "status": "unknown",
            "rule_label": None,
            "severity": None,
            "rule_pattern": None,
            "rule_cnae": cnae_norm,
            "reason": "Sem arquivo de regras configurado",
        }

    desc_up = desc.upper()

    # candidatos que aplicam ao CNAE
    applicable = [r for r in rules if _rule_applies(r.cnae, cnae_norm)]

    # se NÃO existe nenhuma regra específica/prefixo para esse CNAE, só wildcard -> unknown (evita falso positivo)
    has_specific_scope = any((r.cnae != "*") and _rule_applies(r.cnae, cnae_norm) for r in rules)

    for r in applicable:
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

    # existe regra específica para esse CNAE (ou prefixo) mas nenhuma bateu => alert
    if has_specific_scope:
        return {
            "status": "alert",
            "rule_label": None,
            "severity": "warning",
            "rule_pattern": None,
            "rule_cnae": cnae_norm,
            "reason": "Nenhuma regra aplicável bateu com a descrição",
        }

    # só wildcard global existe => unknown
    return {
        "status": "unknown",
        "rule_label": None,
        "severity": None,
        "rule_pattern": None,
        "rule_cnae": cnae_norm,
        "reason": "Sem regra cadastrada para este CNAE",
    }
