"""Backend solve implementations for structural FEM reduced systems."""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse import linalg as sparse_linalg

from brambhand.structures.fem.contracts import (
    StructuralIterativePreconditioner,
    StructuralSolverBackend,
    StructuralSolverConfig,
    StructuralSolverTerminationReason,
)
from brambhand.structures.fem.geometry import (
    ElementTerms2D,
    apply_element_terms,
    assemble_global_stiffness_sparse,
    global_diagonal_from_terms,
)


def build_matrix_free_preconditioner(
    element_terms: ElementTerms2D,
    dof_count: int,
    free: np.ndarray,
    preconditioner_kind: StructuralIterativePreconditioner,
) -> sparse_linalg.LinearOperator | None:
    if preconditioner_kind == StructuralIterativePreconditioner.NONE:
        return None

    if preconditioner_kind == StructuralIterativePreconditioner.JACOBI:
        diagonal = global_diagonal_from_terms(element_terms, dof_count)[free]
        if np.any(np.isclose(diagonal, 0.0)):
            raise ValueError("Jacobi preconditioner requires non-zero diagonal entries.")
        inv_diag = 1.0 / diagonal
        return sparse_linalg.LinearOperator(
            shape=(len(free), len(free)),
            matvec=lambda v: inv_diag * v,
        )

    free_set = set(int(i) for i in free)
    reduced_index = {int(dof): idx for idx, dof in enumerate(free)}
    node_blocks: dict[int, np.ndarray] = {}
    node_free_comp_index: dict[int, dict[int, int]] = {}

    for dofs, ke in element_terms:
        for i_local, gi in enumerate(dofs):
            gi_int = int(gi)
            if gi_int not in free_set:
                continue
            ni, ci = gi_int // 2, gi_int % 2
            node_blocks.setdefault(ni, np.zeros((2, 2), dtype=float))
            node_free_comp_index.setdefault(ni, {})
            node_free_comp_index[ni][ci] = reduced_index[gi_int]

            for j_local, gj in enumerate(dofs):
                gj_int = int(gj)
                if gj_int not in free_set:
                    continue
                nj, cj = gj_int // 2, gj_int % 2
                if ni == nj:
                    node_blocks[ni][ci, cj] += float(ke[i_local, j_local])

    block_inverses: dict[int, np.ndarray] = {}
    scalar_inverses: dict[int, float] = {}

    for node, comp_map in node_free_comp_index.items():
        block = node_blocks.get(node, np.zeros((2, 2), dtype=float))
        if 0 in comp_map and 1 in comp_map:
            det = block[0, 0] * block[1, 1] - block[0, 1] * block[1, 0]
            if np.isclose(det, 0.0):
                raise ValueError("Block-Jacobi preconditioner encountered singular node block.")
            block_inverses[node] = np.linalg.inv(block)
        else:
            comp = 0 if 0 in comp_map else 1
            val = block[comp, comp]
            if np.isclose(val, 0.0):
                raise ValueError(
                    "Block-Jacobi preconditioner encountered zero scalar diagonal entry."
                )
            scalar_inverses[node] = 1.0 / val

    def _apply(v: np.ndarray) -> np.ndarray:
        out = np.zeros_like(v)
        for node, comp_map in node_free_comp_index.items():
            if node in block_inverses:
                idx0 = comp_map[0]
                idx1 = comp_map[1]
                sub = np.array([v[idx0], v[idx1]], dtype=float)
                solved = block_inverses[node] @ sub
                out[idx0] = solved[0]
                out[idx1] = solved[1]
            else:
                comp = 0 if 0 in comp_map else 1
                idx = comp_map[comp]
                out[idx] = scalar_inverses[node] * v[idx]
        return out

    return sparse_linalg.LinearOperator(
        shape=(len(free), len(free)),
        matvec=_apply,
    )


