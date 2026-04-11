"""CFD adapter contracts for fluid-domain provider integrations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CFDProviderProvenance:
    backend_name: str
    backend_version: str
    config_hash: str

    def __post_init__(self) -> None:
        if not self.backend_name:
            raise ValueError("backend_name must be non-empty.")
        if not self.backend_version:
            raise ValueError("backend_version must be non-empty.")
        if not self.config_hash:
            raise ValueError("config_hash must be non-empty.")
