import math

from brambhand.dynamics.rigid_body_6dof import (
    RigidBody6DoFState,
    RigidBodyProperties,
    UnitQuaternion,
)
from brambhand.fluid.contracts import (
    LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    LeakJetBoundaryPayload,
    SloshBoundaryPayload,
)
from brambhand.fluid.reduced.chamber_flow import (
    ChamberFlowParams,
    ChamberFlowState,
    step_chamber_flow,
)
from brambhand.fluid.reduced.leak_jet_dynamics import LeakJetPath, evaluate_leak_jet
from brambhand.fluid.reduced.slosh_model import (
    SloshFallbackParams,
    SloshGeometryDescriptor,
    SloshModelParams,
    SloshState,
    derive_slosh_model_params,
    step_slosh_state,
)
from brambhand.physics.vector import Vector3
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
from brambhand.propulsion.leak_jet_coupling import (
    build_leak_jet_boundary_payload,
    propagate_leak_jet_to_rigid_body,
)
from brambhand.propulsion.leakage_model import CompartmentState, LeakagePath, apply_leakage
from brambhand.propulsion.performance import (
    ReducedOrderFallbackMode,
    apply_slosh_degraded_mode,
    benchmark_reduced_order_propulsion_latency,
    benchmark_reduced_order_slosh_latency,
    cadence_guard_mode,
)
from brambhand.propulsion.slosh_6dof_coupling import propagate_slosh_to_rigid_body
from brambhand.propulsion.slosh_coupling import build_slosh_boundary_payload
from brambhand.propulsion.thrust_estimator import (
    ChamberThrustCouplingParams,
    NozzleGeometryCorrection,
    NozzleParams,
    estimate_nozzle_thrust,
    estimate_nozzle_thrust_from_chamber_flow,
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


def test_chamber_flow_step_updates_state_and_emits_diagnostics() -> None:
    params = ChamberFlowParams(
        volume_m3=0.2,
        gas_constant_jpkgk=300.0,
        stoichiometric_of_ratio=3.0,
        min_temperature_k=1200.0,
        max_temperature_k=3200.0,
        thermal_relaxation_time_constant_s=0.5,
    )
    state = ChamberFlowState(
        gas_mass_kg=1.0,
        pressure_pa=1_000_000.0,
        temperature_k=1500.0,
        fuel_mass_fraction=0.3,
    )

    result = step_chamber_flow(
        state=state,
        params=params,
        inflow_fuel_kgps=0.8,
        inflow_oxidizer_kgps=2.4,
        throat_outflow_kgps=2.0,
        dt_s=0.1,
    )

    assert result.state.gas_mass_kg > 0.0
    assert result.state.pressure_pa > 0.0
    assert params.min_temperature_k <= result.state.temperature_k <= params.max_temperature_k
    assert 0.0 <= result.diagnostics.mixing_quality <= 1.0
    assert result.diagnostics.injector_mass_flow_kgps == 3.2
    assert result.diagnostics.throat_mass_flow_kgps == 2.0


def test_chamber_flow_mixing_quality_worsens_for_off_stoich_input() -> None:
    params = ChamberFlowParams(
        volume_m3=0.2,
        gas_constant_jpkgk=300.0,
        stoichiometric_of_ratio=3.0,
        min_temperature_k=1200.0,
        max_temperature_k=3200.0,
        thermal_relaxation_time_constant_s=0.5,
    )
    state = ChamberFlowState(
        gas_mass_kg=0.5,
        pressure_pa=500_000.0,
        temperature_k=1400.0,
        fuel_mass_fraction=0.25,
    )

    near_stoich = step_chamber_flow(
        state=state,
        params=params,
        inflow_fuel_kgps=0.4,
        inflow_oxidizer_kgps=1.2,
        throat_outflow_kgps=1.0,
        dt_s=0.1,
    )
    fuel_rich = step_chamber_flow(
        state=state,
        params=params,
        inflow_fuel_kgps=0.9,
        inflow_oxidizer_kgps=0.2,
        throat_outflow_kgps=1.0,
        dt_s=0.1,
    )

    assert near_stoich.diagnostics.mixing_quality > fuel_rich.diagnostics.mixing_quality


def test_thrust_coupling_from_chamber_flow_matches_proxy_mass_flow() -> None:
    chamber_state = ChamberFlowState(
        gas_mass_kg=1.2,
        pressure_pa=1_800_000.0,
        temperature_k=2200.0,
        fuel_mass_fraction=0.25,
    )
    nozzle = NozzleParams(
        exit_area_m2=0.05,
        ambient_pressure_pa=101_325.0,
        exhaust_velocity_mps=2550.0,
    )
    coupling = ChamberThrustCouplingParams(
        gas_constant_jpkgk=300.0,
        throat_area_m2=0.012,
        throat_discharge_coefficient=0.92,
    )

    coupled = estimate_nozzle_thrust_from_chamber_flow(
        chamber_state=chamber_state,
        nozzle=nozzle,
        coupling=coupling,
    )

    proxy_mass_flow = (
        coupling.throat_discharge_coefficient
        * coupling.throat_area_m2
        * chamber_state.pressure_pa
        / math.sqrt(coupling.gas_constant_jpkgk * chamber_state.temperature_k)
    )
    direct = estimate_nozzle_thrust(
        chamber_pressure_pa=chamber_state.pressure_pa,
        mass_flow_kgps=proxy_mass_flow,
        nozzle=nozzle,
    )

    assert math.isclose(coupled.thrust_n, direct.thrust_n)
    assert math.isclose(coupled.momentum_thrust_n, direct.momentum_thrust_n)
    assert math.isclose(coupled.pressure_thrust_n, direct.pressure_thrust_n)


def test_thrust_coupling_from_chamber_flow_respects_geometry_correction() -> None:
    chamber_state = ChamberFlowState(
        gas_mass_kg=1.0,
        pressure_pa=2_000_000.0,
        temperature_k=2300.0,
        fuel_mass_fraction=0.25,
    )
    nozzle = NozzleParams(
        exit_area_m2=0.06,
        ambient_pressure_pa=101_325.0,
        exhaust_velocity_mps=2600.0,
    )
    coupling = ChamberThrustCouplingParams(
        gas_constant_jpkgk=300.0,
        throat_area_m2=0.015,
        throat_discharge_coefficient=1.0,
    )
    ideal = NozzleGeometryCorrection(throat_area_m2=0.015, contour_loss_factor=1.0)
    lossy = NozzleGeometryCorrection(throat_area_m2=0.015, contour_loss_factor=0.9)

    ideal_estimate = estimate_nozzle_thrust_from_chamber_flow(
        chamber_state=chamber_state,
        nozzle=nozzle,
        coupling=coupling,
        geometry=ideal,
    )
    lossy_estimate = estimate_nozzle_thrust_from_chamber_flow(
        chamber_state=chamber_state,
        nozzle=nozzle,
        coupling=coupling,
        geometry=lossy,
    )

    assert lossy_estimate.thrust_n < ideal_estimate.thrust_n


def test_leak_jet_dynamics_produces_reaction_force_and_torque() -> None:
    path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
        lever_arm_body_m=Vector3(0.0, 0.5, 0.0),
    )

    state = evaluate_leak_jet(
        path=path,
        compartment_pressure_pa=300_000.0,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
    )

    assert state.mass_flow_kgps > 0.0
    assert state.exit_velocity_mps > 0.0
    assert state.reaction_force_body_n.x < 0.0
    assert state.reaction_torque_body_nm.z > 0.0


