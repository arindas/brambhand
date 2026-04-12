from brambhand.coupling.controller import (
    FSICouplingControllerPolicy,
    run_fsi_coupling_with_controller,
)
from brambhand.coupling.fsi_coupler import InterfaceDisplacement
from brambhand.coupling.telemetry import (
    FSI_TELEMETRY_SCHEMA_VERSION,
    FSICouplingConvergenceDiagnostics,
    build_fsi_convergence_diagnostics,
)
from brambhand.fluid.contracts import FluidBoundaryLoad
from brambhand.physics.vector import Vector3


class _LinearFluidProvider:
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
                force_body_n=Vector3(10.0 - 0.5 * displacement_x, 0.0, 0.0),
                torque_body_nm=Vector3(0.0, 0.0, 0.0),
                mass_flow_kgps=0.0,
                temperature_k=300.0,
            ),
        )


class _LinearStructuralProvider:
    def evaluate(
        self,
        fluid_loads: tuple[FluidBoundaryLoad, ...],
    ) -> tuple[InterfaceDisplacement, ...]:
        return (
            InterfaceDisplacement(
                interface_id="if0",
                displacement_body_m=Vector3(0.1 * fluid_loads[0].force_body_n.x, 0.0, 0.0),
            ),
        )


def test_fsi_convergence_diagnostics_emits_residual_and_mode_channels() -> None:
    controller_result = run_fsi_coupling_with_controller(
        fluid_provider=_LinearFluidProvider(),
        structural_provider=_LinearStructuralProvider(),
        policy=FSICouplingControllerPolicy(
            nominal_iteration_budget=20,
            nominal_residual_threshold=1e-6,
            fallback_enabled=True,
        ),
    )

    diagnostics = build_fsi_convergence_diagnostics(controller_result)

    assert diagnostics.schema_version == FSI_TELEMETRY_SCHEMA_VERSION
    assert diagnostics.converged is True
    assert diagnostics.iterations_used == controller_result.total_iterations_used
    assert diagnostics.final_residual >= 0.0
    assert len(diagnostics.channels.residual_history) >= 1
    assert diagnostics.channels.mode_and_reason[0] == controller_result.mode


def test_fsi_convergence_diagnostics_rejects_unsupported_schema_version() -> None:
    try:
        FSICouplingConvergenceDiagnostics(
            schema_version=999,
            final_residual=0.0,
            iterations_used=0,
            converged=False,
            channels=build_fsi_convergence_diagnostics(
                run_fsi_coupling_with_controller(
                    fluid_provider=_LinearFluidProvider(),
                    structural_provider=_LinearStructuralProvider(),
                    policy=FSICouplingControllerPolicy(
                        nominal_iteration_budget=1,
                        nominal_residual_threshold=1.0,
                    ),
                    initial_displacements=(
                        InterfaceDisplacement(
                            interface_id="if0",
                            displacement_body_m=Vector3(0.0, 0.0, 0.0),
                        ),
                    ),
                )
            ).channels,
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected FSI telemetry schema-version validation failure")
