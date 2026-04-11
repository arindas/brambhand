import math

import pytest

from brambhand.physics.vector import Vector3


def test_vector_addition_and_subtraction() -> None:
    a = Vector3(1.0, 2.0, 3.0)
    b = Vector3(-4.0, 5.0, 0.5)

    assert a + b == Vector3(-3.0, 7.0, 3.5)
    assert a - b == Vector3(5.0, -3.0, 2.5)


def test_scalar_multiplication_and_division() -> None:
    v = Vector3(2.0, -4.0, 8.0)

    assert v * 0.5 == Vector3(1.0, -2.0, 4.0)
    assert 0.5 * v == Vector3(1.0, -2.0, 4.0)
    assert v / 2.0 == Vector3(1.0, -2.0, 4.0)


def test_dot_and_cross_products() -> None:
    i = Vector3(1.0, 0.0, 0.0)
    j = Vector3(0.0, 1.0, 0.0)
    k = Vector3(0.0, 0.0, 1.0)

    assert i.dot(j) == 0.0
    assert i.dot(i) == 1.0
    assert i.cross(j) == k


def test_norm_and_normalization() -> None:
    v = Vector3(3.0, 4.0, 0.0)

    assert v.squared_norm() == 25.0
    assert v.norm() == 5.0

    n = v.normalized()
    assert math.isclose(n.norm(), 1.0)
    assert n == Vector3(0.6, 0.8, 0.0)


def test_divide_by_zero_raises() -> None:
    with pytest.raises(ZeroDivisionError):
        _ = Vector3(1.0, 2.0, 3.0) / 0.0


def test_normalize_zero_raises() -> None:
    with pytest.raises(ValueError):
        _ = Vector3(0.0, 0.0, 0.0).normalized()
