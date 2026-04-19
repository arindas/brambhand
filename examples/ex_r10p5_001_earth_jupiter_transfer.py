#!/usr/bin/env python3
"""Generate replay JSONL via brambhand physics for Earth->Jupiter transfer demo."""

from __future__ import annotations

import argparse
import json
import math
import sys
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

EXAMPLE_ID = "EX-R10.5-001"
EXAMPLE_MILESTONE = "R10.5"
EXAMPLE_SLUG = "earth-jupiter-transfer"
EXAMPLE_DESCRIPTION = (
    "Reference non-optimizer mission harness for Earth->Jupiter transfer with replay-compatible "
    "maneuver/state/event provenance."
)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python" / "brambhand" / "src"))

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.gravity_model import NBodyGravityModel
from brambhand.physics.integrator import VelocityVerletIntegrator
from brambhand.physics.vector import Vector3
from brambhand.spacecraft.mass_model import MassModel
from brambhand.spacecraft.propulsion import PropulsionSystem
from brambhand.trajectory.handoff_contracts import (
    HandoffPhaseKind,
    TwoBodySOIHandoffMetadataProvider,
    build_soi_handoff_metadata,
)
from brambhand.trajectory.maneuver_contracts import MANEUVER_SCHEMA_VERSION, ManeuverCommand, ManeuverMode
from brambhand.trajectory.maneuver_executor import ManeuverExecutor
from brambhand.trajectory.replay_validation import validate_replay_probe_continuity

AU_M = 149_597_870_700.0
MU_SUN_M3_S2 = 1.32712440018e20

EARTH_ORBIT_RADIUS_M = 1.0 * AU_M
JUPITER_ORBIT_RADIUS_M = 5.2044 * AU_M
MARS_PROBE_FINAL_ORBIT_RADIUS_M = 8_000_000.0
MU_MARS_M3_S2 = 4.282837e13

MASS_KG = {
    "sun": 1.98847e30,
    "mercury": 3.3011e23,
    "venus": 4.8675e24,
    "earth": 5.97237e24,
    "mars": 6.4171e23,
    "jupiter": 1.8982e27,
    "saturn": 5.6834e26,
    "uranus": 8.6810e25,
    "neptune": 1.02413e26,
}

PLANET_ORBITAL_ELEMENTS = {
    "mercury": {"a_m": 0.3871 * AU_M, "e": 0.2056, "mean_anomaly0_rad": 1.1, "arg_periapsis_rad": 0.50},
    "venus": {"a_m": 0.7233 * AU_M, "e": 0.0068, "mean_anomaly0_rad": 2.2, "arg_periapsis_rad": 0.95},
    "earth": {"a_m": 1.0 * AU_M, "e": 0.0167, "mean_anomaly0_rad": 0.0, "arg_periapsis_rad": 1.80},
    "mars": {"a_m": 1.5237 * AU_M, "e": 0.0934, "mean_anomaly0_rad": 0.4, "arg_periapsis_rad": 5.00},
    "jupiter": {"a_m": 5.2044 * AU_M, "e": 0.0489, "mean_anomaly0_rad": 0.0, "arg_periapsis_rad": 0.25},
    "saturn": {"a_m": 9.5826 * AU_M, "e": 0.0565, "mean_anomaly0_rad": 2.9, "arg_periapsis_rad": 1.60},
    "uranus": {"a_m": 19.1913 * AU_M, "e": 0.0472, "mean_anomaly0_rad": 1.7, "arg_periapsis_rad": 2.90},
    "neptune": {"a_m": 30.07 * AU_M, "e": 0.0086, "mean_anomaly0_rad": 0.9, "arg_periapsis_rad": 4.80},
}


@dataclass
class BodyIdCatalogTracker:
    """Tracks simulation body-id lifecycle using init + per-tick diffs."""

    active_ids: set[str]
    _pending_created: set[str]
    _pending_destroyed: set[str]
    _initial_emitted: bool

    @classmethod
    def from_initial(cls, body_ids: list[str]) -> "BodyIdCatalogTracker":
        return cls(
            active_ids=set(body_ids),
            _pending_created=set(),
            _pending_destroyed=set(),
            _initial_emitted=False,
        )

    def mark_created(self, body_id: str) -> None:
        if body_id in self.active_ids:
            raise ValueError(f"body id already active: {body_id}")
        self.active_ids.add(body_id)
        self._pending_created.add(body_id)
        self._pending_destroyed.discard(body_id)

    def mark_destroyed(self, body_id: str) -> None:
        if body_id not in self.active_ids:
            raise ValueError(f"body id not active: {body_id}")
        self.active_ids.remove(body_id)
        self._pending_destroyed.add(body_id)
        self._pending_created.discard(body_id)

    def emit_frame_payload(self) -> dict[str, Any]:
        payload = {
            "schema_version": 1,
            "initial_body_ids": sorted(self.active_ids) if not self._initial_emitted else [],
            "created_body_ids": sorted(self._pending_created),
            "destroyed_body_ids": sorted(self._pending_destroyed),
        }
        self._initial_emitted = True
        self._pending_created.clear()
        self._pending_destroyed.clear()
        return payload


