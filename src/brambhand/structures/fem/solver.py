"""R3 baseline FEM solver for chassis-component structural evaluation.

This module now acts as a facade/orchestrator over modularized FEM components:
- contracts/types (`fem/contracts.py`)
- geometry/assembly (`fem/geometry.py`)
- backend solve implementations (`fem/backends.py`)
"""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import numpy as np
from scipy import sparse

from brambhand.structures.fem.backends import (
    solve_reduced_system,
    solve_reduced_system_matrix_free,
)
from brambhand.structures.fem.contracts import (
    BoundaryConstraint2D,
    BoundaryConstraint3D,
    FEMModel2D,
    FEMModel3D,
    FEMSolveResult2D,
    FEMSolveResult3D,
    LinearTetrahedronElement,
    LinearTriangleElement,
    MatrixFreeAcceptanceEvaluation,
    MatrixFreeAcceptanceThreshold,
    MatrixFreePreconditionerBenchmarkResult,
    NodalLoad2D,
    NodalLoad3D,
    Node2D,
    Node3D,
    Structural2DMode,
    Structural2DValidityEnvelope,
    Structural3DValidityEnvelope,
    StructuralIterativePreconditioner,
    StructuralLatencyMemoryBenchmarkResult,
    StructuralModelDimension,
    StructuralModelSelectionDecision,
    StructuralModelSelectionInput,
    StructuralModelSelectionPolicy,
    StructuralProfileClass,
    StructuralSolverBackend,
    StructuralSolverConfig,
    StructuralSolverTerminationReason,
    StructuralSolveTelemetry2D,
    StructuralSolveTelemetry3D,
    TetrahedronElementResult,
    TriangleElementResult,
)
from brambhand.structures.fem.geometry import (
    apply_element_terms,
    assemble_element_stiffness_terms,
    assemble_element_stiffness_terms_3d,
    assemble_global_stiffness_sparse,
    constitutive_matrix,
    constitutive_matrix_3d,
    tetrahedron_volume_and_b_matrix,
    triangle_area_and_b_matrix,
)
from brambhand.structures.fem.selection import select_structural_model_dimension


