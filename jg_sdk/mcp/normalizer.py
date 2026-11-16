# ==============================================================================
# Part of the javiergalvez-ia ecosystem.
# Author: Javier Gálvez
# License: MIT License
# Project URL: https://javiergalvez.com | https://gitlab.com/javiergalvez-ia/jg_agente_sdk
# ==============================================================================

"""Utilidades de normalización, truncado y cálculo criptográfico de esquemas MCP."""

import hashlib
import json
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

TRUNCATION_MARKER = "\n... [TRUNCATED_AT_64KB]"


def compute_canonical_schema_hash(tool_def: dict[str, Any]) -> str:
    """Calcula el hash SHA-256 canónico del esquema de una herramienta MCP.

    Considera de forma determinista name, description e inputSchema.
    """
    canonical_payload = {
        "name": str(tool_def.get("name", "")).strip(),
        "description": str(tool_def.get("description", "")).strip(),
        "inputSchema": tool_def.get("inputSchema") or {},
    }
    serialized = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def truncate_text(text: str, max_bytes: int = 65536) -> str:
    """Trunca el texto asegurando que su tamaño en bytes UTF-8 no supere max_bytes."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text

    marker_bytes = TRUNCATION_MARKER.encode("utf-8")
    slice_limit = max(0, max_bytes - len(marker_bytes))
    truncated_raw = encoded[:slice_limit].decode("utf-8", errors="ignore")
    return truncated_raw + TRUNCATION_MARKER


def normalize_to_json_primitives(val: Any) -> Any:
    """Normaliza recursivamente cualquier estructura a tipos primitivos JSON seguros."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    if isinstance(val, BaseModel):
        return normalize_to_json_primitives(val.model_dump())
    if isinstance(val, dict):
        return {str(k): normalize_to_json_primitives(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [normalize_to_json_primitives(item) for item in val]
    return str(val)
