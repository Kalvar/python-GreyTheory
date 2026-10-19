"""Least squares with diagnostics for the original design matrix."""

import warnings

import numpy as np

from ..._validation import array, scalar


class GreyMath:
    def solve_equations(
        self,
        equations,
        equals,
        *,
        ridge_alpha=0.0,
        rank_policy="warn",
        return_diagnostics=False,
        rcond=None,
        solver="lstsq",
        strict=False,
        penalty_weights=None,
    ):
        B = array(equations, name="equations")
        y = array(equals, name="equals", ndim=1)
        if B.shape[0] != y.size:
            raise ValueError("equations and equals must have the same row count")
        ridge_alpha = scalar(ridge_alpha, "ridge_alpha", minimum=0)
        if rank_policy not in {"warn", "raise", "allow"}:
            raise ValueError("rank_policy must be warn, raise or allow")
        if rcond is not None:
            rcond = scalar(rcond, "rcond", minimum=0)
        if solver not in {"lstsq", "legacy_normal_eq"}:
            raise ValueError("unknown solver")
        coefficients, _, rank, singular = np.linalg.lstsq(B, y, rcond=rcond)
        deficient = rank < B.shape[1]
        condition = float(singular[0] / singular[-1]) if not deficient and singular[-1] > 0 else float("inf")
        messages = []
        if deficient or condition > 1e12:
            message = (
                f"Design matrix rank {rank}/{B.shape[1]}, condition {condition:.3g}; "
                "coefficients and their rankings may not be identifiable"
            )
            messages.append(message)
            if strict or rank_policy == "raise":
                raise ValueError(message)
            if rank_policy == "warn":
                warnings.warn(message, RuntimeWarning, stacklevel=2)
        if ridge_alpha:
            weights = (
                np.ones(B.shape[1])
                if penalty_weights is None
                else array(penalty_weights, name="penalty_weights", ndim=1)
            )
            if weights.shape != (B.shape[1],) or np.any(weights < 0):
                raise ValueError("penalty_weights must be nonnegative, one per coefficient")
            augmented = np.vstack((B, np.diag(np.sqrt(ridge_alpha * weights))))
            coefficients = np.linalg.lstsq(augmented, np.r_[y, np.zeros(B.shape[1])], rcond=rcond)[0]
        elif solver == "legacy_normal_eq":
            warnings.warn("legacy_normal_eq is deprecated and may fail", DeprecationWarning, stacklevel=2)
            coefficients = np.linalg.solve(B.T @ B, B.T @ y)
        if not np.isfinite(coefficients).all() or not np.isfinite(singular).all():
            raise ValueError("nonfinite least-squares result; rescale the input")
        with np.errstate(over="raise", invalid="raise"):
            try:
                residual = y - B @ coefficients
            except FloatingPointError as exc:
                raise ValueError("least-squares residual overflow; rescale the input") from exc
        diagnostics = dict(
            shape=B.shape,
            rank=int(rank),
            singular_values=singular,
            condition_number=condition,
            residual_norm=float(np.linalg.norm(residual)),
            residual_sum_squares=float(residual @ residual),
            solver="ridge_lstsq" if ridge_alpha else solver,
            is_rank_deficient=bool(deficient),
            warnings=messages,
        )
        result = coefficients.tolist()
        return (result, diagnostics) if return_diagnostics else result


def solve_grey_system(B, y, *, method="lstsq", **kwargs):
    return GreyMath().solve_equations(B, y, solver=method, return_diagnostics=True, **kwargs)