def solve_linear_static_fem(model: FEMModel2D) -> FEMSolveResult2D:
    """Solve linear static 2D FEM system within configured validity envelope."""
    dof_count = 2 * len(model.nodes)
    forces = np.zeros(dof_count, dtype=float)

    for node_id, load in model.nodal_loads.items():
        forces[2 * node_id] += load.fx_n
        forces[2 * node_id + 1] += load.fy_n

    element_terms = assemble_element_stiffness_terms(model)

    fixed_dofs: list[int] = []
    for node_id, constraint in model.constraints.items():
        if constraint.fix_x:
            fixed_dofs.append(2 * node_id)
        if constraint.fix_y:
            fixed_dofs.append(2 * node_id + 1)

    fixed_dofs_set = set(fixed_dofs)
    free_dofs = [dof for dof in range(dof_count) if dof not in fixed_dofs_set]
    if not free_dofs:
        raise ValueError("Model has no free DOFs to solve.")

    stiffness: sparse.csr_matrix | None = None
    reduced_stiffness: sparse.csr_matrix | None = None
    rhs = forces[free_dofs]

    if model.solver_config.backend == StructuralSolverBackend.MATRIX_FREE_ITERATIVE:
        (
            u_f,
            iterative_preconditioner,
            iterative_iterations,
            iterative_residual_norm,
            iterative_relative_residual_norm,
            matrix_free_reference_delta_norm,
            termination_reason,
        ) = solve_reduced_system_matrix_free(
            element_terms,
            rhs,
            free_dofs,
            dof_count,
            model.solver_config,
        )
    else:
        stiffness = assemble_global_stiffness_sparse(dof_count, element_terms)
        reduced_stiffness = stiffness[free_dofs, :][:, free_dofs].tocsr()
        (
            u_f,
            iterative_preconditioner,
            iterative_iterations,
            iterative_residual_norm,
            iterative_relative_residual_norm,
            matrix_free_reference_delta_norm,
            termination_reason,
        ) = solve_reduced_system(reduced_stiffness, rhs, model.solver_config)

    if np.any(~np.isfinite(u_f)):
        raise ValueError("FEM system solve produced non-finite values.")

    displacements = np.zeros(dof_count, dtype=float)
    displacements[free_dofs] = u_f

    internal_forces = apply_element_terms(element_terms, displacements, dof_count)
    reactions = internal_forces - forces

    element_results: list[TriangleElementResult] = []
    max_abs_strain = 0.0
    for element in model.elements:
        n0, n1, n2 = element.node_ids
        element_nodes = (model.nodes[n0], model.nodes[n1], model.nodes[n2])
        _, b_matrix = triangle_area_and_b_matrix(element_nodes)
        d_matrix = constitutive_matrix(
            element.youngs_modulus_pa,
            element.poisson_ratio,
            model.validity_envelope.mode,
        )

        dofs = [2 * node_id + c for node_id in element.node_ids for c in (0, 1)]
        u_e = displacements[dofs]
        strain = b_matrix @ u_e
        stress = d_matrix @ strain
        max_abs_strain = max(max_abs_strain, float(np.max(np.abs(strain))))

        sx, sy, txy = stress[0], stress[1], stress[2]
        von_mises = float(np.sqrt(sx * sx - sx * sy + sy * sy + 3.0 * txy * txy))
        element_results.append(
            TriangleElementResult(
                strain_xx=float(strain[0]),
                strain_yy=float(strain[1]),
                strain_xy=float(strain[2]),
                stress_xx_pa=float(sx),
                stress_yy_pa=float(sy),
                stress_xy_pa=float(txy),
                von_mises_pa=von_mises,
            )
        )

    if max_abs_strain > model.validity_envelope.small_strain_limit:
        raise ValueError(
            "2D FEM validity envelope exceeded: small-strain assumption violated."
        )

    displacements_m = tuple(
        (float(displacements[2 * i]), float(displacements[2 * i + 1]))
        for i in range(len(model.nodes))
    )
    reaction_forces_n = tuple(
        (float(reactions[2 * i]), float(reactions[2 * i + 1]))
        for i in range(len(model.nodes))
    )

    if stiffness is None:
        assembly_backend = "matrix_free_operator"
        global_nnz = 0
        reduced_nnz = 0
    else:
        assembly_backend = "sparse_coo_csr"
        global_nnz = int(stiffness.nnz)
        reduced_nnz = int(reduced_stiffness.nnz) if reduced_stiffness is not None else 0

    telemetry = StructuralSolveTelemetry2D(
        assembly_backend=assembly_backend,
        solver_backend=model.solver_config.backend,
        termination_reason=termination_reason,
        global_dof_count=dof_count,
        global_matrix_nnz=global_nnz,
        reduced_matrix_nnz=reduced_nnz,
        iterative_preconditioner=iterative_preconditioner,
        iterative_iterations=iterative_iterations,
        iterative_residual_norm=iterative_residual_norm,
        iterative_relative_residual_norm=iterative_relative_residual_norm,
        matrix_free_reference_delta_norm=matrix_free_reference_delta_norm,
    )

    return FEMSolveResult2D(
        displacements_m=displacements_m,
        reaction_forces_n=reaction_forces_n,
        element_results=tuple(element_results),
        telemetry=telemetry,
    )


