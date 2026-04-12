from brambhand.coupling.fsi_coupler import (
    FSICouplingParams,
    InterfaceDisplacement,
    couple_fsi_two_way,
)
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

        # Intentionally unsorted to verify deterministic canonical ordering.
        return (load("b_iface"), load("a_iface"))


class _LinearStructuralProvider:
    def __init__(self, compliance_mpn: float) -> None:
        self._compliance_mpn = compliance_mpn

    def evaluate(
        self,
        fluid_loads: tuple[FluidBoundaryLoad, ...],
    ) -> tuple[InterfaceDisplacement, ...]:
        displacements = [
            InterfaceDisplacement(
                interface_id=load.interface_id,
                displacement_body_m=Vector3(self._compliance_mpn * load.force_body_n.x, 0.0, 0.0),
            )
            for load in fluid_loads
        ]
        # Intentionally unsorted to verify deterministic canonical ordering.
        return tuple(sorted(displacements, key=lambda item: item.interface_id, reverse=True))


def test_two_way_fsi_coupler_converges_with_residual_telemetry() -> None:
    fluid = _LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=0.5)
    structure = _LinearStructuralProvider(compliance_mpn=0.1)

    result = couple_fsi_two_way(
        fluid_provider=fluid,
        structural_provider=structure,
        params=FSICouplingParams(
            max_iterations=25,
            residual_tolerance=1e-8,
            relaxation_factor=1.0,
        ),
    )

    assert result.converged is True
    assert result.termination_reason == "converged"
    assert result.iterations_used >= 2
    assert result.residual_history[-1].residual <= 1e-8

    assert tuple(load.interface_id for load in result.fluid_loads) == ("a_iface", "b_iface")
    assert tuple(item.interface_id for item in result.interface_displacements) == (
        "a_iface",
        "b_iface",
    )

    # Fixed point for x = c*(F0 - kx): x = c*F0 / (1 + c*k)
    expected_x = (0.1 * 10.0) / (1.0 + 0.1 * 0.5)
    assert abs(result.interface_displacements[0].displacement_body_m.x - expected_x) < 1e-6
    assert abs(result.interface_displacements[1].displacement_body_m.x - expected_x) < 1e-6


def test_two_way_fsi_coupler_reports_max_iterations_when_not_converged() -> None:
    fluid = _LinearFluidProvider(base_force_n=10.0, displacement_gain_npm=-5.0)
    structure = _LinearStructuralProvider(compliance_mpn=0.5)

    result = couple_fsi_two_way(
        fluid_provider=fluid,
        structural_provider=structure,
        params=FSICouplingParams(
            max_iterations=4,
            residual_tolerance=1e-9,
            relaxation_factor=1.0,
        ),
        initial_displacements=(
            InterfaceDisplacement(
                interface_id="a_iface",
                displacement_body_m=Vector3(0.0, 0.0, 0.0),
            ),
            InterfaceDisplacement(
                interface_id="b_iface",
                displacement_body_m=Vector3(0.0, 0.0, 0.0),
            ),
        ),
    )

    assert result.converged is False
    assert result.termination_reason == "max_iterations"
    assert result.iterations_used == 4
    assert len(result.residual_history) == 4
    assert result.residual_history[-1].residual > result.residual_history[0].residual


def test_fsi_coupling_params_validate_input_ranges() -> None:
    for max_iterations, residual_tolerance, relaxation_factor in (
        (0, 1e-4, 1.0),
        (1, -1.0, 1.0),
        (1, 1e-4, 0.0),
        (1, 1e-4, 1.1),
    ):
        try:
            FSICouplingParams(
                max_iterations=max_iterations,
                residual_tolerance=residual_tolerance,
                relaxation_factor=relaxation_factor,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected FSICouplingParams validation failure")