@dataclass(frozen=True)
class ProbeAdvanceContext:
    dt_s: float
    samples: int
    undock_index: int
    encounter_target_index: int
    maneuver_executor: ManeuverExecutor
    probe_propulsion: PropulsionSystem
    stage_dv_budget_mps: dict[str, float]


@dataclass
class ProbeAdvanceState:
    bodies: list[PhysicalBody]
    probe_mass_model: MassModel | None
    mission_stage: str
    capture_start_index: int | None
    circularization_complete_index: int | None
    capture_success_tick: int | None
    capture_failure_reason: str | None
    stage_dv_used_mps: dict[str, float]


def _build_event(
    sequence: int,
    sim_time_s: float,
    kind: str,
    severity: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "sim_time_s": sim_time_s,
        "kind": kind,
        "severity": severity,
        "payload_json": payload or {},
    }


def _solve_kepler_eccentric_anomaly(mean_anomaly_rad: float, eccentricity: float) -> float:
    m = math.fmod(mean_anomaly_rad, 2.0 * math.pi)
    if m < -math.pi:
        m += 2.0 * math.pi
    elif m > math.pi:
        m -= 2.0 * math.pi

    e_anomaly = m if eccentricity < 0.8 else math.pi
    for _ in range(20):
        f = e_anomaly - eccentricity * math.sin(e_anomaly) - m
        fp = 1.0 - eccentricity * math.cos(e_anomaly)
        if abs(fp) < 1e-12:
            break
        delta = f / fp
        e_anomaly -= delta
        if abs(delta) < 1e-12:
            break
    return e_anomaly


def _planet_position(planet: dict[str, float], sim_time_s: float) -> tuple[float, float]:
    n = math.sqrt(MU_SUN_M3_S2 / planet["a_m"]**3)
    mean_anomaly = planet["mean_anomaly0_rad"] + n * sim_time_s
    e_anomaly = _solve_kepler_eccentric_anomaly(mean_anomaly, planet["e"])

    x_orbit = planet["a_m"] * (math.cos(e_anomaly) - planet["e"])
    y_orbit = planet["a_m"] * math.sqrt(1.0 - planet["e"] * planet["e"]) * math.sin(e_anomaly)

    w = planet["arg_periapsis_rad"]
    x = x_orbit * math.cos(w) - y_orbit * math.sin(w)
    y = x_orbit * math.sin(w) + y_orbit * math.cos(w)
    return x, y


def _orbital_state_about_sun(a_m: float, e: float, mean_anomaly0_rad: float, arg_periapsis_rad: float) -> tuple[Vector3, Vector3]:
    e_anomaly = _solve_kepler_eccentric_anomaly(mean_anomaly0_rad, e)
    cos_e = math.cos(e_anomaly)
    sin_e = math.sin(e_anomaly)

    x_orb = a_m * (cos_e - e)
    y_orb = a_m * math.sqrt(1.0 - e * e) * sin_e

    n = math.sqrt(MU_SUN_M3_S2 / (a_m**3))
    denom = max(1e-12, 1.0 - e * cos_e)
    vx_orb = -a_m * n * sin_e / denom
    vy_orb = a_m * n * math.sqrt(1.0 - e * e) * cos_e / denom

    cw = math.cos(arg_periapsis_rad)
    sw = math.sin(arg_periapsis_rad)

    x = x_orb * cw - y_orb * sw
    y = x_orb * sw + y_orb * cw
    vx = vx_orb * cw - vy_orb * sw
    vy = vx_orb * sw + vy_orb * cw
    return Vector3(x, y, 0.0), Vector3(vx, vy, 0.0)


def _make_body(name: str, mass: float, pos: Vector3, vel: Vector3) -> PhysicalBody:
    return PhysicalBody(name=name, mass=mass, state=InertialState(position=pos, velocity=vel))


def _find_body(bodies: list[PhysicalBody], name: str) -> PhysicalBody:
    for body in bodies:
        if body.name == name:
            return body
    raise KeyError(name)


def _replace_body(bodies: list[PhysicalBody], updated: PhysicalBody) -> list[PhysicalBody]:
    out: list[PhysicalBody] = []
    for body in bodies:
        out.append(updated if body.name == updated.name else body)
    return out


