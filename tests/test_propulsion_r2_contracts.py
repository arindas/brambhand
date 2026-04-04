import math

from brambhand.propulsion.combustion_model import (
    CombustionChamberParams,
    CombustionChamberState,
    step_combustion_chamber,
)
from brambhand.propulsion.fluid_network import (
    FluidNetworkState,
    LineState,
    TankState,
    ValveState,
    step_fluid_network,
)
from brambhand.propulsion.leakage_model import CompartmentState, LeakagePath, apply_leakage
from brambhand.propulsion.thrust_estimator import (
    NozzleGeometryCorrection,
    NozzleParams,
    estimate_nozzle_thrust,
)


def test_fluid_network_delivers_mass_and_depletes_tank() -> None:
    state = FluidNetworkState(
        tank=TankState(
            mass_kg=10.0,
            nominal_mass_kg=10.0,
            nominal_pressure_pa=2_000_000.0,
            temperature_k=290.0,
        ),
        valve=ValveState(opening=0.5, flow_coefficient=1e-3),
        line=LineState(max_flow_kgps=2.0),
        downstream_pressure_pa=1_000_000.0,
    )

    next_state = step_fluid_network(state, dt_s=1.0)

    assert next_state.delivered_mass_flow_kgps > 0.0
    assert next_state.tank.mass_kg < state.tank.mass_kg
    assert next_state.tank.pressure_pa < state.tank.pressure_pa


def test_combustion_chamber_ideal_gas_update() -> None:
    params = CombustionChamberParams(volume_m3=0.2, gas_constant_jpkgk=300.0, temperature_k=2500.0)
    state = CombustionChamberState(gas_mass_kg=1.0, pressure_pa=0.0)

    next_state = step_combustion_chamber(state, params, inflow_kgps=0.5, outflow_kgps=0.1, dt_s=2.0)

    expected_mass = 1.0 + (0.5 - 0.1) * 2.0
    expected_pressure = expected_mass * 300.0 * 2500.0 / 0.2

    assert math.isclose(next_state.gas_mass_kg, expected_mass)
    assert math.isclose(next_state.pressure_pa, expected_pressure)


def test_thrust_estimator_matches_momentum_plus_pressure_term() -> None:
    nozzle = NozzleParams(
        exit_area_m2=0.05,
        ambient_pressure_pa=101_325.0,
        exhaust_velocity_mps=2500.0,
    )
    estimate = estimate_nozzle_thrust(
        chamber_pressure_pa=2_000_000.0,
        mass_flow_kgps=12.0,
        nozzle=nozzle,
    )

    expected = 12.0 * 2500.0 + (2_000_000.0 - 101_325.0) * 0.05
    assert math.isclose(estimate.thrust_n, expected)


def test_nozzle_geometry_area_ratio_influences_thrust() -> None:
    nozzle = NozzleParams(
        exit_area_m2=0.06,
        ambient_pressure_pa=101_325.0,
        exhaust_velocity_mps=2600.0,
    )

    low_ratio = NozzleGeometryCorrection(throat_area_m2=0.03, contour_loss_factor=1.0)
    high_ratio = NozzleGeometryCorrection(throat_area_m2=0.01, contour_loss_factor=1.0)

    low = estimate_nozzle_thrust(
        chamber_pressure_pa=2_000_000.0,
        mass_flow_kgps=10.0,
        nozzle=nozzle,
        geometry=low_ratio,
    )
    high = estimate_nozzle_thrust(
        chamber_pressure_pa=2_000_000.0,
        mass_flow_kgps=10.0,
        nozzle=nozzle,
        geometry=high_ratio,
    )

    assert high.thrust_n > low.thrust_n