def solve_linear_static_fem_3d(model: FEMModel3D) -> FEMSolveResult3D:
    """Solve linear static 3D FEM system with tetrahedral solid elements."""
    if model.solver_config.backend == StructuralSolverBackend.MATRIX_FREE_ITERATIVE:
        raise ValueError("3D baseline currently supports matrix-based backends only.")

    dof_count = 3 * len(model.nodes)
    forces = np.zeros(dof_count, dtype=float)

    for node_id, load in model.nodal_loads.items():
        base = 3 * node_id
        forces[base] += load.fx_n
        forces[base + 1] += load.fy_n
        forces[base + 2] += load.fz_n

    element_terms = assemble_element_stiffness_terms_3d(model)

    fixed_dofs: list[int] = []
    for node_id, constraint in model.constraints.items():
        base = 3 * node_id
        if constraint.fix_x:
            fixed_dofs.append(base)
        if constraint.fix_y:
            fixed_dofs.append(base + 1)
        if constraint.fix_z:
            fixed_dofs.append(base + 2)

    fixed_dofs_set = set(fixed_dofs)
    free_dofs = [dof for dof in range(dof_count) if dof not in fixed_dofs_set]
    if not free_dofs:
        raise ValueError("Model has no free DOFs to solve.")

    stiffness = assemble_global_stiffness_sparse(dof_count, element_terms)
    reduced_stiffness = stiffness[free_dofs, :][:, free_dofs].tocsr()
    rhs = forces[free_dofs]

    (
        u_f,
        iterative_preconditioner,
        iterative_iterations,
        iterative_residual_norm,
        iterative_relative_residual_norm,
        _,
        termination_reason,
    ) = solve_reduced_system(reduced_stiffness, rhs, model.solver_config)

    if np.any(~np.isfinite(u_f)):
        raise ValueError("FEM system solve produced non-finite values.")

    displacements = np.zeros(dof_count, dtype=float)
    displacements[free_dofs] = u_f

    internal_forces = apply_element_terms(element_terms, displacements, dof_count)
    reactions = internal_forces - forces

    element_results: list[TetrahedronElementResult] = []
    max_abs_strain = 0.0
    for element in model.elements:
        n0, n1, n2, n3 = element.node_ids
        element_nodes = (model.nodes[n0], model.nodes[n1], model.nodes[n2], model.nodes[n3])
        _, b_matrix = tetrahedron_volume_and_b_matrix(element_nodes)
        d_matrix = constitutive_matrix_3d(
            element.youngs_modulus_pa,
            element.poisson_ratio,
        )

        dofs = [3 * node_id + c for node_id in element.node_ids for c in (0, 1, 2)]
        u_e = displacements[dofs]
        strain = b_matrix @ u_e
        stress = d_matrix @ strain
        max_abs_strain = max(max_abs_strain, float(np.max(np.abs(strain))))

        sx, sy, sz, txy, tyz, tzx = (
            float(stress[0]),
            float(stress[1]),
            float(stress[2]),
            float(stress[3]),
            float(stress[4]),
            float(stress[5]),
        )
        von_mises = float(
            np.sqrt(
                0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
                + 3.0 * (txy * txy + tyz * tyz + tzx * tzx)
            )
        )
        element_results.append(
            TetrahedronElementResult(
                strain_xx=float(strain[0]),
                strain_yy=float(strain[1]),
                strain_zz=float(strain[2]),
                strain_xy=float(strain[3]),
                strain_yz=float(strain[4]),
                strain_zx=float(strain[5]),
                stress_xx_pa=sx,
                stress_yy_pa=sy,
                stress_zz_pa=sz,
                stress_xy_pa=txy,
                stress_yz_pa=tyz,
                stress_zx_pa=tzx,
                von_mises_pa=von_mises,
            )
        )

    if max_abs_strain > model.validity_envelope.small_strain_limit:
        raise ValueError(
            "3D FEM validity envelope exceeded: small-strain assumption violated."
        )

    displacements_m = tuple(
        (
            float(displacements[3 * i]),
            float(displacements[3 * i + 1]),
            float(displacements[3 * i + 2]),
        )
        for i in range(len(model.nodes))
    )
    reaction_forces_n = tuple(
        (
            float(reactions[3 * i]),
            float(reactions[3 * i + 1]),
            float(reactions[3 * i + 2]),
        )
        for i in range(len(model.nodes))
    )

    telemetry = StructuralSolveTelemetry3D(
        assembly_backend="sparse_coo_csr",
        solver_backend=model.solver_config.backend,
        termination_reason=termination_reason,
        global_dof_count=dof_count,
        global_matrix_nnz=int(stiffness.nnz),
        reduced_matrix_nnz=int(reduced_stiffness.nnz),
        iterative_preconditioner=iterative_preconditioner,
        iterative_iterations=iterative_iterations,
        iterative_residual_norm=iterative_residual_norm,
        iterative_relative_residual_norm=iterative_relative_residual_norm,
    )

    return FEMSolveResult3D(
        displacements_m=displacements_m,
        reaction_forces_n=reaction_forces_n,
        element_results=tuple(element_results),
        telemetry=telemetry,
    )