def test_leak_jet_dynamics_zero_delta_p_returns_zero_wrench() -> None:
    path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(0.0, 1.0, 0.0),
    )

    state = evaluate_leak_jet(
        path=path,
        compartment_pressure_pa=90_000.0,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
    )

    assert state.mass_flow_kgps == 0.0
    assert state.exit_velocity_mps == 0.0
    assert state.reaction_force_body_n == Vector3(0.0, 0.0, 0.0)
    assert state.reaction_torque_body_nm == Vector3(0.0, 0.0, 0.0)
    assert state.jet_temperature_k == 280.0


def test_leak_jet_propagates_into_6dof_body_frame_dynamics() -> None:
    leak_path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )
    leak = evaluate_leak_jet(
        path=leak_path,
        compartment_pressure_pa=300_000.0,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
    )

    state = RigidBody6DoFState(
        position_m=Vector3(0.0, 0.0, 0.0),
        velocity_mps=Vector3(0.0, 0.0, 0.0),
        attitude=UnitQuaternion(1.0, 0.0, 0.0, 0.0),
        angular_velocity_radps=Vector3(0.0, 0.0, 0.0),
    )
    props = RigidBodyProperties(mass_kg=100.0, inertia_diag_kgm2=(20.0, 20.0, 20.0))

    next_state = propagate_leak_jet_to_rigid_body(
        state=state,
        props=props,
        leak_jet=leak,
        dt_s=0.1,
    )

    assert next_state.velocity_mps.x < 0.0


