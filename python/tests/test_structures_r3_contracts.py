import math

from brambhand.core.event_bus import Event, EventBus
from brambhand.propulsion.leakage_model import CompartmentState, LeakagePath, apply_leakage
from brambhand.structures.fem.solver import (
    BoundaryConstraint2D,
    BoundaryConstraint3D,
    FEMModel2D,
    FEMModel3D,
    LinearTetrahedronElement,
    LinearTriangleElement,
    MatrixFreeAcceptanceThreshold,
    NodalLoad2D,
    NodalLoad3D,
    Node2D,
    Node3D,
    Structural2DMode,
    Structural2DValidityEnvelope,
    StructuralIterativePreconditioner,
    StructuralModelDimension,
    StructuralModelSelectionInput,
    StructuralProfileClass,
    StructuralSolverBackend,
    StructuralSolverConfig,
    StructuralSolverTerminationReason,
    benchmark_matrix_free_preconditioners,
    benchmark_structural_latency_memory_profiles,
    evaluate_matrix_free_acceptance,
    select_structural_model_dimension,
    solve_linear_static_fem,
    solve_linear_static_fem_3d,
)
from brambhand.structures.fracture import (
    CONNECTED_TOPOLOGY_DAMAGE_PAYLOAD_SCHEMA_VERSION,
    ConnectedTopologyDamagePayload,
    FractureInitiationParams,
    build_connected_topology_damage_payload,
    evaluate_fracture_initiation,
    evaluate_fracture_initiation_from_fem_2d,
    propagate_damage_effects,
)


