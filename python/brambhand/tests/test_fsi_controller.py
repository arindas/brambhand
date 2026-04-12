from brambhand.coupling.controller import (
    FSICouplingControllerPolicy,
    run_fsi_coupling_with_controller,
)
from brambhand.coupling.fsi_coupler import InterfaceDisplacement
from brambhand.fluid.contracts import FluidBoundaryLoad
from brambhand.physics.vector import Vector3


class _LinearFluidProvider:
    def __init__(self, base_force_n: float, displacement_gain_npm: float) -> None:
        self._base_force_n = base_force_n
        self._displacement_gain_npm = displacement_gain_npm

    def evaluate(
        self,
        interface_displacements: tuple[InterfaceDisplacement, ...],
    ) -> tuple[FluidBoundaryLoad, ...]:
        displacement_by_id = {
            item.interface_id: item.displacement_body_m.x for item in interface_displacements
        }

        def load(interface_id: str) -> FluidBoundaryLoad:
            displacement_x = displacement_by_id.get(interface_id, 0.0)
            force_x = self._base_force_n - self._displacement_gain_npm * displacement_x
            return FluidBoundaryLoad(
                interface_id=interface_id,
                force_body_n=Vector3(force_x, 0.0, 0.0),
                torque_body_nm=Vector3(0.0, 0.0, 0.0),
                mass_flow_kgps=0.0,
                temperature_k=300.0,
            )

        return (load("a_iface"),)


class _LinearStructuralProvider:
    def __init__(self, compliance_mpn: float) -> None:
        self._compliance_mpn = compliance_mpn

    def evaluate(
        self,
        fluid_loads: tuple[FluidBoundaryLoad, ...],
    ) -> tuple[InterfaceDisplacement, ...]:
        load = fluid_loads[0]
        return (
            InterfaceDisplacement(
                interface_id=load.interface_id,
                displacement_body_m=Vector3(self._compliance_mpn * load.force_body_n.x, 0.0, 0.0),
            ),
        )


def test_fsi_controller_returns_nominal_mode_when_nominal_converges() -> None:
    fluid = _LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=0.5)
    structure = _LinearStructuralProvider(compliance_mpn=0.1)

    result = run_fsi_coupling_with_controller(
        fluid_provider=fluid,
        structural_provider=structure,
        policy=FSICouplingControllerPolicy(
            nominal_iteration_budget=20,
            nominal_residual_threshold=1e-6,
            nominal_relaxation_factor=1.0,
            fallback_enabled=True,
        ),
    )

    assert result.mode == "nominal"
    assert result.converged is True
    assert result.termination_reason == "nominal_converged"
    assert result.fallback_result is None


def test_fsi_controller_uses_fallback_when_nominal_budget_is_exhausted() -> None:
    fluid = _LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=0.5)
    structure = _LinearStructuralProvider(compliance_mpn=0.1)

    result = run_fsi_coupling_with_controller(
        fluid_provider=fluid,
        structural_provider=structure,
        policy=FSICouplingControllerPolicy(
            nominal_iteration_budget=1,
            nominal_residual_threshold=1e-9,
            nominal_relaxation_factor=1.0,
            fallback_enabled=True,
            fallback_iteration_budget=30,
            fallback_residual_threshold=1e-4,
            fallback_relaxation_factor=0.5,
        ),
    )

    assert result.mode == "fallback"
    assert result.converged is True
    assert result.termination_reason == "fallback_converged"
    assert result.fallback_result is not None
    assert result.total_iterations_used > result.nominal_result.iterations_used


def test_fsi_controller_reports_failure_when_fallback_disabled() -> None:
    fluid = _LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=-5.0)
    structure = _LinearStructuralProvider(compliance_mpn=0.5)

    result = run_fsi_coupling_with_controller(
        fluid_provider=fluid,
        structural_provider=structure,
        policy=FSICouplingControllerPolicy(
            nominal_iteration_budget=2,
            nominal_residual_threshold=1e-12,
            fallback_enabled=False,
        ),
        initial_displacements=(
            InterfaceDisplacement(
                interface_id="a_iface",
                displacement_body_m=Vector3(0.0, 0.0, 0.0),
            ),
        ),
    )

    assert result.mode == "failed"
    assert result.converged is False
    assert result.termination_reason == "nominal_not_converged_no_fallback"


def test_fsi_controller_policy_validation_guards() -> None:
    try:
        FSICouplingControllerPolicy(nominal_iteration_budget=0, nominal_residual_threshold=1e-6)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected FSICouplingControllerPolicy validation failure")

    try:
        FSICouplingControllerPolicy(nominal_iteration_budget=1, nominal_residual_threshold=-1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected FSICouplingControllerPolicy validation failure")

    try:
        FSICouplingControllerPolicy(
            nominal_iteration_budget=1,
            nominal_residual_threshold=1e-6,
            nominal_relaxation_factor=0.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected FSICouplingControllerPolicy validation failure")

    try:
        FSICouplingControllerPolicy(
            nominal_iteration_budget=1,
            nominal_residual_threshold=1e-6,
            fallback_iteration_budget=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected FSICouplingControllerPolicy validation failure")

    try:
        FSICouplingControllerPolicy(
            nominal_iteration_budget=1,
            nominal_residual_threshold=1e-6,
            fallback_residual_threshold=-1.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected FSICouplingControllerPolicy validation failure")

    try:
        FSICouplingControllerPolicy(
            nominal_iteration_budget=1,
            nominal_residual_threshold=1e-6,
            fallback_relaxation_factor=1.5,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected FSICouplingControllerPolicy validation failure")