def _init_elements_for_transfer(mars_mean_anomaly_override: float | None = None) -> dict[str, dict[str, float]]:
    elements = deepcopy(PLANET_ORBITAL_ELEMENTS)
    r1 = EARTH_ORBIT_RADIUS_M
    r2 = JUPITER_ORBIT_RADIUS_M
    a_trans = 0.5 * (r1 + r2)
    e_trans = (r2 - r1) / (r2 + r1)
    transfer_mean_motion = math.sqrt(MU_SUN_M3_S2 / a_trans**3)
    transfer_time_s = math.pi * math.sqrt(a_trans**3 / MU_SUN_M3_S2)

    # Phase Jupiter so the transfer arrival longitude matches Jupiter longitude.
    jupiter_mean_motion = math.sqrt(MU_SUN_M3_S2 / r2**3)
    elements["jupiter"]["mean_anomaly0_rad"] = math.pi - jupiter_mean_motion * transfer_time_s

    if mars_mean_anomaly_override is not None:
        elements["mars"]["mean_anomaly0_rad"] = mars_mean_anomaly_override

    return elements


def _init_bodies(mars_phase_override: float | None = None) -> list[PhysicalBody]:
    elements = _init_elements_for_transfer(mars_phase_override)
    bodies: list[PhysicalBody] = [_make_body("sun", MASS_KG["sun"], Vector3(0.0, 0.0, 0.0), Vector3(0.0, 0.0, 0.0))]

    for planet_name in sorted(elements.keys()):
        e = elements[planet_name]
        pos, vel = _orbital_state_about_sun(e["a_m"], e["e"], e["mean_anomaly0_rad"], e["arg_periapsis_rad"])
        bodies.append(_make_body(planet_name, MASS_KG[planet_name], pos, vel))

    earth = _find_body(bodies, "earth")
    r1 = EARTH_ORBIT_RADIUS_M
    r2 = JUPITER_ORBIT_RADIUS_M
    a_trans = 0.5 * (r1 + r2)
    v_transfer = math.sqrt(MU_SUN_M3_S2 * ((2.0 / r1) - (1.0 / a_trans)))

    earth_v = earth.state.velocity
    tangent_hat = earth_v.normalized()
    planned_vel = tangent_hat * v_transfer
    current_vel = tangent_hat * (v_transfer * 0.992)

    bodies.append(_make_body("planned_vehicle", 15000.0, earth.state.position, planned_vel))
    bodies.append(_make_body("current_vehicle", 18000.0, earth.state.position, current_vel))
    return bodies


def _simulate_base(samples: int, dt_s: float, mars_phase_override: float | None = None) -> list[list[PhysicalBody]]:
    gravity = NBodyGravityModel(softening_length=1_000_000.0)
    integrator = VelocityVerletIntegrator(gravity_model=gravity)
    bodies = _init_bodies(mars_phase_override)

    history: list[list[PhysicalBody]] = [bodies]
    for _ in range(samples):
        bodies = integrator.step(bodies, dt_s)
        history.append(bodies)
    return history


def _mars_relative_orbit_metrics(probe: PhysicalBody, mars: PhysicalBody) -> dict[str, float]:
    mu_mars = 4.282837e13
    rel_r = probe.state.position - mars.state.position
    rel_v = probe.state.velocity - mars.state.velocity
    r = max(1.0, rel_r.norm())
    v2 = rel_v.dot(rel_v)
    energy = 0.5 * v2 - (mu_mars / r)
    h = rel_r.x * rel_v.y - rel_r.y * rel_v.x
    e_sq = 1.0 + (2.0 * energy * h * h) / (mu_mars * mu_mars)
    e = math.sqrt(max(0.0, e_sq))

    if energy >= 0.0:
        return {"bound": 0.0, "energy": energy, "r": r, "rp": float("inf"), "ra": float("inf"), "e": e}

    a = -mu_mars / (2.0 * energy)
    rp = a * (1.0 - e)
    ra = a * (1.0 + e)
    return {"bound": 1.0, "energy": energy, "r": r, "rp": rp, "ra": ra, "e": e}


def _accel_sun_mars(probe_pos: Vector3, mars_pos: Vector3) -> Vector3:
    r_sun = max(1.0, probe_pos.norm())
    a_sun = probe_pos * (-MU_SUN_M3_S2 / (r_sun**3))

    rel = probe_pos - mars_pos
    r_mars = max(1.0, rel.norm())
    a_mars = rel * (-MU_MARS_M3_S2 / (r_mars**3))
    return a_sun + a_mars