def _build_plate_model(
    load_scale: float = 1.0,
    backend: StructuralSolverBackend = StructuralSolverBackend.SPARSE_DIRECT,
    preconditioner: StructuralIterativePreconditioner = StructuralIterativePreconditioner.JACOBI,
) -> FEMModel2D:
    nodes = (
        Node2D(0.0, 0.0),
        Node2D(1.0, 0.0),
        Node2D(1.0, 1.0),
        Node2D(0.0, 1.0),
    )
    elements = (
        LinearTriangleElement(
            node_ids=(0, 1, 2),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            node_ids=(0, 2, 3),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
    )
    constraints = {
        0: BoundaryConstraint2D(fix_x=True, fix_y=True),
        3: BoundaryConstraint2D(fix_x=True, fix_y=True),
    }
    loads = {
        1: NodalLoad2D(fx_n=1_000.0 * load_scale, fy_n=0.0),
        2: NodalLoad2D(fx_n=1_000.0 * load_scale, fy_n=0.0),
    }
    return FEMModel2D(
        nodes=nodes,
        elements=elements,
        nodal_loads=loads,
        constraints=constraints,
        solver_config=StructuralSolverConfig(
            backend=backend,
            iterative_preconditioner=preconditioner,
        ),
    )


def test_fem_zero_load_yields_zero_displacement() -> None:
    model = _build_plate_model(load_scale=0.0)

    result = solve_linear_static_fem(model)

    for ux, uy in result.displacements_m:
        assert math.isclose(ux, 0.0, abs_tol=1e-18)
        assert math.isclose(uy, 0.0, abs_tol=1e-18)


def test_fem_displacement_scales_linearly_with_load() -> None:
    result1 = solve_linear_static_fem(_build_plate_model(load_scale=1.0))
    result2 = solve_linear_static_fem(_build_plate_model(load_scale=2.0))

    for (ux1, uy1), (ux2, uy2) in zip(
        result1.displacements_m,
        result2.displacements_m,
        strict=True,
    ):
        assert math.isclose(ux2, 2.0 * ux1, rel_tol=1e-9, abs_tol=1e-18)
        assert math.isclose(uy2, 2.0 * uy1, rel_tol=1e-9, abs_tol=1e-18)


def test_fem_returns_element_stress_metrics() -> None:
    result = solve_linear_static_fem(
        _build_plate_model(
            load_scale=1.0,
            backend=StructuralSolverBackend.SPARSE_DIRECT,
        )
    )

    assert len(result.element_results) == 2
    for element in result.element_results:
        assert element.von_mises_pa >= 0.0

    assert result.telemetry.assembly_backend == "sparse_coo_csr"
    assert result.telemetry.solver_backend == StructuralSolverBackend.SPARSE_DIRECT
    assert (
        result.telemetry.termination_reason
        == StructuralSolverTerminationReason.DIRECT_SOLVE_SUCCESS
    )
    assert result.telemetry.global_matrix_nnz > 0
    assert result.telemetry.reduced_matrix_nnz > 0

    # Right edge nodes should move in +x under +x load.
    assert result.displacements_m[1][0] > 0.0
    assert result.displacements_m[2][0] > 0.0



def test_fem_plane_stress_validity_envelope_rejects_thick_geometry() -> None:
    nodes = (
        Node2D(0.0, 0.0),
        Node2D(1.0, 0.0),
        Node2D(0.0, 1.0),
    )
    thick_element = LinearTriangleElement(
        node_ids=(0, 1, 2),
        thickness_m=0.4,
        youngs_modulus_pa=1e9,
        poisson_ratio=0.2,
    )

    try:
        FEMModel2D(
            nodes=nodes,
            elements=(thick_element,),
            nodal_loads={},
            constraints={0: BoundaryConstraint2D(fix_x=True, fix_y=True)},
            validity_envelope=Structural2DValidityEnvelope(
                mode=Structural2DMode.PLANE_STRESS,
                max_thickness_to_span_ratio_for_plane_stress=0.1,
            ),
        )
    except ValueError as exc:
        assert "Plane-stress validity envelope exceeded" in str(exc)
    else:
        raise AssertionError("Expected validity-envelope rejection for thick plane-stress model")


def test_fem_plane_strain_mode_is_supported_when_envelope_is_satisfied() -> None:
    nodes = (
        Node2D(0.0, 0.0),
        Node2D(1.0, 0.0),
        Node2D(0.0, 1.0),
    )
    element = LinearTriangleElement(
        node_ids=(0, 1, 2),
        thickness_m=0.8,
        youngs_modulus_pa=2e9,
        poisson_ratio=0.25,
    )
    model = FEMModel2D(
        nodes=nodes,
        elements=(element,),
        nodal_loads={1: NodalLoad2D(fx_n=100.0, fy_n=0.0)},
        constraints={
            0: BoundaryConstraint2D(fix_x=True, fix_y=True),
            2: BoundaryConstraint2D(fix_x=True, fix_y=True),
        },
        validity_envelope=Structural2DValidityEnvelope(
            mode=Structural2DMode.PLANE_STRAIN,
            min_thickness_to_span_ratio_for_plane_strain=0.5,
        ),
    )

    result = solve_linear_static_fem(model)
    assert result.displacements_m[1][0] > 0.0


def test_fem_rejects_out_of_plane_envelope_flag() -> None:
    base_model = _build_plate_model()
    try:
        FEMModel2D(
            nodes=base_model.nodes,
            elements=base_model.elements,
            nodal_loads=base_model.nodal_loads,
            constraints=base_model.constraints,
            validity_envelope=Structural2DValidityEnvelope(out_of_plane_effects_present=True),
        )
    except ValueError as exc:
        assert "out-of-plane effects require 3D" in str(exc)
    else:
        raise AssertionError("Expected envelope rejection for out-of-plane effects")


def test_fem_solver_backends_produce_consistent_displacements() -> None:
    dense_result = solve_linear_static_fem(
        _build_plate_model(load_scale=1.0, backend=StructuralSolverBackend.DENSE_DIRECT)
    )
    sparse_direct_result = solve_linear_static_fem(
        _build_plate_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_DIRECT)
    )
    sparse_iterative_result = solve_linear_static_fem(
        _build_plate_model(
            load_scale=1.0,
            backend=StructuralSolverBackend.SPARSE_ITERATIVE,
            preconditioner=StructuralIterativePreconditioner.JACOBI,
        )
    )
    matrix_free_result = solve_linear_static_fem(
        _build_plate_model(
            load_scale=1.0,
            backend=StructuralSolverBackend.MATRIX_FREE_ITERATIVE,
            preconditioner=StructuralIterativePreconditioner.JACOBI,
        )
    )

    assert dense_result.telemetry.iterative_preconditioner is None
    assert (
        dense_result.telemetry.termination_reason
        == StructuralSolverTerminationReason.DIRECT_SOLVE_SUCCESS
    )
    assert sparse_direct_result.telemetry.iterative_preconditioner is None
    assert (
        sparse_direct_result.telemetry.termination_reason
        == StructuralSolverTerminationReason.DIRECT_SOLVE_SUCCESS
    )
    assert (
        sparse_iterative_result.telemetry.iterative_preconditioner
        == StructuralIterativePreconditioner.JACOBI
    )
    assert (
        matrix_free_result.telemetry.iterative_preconditioner
        == StructuralIterativePreconditioner.JACOBI
    )
    assert (
        sparse_iterative_result.telemetry.termination_reason
        == StructuralSolverTerminationReason.ITERATIVE_CONVERGED
    )
    assert sparse_iterative_result.telemetry.iterative_iterations is not None
    assert sparse_iterative_result.telemetry.iterative_iterations >= 1
    assert sparse_iterative_result.telemetry.iterative_residual_norm is not None
    assert sparse_iterative_result.telemetry.iterative_residual_norm < 1e-5
    assert sparse_iterative_result.telemetry.iterative_relative_residual_norm is not None
    assert sparse_iterative_result.telemetry.iterative_relative_residual_norm < 1e-5
    assert (
        matrix_free_result.telemetry.termination_reason
        == StructuralSolverTerminationReason.MATRIX_FREE_CONSISTENCY_VALIDATED
    )
    assert matrix_free_result.telemetry.iterative_iterations is not None
    assert matrix_free_result.telemetry.iterative_iterations >= 1
    assert matrix_free_result.telemetry.iterative_residual_norm is not None
    assert matrix_free_result.telemetry.iterative_residual_norm < 1e-5
    assert matrix_free_result.telemetry.iterative_relative_residual_norm is not None
    assert matrix_free_result.telemetry.iterative_relative_residual_norm < 1e-5
    assert matrix_free_result.telemetry.matrix_free_reference_delta_norm is not None
    assert matrix_free_result.telemetry.matrix_free_reference_delta_norm < 1e-8
    assert matrix_free_result.telemetry.assembly_backend == "matrix_free_operator"

    for dense, sparse_direct, sparse_iter, matrix_free in zip(
        dense_result.displacements_m,
        sparse_direct_result.displacements_m,
        sparse_iterative_result.displacements_m,
        matrix_free_result.displacements_m,
        strict=True,
    ):
        assert math.isclose(dense[0], sparse_direct[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[1], sparse_direct[1], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[0], sparse_iter[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[1], sparse_iter[1], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[0], matrix_free[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[1], matrix_free[1], rel_tol=1e-9, abs_tol=1e-15)


def test_fem_2d_dense_vs_sparse_backends_are_repeatably_deterministic_within_tolerance() -> None:
    dense_first = solve_linear_static_fem(
        _build_plate_model(load_scale=1.0, backend=StructuralSolverBackend.DENSE_DIRECT)
    )
    dense_second = solve_linear_static_fem(
        _build_plate_model(load_scale=1.0, backend=StructuralSolverBackend.DENSE_DIRECT)
    )
    sparse_direct_first = solve_linear_static_fem(
        _build_plate_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_DIRECT)
    )
    sparse_direct_second = solve_linear_static_fem(
        _build_plate_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_DIRECT)
    )
    sparse_iterative_first = solve_linear_static_fem(
        _build_plate_model(
            load_scale=1.0,
            backend=StructuralSolverBackend.SPARSE_ITERATIVE,
            preconditioner=StructuralIterativePreconditioner.JACOBI,
        )
    )
    sparse_iterative_second = solve_linear_static_fem(
        _build_plate_model(
            load_scale=1.0,
            backend=StructuralSolverBackend.SPARSE_ITERATIVE,
            preconditioner=StructuralIterativePreconditioner.JACOBI,
        )
    )

    for dense_a, dense_b, sparse_a, sparse_b, iter_a, iter_b in zip(
        dense_first.displacements_m,
        dense_second.displacements_m,
        sparse_direct_first.displacements_m,
        sparse_direct_second.displacements_m,
        sparse_iterative_first.displacements_m,
        sparse_iterative_second.displacements_m,
        strict=True,
    ):
        # determinism: repeat same backend and model gives numerically identical
        # displacement outputs within tight tolerance
        assert math.isclose(dense_a[0], dense_b[0], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(dense_a[1], dense_b[1], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(sparse_a[0], sparse_b[0], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(sparse_a[1], sparse_b[1], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(iter_a[0], iter_b[0], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(iter_a[1], iter_b[1], rel_tol=0.0, abs_tol=1e-18)

        # backend equivalence: dense and sparse paths agree within strict tolerance
        assert math.isclose(dense_a[0], sparse_a[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[1], sparse_a[1], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[0], iter_a[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[1], iter_a[1], rel_tol=1e-9, abs_tol=1e-15)

    assert (
        sparse_iterative_first.telemetry.iterative_iterations
        == sparse_iterative_second.telemetry.iterative_iterations
    )
    assert math.isclose(
        sparse_iterative_first.telemetry.iterative_residual_norm or 0.0,
        sparse_iterative_second.telemetry.iterative_residual_norm or 0.0,
        rel_tol=0.0,
        abs_tol=1e-18,
    )


def test_matrix_free_residual_safeguard_can_reject_solution() -> None:
    model = _build_plate_model(
        load_scale=1.0,
        backend=StructuralSolverBackend.MATRIX_FREE_ITERATIVE,
        preconditioner=StructuralIterativePreconditioner.JACOBI,
    )
    strict_model = FEMModel2D(
        nodes=model.nodes,
        elements=model.elements,
        nodal_loads=model.nodal_loads,
        constraints=model.constraints,
        validity_envelope=model.validity_envelope,
        solver_config=StructuralSolverConfig(
            backend=StructuralSolverBackend.MATRIX_FREE_ITERATIVE,
            iterative_preconditioner=StructuralIterativePreconditioner.JACOBI,
            matrix_free_max_relative_residual=1e-20,
            matrix_free_consistency_check=False,
        ),
    )

    try:
        solve_linear_static_fem(strict_model)
    except ValueError as exc:
        assert "relative residual safeguard" in str(exc)
    else:
        raise AssertionError("Expected matrix-free residual safeguard failure")


def test_matrix_free_preconditioner_benchmark_reports_results() -> None:
    model = _build_plate_model(
        load_scale=1.0,
        backend=StructuralSolverBackend.MATRIX_FREE_ITERATIVE,
        preconditioner=StructuralIterativePreconditioner.JACOBI,
    )
    results = benchmark_matrix_free_preconditioners(
        model,
        preconditioners=(
            StructuralIterativePreconditioner.NONE,
            StructuralIterativePreconditioner.JACOBI,
            StructuralIterativePreconditioner.BLOCK_JACOBI,
        ),
    )

    assert len(results) == 3
    by_precond = {r.preconditioner: r for r in results}
    assert by_precond[StructuralIterativePreconditioner.NONE].iterations >= 1
    assert by_precond[StructuralIterativePreconditioner.JACOBI].iterations >= 1
    assert by_precond[StructuralIterativePreconditioner.BLOCK_JACOBI].iterations >= 1

    # Advanced preconditioner should not regress against unpreconditioned
    # solve on this reference case.
    assert (
        by_precond[StructuralIterativePreconditioner.BLOCK_JACOBI].iterations
        <= by_precond[StructuralIterativePreconditioner.NONE].iterations
    )


def test_matrix_free_acceptance_threshold_evaluation_operational_and_analysis() -> None:
    matrix_free_result = solve_linear_static_fem(
        _build_plate_model(
            load_scale=1.0,
            backend=StructuralSolverBackend.MATRIX_FREE_ITERATIVE,
            preconditioner=StructuralIterativePreconditioner.BLOCK_JACOBI,
        )
    )

    op_eval = evaluate_matrix_free_acceptance(
        matrix_free_result.telemetry,
        StructuralProfileClass.OPERATIONAL,
    )
    analysis_eval = evaluate_matrix_free_acceptance(
        matrix_free_result.telemetry,
        StructuralProfileClass.ANALYSIS,
    )

    assert op_eval.accepted
    assert analysis_eval.accepted


def test_matrix_free_acceptance_threshold_can_fail_with_strict_override() -> None:
    matrix_free_result = solve_linear_static_fem(
        _build_plate_model(
            load_scale=1.0,
            backend=StructuralSolverBackend.MATRIX_FREE_ITERATIVE,
            preconditioner=StructuralIterativePreconditioner.BLOCK_JACOBI,
        )
    )

    strict = MatrixFreeAcceptanceThreshold(
        max_relative_residual_norm=1e-20,
        max_reference_delta_norm=1e-20,
        max_iterations=1,
    )
    evaluation = evaluate_matrix_free_acceptance(
        matrix_free_result.telemetry,
        StructuralProfileClass.OPERATIONAL,
        threshold=strict,
    )

    assert not evaluation.accepted
    assert len(evaluation.reasons) >= 1


def test_fem_invalid_element_connectivity_is_rejected() -> None:
    model_nodes = (Node2D(0.0, 0.0), Node2D(1.0, 0.0), Node2D(0.0, 1.0))
    bad_element = LinearTriangleElement(
        node_ids=(0, 1, 3),
        thickness_m=0.01,
        youngs_modulus_pa=1e9,
        poisson_ratio=0.2,
    )

    try:
        FEMModel2D(
            nodes=model_nodes,
            elements=(bad_element,),
            nodal_loads={},
            constraints={0: BoundaryConstraint2D(fix_x=True, fix_y=True)},
        )
    except ValueError as exc:
        assert "out of range" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid connectivity")


def _build_tetra_model(
    load_scale: float = 1.0,
    backend: StructuralSolverBackend = StructuralSolverBackend.SPARSE_DIRECT,
) -> FEMModel3D:
    nodes = (
        Node3D(0.0, 0.0, 0.0),
        Node3D(1.0, 0.0, 0.0),
        Node3D(0.0, 1.0, 0.0),
        Node3D(0.0, 0.0, 1.0),
    )
    elements = (
        LinearTetrahedronElement(
            node_ids=(0, 1, 2, 3),
            youngs_modulus_pa=50e9,
            poisson_ratio=0.29,
        ),
    )
    constraints = {
        0: BoundaryConstraint3D(fix_x=True, fix_y=True, fix_z=True),
        1: BoundaryConstraint3D(fix_y=True, fix_z=True),
        2: BoundaryConstraint3D(fix_x=True, fix_z=True),
    }
    loads = {
        3: NodalLoad3D(fx_n=1_000.0 * load_scale, fy_n=0.0, fz_n=0.0),
    }
    return FEMModel3D(
        nodes=nodes,
        elements=elements,
        nodal_loads=loads,
        constraints=constraints,
        solver_config=StructuralSolverConfig(backend=backend),
    )


def _build_benchmark_plate_model_2d() -> FEMModel2D:
    nodes = (
        Node2D(0.0, 0.0),
        Node2D(1.0, 0.0),
        Node2D(2.0, 0.0),
        Node2D(0.0, 1.0),
        Node2D(1.0, 1.0),
        Node2D(2.0, 1.0),
        Node2D(0.0, 2.0),
        Node2D(1.0, 2.0),
        Node2D(2.0, 2.0),
    )

    elements = (
        LinearTriangleElement(
            (0, 1, 4),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            (0, 4, 3),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            (1, 2, 5),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            (1, 5, 4),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            (3, 4, 7),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            (3, 7, 6),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            (4, 5, 8),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
        LinearTriangleElement(
            (4, 8, 7),
            thickness_m=0.01,
            youngs_modulus_pa=70e9,
            poisson_ratio=0.33,
        ),
    )

    constraints = {
        0: BoundaryConstraint2D(fix_x=True, fix_y=True),
        3: BoundaryConstraint2D(fix_x=True, fix_y=True),
        6: BoundaryConstraint2D(fix_x=True, fix_y=True),
    }
    loads = {
        2: NodalLoad2D(fx_n=500.0, fy_n=0.0),
        5: NodalLoad2D(fx_n=500.0, fy_n=0.0),
        8: NodalLoad2D(fx_n=500.0, fy_n=0.0),
    }

    return FEMModel2D(
        nodes=nodes,
        elements=elements,
        nodal_loads=loads,
        constraints=constraints,
        solver_config=StructuralSolverConfig(backend=StructuralSolverBackend.SPARSE_DIRECT),
    )


def _build_benchmark_tetra_model_3d() -> FEMModel3D:
    nodes = (
        Node3D(0.0, 0.0, 0.0),
        Node3D(1.0, 0.0, 0.0),
        Node3D(1.0, 1.0, 0.0),
        Node3D(0.0, 1.0, 0.0),
        Node3D(0.0, 0.0, 1.0),
        Node3D(1.0, 0.0, 1.0),
        Node3D(1.0, 1.0, 1.0),
        Node3D(0.0, 1.0, 1.0),
    )

    elements = (
        LinearTetrahedronElement((0, 1, 3, 4), youngs_modulus_pa=50e9, poisson_ratio=0.29),
        LinearTetrahedronElement((1, 2, 3, 6), youngs_modulus_pa=50e9, poisson_ratio=0.29),
        LinearTetrahedronElement((1, 4, 5, 6), youngs_modulus_pa=50e9, poisson_ratio=0.29),
        LinearTetrahedronElement((3, 4, 6, 7), youngs_modulus_pa=50e9, poisson_ratio=0.29),
        LinearTetrahedronElement((1, 3, 4, 6), youngs_modulus_pa=50e9, poisson_ratio=0.29),
    )

    constraints = {
        0: BoundaryConstraint3D(fix_x=True, fix_y=True, fix_z=True),
        1: BoundaryConstraint3D(fix_x=True, fix_y=True, fix_z=True),
        2: BoundaryConstraint3D(fix_x=True, fix_y=True, fix_z=True),
        3: BoundaryConstraint3D(fix_x=True, fix_y=True, fix_z=True),
    }
    loads = {
        4: NodalLoad3D(fx_n=250.0, fy_n=0.0, fz_n=0.0),
        5: NodalLoad3D(fx_n=250.0, fy_n=0.0, fz_n=0.0),
        6: NodalLoad3D(fx_n=250.0, fy_n=0.0, fz_n=0.0),
        7: NodalLoad3D(fx_n=250.0, fy_n=0.0, fz_n=0.0),
    }

    return FEMModel3D(
        nodes=nodes,
        elements=elements,
        nodal_loads=loads,
        constraints=constraints,
        solver_config=StructuralSolverConfig(backend=StructuralSolverBackend.SPARSE_DIRECT),
    )


def test_fem_3d_zero_load_yields_zero_displacement() -> None:
    result = solve_linear_static_fem_3d(_build_tetra_model(load_scale=0.0))

    for ux, uy, uz in result.displacements_m:
        assert math.isclose(ux, 0.0, abs_tol=1e-18)
        assert math.isclose(uy, 0.0, abs_tol=1e-18)
        assert math.isclose(uz, 0.0, abs_tol=1e-18)


def test_fem_3d_displacement_scales_linearly_with_load() -> None:
    result1 = solve_linear_static_fem_3d(_build_tetra_model(load_scale=1.0))
    result2 = solve_linear_static_fem_3d(_build_tetra_model(load_scale=2.0))

    for (ux1, uy1, uz1), (ux2, uy2, uz2) in zip(
        result1.displacements_m,
        result2.displacements_m,
        strict=True,
    ):
        assert math.isclose(ux2, 2.0 * ux1, rel_tol=1e-9, abs_tol=1e-18)
        assert math.isclose(uy2, 2.0 * uy1, rel_tol=1e-9, abs_tol=1e-18)
        assert math.isclose(uz2, 2.0 * uz1, rel_tol=1e-9, abs_tol=1e-18)


def test_fem_3d_solver_backends_produce_consistent_displacements() -> None:
    dense_result = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.DENSE_DIRECT)
    )
    sparse_direct_result = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_DIRECT)
    )
    sparse_iterative_result = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_ITERATIVE)
    )

    assert (
        dense_result.telemetry.termination_reason
        == StructuralSolverTerminationReason.DIRECT_SOLVE_SUCCESS
    )
    assert (
        sparse_direct_result.telemetry.termination_reason
        == StructuralSolverTerminationReason.DIRECT_SOLVE_SUCCESS
    )
    assert (
        sparse_iterative_result.telemetry.termination_reason
        == StructuralSolverTerminationReason.ITERATIVE_CONVERGED
    )

    for dense, sparse_direct, sparse_iter in zip(
        dense_result.displacements_m,
        sparse_direct_result.displacements_m,
        sparse_iterative_result.displacements_m,
        strict=True,
    ):
        assert math.isclose(dense[0], sparse_direct[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[1], sparse_direct[1], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[2], sparse_direct[2], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[0], sparse_iter[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[1], sparse_iter[1], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense[2], sparse_iter[2], rel_tol=1e-9, abs_tol=1e-15)


def test_fem_3d_dense_vs_sparse_backends_are_repeatably_deterministic_within_tolerance() -> None:
    dense_first = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.DENSE_DIRECT)
    )
    dense_second = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.DENSE_DIRECT)
    )
    sparse_direct_first = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_DIRECT)
    )
    sparse_direct_second = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_DIRECT)
    )
    sparse_iterative_first = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_ITERATIVE)
    )
    sparse_iterative_second = solve_linear_static_fem_3d(
        _build_tetra_model(load_scale=1.0, backend=StructuralSolverBackend.SPARSE_ITERATIVE)
    )

    for dense_a, dense_b, sparse_a, sparse_b, iter_a, iter_b in zip(
        dense_first.displacements_m,
        dense_second.displacements_m,
        sparse_direct_first.displacements_m,
        sparse_direct_second.displacements_m,
        sparse_iterative_first.displacements_m,
        sparse_iterative_second.displacements_m,
        strict=True,
    ):
        assert math.isclose(dense_a[0], dense_b[0], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(dense_a[1], dense_b[1], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(dense_a[2], dense_b[2], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(sparse_a[0], sparse_b[0], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(sparse_a[1], sparse_b[1], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(sparse_a[2], sparse_b[2], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(iter_a[0], iter_b[0], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(iter_a[1], iter_b[1], rel_tol=0.0, abs_tol=1e-18)
        assert math.isclose(iter_a[2], iter_b[2], rel_tol=0.0, abs_tol=1e-18)

        assert math.isclose(dense_a[0], sparse_a[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[1], sparse_a[1], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[2], sparse_a[2], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[0], iter_a[0], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[1], iter_a[1], rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(dense_a[2], iter_a[2], rel_tol=1e-9, abs_tol=1e-15)

    assert (
        sparse_iterative_first.telemetry.iterative_iterations
        == sparse_iterative_second.telemetry.iterative_iterations
    )
    assert math.isclose(
        sparse_iterative_first.telemetry.iterative_residual_norm or 0.0,
        sparse_iterative_second.telemetry.iterative_residual_norm or 0.0,
        rel_tol=0.0,
        abs_tol=1e-18,
    )


def test_structural_latency_memory_benchmark_suite_for_2d_vs_3d_profiles() -> None:
    benchmark_2d, benchmark_3d = benchmark_structural_latency_memory_profiles(
        _build_benchmark_plate_model_2d(),
        _build_benchmark_tetra_model_3d(),
        profile=StructuralProfileClass.OPERATIONAL,
        repeats=3,
    )

    assert benchmark_2d.profile == StructuralProfileClass.OPERATIONAL
    assert benchmark_3d.profile == StructuralProfileClass.OPERATIONAL

    assert benchmark_2d.dimension == StructuralModelDimension.TWO_D
    assert benchmark_3d.dimension == StructuralModelDimension.THREE_D

    assert benchmark_2d.repeats == 3
    assert benchmark_3d.repeats == 3

    assert benchmark_2d.p50_solve_seconds > 0.0
    assert benchmark_2d.p95_solve_seconds > 0.0
    assert benchmark_3d.p50_solve_seconds > 0.0
    assert benchmark_3d.p95_solve_seconds > 0.0

    assert benchmark_2d.global_dof_count > 0
    assert benchmark_3d.global_dof_count > benchmark_2d.global_dof_count

    assert benchmark_2d.global_matrix_nnz > 0
    assert benchmark_3d.global_matrix_nnz > benchmark_2d.global_matrix_nnz

    assert benchmark_2d.estimated_sparse_matrix_storage_bytes > 0
    assert (
        benchmark_3d.estimated_sparse_matrix_storage_bytes
        > benchmark_2d.estimated_sparse_matrix_storage_bytes
    )


def test_structural_latency_memory_benchmark_rejects_non_positive_repeats() -> None:
    try:
        benchmark_structural_latency_memory_profiles(
            _build_benchmark_plate_model_2d(),
            _build_benchmark_tetra_model_3d(),
            repeats=0,
        )
    except ValueError as exc:
        assert "repeats must be positive" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-positive repeats")


def test_structural_model_selection_policy_for_2d_vs_3d() -> None:
    decision_2d = select_structural_model_dimension(
        StructuralModelSelectionInput(
            in_plane_span_m=2.0,
            out_of_plane_span_m=0.02,
            out_of_plane_load_fraction=0.01,
            has_out_of_plane_constraints=False,
        )
    )
    assert decision_2d.dimension == StructuralModelDimension.TWO_D

    decision_3d = select_structural_model_dimension(
        StructuralModelSelectionInput(
            in_plane_span_m=2.0,
            out_of_plane_span_m=0.4,
            out_of_plane_load_fraction=0.2,
            has_out_of_plane_constraints=True,
        )
    )
    assert decision_3d.dimension == StructuralModelDimension.THREE_D
    assert len(decision_3d.reasons) >= 1


def test_fracture_initiation_damage_progression_from_stress_levels() -> None:
    params = FractureInitiationParams(
        yield_von_mises_pa=100.0,
        ultimate_von_mises_pa=200.0,
    )
    states = evaluate_fracture_initiation((50.0, 150.0, 250.0), params)

    assert states[0].damage_fraction == 0.0
    assert math.isclose(states[1].damage_fraction, 0.5)
    assert states[2].damage_fraction == 1.0
    assert not states[1].fractured
    assert states[2].fractured


def test_fracture_initiation_can_be_evaluated_from_fem_results() -> None:
    result = solve_linear_static_fem(_build_plate_model(load_scale=1.0))
    params = FractureInitiationParams(
        yield_von_mises_pa=1e5,
        ultimate_von_mises_pa=1e7,
    )

    states = evaluate_fracture_initiation_from_fem_2d(result, params)

    assert len(states) == len(result.element_results)
    assert all(state.von_mises_pa >= 0.0 for state in states)


def test_damage_propagation_updates_mass_stiffness_contact_and_leak_indicator() -> None:
    params = FractureInitiationParams(
        yield_von_mises_pa=100.0,
        ultimate_von_mises_pa=200.0,
    )
    states = evaluate_fracture_initiation((80.0, 140.0, 220.0), params)

    propagated = propagate_damage_effects(
        states,
        max_mass_loss_fraction=0.3,
        min_stiffness_scale=0.1,
        max_contact_compliance_multiplier=5.0,
        leak_path_damage_threshold=0.9,
    )

    assert propagated.mean_damage_fraction > 0.0
    assert propagated.mass_scale < 1.0
    assert propagated.stiffness_scale < 1.0
    assert propagated.contact_stiffness_scale < 1.0
    assert propagated.leak_path_created


def test_connected_topology_damage_payload_mapping_for_leak_fsi_consumers() -> None:
    params = FractureInitiationParams(
        yield_von_mises_pa=100.0,
        ultimate_von_mises_pa=200.0,
    )
    states = evaluate_fracture_initiation((80.0, 140.0, 220.0, 260.0), params)

    payload = build_connected_topology_damage_payload(
        states,
        component_id="hab_shell",
        leak_path_damage_threshold=0.9,
        hole_area_per_failed_element_m2=2e-4,
    )

    assert payload.schema_version == CONNECTED_TOPOLOGY_DAMAGE_PAYLOAD_SCHEMA_VERSION
    assert payload.component_id == "hab_shell"
    assert payload.failed_element_ids == (2, 3)
    assert payload.leak_path_candidate_element_ids == (2, 3)
    assert payload.hole_area_proxy_m2 == 4e-4
    assert len(payload.crack_network_edges) >= 1


def test_connected_topology_damage_payload_rejects_invalid_version() -> None:
    try:
        ConnectedTopologyDamagePayload(
            component_id="hab_shell",
            schema_version=999,
            damaged_element_ids=(1,),
            failed_element_ids=(1,),
            crack_network_edges=((1, 2),),
            hole_area_proxy_m2=1e-4,
            leak_path_candidate_element_ids=(1,),
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected connected-topology payload version validation failure")


def test_structural_failure_scenario_generates_leak_path_candidates() -> None:
    fem_result = solve_linear_static_fem(_build_plate_model(load_scale=3.0))
    fracture_states = evaluate_fracture_initiation_from_fem_2d(
        fem_result,
        FractureInitiationParams(
            yield_von_mises_pa=2e5,
            ultimate_von_mises_pa=8e5,
        ),
    )

    propagated = propagate_damage_effects(
        fracture_states,
        leak_path_damage_threshold=0.6,
    )
    payload = build_connected_topology_damage_payload(
        fracture_states,
        component_id="pressure_vessel",
        leak_path_damage_threshold=0.6,
    )

    assert propagated.leak_path_created
    assert len(payload.leak_path_candidate_element_ids) >= 1
    assert payload.component_id == "pressure_vessel"


def test_asteroid_impact_fault_chain_connected_topology_progression() -> None:
    bus = EventBus()

    fem_result = solve_linear_static_fem(_build_plate_model(load_scale=4.0))
    fracture_states = evaluate_fracture_initiation_from_fem_2d(
        fem_result,
        FractureInitiationParams(
            yield_von_mises_pa=2e5,
            ultimate_von_mises_pa=7e5,
        ),
    )
    payload = build_connected_topology_damage_payload(
        fracture_states,
        component_id="hab_shell",
        leak_path_damage_threshold=0.6,
        hole_area_per_failed_element_m2=3e-4,
    )

    bus.emit(
        Event(
            sim_time_s=0.0,
            kind="impact_detected",
            payload={"component_id": payload.component_id},
        )
    )
    bus.emit(
        Event(
            sim_time_s=0.1,
            kind="connected_topology_damage_updated",
            payload={
                "failed_element_count": len(payload.failed_element_ids),
                "hole_area_proxy_m2": payload.hole_area_proxy_m2,
            },
        )
    )

    compartment = CompartmentState(
        mass_kg=25.0,
        pressure_pa=101_325.0,
        volume_m3=30.0,
        gas_constant_jpkgk=287.0,
        temperature_k=294.0,
    )
    leak = LeakagePath(
        area_m2=max(payload.hole_area_proxy_m2, 1e-5),
        discharge_coefficient=0.7,
        fluid_density_kgpm3=1.2,
        external_pressure_pa=100.0,
    )

    for step in range(1, 6):
        compartment, leaked_mass = apply_leakage(compartment, leak, dt_s=0.5)
        if leaked_mass > 0.0:
            bus.emit(
                Event(
                    sim_time_s=0.1 + 0.5 * step,
                    kind="depressurization_step",
                    payload={"pressure_pa": compartment.pressure_pa},
                )
            )

    if compartment.pressure_pa < 80_000.0:
        bus.emit(
            Event(
                sim_time_s=3.0,
                kind="alarm_critical_depressurization",
                payload={"pressure_pa": compartment.pressure_pa},
            )
        )

    events = bus.snapshot()

    assert payload.component_id == "hab_shell"
    assert payload.schema_version == CONNECTED_TOPOLOGY_DAMAGE_PAYLOAD_SCHEMA_VERSION
    assert payload.hole_area_proxy_m2 > 0.0
    assert len(payload.failed_element_ids) >= 1
    assert compartment.pressure_pa < 101_325.0
    assert any(event.kind == "alarm_critical_depressurization" for event in events)


