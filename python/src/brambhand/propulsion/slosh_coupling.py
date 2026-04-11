"""Slosh boundary-payload coupling helpers."""

from __future__ import annotations

from brambhand.fluid.contracts import (
    SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    SloshBoundaryPayload,
)
from brambhand.fluid.reduced.slosh_model import SloshLoad


def build_slosh_boundary_payload(
    slosh_load: SloshLoad,
    interface_id: str,
) -> SloshBoundaryPayload:
    """Build versioned slosh boundary payload for FSI/coupling exchange contracts."""
    return SloshBoundaryPayload(
        interface_id=interface_id,
        schema_version=SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
        slosh_force_body_n=slosh_load.force_body_n,
        slosh_torque_body_nm=slosh_load.torque_body_nm,
        com_offset_body_m=slosh_load.com_offset_body_m,
    )