def test_leak_jet_body_frame_coupling_respects_attitude_rotation() -> None:
    leak_path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )
    leak = evaluate_leak_jet(
        path=leak_path,
        compartment_pressure_pa=300_000.0,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
    )

    q = UnitQuaternion.normalized(math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))
    state = RigidBody6DoFState(
        position_m=Vector3(0.0, 0.0, 0.0),
        velocity_mps=Vector3(0.0, 0.0, 0.0),
        attitude=q,
        angular_velocity_radps=Vector3(0.0, 0.0, 0.0),
    )
    props = RigidBodyProperties(mass_kg=100.0, inertia_diag_kgm2=(20.0, 20.0, 20.0))

    next_state = propagate_leak_jet_to_rigid_body(
        state=state,
        props=props,
        leak_jet=leak,
        dt_s=0.1,
    )

    assert abs(next_state.velocity_mps.x) < 1e-9
    assert next_state.velocity_mps.y < 0.0


def test_leak_jet_boundary_payload_contract_mapping() -> None:
    path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )
    leak = evaluate_leak_jet(
        path=path,
        compartment_pressure_pa=300_000.0,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
    )

    payload = build_leak_jet_boundary_payload(leak_jet=leak, interface_id="tank_A_leak_1")

    assert payload.schema_version == LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION
    boundary = payload.to_fluid_boundary_load()
    assert boundary.interface_id == "tank_A_leak_1"
    assert boundary.force_body_n == leak.reaction_force_body_n
    assert boundary.torque_body_nm == leak.reaction_torque_body_nm


def test_leak_jet_boundary_payload_rejects_unsupported_version() -> None:
    try:
        LeakJetBoundaryPayload(
            interface_id="ifc",
            schema_version=999,
            reaction_force_body_n=Vector3(0.0, 0.0, 0.0),
            reaction_torque_body_nm=Vector3(0.0, 0.0, 0.0),
            mass_flow_kgps=0.0,
            jet_temperature_k=300.0,
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected leak-jet boundary payload version validation failure")


def test_slosh_boundary_payload_contract_mapping() -> None:
    slosh_result = step_slosh_state(
        state=SloshState(
            displacement_body_m=Vector3(0.0, 0.0, 0.0),
            velocity_body_mps=Vector3(0.0, 0.0, 0.0),
        ),
        params=SloshModelParams(
            slosh_mass_kg=10.0,
            spring_constant_npm=200.0,
            damping_nspm=5.0,
            max_displacement_m=0.2,
            lever_arm_body_m=Vector3(0.0, 0.5, 0.0),
        ),
        body_linear_accel_body_mps2=Vector3(1.0, 0.0, 0.0),
        dt_s=0.1,
    )

    payload = build_slosh_boundary_payload(slosh_result.load, interface_id="tank_A_slosh")

    assert payload.schema_version == SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION
    assert payload.com_offset_body_m == slosh_result.load.com_offset_body_m
    boundary = payload.to_fluid_boundary_load()
    assert boundary.interface_id == "tank_A_slosh"
    assert boundary.force_body_n == slosh_result.load.force_body_n
    assert boundary.torque_body_nm == slosh_result.load.torque_body_nm
    assert boundary.mass_flow_kgps == 0.0


def test_slosh_boundary_payload_rejects_unsupported_version() -> None:
    try:
        SloshBoundaryPayload(
            interface_id="ifc",
            schema_version=999,
            slosh_force_body_n=Vector3(0.0, 0.0, 0.0),
            slosh_torque_body_nm=Vector3(0.0, 0.0, 0.0),
            com_offset_body_m=Vector3(0.0, 0.0, 0.0),
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected slosh boundary payload version validation failure")


def test_leak_jet_force_is_consistent_with_momentum_plus_pressure_terms() -> None:
    path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )
    compartment_pressure_pa = 300_000.0

    leak = evaluate_leak_jet(
        path=path,
        compartment_pressure_pa=compartment_pressure_pa,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
    )

    delta_p = compartment_pressure_pa - path.external_pressure_pa
    expected_thrust = leak.mass_flow_kgps * leak.exit_velocity_mps + delta_p * path.area_m2
    assert math.isclose(leak.reaction_force_body_n.norm(), expected_thrust)


def test_leak_jet_mass_flow_matches_leakage_mass_loss_rate_envelope() -> None:
    pressure_pa = 300_000.0
    dt_s = 0.2

    leak_state = CompartmentState(
        mass_kg=100.0,
        pressure_pa=pressure_pa,
        volume_m3=10.0,
        gas_constant_jpkgk=287.0,
        temperature_k=320.0,
    )
    leakage_path = LeakagePath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
    )
    leak_jet_path = LeakJetPath(
        area_m2=leakage_path.area_m2,
        discharge_coefficient=leakage_path.discharge_coefficient,
        fluid_density_kgpm3=leakage_path.fluid_density_kgpm3,
        external_pressure_pa=leakage_path.external_pressure_pa,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )

    leak_jet = evaluate_leak_jet(
        path=leak_jet_path,
        compartment_pressure_pa=pressure_pa,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
    )
    _, leaked_mass = apply_leakage(leak_state, leakage_path, dt_s=dt_s)

    expected_leaked_mass = leak_jet.mass_flow_kgps * dt_s
    assert math.isclose(leaked_mass, expected_leaked_mass)