def _propagate_probe_to_target(
    probe_pos0: Vector3,
    probe_vel0: Vector3,
    dt_s: float,
    mars_track: list[Vector3],
) -> tuple[Vector3, Vector3]:
    pos = probe_pos0
    vel = probe_vel0
    for k in range(len(mars_track) - 1):
        a0 = _accel_sun_mars(pos, mars_track[k])
        v_half = vel + a0 * (0.5 * dt_s)
        pos = pos + v_half * dt_s
        a1 = _accel_sun_mars(pos, mars_track[k + 1])
        vel = v_half + a1 * (0.5 * dt_s)
    return pos, vel


def _target_departure_velocity_single_shoot(
    probe_pos0: Vector3,
    mars_target_pos: Vector3,
    dt_s: float,
    mars_track: list[Vector3],
) -> Vector3:
    tof_s = max(dt_s, dt_s * (len(mars_track) - 1))
    vel = (mars_target_pos - probe_pos0) / tof_s  # Lambert-like straight-line seed

    eps = 1.0
    for _ in range(6):
        pos_nom, _ = _propagate_probe_to_target(probe_pos0, vel, dt_s, mars_track)
        miss = pos_nom - mars_target_pos
        if miss.norm() < 5.0e7:
            break

        pos_dx, _ = _propagate_probe_to_target(probe_pos0, vel + Vector3(eps, 0.0, 0.0), dt_s, mars_track)
        pos_dy, _ = _propagate_probe_to_target(probe_pos0, vel + Vector3(0.0, eps, 0.0), dt_s, mars_track)

        j11 = (pos_dx.x - pos_nom.x) / eps
        j12 = (pos_dy.x - pos_nom.x) / eps
        j21 = (pos_dx.y - pos_nom.y) / eps
        j22 = (pos_dy.y - pos_nom.y) / eps

        det = j11 * j22 - j12 * j21
        if abs(det) < 1e-9:
            break

        rhs_x = -miss.x
        rhs_y = -miss.y
        dvx = (rhs_x * j22 - rhs_y * j12) / det
        dvy = (j11 * rhs_y - j21 * rhs_x) / det
        dv = Vector3(dvx, dvy, 0.0)

        max_step = 1200.0
        if dv.norm() > max_step:
            dv = dv * (max_step / dv.norm())
        vel = vel + dv

    return vel


def _body_role(name: str) -> str:
    match name:
        case "sun":
            return "orbit"
        case "mars_probe":
            return "probe"
        case planet_name if planet_name in PLANET_ORBITAL_ELEMENTS:
            return "orbit"
        case _:
            return "vehicle"


def _build_body_json_payload(bodies: list[PhysicalBody]) -> list[dict[str, Any]]:
    return [
        {
            "body_id": body.name,
            "visualization_role": _body_role(body.name),
            "position_m": {
                "x": body.state.position.x,
                "y": body.state.position.y,
                "z": body.state.position.z,
            },
        }
        for body in bodies
    ]