def benchmark_matrix_free_preconditioners(
    model: FEMModel2D,
    preconditioners: tuple[
        StructuralIterativePreconditioner, ...
    ] = (
        StructuralIterativePreconditioner.NONE,
        StructuralIterativePreconditioner.JACOBI,
        StructuralIterativePreconditioner.BLOCK_JACOBI,
    ),
) -> tuple[MatrixFreePreconditionerBenchmarkResult, ...]:
    """Benchmark matrix-free preconditioner choices on a common model."""
    results: list[MatrixFreePreconditionerBenchmarkResult] = []

    for preconditioner in preconditioners:
        cfg = replace(
            model.solver_config,
            backend=StructuralSolverBackend.MATRIX_FREE_ITERATIVE,
            iterative_preconditioner=preconditioner,
        )
        benchmark_model = replace(model, solver_config=cfg)
        solve_result = solve_linear_static_fem(benchmark_model)

        iterations = solve_result.telemetry.iterative_iterations
        residual = solve_result.telemetry.iterative_residual_norm
        relative_residual = solve_result.telemetry.iterative_relative_residual_norm

        if iterations is None or residual is None or relative_residual is None:
            raise ValueError(
                "Matrix-free benchmark expected iterative telemetry but did not receive it."
            )

        results.append(
            MatrixFreePreconditionerBenchmarkResult(
                preconditioner=preconditioner,
                iterations=iterations,
                residual_norm=residual,
                relative_residual_norm=relative_residual,
            )
        )

    return tuple(results)


def benchmark_structural_latency_memory_profiles(
    model_2d: FEMModel2D,
    model_3d: FEMModel3D,
    profile: StructuralProfileClass = StructuralProfileClass.OPERATIONAL,
    repeats: int = 5,
) -> tuple[StructuralLatencyMemoryBenchmarkResult, StructuralLatencyMemoryBenchmarkResult]:
    """Benchmark structural latency/memory telemetry for paired 2D and 3D models."""
    if repeats <= 0:
        raise ValueError("repeats must be positive.")

    def _p95(samples: list[float]) -> float:
        ordered = sorted(samples)
        rank = max(int(np.ceil(0.95 * len(ordered))) - 1, 0)
        return float(ordered[rank])

    times_2d: list[float] = []
    result_2d: FEMSolveResult2D | None = None
    for _ in range(repeats):
        start = perf_counter()
        result_2d = solve_linear_static_fem(model_2d)
        times_2d.append(perf_counter() - start)

    times_3d: list[float] = []
    result_3d: FEMSolveResult3D | None = None
    for _ in range(repeats):
        start = perf_counter()
        result_3d = solve_linear_static_fem_3d(model_3d)
        times_3d.append(perf_counter() - start)

    if result_2d is None or result_3d is None:
        raise ValueError("Benchmark requires at least one solve sample per profile.")

    telemetry_2d = result_2d.telemetry
    telemetry_3d = result_3d.telemetry

    estimate_2d = (
        telemetry_2d.global_matrix_nnz * 12
        + (telemetry_2d.global_dof_count + 1) * 4
    )
    estimate_3d = (
        telemetry_3d.global_matrix_nnz * 12
        + (telemetry_3d.global_dof_count + 1) * 4
    )

    return (
        StructuralLatencyMemoryBenchmarkResult(
            profile=profile,
            dimension=StructuralModelDimension.TWO_D,
            solver_backend=telemetry_2d.solver_backend,
            repeats=repeats,
            p50_solve_seconds=float(np.median(np.array(times_2d, dtype=float))),
            p95_solve_seconds=_p95(times_2d),
            global_dof_count=telemetry_2d.global_dof_count,
            global_matrix_nnz=telemetry_2d.global_matrix_nnz,
            reduced_matrix_nnz=telemetry_2d.reduced_matrix_nnz,
            estimated_sparse_matrix_storage_bytes=estimate_2d,
        ),
        StructuralLatencyMemoryBenchmarkResult(
            profile=profile,
            dimension=StructuralModelDimension.THREE_D,
            solver_backend=telemetry_3d.solver_backend,
            repeats=repeats,
            p50_solve_seconds=float(np.median(np.array(times_3d, dtype=float))),
            p95_solve_seconds=_p95(times_3d),
            global_dof_count=telemetry_3d.global_dof_count,
            global_matrix_nnz=telemetry_3d.global_matrix_nnz,
            reduced_matrix_nnz=telemetry_3d.reduced_matrix_nnz,
            estimated_sparse_matrix_storage_bytes=estimate_3d,
        ),
    )


