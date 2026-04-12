from typing import TYPE_CHECKING

from brambhand.fluid.contracts import (
    FluidBoundaryDisplacement,
    FluidBoundaryLoad,
    FSIFluidBoundaryProvider,
)
from brambhand.physics.vector import Vector3

if TYPE_CHECKING:
    pass


class _ReducedOrderProvider:
    def evaluate(
        self,
        interface_displacements: tuple[FluidBoundaryDisplacement, ...],
    ) -> tuple[FluidBoundaryLoad, ...]:
        return tuple(
            FluidBoundaryLoad(
                interface_id=item.interface_id,
                force_body_n=Vector3(-10.0 * item.displacement_body_m.x, 0.0, 0.0),
                torque_body_nm=Vector3(0.0, 0.0, 0.0),
                mass_flow_kgps=0.0,
                temperature_k=295.0,
            )
            for item in interface_displacements
        )


class _CFDProviderAdapter:
    def evaluate(
        self,
        interface_displacements: tuple[FluidBoundaryDisplacement, ...],
    ) -> tuple[FluidBoundaryLoad, ...]:
        return tuple(
            FluidBoundaryLoad(
                interface_id=item.interface_id,
                force_body_n=Vector3(-12.0 * item.displacement_body_m.x, 0.0, 0.0),
                torque_body_nm=Vector3(0.0, 0.0, 0.0),
                mass_flow_kgps=0.0,
                temperature_k=305.0,
            )
            for item in interface_displacements
        )


def _evaluate_provider(
    provider: FSIFluidBoundaryProvider,
    interface_displacements: tuple[FluidBoundaryDisplacement, ...],
) -> tuple[FluidBoundaryLoad, ...]:
    return provider.evaluate(interface_displacements)


def test_backend_neutral_fsi_provider_contract_accepts_reduced_and_cfd_adapters() -> None:
    displacements = (
        FluidBoundaryDisplacement(
            interface_id="tank_shell",
            displacement_body_m=Vector3(0.2, 0.0, 0.0),
        ),
    )

    reduced_loads = _evaluate_provider(_ReducedOrderProvider(), displacements)
    cfd_loads = _evaluate_provider(_CFDProviderAdapter(), displacements)

    assert reduced_loads[0].interface_id == "tank_shell"
    assert cfd_loads[0].interface_id == "tank_shell"
    assert reduced_loads[0].force_body_n.x != cfd_loads[0].force_body_n.x


def test_interface_displacement_alias_stays_compatible_with_backend_neutral_contract() -> None:
    from brambhand.coupling.fsi_coupler import InterfaceDisplacement

    displacement = InterfaceDisplacement(
        interface_id="joint_a",
        displacement_body_m=Vector3(0.0, 0.01, 0.0),
    )
    load = _evaluate_provider(_ReducedOrderProvider(), (displacement,))[0]

    assert load.interface_id == "joint_a"
    assert load.temperature_k == 295.0
