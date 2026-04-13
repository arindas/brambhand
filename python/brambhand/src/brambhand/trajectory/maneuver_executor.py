"""Deterministic maneuver command contracts and per-tick execution.

Why this module exists:
- Provide first-class maneuver primitives before full optimizer integration.
- Ensure idempotent replay-safe command application semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.spacecraft.mass_model import MassModel
from brambhand.spacecraft.propulsion import PropulsionSystem
from brambhand.trajectory.maneuver_contracts import ManeuverCommand, ManeuverMode


@dataclass(frozen=True)
class BurnExecutionRecord:
    command_id: str
    body_id: str
    phase_id: str
    target_id: str
    requested_tick: int
    applied_tick: int
    mode: ManeuverMode
    delta_v_commanded_mps: float
    delta_v_applied_mps: float
    propellant_used_kg: float
    termination_reason: str


@dataclass
class ManeuverExecutor:
    _applied_impulsive_ids: set[str] = field(default_factory=set)
    _applied_finite_segments: set[tuple[str, int]] = field(default_factory=set)

    def apply_tick(
        self,
        tick: int,
        dt_s: float,
        body: PhysicalBody,
        mass_model: MassModel,
        propulsion: PropulsionSystem,
        commands: list[ManeuverCommand],
    ) -> tuple[PhysicalBody, MassModel, list[BurnExecutionRecord]]:
        if tick < 0:
            raise ValueError("tick cannot be negative")
        if dt_s <= 0.0:
            raise ValueError("dt_s must be positive")

        current_body = body
        current_mass = mass_model
        records: list[BurnExecutionRecord] = []

        applicable = sorted(
            [c for c in commands if c.body_id == body.name],
            key=lambda c: (c.requested_tick, c.command_id),
        )

        for cmd in applicable:
            if cmd.mode == ManeuverMode.IMPULSIVE:
                if tick != cmd.requested_tick or cmd.command_id in self._applied_impulsive_ids:
                    continue
                direction = cmd.direction.normalized()
                delta_v = direction * cmd.delta_v_mps
                updated_body = PhysicalBody(
                    name=current_body.name,
                    mass=current_body.mass,
                    state=InertialState(
                        position=current_body.state.position,
                        velocity=current_body.state.velocity + delta_v,
                    ),
                )
                current_body = updated_body
                self._applied_impulsive_ids.add(cmd.command_id)
                records.append(
                    BurnExecutionRecord(
                        command_id=cmd.command_id,
                        body_id=cmd.body_id,
                        phase_id=cmd.phase_id,
                        target_id=cmd.target_id,
                        requested_tick=cmd.requested_tick,
                        applied_tick=tick,
                        mode=cmd.mode,
                        delta_v_commanded_mps=cmd.delta_v_mps,
                        delta_v_applied_mps=delta_v.norm(),
                        propellant_used_kg=0.0,
                        termination_reason="nominal_cutoff",
                    )
                )
                continue

            if cmd.mode in {
                ManeuverMode.FINITE_BURN_CONSTANT_THRUST,
                ManeuverMode.FINITE_BURN_GUIDED,
            }:
                if not (cmd.requested_tick <= tick < cmd.requested_tick + cmd.duration_ticks):
                    continue
                key = (cmd.command_id, tick)
                if key in self._applied_finite_segments:
                    continue

                requested_prop = propulsion.mass_flow_rate_kgps(cmd.throttle) * dt_s
                result = propulsion.apply_burn(
                    body=current_body,
                    mass_model=current_mass,
                    direction=cmd.direction,
                    throttle=cmd.throttle,
                    duration_s=dt_s,
                )
                current_body = result.body
                current_mass = result.mass_model
                self._applied_finite_segments.add(key)
                records.append(
                    BurnExecutionRecord(
                        command_id=cmd.command_id,
                        body_id=cmd.body_id,
                        phase_id=cmd.phase_id,
                        target_id=cmd.target_id,
                        requested_tick=cmd.requested_tick,
                        applied_tick=tick,
                        mode=cmd.mode,
                        delta_v_commanded_mps=(
                            (propulsion.thrust_n(cmd.throttle) * dt_s)
                            / max(current_body.mass, 1e-9)
                        ),
                        delta_v_applied_mps=result.delta_v_mps.norm(),
                        propellant_used_kg=result.consumed_propellant_kg,
                        termination_reason=(
                            "propellant_depleted"
                            if result.consumed_propellant_kg + 1e-12 < requested_prop
                            else "nominal_cutoff"
                        ),
                    )
                )

        return current_body, current_mass, records