def test_slosh_model_baseline_integrates_with_restoring_response() -> None:
    params = SloshModelParams(
        slosh_mass_kg=20.0,
        spring_constant_npm=120.0,
        damping_nspm=8.0,
        max_displacement_m=0.3,
    )
    state = SloshState(
        displacement_body_m=Vector3(0.0, 0.0, 0.0),
        velocity_body_mps=Vector3(0.0, 0.0, 0.0),
    )

    result = step_slosh_state(
        state=state,
        params=params,
        body_linear_accel_body_mps2=Vector3(1.0, 0.0, 0.0),
        dt_s=0.1,
    )

    assert result.state.displacement_body_m.x < 0.0
    assert result.state.velocity_body_mps.x < 0.0
    assert result.load.force_body_n.x < 0.0
    assert result.load.com_offset_body_m == result.state.displacement_body_m


def test_slosh_model_emits_torque_from_lever_arm_cross_force() -> None:
    params = SloshModelParams(
        slosh_mass_kg=10.0,
        spring_constant_npm=200.0,
        damping_nspm=0.0,
        max_displacement_m=1.0,
        lever_arm_body_m=Vector3(0.0, 0.5, 0.0),
    )
    state = SloshState(
        displacement_body_m=Vector3(0.1, 0.0, 0.0),
        velocity_body_mps=Vector3(0.0, 0.0, 0.0),
    )

    result = step_slosh_state(
        state=state,
        params=params,
        body_linear_accel_body_mps2=Vector3(0.0, 0.0, 0.0),
        dt_s=0.05,
    )

    assert result.load.force_body_n.x > 0.0
    assert result.load.torque_body_nm.z < 0.0


def test_slosh_model_validation_rejects_bad_inputs() -> None:
    try:
        SloshModelParams(
            slosh_mass_kg=0.0,
            spring_constant_npm=100.0,
            damping_nspm=1.0,
            max_displacement_m=0.2,
        )
    except ValueError as exc:
        assert "slosh_mass_kg" in str(exc)
    else:
        raise AssertionError("Expected slosh parameter validation failure")

    params = SloshModelParams(
        slosh_mass_kg=5.0,
        spring_constant_npm=100.0,
        damping_nspm=1.0,
        max_displacement_m=0.2,
    )
    state = SloshState(
        displacement_body_m=Vector3(0.0, 0.0, 0.0),
        velocity_body_mps=Vector3(0.0, 0.0, 0.0),
    )

    try:
        step_slosh_state(
            state=state,
            params=params,
            body_linear_accel_body_mps2=Vector3(0.0, 0.0, 0.0),
            dt_s=0.0,
        )
    except ValueError as exc:
        assert "dt_s must be positive" in str(exc)
    else:
        raise AssertionError("Expected slosh step validation failure")


