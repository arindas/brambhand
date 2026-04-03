"""Contracts and configuration types for structural FEM workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class Node2D:
    """Planar node coordinates in meters."""

    x_m: float
    y_m: float


@dataclass(frozen=True)
class Node3D:
    """Spatial node coordinates in meters."""

    x_m: float
    y_m: float
    z_m: float


@dataclass(frozen=True)
class LinearTriangleElement:
    """Plane-stress constant-strain triangular element."""

    node_ids: tuple[int, int, int]
    thickness_m: float
    youngs_modulus_pa: float
    poisson_ratio: float

    def __post_init__(self) -> None:
        if len(set(self.node_ids)) != 3:
            raise ValueError("Triangle element requires three unique node_ids.")
        if self.thickness_m <= 0.0:
            raise ValueError("thickness_m must be positive.")
        if self.youngs_modulus_pa <= 0.0:
            raise ValueError("youngs_modulus_pa must be positive.")
        if not -0.99 < self.poisson_ratio < 0.49:
            raise ValueError("poisson_ratio must be in (-0.99, 0.49) for stability.")


@dataclass(frozen=True)
class LinearTetrahedronElement:
    """Linear 4-node tetrahedral solid element."""

    node_ids: tuple[int, int, int, int]
    youngs_modulus_pa: float
    poisson_ratio: float

    def __post_init__(self) -> None:
        if len(set(self.node_ids)) != 4:
            raise ValueError("Tetrahedron element requires four unique node_ids.")
        if self.youngs_modulus_pa <= 0.0:
            raise ValueError("youngs_modulus_pa must be positive.")
        if not -0.99 < self.poisson_ratio < 0.49:
            raise ValueError("poisson_ratio must be in (-0.99, 0.49) for stability.")


@dataclass(frozen=True)
class NodalLoad2D:
    """Nodal force vector in Newtons."""

    fx_n: float = 0.0
    fy_n: float = 0.0


@dataclass(frozen=True)
class NodalLoad3D:
    """3D nodal force vector in Newtons."""

    fx_n: float = 0.0
    fy_n: float = 0.0
    fz_n: float = 0.0


@dataclass(frozen=True)
class BoundaryConstraint2D:
    """Boundary condition flags for each translational DOF."""

    fix_x: bool = False
    fix_y: bool = False


@dataclass(frozen=True)
class BoundaryConstraint3D:
    """Boundary condition flags for each translational DOF in 3D."""

    fix_x: bool = False
    fix_y: bool = False
    fix_z: bool = False


class Structural2DMode(StrEnum):
    """Constitutive assumption for reduced-order 2D structural solve."""

    PLANE_STRESS = "plane_stress"
    PLANE_STRAIN = "plane_strain"


class StructuralModelDimension(StrEnum):
    """Dimensionality selection result for structural evaluation."""

    TWO_D = "2d"
    THREE_D = "3d"


class StructuralSolverBackend(StrEnum):
    """Available linear solve backends for structural reduced system."""

    DENSE_DIRECT = "dense_direct"
    SPARSE_DIRECT = "sparse_direct"
    SPARSE_ITERATIVE = "sparse_iterative"
    MATRIX_FREE_ITERATIVE = "matrix_free_iterative"


class StructuralIterativePreconditioner(StrEnum):
    """Preconditioner options for sparse iterative structural solve."""

    NONE = "none"
    JACOBI = "jacobi"
    BLOCK_JACOBI = "block_jacobi"


class StructuralSolverTerminationReason(StrEnum):
    """Termination reason codes for structural linear solve observability."""

    DIRECT_SOLVE_SUCCESS = "direct_solve_success"
    ITERATIVE_CONVERGED = "iterative_converged"
    MATRIX_FREE_CONSISTENCY_VALIDATED = "matrix_free_consistency_validated"


class StructuralProfileClass(StrEnum):
    """Profile class used for matrix-free acceptance thresholds."""

    OPERATIONAL = "operational"
    ANALYSIS = "analysis"


@dataclass(frozen=True)
class StructuralSolverConfig:
    """Backend and controls for structural linear solve."""

    backend: StructuralSolverBackend = StructuralSolverBackend.SPARSE_DIRECT
    iterative_rtol: float = 1e-10
    iterative_max_iterations: int = 10_000
    iterative_preconditioner: StructuralIterativePreconditioner = (
        StructuralIterativePreconditioner.JACOBI
    )
    matrix_free_max_relative_residual: float = 1e-8
    matrix_free_consistency_check: bool = True
    matrix_free_consistency_rtol: float = 1e-8
    matrix_free_consistency_atol: float = 1e-12

    def __post_init__(self) -> None:
        if self.iterative_rtol <= 0.0:
            raise ValueError("iterative_rtol must be positive.")
        if self.iterative_max_iterations <= 0:
            raise ValueError("iterative_max_iterations must be positive.")
        if self.matrix_free_max_relative_residual <= 0.0:
            raise ValueError("matrix_free_max_relative_residual must be positive.")
        if self.matrix_free_consistency_rtol < 0.0:
            raise ValueError("matrix_free_consistency_rtol cannot be negative.")
        if self.matrix_free_consistency_atol < 0.0:
            raise ValueError("matrix_free_consistency_atol cannot be negative.")


@dataclass(frozen=True)
class Structural2DValidityEnvelope:
    """Validity-envelope controls for reduced-order 2D FEM."""

    mode: Structural2DMode = Structural2DMode.PLANE_STRESS
    max_thickness_to_span_ratio_for_plane_stress: float = 0.15
    min_thickness_to_span_ratio_for_plane_strain: float = 0.5
    out_of_plane_effects_present: bool = False
    small_strain_limit: float = 0.02

    def __post_init__(self) -> None:
        if self.max_thickness_to_span_ratio_for_plane_stress <= 0.0:
            raise ValueError("Plane-stress thickness/span limit must be positive.")
        if self.min_thickness_to_span_ratio_for_plane_strain < 0.0:
            raise ValueError("Plane-strain thickness/span floor cannot be negative.")
        if self.small_strain_limit <= 0.0:
            raise ValueError("small_strain_limit must be positive.")


@dataclass(frozen=True)
class Structural3DValidityEnvelope:
    """Validity-envelope controls for 3D linear-static FEM."""

    small_strain_limit: float = 0.02

    def __post_init__(self) -> None:
        if self.small_strain_limit <= 0.0:
            raise ValueError("small_strain_limit must be positive.")


@dataclass(frozen=True)
class StructuralModelSelectionPolicy:
    """Policy thresholds for selecting 2D versus 3D structural models."""

    max_out_of_plane_span_ratio_for_2d: float = 0.05
    max_out_of_plane_load_fraction_for_2d: float = 0.05
    require_3d_for_out_of_plane_constraints: bool = True

    def __post_init__(self) -> None:
        if self.max_out_of_plane_span_ratio_for_2d < 0.0:
            raise ValueError("max_out_of_plane_span_ratio_for_2d cannot be negative.")
        if not 0.0 <= self.max_out_of_plane_load_fraction_for_2d <= 1.0:
            raise ValueError(
                "max_out_of_plane_load_fraction_for_2d must be in [0, 1]."
            )


@dataclass(frozen=True)
class StructuralModelSelectionInput:
    """Inputs consumed by dimensional model-selection policy."""

    in_plane_span_m: float
    out_of_plane_span_m: float
    out_of_plane_load_fraction: float = 0.0
    has_out_of_plane_constraints: bool = False

    def __post_init__(self) -> None:
        if self.in_plane_span_m <= 0.0:
            raise ValueError("in_plane_span_m must be positive.")
        if self.out_of_plane_span_m < 0.0:
            raise ValueError("out_of_plane_span_m cannot be negative.")
        if not 0.0 <= self.out_of_plane_load_fraction <= 1.0:
            raise ValueError("out_of_plane_load_fraction must be in [0, 1].")


@dataclass(frozen=True)
class StructuralModelSelectionDecision:
    """Output of 2D-vs-3D structural model selection."""

    dimension: StructuralModelDimension
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class FEMModel2D:
    """Linear static FEM model container."""

    nodes: tuple[Node2D, ...]
    elements: tuple[LinearTriangleElement, ...]
    nodal_loads: dict[int, NodalLoad2D]
    constraints: dict[int, BoundaryConstraint2D]
    validity_envelope: Structural2DValidityEnvelope = field(
        default_factory=Structural2DValidityEnvelope
    )
    solver_config: StructuralSolverConfig = field(default_factory=StructuralSolverConfig)

    def __post_init__(self) -> None:
        from brambhand.structures.fem.geometry import validate_fem_model_2d

        validate_fem_model_2d(self)


@dataclass(frozen=True)
class FEMModel3D:
    """Linear static 3D FEM model container."""

    nodes: tuple[Node3D, ...]
    elements: tuple[LinearTetrahedronElement, ...]
    nodal_loads: dict[int, NodalLoad3D]
    constraints: dict[int, BoundaryConstraint3D]
    validity_envelope: Structural3DValidityEnvelope = field(
        default_factory=Structural3DValidityEnvelope
    )
    solver_config: StructuralSolverConfig = field(default_factory=StructuralSolverConfig)

    def __post_init__(self) -> None:
        from brambhand.structures.fem.geometry import validate_fem_model_3d

        validate_fem_model_3d(self)


@dataclass(frozen=True)
class TriangleElementResult:
    """Per-element strain/stress metrics."""

    strain_xx: float
    strain_yy: float
    strain_xy: float
    stress_xx_pa: float
    stress_yy_pa: float
    stress_xy_pa: float
    von_mises_pa: float


@dataclass(frozen=True)
class TetrahedronElementResult:
    """Per-element 3D strain/stress metrics."""

    strain_xx: float
    strain_yy: float
    strain_zz: float
    strain_xy: float
    strain_yz: float
    strain_zx: float
    stress_xx_pa: float
    stress_yy_pa: float
    stress_zz_pa: float
    stress_xy_pa: float
    stress_yz_pa: float
    stress_zx_pa: float
    von_mises_pa: float


@dataclass(frozen=True)
class StructuralSolveTelemetry2D:
    """Solve telemetry for structural FEM observability."""

    assembly_backend: str
    solver_backend: StructuralSolverBackend
    termination_reason: StructuralSolverTerminationReason
    global_dof_count: int
    global_matrix_nnz: int
    reduced_matrix_nnz: int
    iterative_preconditioner: StructuralIterativePreconditioner | None = None
    iterative_iterations: int | None = None
    iterative_residual_norm: float | None = None
    iterative_relative_residual_norm: float | None = None
    matrix_free_reference_delta_norm: float | None = None


@dataclass(frozen=True)
class StructuralSolveTelemetry3D:
    """Solve telemetry for 3D structural FEM observability."""

    assembly_backend: str
    solver_backend: StructuralSolverBackend
    termination_reason: StructuralSolverTerminationReason
    global_dof_count: int
    global_matrix_nnz: int
    reduced_matrix_nnz: int
    iterative_preconditioner: StructuralIterativePreconditioner | None = None
    iterative_iterations: int | None = None
    iterative_residual_norm: float | None = None
    iterative_relative_residual_norm: float | None = None


@dataclass(frozen=True)
class FEMSolveResult2D:
    """Global FEM solve outputs."""

    displacements_m: tuple[tuple[float, float], ...]
    reaction_forces_n: tuple[tuple[float, float], ...]
    element_results: tuple[TriangleElementResult, ...]
    telemetry: StructuralSolveTelemetry2D


@dataclass(frozen=True)
class FEMSolveResult3D:
    """Global 3D FEM solve outputs."""

    displacements_m: tuple[tuple[float, float, float], ...]
    reaction_forces_n: tuple[tuple[float, float, float], ...]
    element_results: tuple[TetrahedronElementResult, ...]
    telemetry: StructuralSolveTelemetry3D


@dataclass(frozen=True)
class MatrixFreePreconditionerBenchmarkResult:
    """Benchmark result for one matrix-free preconditioner selection."""

    preconditioner: StructuralIterativePreconditioner
    iterations: int
    residual_norm: float
    relative_residual_norm: float


@dataclass(frozen=True)
class MatrixFreeAcceptanceThreshold:
    """Acceptance bounds for matrix-free solve telemetry under a profile."""

    max_relative_residual_norm: float
    max_reference_delta_norm: float
    max_iterations: int


@dataclass(frozen=True)
class MatrixFreeAcceptanceEvaluation:
    """Pass/fail evaluation output against matrix-free acceptance thresholds."""

    accepted: bool
    profile: StructuralProfileClass
    reasons: tuple[str, ...]
    threshold: MatrixFreeAcceptanceThreshold