def _append_fixed_timeline_events(
    events: list[dict[str, Any]],
    i: int,
    samples: int,
    sim_time_s: float,
) -> None:
    match i:
        case 0:
            events.append(_build_event(i, sim_time_s, "simulation_started", "info"))
            events.append(_build_event(i, sim_time_s, "departure_burn_start", "info"))
        case _ if i == max(1, samples // 20):
            events.append(_build_event(i, sim_time_s, "departure_burn_complete", "info"))
        case _ if i == samples // 3:
            events.append(_build_event(i, sim_time_s, "midcourse_correction", "warning"))
        case _ if i == (2 * samples) // 3:
            events.append(_build_event(i, sim_time_s, "jupiter_soi_entry", "warning"))
        case _ if i == max(samples - max(1, samples // 20), 1):
            events.append(_build_event(i, sim_time_s, "arrival_insertion_burn_start", "warning"))
        case _ if i == samples:
            events.append(_build_event(i, sim_time_s, "arrival_insertion_burn_complete", "critical"))
        case _:
            pass


def _append_budgeted_finite_burn_command(
    *,
    commands: list[ManeuverCommand],
    mission_stage: str,
    tick: int,
    dv_vector: Vector3,
    probe_mass_kg: float,
    dt_s: float,
    stage_dv_budget_mps: dict[str, float],
    stage_dv_used_mps: dict[str, float],
    propulsion: PropulsionSystem,
) -> str | None:
    dv_mag = dv_vector.norm()
    if dv_mag <= 1e-9:
        return None

    budget_remaining = stage_dv_budget_mps[mission_stage] - stage_dv_used_mps[mission_stage]
    if budget_remaining <= 1e-6:
        return "budget_exhausted"

    if dv_mag > budget_remaining:
        dv_vector = dv_vector * (budget_remaining / dv_mag)
        dv_mag = dv_vector.norm()

    throttle = min(1.0, (dv_mag * probe_mass_kg) / max(propulsion.max_thrust_n * dt_s, 1e-9))
    commands.append(
        ManeuverCommand(
            schema_version=MANEUVER_SCHEMA_VERSION,
            command_id=f"{mission_stage}-{tick}",
            body_id="mars_probe",
            requested_tick=tick,
            mode=ManeuverMode.FINITE_BURN_CONSTANT_THRUST,
            direction=dv_vector,
            throttle=throttle,
            duration_ticks=1,
        )
    )
    return None


def _capture_tangential_hat(rel_r: Vector3, rel_v: Vector3) -> Vector3:
    radial_hat = rel_r.normalized()
    tangential_hat = Vector3(-radial_hat.y, radial_hat.x, 0.0)
    if (rel_r.x * rel_v.y - rel_r.y * rel_v.x) < 0.0:
        tangential_hat = tangential_hat * -1.0
    return tangential_hat


def _advance_probe_if_active(
    *,
    i: int,
    context: ProbeAdvanceContext,
    state: ProbeAdvanceState,
) -> list[dict[str, Any]]:
    frame_maneuver_records: list[dict[str, Any]] = []
    if not (
        i >= context.undock_index
        and any(body.name == "mars_probe" for body in state.bodies)
        and state.probe_mass_model is not None
    ):
        return frame_maneuver_records

    probe = _find_body(state.bodies, "mars_probe")
    mars = _find_body(state.bodies, "mars")
    rel_r = probe.state.position - mars.state.position
    rel_v = probe.state.velocity - mars.state.velocity
    rmag = max(1.0, rel_r.norm())

    if state.mission_stage == "departure_correction" and i >= context.undock_index + max(2, context.samples // 24):
        state.mission_stage = "midcourse_trim"

    if state.mission_stage in {"departure_correction", "midcourse_trim"} and rmag < 6.0e9:
        state.mission_stage = "capture_burn"
        state.capture_start_index = i
        state.circularization_complete_index = min(context.samples, i + max(20, context.samples // 10))

    commands: list[ManeuverCommand] = []
    if state.capture_success_tick is None and state.capture_failure_reason is None:
        match state.mission_stage:
            case "departure_correction" | "midcourse_trim":
                match state.mission_stage:
                    case "departure_correction":
                        rendezvous_tick = context.encounter_target_index
                        stage_scale = 1.0
                    case "midcourse_trim":
                        rendezvous_tick = min(context.samples, context.encounter_target_index + max(8, context.samples // 20))
                        stage_scale = 0.65
                    case _:
                        raise RuntimeError(f"unexpected stage: {state.mission_stage}")

                remaining_time_s = max((rendezvous_tick - i) * context.dt_s, context.dt_s)
                desired_rel_vel = (mars.state.position - probe.state.position) / remaining_time_s
                target_velocity = mars.state.velocity + desired_rel_vel
                dv_cmd = (target_velocity - probe.state.velocity) * stage_scale

                state.capture_failure_reason = _append_budgeted_finite_burn_command(
                    commands=commands,
                    mission_stage=state.mission_stage,
                    tick=i,
                    dv_vector=dv_cmd,
                    probe_mass_kg=probe.mass,
                    dt_s=context.dt_s,
                    stage_dv_budget_mps=context.stage_dv_budget_mps,
                    stage_dv_used_mps=state.stage_dv_used_mps,
                    propulsion=context.probe_propulsion,
                )

            case "capture_burn" | "circularization":
                tangential_hat = _capture_tangential_hat(rel_r, rel_v)

                match state.mission_stage:
                    case "capture_burn":
                        target_radius = max(rmag, 3.0 * MARS_PROBE_FINAL_ORBIT_RADIUS_M)
                        stage_scale = 1.0
                    case "circularization":
                        target_radius = MARS_PROBE_FINAL_ORBIT_RADIUS_M
                        stage_scale = 0.55
                    case _:
                        raise RuntimeError(f"unexpected stage: {state.mission_stage}")

                target_speed = math.sqrt(MU_MARS_M3_S2 / max(target_radius, 1.0))
                target_velocity = mars.state.velocity + tangential_hat * target_speed
                dv_cap = (target_velocity - probe.state.velocity) * stage_scale

                state.capture_failure_reason = _append_budgeted_finite_burn_command(
                    commands=commands,
                    mission_stage=state.mission_stage,
                    tick=i,
                    dv_vector=dv_cap,
                    probe_mass_kg=probe.mass,
                    dt_s=context.dt_s,
                    stage_dv_budget_mps=context.stage_dv_budget_mps,
                    stage_dv_used_mps=state.stage_dv_used_mps,
                    propulsion=context.probe_propulsion,
                )
            case _:
                pass

    probe_after, mass_after, records = context.maneuver_executor.apply_tick(
        tick=i,
        dt_s=context.dt_s,
        body=probe,
        mass_model=state.probe_mass_model,
        propulsion=context.probe_propulsion,
        commands=commands,
    )
    state.probe_mass_model = mass_after
    state.bodies = _replace_body(state.bodies, probe_after)

    frame_maneuver_records = [
        {
            "command_id": record.command_id,
            "body_id": record.body_id,
            "phase_id": record.phase_id,
            "target_id": record.target_id,
            "requested_tick": record.requested_tick,
            "applied_tick": record.applied_tick,
            "mode": str(record.mode),
            "delta_v_commanded_mps": record.delta_v_commanded_mps,
            "delta_v_applied_mps": record.delta_v_applied_mps,
            "propellant_used_kg": record.propellant_used_kg,
            "termination_reason": record.termination_reason,
        }
        for record in records
    ]

    state.stage_dv_used_mps[state.mission_stage] = state.stage_dv_used_mps.get(state.mission_stage, 0.0) + sum(
        record.delta_v_applied_mps for record in records
    )

    probe_metrics = _mars_relative_orbit_metrics(probe_after, mars)
    if state.mission_stage == "capture_burn" and probe_metrics["bound"] > 0.5:
        state.mission_stage = "circularization"

    rp_ok = 0.5 * MARS_PROBE_FINAL_ORBIT_RADIUS_M <= probe_metrics["rp"] <= 4.0 * MARS_PROBE_FINAL_ORBIT_RADIUS_M
    ra_ok = probe_metrics["ra"] <= (8.0 * MARS_PROBE_FINAL_ORBIT_RADIUS_M)
    if state.capture_success_tick is None and probe_metrics["bound"] > 0.5 and rp_ok and ra_ok:
        state.capture_success_tick = i
        state.mission_stage = "insertion_complete"

    if (
        state.mission_stage in {"departure_correction", "midcourse_trim"}
        and i >= context.encounter_target_index + max(10, context.samples // 12)
        and rmag > 1.2e10
    ):
        state.capture_failure_reason = "geometry_miss"
    if (
        state.mission_stage == "circularization"
        and state.circularization_complete_index is not None
        and i >= state.circularization_complete_index
        and state.capture_success_tick is None
    ):
        state.capture_failure_reason = "capture_energy_positive"

    return frame_maneuver_records


def generate_frames(samples: int, run_id: str) -> list[dict[str, Any]]:
    if samples < 32:
        raise ValueError("samples must be >= 32")

    r1 = EARTH_ORBIT_RADIUS_M
    r2 = JUPITER_ORBIT_RADIUS_M
    a_trans = 0.5 * (r1 + r2)
    transfer_time_s = math.pi * math.sqrt(a_trans**3 / MU_SUN_M3_S2)
    dt_s = transfer_time_s / samples

    best_mars_phase = 0.0
    best_mars_miss = float("inf")
    for k in range(24):
        trial_phase = (2.0 * math.pi * k) / 24.0
        trial_history = _simulate_base(samples, dt_s, trial_phase)
        trial_miss = min(
            (
                _find_body(trial_history[i], "current_vehicle").state.position
                - _find_body(trial_history[i], "mars").state.position
            ).norm()
            for i in range(samples + 1)
        )
        if trial_miss < best_mars_miss:
            best_mars_miss = trial_miss
            best_mars_phase = trial_phase

    base_history = _simulate_base(samples, dt_s, best_mars_phase)

    closest_idx = min(
        range(samples + 1),
        key=lambda i: (
            _find_body(base_history[i], "current_vehicle").state.position
            - _find_body(base_history[i], "mars").state.position
        ).norm(),
    )

    undock_index = max(2, closest_idx - 2)
    encounter_target_index = max(undock_index + 1, closest_idx)
    mars_track_for_targeting = [
        _find_body(base_history[idx], "mars").state.position
        for idx in range(undock_index, encounter_target_index + 1)
    ]

    capture_failed_emitted = False
    stage_dv_budget_mps = {
        "departure_correction": 5000.0,
        "midcourse_trim": 2500.0,
        "capture_burn": 2200.0,
        "circularization": 1400.0,
    }

    gravity = NBodyGravityModel(softening_length=1_000_000.0)
    integrator = VelocityVerletIntegrator(gravity_model=gravity)
    initial_bodies = _init_bodies(best_mars_phase)
    body_catalog_tracker = BodyIdCatalogTracker.from_initial([body.name for body in initial_bodies])

    probe_propulsion = PropulsionSystem(max_thrust_n=1200.0, specific_impulse_s=315.0)
    probe_context = ProbeAdvanceContext(
        dt_s=dt_s,
        samples=samples,
        undock_index=undock_index,
        encounter_target_index=encounter_target_index,
        maneuver_executor=ManeuverExecutor(),
        probe_propulsion=probe_propulsion,
        stage_dv_budget_mps=stage_dv_budget_mps,
    )
    probe_state = ProbeAdvanceState(
        bodies=initial_bodies,
        probe_mass_model=None,
        mission_stage="departure_correction",
        capture_start_index=None,
        circularization_complete_index=None,
        capture_success_tick=None,
        capture_failure_reason=None,
        stage_dv_used_mps={key: 0.0 for key in stage_dv_budget_mps},
    )
    mars_handoff_provider = TwoBodySOIHandoffMetadataProvider(
        mu_primary_m3_s2=MU_MARS_M3_S2,
        sphere_of_influence_radius_m=5.77e8,
    )

    frames: list[dict[str, Any]] = []
    for i in range(samples + 1):
        sim_time_s = i * dt_s
        frame_maneuver_records: list[dict[str, Any]] = []

        match i:
            case _ if i == undock_index:
                current = _find_body(probe_state.bodies, "current_vehicle")
                mars = _find_body(probe_state.bodies, "mars")
                rel = current.state.position - mars.state.position
                rel_hat = Vector3(1.0, 0.0, 0.0) if rel.norm() < 1.0 else rel.normalized()

                probe_state.probe_mass_model = MassModel(dry_mass_kg=500.0, propellant_mass_kg=450.0)
                sep_pos = current.state.position + rel_hat * 60_000.0
                sep_vel = current.state.velocity + rel_hat * 4.0

                # Lambert-seeded and single-shoot-corrected departure velocity target.
                mars_target_pos = mars_track_for_targeting[-1]
                target_vel = _target_departure_velocity_single_shoot(
                    probe_pos0=sep_pos,
                    mars_target_pos=mars_target_pos,
                    dt_s=dt_s,
                    mars_track=mars_track_for_targeting,
                )
                sep_vel = sep_vel + (target_vel - sep_vel)

                bodies_next = list(probe_state.bodies)
                bodies_next.append(_make_body("mars_probe", probe_state.probe_mass_model.total_mass_kg, sep_pos, sep_vel))
                probe_state.bodies = bodies_next
                body_catalog_tracker.mark_created("mars_probe")
            case _:
                pass

        frame_maneuver_records = _advance_probe_if_active(
            i=i,
            context=probe_context,
            state=probe_state,
        )

        probe_handoff_payload_by_phase: dict[HandoffPhaseKind, dict[str, Any]] = {}
        if any(body.name == "mars_probe" for body in probe_state.bodies):
            probe_body = _find_body(probe_state.bodies, "mars_probe")
            mars_body = _find_body(probe_state.bodies, "mars")
            for phase_kind in (
                HandoffPhaseKind.ENCOUNTER,
                HandoffPhaseKind.CAPTURE_START,
                HandoffPhaseKind.INSERTION_COMPLETE,
            ):
                metadata = build_soi_handoff_metadata(
                    mars_handoff_provider,
                    phase_kind=phase_kind,
                    body_id="mars_probe",
                    primary_body_id="mars",
                    tick_id=i,
                    sim_time_s=sim_time_s,
                    body_position_m=probe_body.state.position,
                    body_velocity_mps=probe_body.state.velocity,
                    primary_position_m=mars_body.state.position,
                    primary_velocity_mps=mars_body.state.velocity,
                )
                payload = asdict(metadata)
                payload["phase_kind"] = str(metadata.phase_kind)
                probe_handoff_payload_by_phase[phase_kind] = payload

        events: list[dict[str, Any]] = []
        _append_fixed_timeline_events(events, i, samples, sim_time_s)

        match i:
            case _ if i == undock_index:
                events.append(_build_event(i, sim_time_s, "mars_probe_undock", "warning"))
            case _ if i == encounter_target_index and HandoffPhaseKind.ENCOUNTER in probe_handoff_payload_by_phase:
                events.append(
                    _build_event(
                        i,
                        sim_time_s,
                        "mars_probe_encounter",
                        "warning",
                        payload={"handoff": probe_handoff_payload_by_phase[HandoffPhaseKind.ENCOUNTER]},
                    )
                )
            case _:
                pass

        if probe_state.capture_start_index is not None and i == probe_state.capture_start_index:
            payload: dict[str, Any] = {}
            if HandoffPhaseKind.CAPTURE_START in probe_handoff_payload_by_phase:
                payload["handoff"] = probe_handoff_payload_by_phase[HandoffPhaseKind.CAPTURE_START]
            events.append(_build_event(i, sim_time_s, "mars_probe_capture_burn_start", "warning", payload=payload))

        if probe_state.capture_success_tick is not None and i == probe_state.capture_success_tick:
            events.append(
                _build_event(
                    i,
                    sim_time_s,
                    "mars_probe_orbit_insertion_complete",
                    "warning",
                    payload={
                        "stage_dv_used_mps": probe_state.stage_dv_used_mps,
                        "failure_reason": None,
                        "handoff": probe_handoff_payload_by_phase.get(HandoffPhaseKind.INSERTION_COMPLETE),
                    },
                )
            )

        if probe_state.capture_failure_reason is not None and not capture_failed_emitted:
            events.append(
                _build_event(
                    i,
                    sim_time_s,
                    "mars_probe_capture_failed",
                    "critical",
                    payload={
                        "failure_reason": probe_state.capture_failure_reason,
                        "stage_dv_used_mps": probe_state.stage_dv_used_mps,
                    },
                )
            )
            capture_failed_emitted = True

        if (
            i == samples
            and probe_state.capture_success_tick is None
            and not capture_failed_emitted
            and any(body.name == "mars_probe" for body in probe_state.bodies)
        ):
            events.append(
                _build_event(
                    i,
                    sim_time_s,
                    "mars_probe_capture_failed",
                    "critical",
                    payload={
                        "failure_reason": "circularization_timeout",
                        "stage_dv_used_mps": probe_state.stage_dv_used_mps,
                    },
                )
            )
            capture_failed_emitted = True

        body_json = _build_body_json_payload(probe_state.bodies)

        frames.append(
            {
                "schema_version": 1,
                "run_id": run_id,
                "tick_id": i,
                "sim_time_s": sim_time_s,
                "sequence": i,
                "body_id_catalog": body_catalog_tracker.emit_frame_payload(),
                "bodies": body_json,
                "events": events,
                "maneuver_records": frame_maneuver_records,
            }
        )

        if i < samples:
            probe_state.bodies = integrator.step(probe_state.bodies, dt_s)

    return frames


def save_jsonl(frames: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for frame in frames:
            handle.write(json.dumps(frame, sort_keys=True))
            handle.write("\n")


def save_render_config(out_path: Path) -> None:
    planet_ids = sorted(PLANET_ORBITAL_ELEMENTS.keys())
    payload = {
        "schema_version": 1,
        "dim_trajectory_body_ids": ["sun", *planet_ids],
        "focus_body_id": "sun",
        "sun_body_ids": ["sun"],
        "planet_body_ids": planet_ids,
        "probe_body_ids": ["mars_probe"],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Earth->Jupiter replay JSONL demo using brambhand physics integration."
    )
    parser.add_argument("--out", type=Path, required=True, help="Output replay JSONL path.")
    parser.add_argument("--samples", type=int, default=360, help="Transfer samples (>=32).")
    parser.add_argument("--run-id", type=str, default="ex-r10p5-001-earth-jupiter-transfer")
    parser.add_argument(
        "--render-config-out",
        type=Path,
        default=None,
        help="Output render config JSON path. Defaults to <out>.render.json",
    )
    parser.add_argument(
        "--strict-capture",
        action="store_true",
        help="Exit non-zero if Mars capture insertion-complete event is not achieved.",
    )
    parser.add_argument(
        "--strict-continuity",
        action="store_true",
        help="Exit non-zero if replay contains uncommanded mars_probe trajectory discontinuities.",
    )
    args = parser.parse_args()

    frames = generate_frames(samples=args.samples, run_id=args.run_id)
    save_jsonl(frames, args.out)

    render_config_out = args.render_config_out or args.out.with_suffix(args.out.suffix + ".render.json")
    save_render_config(render_config_out)

    has_capture_success = any(
        event["kind"] == "mars_probe_orbit_insertion_complete"
        for frame in frames
        for event in frame["events"]
    )

    discontinuities = validate_replay_probe_continuity(frames)

    print(
        f"saved={args.out} render_config={render_config_out} frames={len(frames)} transfer_time_days="
        f"{frames[-1]['sim_time_s'] / 86400.0:.2f} capture_success={has_capture_success} "
        f"probe_discontinuities={len(discontinuities)}"
    )

    if args.strict_capture and not has_capture_success:
        return 3
    if args.strict_continuity and discontinuities:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