def test_slosh_parameter_derivation_uses_geometry_hooks_and_fallback() -> None:
    fallback = SloshFallbackParams(
        natural_frequency_hz=0.8,
        damping_ratio=0.06,
        max_displacement_m=0.25,
    )
    from_geometry = derive_slosh_model_params(
        slosh_mass_kg=15.0,
        fallback=fallback,
        geometry=SloshGeometryDescriptor(
            source="stl",
            characteristic_length_m=2.4,
            equivalent_radius_m=0.5,
            fill_fraction=0.7,
            baffle_count=2,
        ),
    )
    from_fallback = derive_slosh_model_params(
        slosh_mass_kg=15.0,
        fallback=fallback,
        geometry=None,
    )

    assert from_geometry.spring_constant_npm != from_fallback.spring_constant_npm
    assert from_geometry.damping_nspm > from_fallback.damping_nspm
    assert from_geometry.max_displacement_m <= from_fallback.max_displacement_m


def test_slosh_to_6dof_coupling_propagates_wrench_and_com_offset() -> None:
    state = RigidBody6DoFState(
        position_m=Vector3(0.0, 0.0, 0.0),
        velocity_mps=Vector3(0.0, 0.0, 0.0),
        attitude=UnitQuaternion(1.0, 0.0, 0.0, 0.0),
        angular_velocity_radps=Vector3(0.0, 0.0, 0.0),
    )
    props = RigidBodyProperties(mass_kg=100.0, inertia_diag_kgm2=(20.0, 20.0, 20.0))

    result = propagate_slosh_to_rigid_body(
        state=state,
        props=props,
        slosh_load=step_slosh_state(
            state=SloshState(
                displacement_body_m=Vector3(0.1, 0.0, 0.0),
                velocity_body_mps=Vector3(0.0, 0.0, 0.0),
            ),
            params=SloshModelParams(
                slosh_mass_kg=10.0,
                spring_constant_npm=200.0,
                damping_nspm=0.0,
                max_displacement_m=0.5,
                lever_arm_body_m=Vector3(0.0, 0.5, 0.0),
            ),
            body_linear_accel_body_mps2=Vector3(0.0, 0.0, 0.0),
            dt_s=0.1,
        ).load,
        dt_s=0.1,
        nominal_com_body_m=Vector3(0.0, 0.0, 0.0),
    )

    assert result.state.velocity_mps.x > 0.0
    assert result.state.angular_velocity_radps.z < 0.0
    assert result.effective_com_body_m.x > 0.0
    assert result.effective_com_inertial_m.x > 0.0


def test_slosh_energy_sanity_envelope_without_external_forcing() -> None:
    params = SloshModelParams(
        slosh_mass_kg=10.0,
        spring_constant_npm=200.0,
        damping_nspm=0.5,
        max_displacement_m=0.5,
    )
    state = SloshState(
        displacement_body_m=Vector3(0.1, 0.0, 0.0),
        velocity_body_mps=Vector3(0.0, 0.0, 0.0),
    )

    def slosh_energy(current: SloshState) -> float:
        kinetic = 0.5 * params.slosh_mass_kg * current.velocity_body_mps.squared_norm()
        potential = 0.5 * params.spring_constant_npm * current.displacement_body_m.squared_norm()
        return kinetic + potential

    initial_energy = slosh_energy(state)
    for _ in range(100):
        state = step_slosh_state(
            state=state,
            params=params,
            body_linear_accel_body_mps2=Vector3(0.0, 0.0, 0.0),
            dt_s=0.01,
        ).state

    final_energy = slosh_energy(state)
    assert final_energy >= 0.0
    assert final_energy < initial_energy


