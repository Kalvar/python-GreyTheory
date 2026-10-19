"""Shared data and solver settings for the three grey models."""

import copy

import numpy as np

from ..._validation import array, scalar
from ..._results import result_alias
from ..libs.grey_lib import GreyLib
from ..libs.grey_math import GreyMath


class GreyClass:
    coefficients = result_alias("coefficients_", "Fitted model coefficients.")
    diagnostics = result_alias("diagnostics_", "Solver rank, conditioning, and residual diagnostics.")
    metrics = result_alias("metrics_", "Forecast error metrics.")
    signed_coefficients = result_alias("signed_coefficient_", "Coefficients with their original signs.")
    absolute_coefficients = result_alias("abs_coefficient_", "Absolute coefficient values.")
    ranks = result_alias("rank_", "Coefficient ranks in input order.")
    development_coefficient = result_alias("development_coefficient_", "GM(1,N) development coefficient.")
    driving_coefficients = result_alias("driving_coefficients_", "GM(1,N) driving coefficients.")

    _TAG_FORECAST_NEXT_MOMENT = "forecasted_next_moment"
    _TAG_FORECAST_HISTORY = "history"

    def __init__(
        self, *, alpha=0.5, background_mode="legacy", ridge_alpha=0.0,
        rank_policy="warn", solver="lstsq",
    ):
        self.tag = type(self).__name__
        self.patterns = []
        self.keys = []
        self.grey_lib = GreyLib(alpha, background_mode)
        self.grey_math = GreyMath()
        self.ridge_alpha = scalar(ridge_alpha, "ridge_alpha", minimum=0)
        if rank_policy not in {"warn", "raise", "allow"}:
            raise ValueError("rank_policy must be warn, raise or allow")
        if solver not in {"lstsq", "legacy_normal_eq"}:
            raise ValueError("unknown solver")
        self.rank_policy = rank_policy
        self.solver = solver
        self._has_output = False
        self.remove_all_analysis()

    def _check_key(self, key):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("pattern_key must be a nonempty string")
        if key in self.keys:
            raise ValueError(f"duplicate pattern_key: {key}")

    def _add_outputs(self, outputs, pattern_key):
        self._check_key(pattern_key)
        if self._has_output:
            raise ValueError("only one output sequence is supported; reset(clear_data=True) first")
        values = array(outputs, name="outputs", ndim=1, min_rows=2)
        self.patterns.insert(0, values.tolist())
        self.keys.insert(0, pattern_key)
        self._has_output = True

    def _add_patterns(self, patterns, pattern_key):
        self._check_key(pattern_key)
        self.patterns.append(patterns)
        self.keys.append(pattern_key)

    def _multivariate_data(self):
        if not self._has_output or len(self.patterns) < 2:
            raise ValueError("one output and at least one factor sequence are required")
        values = array(self.patterns, name="patterns")
        if values.shape[1] < 2:
            raise ValueError("at least two observations are required")
        return values

    def _solve(self, B, y, *, penalty_weights=None):
        result, self.diagnostics_ = self.grey_math.solve_equations(
            B,
            y,
            ridge_alpha=self.ridge_alpha,
            rank_policy=self.rank_policy,
            solver=self.solver,
            penalty_weights=penalty_weights,
            return_diagnostics=True,
        )
        self.coefficients_ = np.asarray(result)
        self.signed_coefficient_ = self.coefficients_.copy()
        self.abs_coefficient_ = np.abs(self.coefficients_)
        return self.coefficients_

    def _ago_arrays(self, patterns):
        return self.grey_lib.accumulate(patterns)

    def ago(self, patterns):
        return self.grey_lib.ago(patterns)

    def remove_all_analysis(self):
        self.analyzed_results = []
        self.influence_degrees = []
        self.forecasts = []
        for name in (
            "coefficients_",
            "diagnostics_",
            "signed_coefficient_",
            "abs_coefficient_",
            "rank_",
            "development_coefficient_",
            "driving_coefficients_",
            "metrics_",
        ):
            self.__dict__.pop(name, None)

    def reset(self, clear_data=False):
        self.remove_all_analysis()
        if hasattr(self, "forecasted_outputs"):
            self.forecasted_outputs = []
            self._continuation = []
        if clear_data:
            self.patterns = []
            self.keys = []
            self._has_output = False
        return self

    def print_self(self):
        print(repr(type(self).__name__))

    def print_analyzed_results(self):
        self.print_self()
        for result in self.analyzed_results:
            print(
                f"Pattern key: {result.name!r}, grey value: {result.equation_value!r}, ranking: {result.ranking!r}"
            )

    def print_influence_degrees(self):
        self.print_self()
        print(
            f"The keys of parameters their influence degrees (ordering): {' > '.join(self.influence_degrees)!r}"
        )

    def print_forecasted_results(self):
        self.print_self()
        for result in self.analyzed_results:
            print(f"K = {result.k!r}")
            if result.tag == self._TAG_FORECAST_HISTORY:
                print(
                    f"From original value {result.original_value!r} to forecasted value is {result.forecast_value!r}"
                )
                print(f"The error rate is {result.error_rate!r}")
            else:
                print(f"Forcated next moment value is {result.forecast_value!r}")
        if self.analyzed_results:
            print(f"The average error rate {self.analyzed_results[-1].average_error_rate!r}")

    def deepcopy(self):
        return copy.deepcopy(self)

    @property
    def alpha(self):
        return self.grey_lib.alpha

    @alpha.setter
    def alpha(self, value):
        self.grey_lib.alpha = value

    @property
    def background_mode(self):
        return self.grey_lib.background_mode

    @background_mode.setter
    def background_mode(self, value):
        self.grey_lib.background_mode = value
