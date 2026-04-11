"""Model-selection helpers for structural FEM dimensionality decisions."""

from brambhand.structures.fem.contracts import (
    StructuralModelDimension,
    StructuralModelSelectionDecision,
    StructuralModelSelectionInput,
    StructuralModelSelectionPolicy,
)


def select_structural_model_dimension(
    selection_input: StructuralModelSelectionInput,
    policy: StructuralModelSelectionPolicy | None = None,
) -> StructuralModelSelectionDecision:
    """Select structural dimensionality (2D vs 3D) from policy thresholds."""
    policy = policy or StructuralModelSelectionPolicy()

    reasons: list[str] = []
    span_ratio = selection_input.out_of_plane_span_m / selection_input.in_plane_span_m

    if span_ratio > policy.max_out_of_plane_span_ratio_for_2d:
        reasons.append("out_of_plane_span_ratio_exceeded")

    if (
        selection_input.out_of_plane_load_fraction
        > policy.max_out_of_plane_load_fraction_for_2d
    ):
        reasons.append("out_of_plane_load_fraction_exceeded")

    if (
        policy.require_3d_for_out_of_plane_constraints
        and selection_input.has_out_of_plane_constraints
    ):
        reasons.append("out_of_plane_constraints_present")

    if reasons:
        return StructuralModelSelectionDecision(
            dimension=StructuralModelDimension.THREE_D,
            reasons=tuple(reasons),
        )

    return StructuralModelSelectionDecision(
        dimension=StructuralModelDimension.TWO_D,
        reasons=("within_2d_policy_envelope",),
    )


__all__ = ["select_structural_model_dimension"]