def test_slosh_latency_benchmark_and_degraded_mode_controls() -> None:
    slosh_state = SloshState(
        displacement_body_m=Vector3(0.0, 0.0, 0.0),
        velocity_body_mps=Vector3(0.0, 0.0, 0.0),
    )
    slosh_params = SloshModelParams(
        slosh_mass_kg=15.0,
        spring_constant_npm=180.0,
        damping_nspm=6.0,
        max_displacement_m=0.25,
    )

    result = benchmark_reduced_order_slosh_latency(
        slosh_state=slosh_state,
        slosh_params=slosh_params,
        body_linear_accel_body_mps2=Vector3(1.0, 0.0, 0.0),
        dt_s=0.1,
        repeats=5,
        operational_budget_s=0.01,
    )

    assert result.repeats == 5
    assert result.p95_step_latency_s >= result.p50_step_latency_s

    nominal_load = step_slosh_state(
        state=slosh_state,
        params=slosh_params,
        body_linear_accel_body_mps2=Vector3(1.0, 0.0, 0.0),
        dt_s=0.1,
    ).load
    degraded_load = apply_slosh_degraded_mode(
        nominal_load,
        ReducedOrderFallbackMode.REDUCED_ORDER_GUARD_ACTIVE,
    )

    assert degraded_load.force_body_n == nominal_load.force_body_n
    assert degraded_load.torque_body_nm == Vector3(0.0, 0.0, 0.0)
    assert degraded_load.com_offset_body_m == Vector3(0.0, 0.0, 0.0)


def test_reduced_order_propulsion_latency_benchmark_reports_summary() -> None:
    chamber_state = ChamberFlowState(
        gas_mass_kg=1.0,
        pressure_pa=1_000_000.0,
        temperature_k=1500.0,
        fuel_mass_fraction=0.25,
    )
    chamber_params = ChamberFlowParams(
        volume_m3=0.2,
        gas_constant_jpkgk=300.0,
        stoichiometric_of_ratio=3.0,
        min_temperature_k=1200.0,
        max_temperature_k=3200.0,
        thermal_relaxation_time_constant_s=0.5,
    )
    leak_path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )

    result = benchmark_reduced_order_propulsion_latency(
        chamber_state=chamber_state,
        chamber_params=chamber_params,
        inflow_fuel_kgps=0.6,
        inflow_oxidizer_kgps=1.8,
        throat_outflow_kgps=1.5,
        leak_path=leak_path,
        compartment_pressure_pa=300_000.0,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
        dt_s=0.1,
        repeats=5,
        operational_budget_s=0.01,
    )

    assert result.repeats == 5
    assert result.p50_step_latency_s > 0.0
    assert result.p95_step_latency_s > 0.0
    assert result.p95_step_latency_s >= result.p50_step_latency_s


def test_cadence_guard_mode_and_fallback_trigger_behavior() -> None:
    assert cadence_guard_mode(0.001, 0.01) is ReducedOrderFallbackMode.NOMINAL
    assert (
        cadence_guard_mode(0.02, 0.01)
        is ReducedOrderFallbackMode.REDUCED_ORDER_GUARD_ACTIVE
    )

    chamber_state = ChamberFlowState(
        gas_mass_kg=1.0,
        pressure_pa=1_000_000.0,
        temperature_k=1500.0,
        fuel_mass_fraction=0.25,
    )
    chamber_params = ChamberFlowParams(
        volume_m3=0.2,
        gas_constant_jpkgk=300.0,
        stoichiometric_of_ratio=3.0,
        min_temperature_k=1200.0,
        max_temperature_k=3200.0,
        thermal_relaxation_time_constant_s=0.5,
    )
    leak_path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )

    result = benchmark_reduced_order_propulsion_latency(
        chamber_state=chamber_state,
        chamber_params=chamber_params,
        inflow_fuel_kgps=0.6,
        inflow_oxidizer_kgps=1.8,
        throat_outflow_kgps=1.5,
        leak_path=leak_path,
        compartment_pressure_pa=300_000.0,
        compartment_temperature_k=320.0,
        ambient_temperature_k=280.0,
        dt_s=0.1,
        repeats=3,
        operational_budget_s=1e-12,
    )

    assert result.fallback_trigger_count == result.repeats