def test_nozzle_geometry_contour_loss_reduces_thrust() -> None:
    nozzle = NozzleParams(
        exit_area_m2=0.06,
        ambient_pressure_pa=101_325.0,
        exhaust_velocity_mps=2600.0,
    )
    ideal = NozzleGeometryCorrection(throat_area_m2=0.02, contour_loss_factor=1.0)
    lossy = NozzleGeometryCorrection(throat_area_m2=0.02, contour_loss_factor=0.9)

    ideal_estimate = estimate_nozzle_thrust(
        chamber_pressure_pa=2_000_000.0,
        mass_flow_kgps=10.0,
        nozzle=nozzle,
        geometry=ideal,
    )
    lossy_estimate = estimate_nozzle_thrust(
        chamber_pressure_pa=2_000_000.0,
        mass_flow_kgps=10.0,
        nozzle=nozzle,
        geometry=lossy,
    )

    assert lossy_estimate.thrust_n < ideal_estimate.thrust_n


def test_propulsion_contracts_reject_invalid_inputs() -> None:
    try:
        CombustionChamberParams(volume_m3=0.0, gas_constant_jpkgk=300.0, temperature_k=2500.0)
    except ValueError as exc:
        assert "volume_m3 must be positive" in str(exc)
    else:
        raise AssertionError("Expected combustion params validation failure")

    try:
        step_combustion_chamber(
            CombustionChamberState(gas_mass_kg=1.0, pressure_pa=1.0),
            CombustionChamberParams(volume_m3=0.2, gas_constant_jpkgk=300.0, temperature_k=2500.0),
            inflow_kgps=-1.0,
            outflow_kgps=0.0,
            dt_s=1.0,
        )
    except ValueError as exc:
        assert "must be non-negative" in str(exc)
    else:
        raise AssertionError("Expected combustion flow validation failure")

    try:
        TankState(
            mass_kg=1.0,
            nominal_mass_kg=10.0,
            nominal_pressure_pa=2_000_000.0,
            temperature_k=0.0,
        )
    except ValueError as exc:
        assert "temperature_k must be positive" in str(exc)
    else:
        raise AssertionError("Expected tank validation failure")

    try:
        NozzleGeometryCorrection(throat_area_m2=0.01, contour_loss_factor=1.1)
    except ValueError as exc:
        assert "contour_loss_factor" in str(exc)
    else:
        raise AssertionError("Expected contour-loss validation failure")


def test_propulsion_edge_paths_zero_flow_and_no_leak_delta_p() -> None:
    closed = FluidNetworkState(
        tank=TankState(
            mass_kg=10.0,
            nominal_mass_kg=10.0,
            nominal_pressure_pa=2_000_000.0,
            temperature_k=290.0,
        ),
        valve=ValveState(opening=0.0, flow_coefficient=1e-3),
        line=LineState(max_flow_kgps=2.0),
        downstream_pressure_pa=1_000_000.0,
    )
    closed_next = step_fluid_network(closed, dt_s=1.0)
    assert closed_next.delivered_mass_flow_kgps == 0.0

    state = CompartmentState(
        mass_kg=4.0,
        pressure_pa=100_000.0,
        volume_m3=1.0,
        gas_constant_jpkgk=287.0,
        temperature_k=300.0,
    )
    leak = LeakagePath(
        area_m2=1e-4,
        discharge_coefficient=0.7,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
    )
    unchanged, leaked = apply_leakage(state, leak, dt_s=1.0)
    assert leaked == 0.0
    assert unchanged == state


def test_leakage_reduces_mass_and_pressure() -> None:
    state = CompartmentState(
        mass_kg=4.0,
        pressure_pa=500_000.0,
        volume_m3=1.0,
        gas_constant_jpkgk=287.0,
        temperature_k=300.0,
    )
    leak = LeakagePath(
        area_m2=1e-4,
        discharge_coefficient=0.7,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
    )

    next_state, leaked = apply_leakage(state, leak, dt_s=1.0)

    assert leaked > 0.0
    assert next_state.mass_kg < state.mass_kg
    assert next_state.pressure_pa < state.pressure_pa