def solve_reduced_system(
    matrix: sparse.csr_matrix,
    rhs: np.ndarray,
    config: StructuralSolverConfig,
) -> tuple[
    np.ndarray,
    StructuralIterativePreconditioner | None,
    int | None,
    float | None,
    float | None,
    float | None,
    StructuralSolverTerminationReason,
]:
    if config.backend == StructuralSolverBackend.DENSE_DIRECT:
        try:
            solution = np.linalg.solve(matrix.toarray(), rhs)
        except np.linalg.LinAlgError as exc:
            raise ValueError("Dense FEM solve failed; system may be singular.") from exc
        residual = float(np.linalg.norm(matrix @ solution - rhs))
        rel_residual = residual / max(float(np.linalg.norm(rhs)), 1e-30)
        return (
            solution,
            None,
            None,
            residual,
            rel_residual,
            None,
            StructuralSolverTerminationReason.DIRECT_SOLVE_SUCCESS,
        )

    if config.backend == StructuralSolverBackend.SPARSE_DIRECT:
        try:
            solution = sparse_linalg.spsolve(matrix, rhs)
        except Exception as exc:
            raise ValueError("Sparse direct FEM solve failed; system may be singular.") from exc
        residual = float(np.linalg.norm(matrix @ solution - rhs))
        rel_residual = residual / max(float(np.linalg.norm(rhs)), 1e-30)
        return (
            solution,
            None,
            None,
            residual,
            rel_residual,
            None,
            StructuralSolverTerminationReason.DIRECT_SOLVE_SUCCESS,
        )

    if config.backend != StructuralSolverBackend.SPARSE_ITERATIVE:
        raise ValueError(f"Unsupported matrix-based backend: {config.backend}")

    preconditioner: sparse_linalg.LinearOperator | None = None
    if config.iterative_preconditioner == StructuralIterativePreconditioner.JACOBI:
        diagonal = matrix.diagonal()
        if np.any(np.isclose(diagonal, 0.0)):
            raise ValueError("Jacobi preconditioner requires non-zero diagonal entries.")
        inv_diag = 1.0 / diagonal
        preconditioner = sparse_linalg.LinearOperator(
            shape=matrix.shape,
            matvec=lambda v: inv_diag * v,
        )
    elif config.iterative_preconditioner == StructuralIterativePreconditioner.BLOCK_JACOBI:
        raise ValueError(
            "Block-Jacobi preconditioner is currently supported only for "
            "matrix-free iterative backend."
        )

    iteration_count = 0

    def _iteration_callback(_: np.ndarray) -> None:
        nonlocal iteration_count
        iteration_count += 1

    solution, info = sparse_linalg.cg(
        matrix,
        rhs,
        M=preconditioner,
        rtol=config.iterative_rtol,
        maxiter=config.iterative_max_iterations,
        callback=_iteration_callback,
    )
    if info < 0:
        raise ValueError("Sparse iterative FEM solve failed due to illegal input/breakdown.")
    if info > 0:
        raise ValueError("Sparse iterative FEM solve did not converge within iteration limit.")

    residual = float(np.linalg.norm(matrix @ solution - rhs))
    rel_residual = residual / max(float(np.linalg.norm(rhs)), 1e-30)
    return (
        solution,
        config.iterative_preconditioner,
        iteration_count,
        residual,
        rel_residual,
        None,
        StructuralSolverTerminationReason.ITERATIVE_CONVERGED,
    )


def solve_reduced_system_matrix_free(
    element_terms: ElementTerms2D,
    rhs: np.ndarray,
    free_dofs: list[int],
    dof_count: int,
    config: StructuralSolverConfig,
) -> tuple[
    np.ndarray,
    StructuralIterativePreconditioner | None,
    int | None,
    float | None,
    float | None,
    float | None,
    StructuralSolverTerminationReason,
]:
    if config.backend != StructuralSolverBackend.MATRIX_FREE_ITERATIVE:
        raise ValueError(f"Unsupported matrix-free backend: {config.backend}")

    free = np.array(free_dofs, dtype=int)

    def _matvec_reduced(v: np.ndarray) -> np.ndarray:
        if np.any(~np.isfinite(v)):
            raise ValueError("Matrix-free matvec received non-finite input vector.")
        full = np.zeros(dof_count, dtype=float)
        full[free] = v
        reduced = apply_element_terms(element_terms, full, dof_count)[free]
        if np.any(~np.isfinite(reduced)):
            raise ValueError("Matrix-free matvec produced non-finite output vector.")
        return reduced

    operator = sparse_linalg.LinearOperator(
        shape=(len(free_dofs), len(free_dofs)),
        matvec=_matvec_reduced,
    )

    preconditioner = build_matrix_free_preconditioner(
        element_terms,
        dof_count,
        free,
        config.iterative_preconditioner,
    )

    iteration_count = 0

    def _iteration_callback(_: np.ndarray) -> None:
        nonlocal iteration_count
        iteration_count += 1

    solution, info = sparse_linalg.cg(
        operator,
        rhs,
        M=preconditioner,
        rtol=config.iterative_rtol,
        maxiter=config.iterative_max_iterations,
        callback=_iteration_callback,
    )
    if info < 0:
        raise ValueError(
            "Matrix-free iterative FEM solve failed due to illegal input/breakdown."
        )
    if info > 0:
        raise ValueError(
            "Matrix-free iterative FEM solve did not converge within iteration limit."
        )

    residual = float(np.linalg.norm(_matvec_reduced(solution) - rhs))
    rel_residual = residual / max(float(np.linalg.norm(rhs)), 1e-30)
    if rel_residual > config.matrix_free_max_relative_residual:
        raise ValueError(
            "Matrix-free iterative FEM solve exceeded relative residual safeguard."
        )

    reference_delta_norm: float | None = None
    if config.matrix_free_consistency_check:
        reduced_sparse = assemble_global_stiffness_sparse(dof_count, element_terms)[
            free_dofs, :
        ][:, free_dofs].tocsr()
        reference_solution = sparse_linalg.spsolve(reduced_sparse, rhs)
        reference_delta_norm = float(np.linalg.norm(solution - reference_solution))
        if not np.allclose(
            solution,
            reference_solution,
            rtol=config.matrix_free_consistency_rtol,
            atol=config.matrix_free_consistency_atol,
        ):
            raise ValueError(
                "Matrix-free consistency check failed against sparse-direct reference."
            )

    return (
        solution,
        config.iterative_preconditioner,
        iteration_count,
        residual,
        rel_residual,
        reference_delta_norm,
        StructuralSolverTerminationReason.MATRIX_FREE_CONSISTENCY_VALIDATED
        if config.matrix_free_consistency_check
        else StructuralSolverTerminationReason.ITERATIVE_CONVERGED,
    )