def test_chamber_flow_validation_rejects_bad_inputs() -> None:
    try:
        ChamberFlowParams(
            volume_m3=0.2,
            gas_constant_jpkgk=300.0,
            stoichiometric_of_ratio=0.0,
            min_temperature_k=1200.0,
            max_temperature_k=3200.0,
            thermal_relaxation_time_constant_s=0.5,
        )
    except ValueError as exc:
        assert "stoichiometric_of_ratio" in str(exc)
    else:
        raise AssertionError("Expected chamber-flow parameter validation failure")

    params = ChamberFlowParams(
        volume_m3=0.2,
        gas_constant_jpkgk=300.0,
        stoichiometric_of_ratio=3.0,
        min_temperature_k=1200.0,
        max_temperature_k=3200.0,
        thermal_relaxation_time_constant_s=0.5,
    )
    state = ChamberFlowState(
        gas_mass_kg=1.0,
        pressure_pa=1_000_000.0,
        temperature_k=1500.0,
        fuel_mass_fraction=0.3,
    )

    try:
        step_chamber_flow(
            state=state,
            params=params,
            inflow_fuel_kgps=-1.0,
            inflow_oxidizer_kgps=0.0,
            throat_outflow_kgps=0.0,
            dt_s=0.1,
        )
    except ValueError as exc:
        assert "must be non-negative" in str(exc)
    else:
        raise AssertionError("Expected chamber-flow step validation failure")

    try:
        ChamberThrustCouplingParams(
            gas_constant_jpkgk=300.0,
            throat_area_m2=0.0,
            throat_discharge_coefficient=1.0,
        )
    except ValueError as exc:
        assert "throat_area_m2 must be positive" in str(exc)
    else:
        raise AssertionError("Expected thrust-coupling validation failure")

    try:
        LeakJetPath(
            area_m2=1e-4,
            discharge_coefficient=0.8,
            fluid_density_kgpm3=1.2,
            external_pressure_pa=0.0,
            jet_direction_body=Vector3(0.0, 0.0, 0.0),
        )
    except ValueError as exc:
        assert "jet_direction_body cannot be zero" in str(exc)
    else:
        raise AssertionError("Expected leak-jet validation failure")

    chamber_state = ChamberFlowState(
        gas_mass_kg=1.0,
        pressure_pa=1_000_000.0,
        temperature_k=1500.0,
        fuel_mass_fraction=0.25,
    )
    chamber_params = ChamberFlowParams(
        volume_m3=0.2,
        gas_constant_jpkgk=300.0,
        stoichiometric_of_ratio=3.0,
        min_temperature_k=1200.0,
        max_temperature_k=3200.0,
        thermal_relaxation_time_constant_s=0.5,
    )
    leak_path = LeakJetPath(
        area_m2=2e-4,
        discharge_coefficient=0.8,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=101_325.0,
        jet_direction_body=Vector3(1.0, 0.0, 0.0),
    )
    try:
        benchmark_reduced_order_propulsion_latency(
            chamber_state=chamber_state,
            chamber_params=chamber_params,
            inflow_fuel_kgps=0.6,
            inflow_oxidizer_kgps=1.8,
            throat_outflow_kgps=1.5,
            leak_path=leak_path,
            compartment_pressure_pa=300_000.0,
            compartment_temperature_k=320.0,
            ambient_temperature_k=280.0,
            dt_s=0.1,
            repeats=0,
            operational_budget_s=0.01,
        )
    except ValueError as exc:
        assert "repeats" in str(exc)
    else:
        raise AssertionError("Expected propulsion latency benchmark validation failure")

    try:
        benchmark_reduced_order_slosh_latency(
            slosh_state=SloshState(
                displacement_body_m=Vector3(0.0, 0.0, 0.0),
                velocity_body_mps=Vector3(0.0, 0.0, 0.0),
            ),
            slosh_params=SloshModelParams(
                slosh_mass_kg=5.0,
                spring_constant_npm=100.0,
                damping_nspm=1.0,
                max_displacement_m=0.2,
            ),
            body_linear_accel_body_mps2=Vector3(0.0, 0.0, 0.0),
            dt_s=0.1,
            repeats=0,
            operational_budget_s=0.01,
        )
    except ValueError as exc:
        assert "repeats" in str(exc)
    else:
        raise AssertionError("Expected slosh latency benchmark validation failure")
