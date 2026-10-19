import numpy as np

from ..._validation import array
from .grey_class import GreyClass
from .grey_factory import GreyFactory


class GreyGM0N(GreyClass):
    def set_data(self, X, y, *, feature_names=None, target_name="target"):
        """Store observations-by-factors X and target y without fitting.

        Inputs are copied. Invalid data leave the previous model unchanged.
        """
        X = array(X, name="X", min_rows=2)
        y = array(y, name="y", ndim=1, min_rows=2)
        if X.shape[0] != y.size:
            raise ValueError("X and y must have the same observation count")
        if isinstance(feature_names, str):
            raise TypeError("feature_names must be a sequence of names, not a string")
        names = list(feature_names) if feature_names is not None else [f"x{i}" for i in range(X.shape[1])]
        if len(names) != X.shape[1]:
            raise ValueError("feature_names must contain one name per factor")
        keys = [target_name, *names]
        if any(not isinstance(name, str) or not name.strip() for name in keys):
            raise ValueError("target_name and feature_names must be nonempty strings")
        if len(set(keys)) != len(keys):
            raise ValueError("target_name and feature_names must be distinct")
        self.reset(clear_data=True)
        self.patterns = [y.tolist(), *X.T.tolist()]
        self.keys = keys
        self._has_output = True
        return self

    def fit(self, X, y, *, feature_names=None, target_name="target"):
        """Fit factor coefficients; X has shape (observations, factors)."""
        self.set_data(X, y, feature_names=feature_names, target_name=target_name)
        self.analyze()
        return self

    def add_outputs(self, outputs, pattern_key):
        self._add_outputs(outputs, pattern_key)

    def add_patterns(self, patterns, pattern_key):
        self._add_patterns(patterns, pattern_key)

    def analyze(self):
        self.remove_all_analysis()
        values = self._multivariate_data()
        accumulated, background = self._ago_arrays(values)
        B = accumulated[1:, 1:].T
        beta = self._solve(B, background)
        order = np.argsort(-np.abs(beta), kind="stable")
        self.rank_ = np.empty(beta.size, dtype=int)
        self.rank_[order] = np.arange(1, beta.size + 1)
        self.analyzed_results = [
            GreyFactory(self.keys[i + 1], float(abs(beta[i])), rank, float(beta[i]))
            for rank, i in enumerate(order, 1)
        ]
        self.influence_degrees = [result.name for result in self.analyzed_results]
