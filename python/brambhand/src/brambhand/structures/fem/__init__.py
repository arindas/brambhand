"""Structural FEM namespace (contracts, geometry, backends, solver, selection)."""

from brambhand.structures.fem.contracts import *  # noqa: F403
from brambhand.structures.fem.selection import (
    select_structural_model_dimension as select_structural_model_dimension,
)
from brambhand.structures.fem.solver import *  # noqa: F403
