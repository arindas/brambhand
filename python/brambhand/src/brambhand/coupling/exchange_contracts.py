"""FSI exchange contracts integrating topology and propulsion boundary payloads."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.fluid.contracts import (
    LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION,
    FluidBoundaryLoad,
    LeakJetBoundaryPayload,
    SloshBoundaryPayload,
    TopologyTransitionPayload,
)
from brambhand.physics.vector import Vector3

FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class FSIBoundaryExchangeContract:
    """Versioned contract consumed by FSI coupler/controller exchange paths."""

    schema_version: int
    topology_transition: TopologyTransitionPayload | None
    leak_jet_payloads: tuple[LeakJetBoundaryPayload, ...]
    slosh_payloads: tuple[SloshBoundaryPayload, ...]
    fluid_boundary_loads: tuple[FluidBoundaryLoad, ...]

    def __post_init__(self) -> None:
        if self.schema_version != FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION:
            raise ValueError("Unsupported FSI boundary exchange schema_version.")
        if self.topology_transition is not None:
            if (
                self.topology_transition.schema_version
                != TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION
            ):
                raise ValueError("Unsupported topology transition payload schema_version.")
        if any(
            payload.schema_version != LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION
            for payload in self.leak_jet_payloads
        ):
            raise ValueError("Unsupported leak-jet payload schema_version.")
        if any(
            payload.schema_version != SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION
            for payload in self.slosh_payloads
        ):
            raise ValueError("Unsupported slosh payload schema_version.")


@dataclass(frozen=True)
class _AggregateBoundaryLoad:
    force_body_n: Vector3
    torque_body_nm: Vector3
    mass_flow_kgps: float
    temperature_mass_flow_weighted_sum: float
    zero_mass_temperature_sum: float
    zero_mass_temperature_count: int


def _aggregate_temperature_k(data: _AggregateBoundaryLoad) -> float:
    if data.mass_flow_kgps > 0.0:
        return data.temperature_mass_flow_weighted_sum / data.mass_flow_kgps
    if data.zero_mass_temperature_count > 0:
        return data.zero_mass_temperature_sum / data.zero_mass_temperature_count
    return 273.15


def _aggregate_boundary_loads(
    loads: tuple[FluidBoundaryLoad, ...],
) -> tuple[FluidBoundaryLoad, ...]:
    by_interface: dict[str, _AggregateBoundaryLoad] = {}

    for load in loads:
        current = by_interface.get(
            load.interface_id,
            _AggregateBoundaryLoad(
                force_body_n=Vector3(0.0, 0.0, 0.0),
                torque_body_nm=Vector3(0.0, 0.0, 0.0),
                mass_flow_kgps=0.0,
                temperature_mass_flow_weighted_sum=0.0,
                zero_mass_temperature_sum=0.0,
                zero_mass_temperature_count=0,
            ),
        )
        if load.mass_flow_kgps > 0.0:
            temperature_mass_flow_weighted_sum = (
                current.temperature_mass_flow_weighted_sum
                + load.mass_flow_kgps * load.temperature_k
            )
            zero_mass_temperature_sum = current.zero_mass_temperature_sum
            zero_mass_temperature_count = current.zero_mass_temperature_count
        else:
            temperature_mass_flow_weighted_sum = current.temperature_mass_flow_weighted_sum
            zero_mass_temperature_sum = current.zero_mass_temperature_sum + load.temperature_k
            zero_mass_temperature_count = current.zero_mass_temperature_count + 1

        by_interface[load.interface_id] = _AggregateBoundaryLoad(
            force_body_n=current.force_body_n + load.force_body_n,
            torque_body_nm=current.torque_body_nm + load.torque_body_nm,
            mass_flow_kgps=current.mass_flow_kgps + load.mass_flow_kgps,
            temperature_mass_flow_weighted_sum=temperature_mass_flow_weighted_sum,
            zero_mass_temperature_sum=zero_mass_temperature_sum,
            zero_mass_temperature_count=zero_mass_temperature_count,
        )

    return tuple(
        FluidBoundaryLoad(
            interface_id=interface_id,
            force_body_n=data.force_body_n,
            torque_body_nm=data.torque_body_nm,
            mass_flow_kgps=data.mass_flow_kgps,
            temperature_k=_aggregate_temperature_k(data),
        )
        for interface_id, data in sorted(by_interface.items())
    )


def build_fsi_boundary_exchange_contract(
    *,
    topology_transition: TopologyTransitionPayload | None,
    leak_jet_payloads: tuple[LeakJetBoundaryPayload, ...],
    slosh_payloads: tuple[SloshBoundaryPayload, ...],
) -> FSIBoundaryExchangeContract:
    """Build deterministic FSI exchange contract from topology + propulsion payloads."""
    converted_loads_list: list[FluidBoundaryLoad] = []
    for payload in leak_jet_payloads:
        converted_loads_list.append(payload.to_fluid_boundary_load())
    for slosh_payload in slosh_payloads:
        converted_loads_list.append(slosh_payload.to_fluid_boundary_load())
    converted_loads = tuple(converted_loads_list)
    return FSIBoundaryExchangeContract(
        schema_version=FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION,
        topology_transition=topology_transition,
        leak_jet_payloads=tuple(sorted(leak_jet_payloads, key=lambda item: item.interface_id)),
        slosh_payloads=tuple(sorted(slosh_payloads, key=lambda item: item.interface_id)),
        fluid_boundary_loads=_aggregate_boundary_loads(converted_loads),
    )