def default_matrix_free_acceptance_threshold(
    profile: StructuralProfileClass,
) -> MatrixFreeAcceptanceThreshold:
    """Return default acceptance thresholds for matrix-free telemetry validation."""
    if profile == StructuralProfileClass.OPERATIONAL:
        return MatrixFreeAcceptanceThreshold(
            max_relative_residual_norm=1e-6,
            max_reference_delta_norm=1e-7,
            max_iterations=1_000,
        )

    return MatrixFreeAcceptanceThreshold(
        max_relative_residual_norm=1e-8,
        max_reference_delta_norm=1e-9,
        max_iterations=5_000,
    )


def evaluate_matrix_free_acceptance(
    telemetry: StructuralSolveTelemetry2D,
    profile: StructuralProfileClass,
    threshold: MatrixFreeAcceptanceThreshold | None = None,
) -> MatrixFreeAcceptanceEvaluation:
    """Evaluate matrix-free solve telemetry against profile thresholds."""
    threshold = threshold or default_matrix_free_acceptance_threshold(profile)
    reasons: list[str] = []

    if telemetry.solver_backend != StructuralSolverBackend.MATRIX_FREE_ITERATIVE:
        reasons.append("solver_backend_not_matrix_free")

    if telemetry.iterative_iterations is None:
        reasons.append("missing_iterative_iterations")
    elif telemetry.iterative_iterations > threshold.max_iterations:
        reasons.append("iteration_limit_exceeded")

    if telemetry.iterative_relative_residual_norm is None:
        reasons.append("missing_relative_residual")
    elif telemetry.iterative_relative_residual_norm > threshold.max_relative_residual_norm:
        reasons.append("relative_residual_exceeded")

    if telemetry.matrix_free_reference_delta_norm is None:
        reasons.append("missing_reference_delta")
    elif telemetry.matrix_free_reference_delta_norm > threshold.max_reference_delta_norm:
        reasons.append("reference_delta_exceeded")

    return MatrixFreeAcceptanceEvaluation(
        accepted=not reasons,
        profile=profile,
        reasons=tuple(reasons),
        threshold=threshold,
    )


__all__ = [
    "BoundaryConstraint2D",
    "BoundaryConstraint3D",
    "FEMModel2D",
    "FEMModel3D",
    "FEMSolveResult2D",
    "FEMSolveResult3D",
    "LinearTetrahedronElement",
    "LinearTriangleElement",
    "MatrixFreeAcceptanceEvaluation",
    "MatrixFreeAcceptanceThreshold",
    "MatrixFreePreconditionerBenchmarkResult",
    "NodalLoad2D",
    "NodalLoad3D",
    "Node2D",
    "Node3D",
    "Structural2DMode",
    "Structural2DValidityEnvelope",
    "Structural3DValidityEnvelope",
    "StructuralIterativePreconditioner",
    "StructuralModelDimension",
    "StructuralModelSelectionDecision",
    "StructuralModelSelectionInput",
    "StructuralModelSelectionPolicy",
    "StructuralProfileClass",
    "StructuralSolveTelemetry2D",
    "StructuralSolveTelemetry3D",
    "StructuralSolverBackend",
    "StructuralSolverConfig",
    "StructuralSolverTerminationReason",
    "StructuralLatencyMemoryBenchmarkResult",
    "TetrahedronElementResult",
    "TriangleElementResult",
    "benchmark_matrix_free_preconditioners",
    "benchmark_structural_latency_memory_profiles",
    "default_matrix_free_acceptance_threshold",
    "evaluate_matrix_free_acceptance",
    "select_structural_model_dimension",
    "solve_linear_static_fem",
    "solve_linear_static_fem_3d",
]
