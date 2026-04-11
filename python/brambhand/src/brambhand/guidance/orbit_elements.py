"""Cartesian/Keplerian conversion utilities for orbital analysis.

Why this module exists:
- Provide compact orbital descriptors for planning and diagnostics.
- Enable round-trip checks and human-readable orbit inspection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from brambhand.physics.body import InertialState
from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class KeplerianElements:
    """Classical orbital elements for two-body orbits."""

    semi_major_axis_m: float
    eccentricity: float
    inclination_rad: float
    raan_rad: float
    arg_periapsis_rad: float
    true_anomaly_rad: float


def cartesian_to_keplerian(state: InertialState, mu_m3_s2: float) -> KeplerianElements:
    """Convert inertial Cartesian state to Keplerian elements."""
    if mu_m3_s2 <= 0.0:
        raise ValueError("mu_m3_s2 must be positive.")

    r = state.position
    v = state.velocity

    r_norm = r.norm()
    v_norm = v.norm()

    h = r.cross(v)
    h_norm = h.norm()

    k_hat = Vector3(0.0, 0.0, 1.0)
    n = k_hat.cross(h)
    n_norm = n.norm()

    e_vec = (v.cross(h) / mu_m3_s2) - (r / r_norm)
    e = e_vec.norm()

    specific_energy = 0.5 * v_norm * v_norm - mu_m3_s2 / r_norm
    a = -mu_m3_s2 / (2.0 * specific_energy)

    i = math.acos(h.z / h_norm)

    if n_norm > 1e-14:
        raan = math.atan2(n.y, n.x) % (2.0 * math.pi)
    else:
        raan = 0.0

    if n_norm > 1e-14 and e > 1e-12:
        argp = math.atan2(n.cross(e_vec).dot(h) / (n_norm * h_norm), n.dot(e_vec) / n_norm) % (
            2.0 * math.pi
        )
    else:
        argp = 0.0

    if e > 1e-12:
        nu_num = e_vec.cross(r).dot(h) / (e * h_norm * r_norm)
        nu_den = e_vec.dot(r) / (e * r_norm)
        nu = math.atan2(nu_num, nu_den) % (2.0 * math.pi)
    else:
        if n_norm > 1e-14:
            nu_num = n.cross(r).dot(h) / (n_norm * h_norm)
            nu_den = n.dot(r) / n_norm
            nu = math.atan2(nu_num, nu_den) % (2.0 * math.pi)
        else:
            nu = math.atan2(r.y, r.x) % (2.0 * math.pi)

    return KeplerianElements(
        semi_major_axis_m=a,
        eccentricity=e,
        inclination_rad=i,
        raan_rad=raan,
        arg_periapsis_rad=argp,
        true_anomaly_rad=nu,
    )


def keplerian_to_cartesian(elements: KeplerianElements, mu_m3_s2: float) -> InertialState:
    """Convert Keplerian elements to inertial Cartesian state."""
    if mu_m3_s2 <= 0.0:
        raise ValueError("mu_m3_s2 must be positive.")

    a = elements.semi_major_axis_m
    e = elements.eccentricity
    i = elements.inclination_rad
    raan = elements.raan_rad
    argp = elements.arg_periapsis_rad
    nu = elements.true_anomaly_rad

    p = a * (1.0 - e * e)
    r_pf = Vector3(
        p * math.cos(nu) / (1.0 + e * math.cos(nu)),
        p * math.sin(nu) / (1.0 + e * math.cos(nu)),
        0.0,
    )
    v_pf = Vector3(
        -math.sqrt(mu_m3_s2 / p) * math.sin(nu),
        math.sqrt(mu_m3_s2 / p) * (e + math.cos(nu)),
        0.0,
    )

    cos_o = math.cos(raan)
    sin_o = math.sin(raan)
    cos_i = math.cos(i)
    sin_i = math.sin(i)
    cos_w = math.cos(argp)
    sin_w = math.sin(argp)

    r11 = cos_o * cos_w - sin_o * sin_w * cos_i
    r12 = -cos_o * sin_w - sin_o * cos_w * cos_i
    r13 = sin_o * sin_i
    r21 = sin_o * cos_w + cos_o * sin_w * cos_i
    r22 = -sin_o * sin_w + cos_o * cos_w * cos_i
    r23 = -cos_o * sin_i
    r31 = sin_w * sin_i
    r32 = cos_w * sin_i
    r33 = cos_i

    r = Vector3(
        r11 * r_pf.x + r12 * r_pf.y + r13 * r_pf.z,
        r21 * r_pf.x + r22 * r_pf.y + r23 * r_pf.z,
        r31 * r_pf.x + r32 * r_pf.y + r33 * r_pf.z,
    )
    v = Vector3(
        r11 * v_pf.x + r12 * v_pf.y + r13 * v_pf.z,
        r21 * v_pf.x + r22 * v_pf.y + r23 * v_pf.z,
        r31 * v_pf.x + r32 * v_pf.y + r33 * v_pf.z,
    )

    return InertialState(position=r, velocity=v)
