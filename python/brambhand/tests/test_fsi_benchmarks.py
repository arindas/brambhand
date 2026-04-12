from brambhand.coupling.controller import (
    FSICouplingControllerPolicy,
    FSICouplingControllerResult,
    run_fsi_coupling_with_controller,
)
from brambhand.coupling.fsi_coupler import InterfaceDisplacement
from brambhand.coupling.performance import benchmark_fsi_coupled_stability
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
        displacement_x = (
            0.0
            if not interface_displacements
            else interface_displacements[0].displacement_body_m.x
        )
        return (
            FluidBoundaryLoad(
                interface_id="if0",
                force_body_n=Vector3(
                    self._base_force_n - self._displacement_gain_npm * displacement_x,
                    0.0,
                    0.0,
                ),
                torque_body_nm=Vector3(0.0, 0.0, 0.0),
                mass_flow_kgps=0.0,
                temperature_k=300.0,
            ),
        )


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


def test_fsi_benchmark_reports_stable_converged_profile() -> None:
    def run_case(_: int):
        return run_fsi_coupling_with_controller(
            fluid_provider=_LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=0.5),
            structural_provider=_LinearStructuralProvider(compliance_mpn=0.1),
            policy=FSICouplingControllerPolicy(
                nominal_iteration_budget=20,
                nominal_residual_threshold=1e-6,
                fallback_enabled=True,
            ),
        )

    result = benchmark_fsi_coupled_stability(run_case, repeats=6)

    assert result.repeats == 6
    assert result.converged_count == 6
    assert result.failure_count == 0
    assert result.fallback_converged_count >= 0
    assert result.max_final_residual >= 0.0


def test_fsi_benchmark_captures_failure_and_recovery_paths() -> None:
    def run_case(run_index: int):
        if run_index % 2 == 0:
            return run_fsi_coupling_with_controller(
                fluid_provider=_LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=-5.0),
                structural_provider=_LinearStructuralProvider(compliance_mpn=0.5),
                policy=FSICouplingControllerPolicy(
                    nominal_iteration_budget=2,
                    nominal_residual_threshold=1e-12,
                    fallback_enabled=False,
                ),
            )
        return run_fsi_coupling_with_controller(
            fluid_provider=_LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=0.5),
            structural_provider=_LinearStructuralProvider(compliance_mpn=0.1),
            policy=FSICouplingControllerPolicy(
                nominal_iteration_budget=20,
                nominal_residual_threshold=1e-6,
                fallback_enabled=True,
            ),
        )

    result = benchmark_fsi_coupled_stability(run_case, repeats=6)

    assert result.failure_count == 3
    assert result.converged_count == 3
    assert result.failure_recovery_count == 3


def test_fsi_benchmark_validates_repeats() -> None:
    def _unused_runner(_: int) -> FSICouplingControllerResult:
        raise AssertionError("runner should not be called when repeats is invalid")

    try:
        benchmark_fsi_coupled_stability(_unused_runner, repeats=0)
    except ValueError as exc:
        assert "repeats" in str(exc)
    else:
        raise AssertionError("Expected benchmark repeats validation failure")
