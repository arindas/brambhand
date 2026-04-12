"""Geometry, constitutive, and assembly helpers for 2D/3D structural FEM."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from brambhand.structures.fem.contracts import (
    FEMModel2D,
    FEMModel3D,
    Node2D,
    Node3D,
    Structural2DMode,
)

ElementStiffnessTerms = list[tuple[tuple[int, ...], np.ndarray]]
ElementTerms2D = ElementStiffnessTerms


def triangle_area_and_b_matrix(nodes: tuple[Node2D, Node2D, Node2D]) -> tuple[float, np.ndarray]:
    x1, y1 = nodes[0].x_m, nodes[0].y_m
    x2, y2 = nodes[1].x_m, nodes[1].y_m
    x3, y3 = nodes[2].x_m, nodes[2].y_m

    two_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    area = 0.5 * abs(two_area)
    if area <= 0.0:
        raise ValueError("Element has zero area and is invalid.")

    b = np.array([y2 - y3, y3 - y1, y1 - y2], dtype=float)
    c = np.array([x3 - x2, x1 - x3, x2 - x1], dtype=float)

    b_matrix = np.array(
        [
            [b[0], 0.0, b[1], 0.0, b[2], 0.0],
            [0.0, c[0], 0.0, c[1], 0.0, c[2]],
            [c[0], b[0], c[1], b[1], c[2], b[2]],
        ],
        dtype=float,
    ) / (2.0 * area)
    return area, b_matrix


def tetrahedron_volume_and_b_matrix(
    nodes: tuple[Node3D, Node3D, Node3D, Node3D],
) -> tuple[float, np.ndarray]:
    coordinate_matrix = np.array(
        [
            [1.0, nodes[0].x_m, nodes[0].y_m, nodes[0].z_m],
            [1.0, nodes[1].x_m, nodes[1].y_m, nodes[1].z_m],
            [1.0, nodes[2].x_m, nodes[2].y_m, nodes[2].z_m],
            [1.0, nodes[3].x_m, nodes[3].y_m, nodes[3].z_m],
        ],
        dtype=float,
    )
    det = float(np.linalg.det(coordinate_matrix))
    volume = abs(det) / 6.0
    if volume <= 0.0:
        raise ValueError("Tetrahedral element has zero volume and is invalid.")

    inverse = np.linalg.inv(coordinate_matrix)
    gradients = inverse[1:4, :]  # rows: b,c,d ; columns: node id in local element ordering

    b_matrix = np.zeros((6, 12), dtype=float)
    for i in range(4):
        bi = float(gradients[0, i])
        ci = float(gradients[1, i])
        di = float(gradients[2, i])
        col = 3 * i

        b_matrix[0, col] = bi
        b_matrix[1, col + 1] = ci
        b_matrix[2, col + 2] = di

        b_matrix[3, col] = ci
        b_matrix[3, col + 1] = bi

        b_matrix[4, col + 1] = di
        b_matrix[4, col + 2] = ci

        b_matrix[5, col] = di
        b_matrix[5, col + 2] = bi

    return volume, b_matrix


def in_plane_span_m(nodes: tuple[Node2D, ...]) -> float:
    x_vals = [node.x_m for node in nodes]
    y_vals = [node.y_m for node in nodes]
    span = max(max(x_vals) - min(x_vals), max(y_vals) - min(y_vals))
    if span <= 0.0:
        raise ValueError("2D model must have non-zero in-plane span.")
    return span


def validate_fem_model_2d(model: FEMModel2D) -> None:
    if not model.nodes:
        raise ValueError("At least one node is required.")
    if not model.elements:
        raise ValueError("At least one element is required.")

    max_node = len(model.nodes) - 1
    for element in model.elements:
        for node_id in element.node_ids:
            if not 0 <= node_id <= max_node:
                raise ValueError("Element node_id out of range.")

    for node_id in model.nodal_loads:
        if not 0 <= node_id <= max_node:
            raise ValueError("Load node_id out of range.")

    for node_id in model.constraints:
        if not 0 <= node_id <= max_node:
            raise ValueError("Constraint node_id out of range.")

    env = model.validity_envelope
    if env.out_of_plane_effects_present:
        raise ValueError(
            "2D FEM validity envelope rejected: out-of-plane effects require 3D modeling."
        )

    span_m = in_plane_span_m(model.nodes)
    if env.mode == Structural2DMode.PLANE_STRESS:
        for element in model.elements:
            ratio = element.thickness_m / span_m
            if ratio > env.max_thickness_to_span_ratio_for_plane_stress:
                raise ValueError(
                    "Plane-stress validity envelope exceeded: thickness/span too large."
                )
    else:
        for element in model.elements:
            ratio = element.thickness_m / span_m
            if ratio < env.min_thickness_to_span_ratio_for_plane_strain:
                raise ValueError(
                    "Plane-strain validity envelope violated: thickness/span too small."
                )


def validate_fem_model_3d(model: FEMModel3D) -> None:
    if not model.nodes:
        raise ValueError("At least one node is required.")
    if not model.elements:
        raise ValueError("At least one element is required.")

    max_node = len(model.nodes) - 1
    for element in model.elements:
        for node_id in element.node_ids:
            if not 0 <= node_id <= max_node:
                raise ValueError("Element node_id out of range.")

        n0, n1, n2, n3 = element.node_ids
        tetrahedron_volume_and_b_matrix(
            (model.nodes[n0], model.nodes[n1], model.nodes[n2], model.nodes[n3])
        )

    for node_id in model.nodal_loads:
        if not 0 <= node_id <= max_node:
            raise ValueError("Load node_id out of range.")

    for node_id in model.constraints:
        if not 0 <= node_id <= max_node:
            raise ValueError("Constraint node_id out of range.")


def constitutive_matrix(
    youngs_modulus_pa: float,
    poisson_ratio: float,
    mode: Structural2DMode,
) -> np.ndarray:
    if mode == Structural2DMode.PLANE_STRESS:
        factor = youngs_modulus_pa / (1.0 - poisson_ratio * poisson_ratio)
        return factor * np.array(
            [
                [1.0, poisson_ratio, 0.0],
                [poisson_ratio, 1.0, 0.0],
                [0.0, 0.0, (1.0 - poisson_ratio) / 2.0],
            ],
            dtype=float,
        )

    factor = youngs_modulus_pa / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    return factor * np.array(
        [
            [1.0 - poisson_ratio, poisson_ratio, 0.0],
            [poisson_ratio, 1.0 - poisson_ratio, 0.0],
            [0.0, 0.0, (1.0 - 2.0 * poisson_ratio) / 2.0],
        ],
        dtype=float,
    )


def constitutive_matrix_3d(youngs_modulus_pa: float, poisson_ratio: float) -> np.ndarray:
    lambda_lame = (
        youngs_modulus_pa
        * poisson_ratio
        / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    )
    mu_lame = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))

    return np.array(
        [
            [lambda_lame + 2.0 * mu_lame, lambda_lame, lambda_lame, 0.0, 0.0, 0.0],
            [lambda_lame, lambda_lame + 2.0 * mu_lame, lambda_lame, 0.0, 0.0, 0.0],
            [lambda_lame, lambda_lame, lambda_lame + 2.0 * mu_lame, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, mu_lame, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, mu_lame, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, mu_lame],
        ],
        dtype=float,
    )


def element_dofs(node_ids: tuple[int, int, int]) -> tuple[int, int, int, int, int, int]:
    n0, n1, n2 = node_ids
    return (2 * n0, 2 * n0 + 1, 2 * n1, 2 * n1 + 1, 2 * n2, 2 * n2 + 1)


def element_dofs_3d(node_ids: tuple[int, int, int, int]) -> tuple[int, ...]:
    n0, n1, n2, n3 = node_ids
    return (
        3 * n0,
        3 * n0 + 1,
        3 * n0 + 2,
        3 * n1,
        3 * n1 + 1,
        3 * n1 + 2,
        3 * n2,
        3 * n2 + 1,
        3 * n2 + 2,
        3 * n3,
        3 * n3 + 1,
        3 * n3 + 2,
    )


def assemble_element_stiffness_terms(model: FEMModel2D) -> ElementStiffnessTerms:
    terms: ElementStiffnessTerms = []
    for element in model.elements:
        n0, n1, n2 = element.node_ids
        element_nodes = (model.nodes[n0], model.nodes[n1], model.nodes[n2])
        area, b_matrix = triangle_area_and_b_matrix(element_nodes)
        d_matrix = constitutive_matrix(
            element.youngs_modulus_pa,
            element.poisson_ratio,
            model.validity_envelope.mode,
        )
        ke = element.thickness_m * area * (b_matrix.T @ d_matrix @ b_matrix)
        terms.append((element_dofs(element.node_ids), ke))
    return terms


def assemble_element_stiffness_terms_3d(model: FEMModel3D) -> ElementStiffnessTerms:
    terms: ElementStiffnessTerms = []
    for element in model.elements:
        n0, n1, n2, n3 = element.node_ids
        element_nodes = (model.nodes[n0], model.nodes[n1], model.nodes[n2], model.nodes[n3])
        volume, b_matrix = tetrahedron_volume_and_b_matrix(element_nodes)
        d_matrix = constitutive_matrix_3d(
            element.youngs_modulus_pa,
            element.poisson_ratio,
        )
        ke = volume * (b_matrix.T @ d_matrix @ b_matrix)
        terms.append((element_dofs_3d(element.node_ids), ke))
    return terms


def assemble_global_stiffness_sparse(
    dof_count: int,
    element_terms: ElementStiffnessTerms,
) -> sparse.csr_matrix:
    row_idx: list[int] = []
    col_idx: list[int] = []
    data: list[float] = []

    for dofs, ke in element_terms:
        for i_local, i_global in enumerate(dofs):
            for j_local, j_global in enumerate(dofs):
                row_idx.append(i_global)
                col_idx.append(j_global)
                data.append(float(ke[i_local, j_local]))

    row = np.asarray(row_idx, dtype=np.int64)
    col = np.asarray(col_idx, dtype=np.int64)
    values = np.asarray(data, dtype=float)
    return sparse.coo_matrix((values, (row, col)), shape=(dof_count, dof_count)).tocsr()


def apply_element_terms(
    element_terms: ElementStiffnessTerms,
    vector: np.ndarray,
    dof_count: int,
) -> np.ndarray:
    result = np.zeros(dof_count, dtype=float)
    for dofs, ke in element_terms:
        local = vector[list(dofs)]
        result[list(dofs)] += ke @ local
    return result


def global_diagonal_from_terms(element_terms: ElementStiffnessTerms, dof_count: int) -> np.ndarray:
    diagonal = np.zeros(dof_count, dtype=float)
    for dofs, ke in element_terms:
        for i_local, i_global in enumerate(dofs):
            diagonal[i_global] += float(ke[i_local, i_local])
    return diagonal
