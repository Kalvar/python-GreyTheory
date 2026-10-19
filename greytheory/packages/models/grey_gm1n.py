import numpy as np

from .grey_gm0n import GreyGM0N
from .grey_factory import GreyFactory


class GreyGM1N(GreyGM0N):
    def analyze(self):
        self.remove_all_analysis()
        values = self._multivariate_data()
        accumulated, background = self._ago_arrays(values)
        B = np.column_stack((-background, accumulated[1:, 1:].T))
        beta = self._solve(B, values[0, 1:])
        self.development_coefficient_ = float(beta[0])
        self.driving_coefficients_ = beta[1:].copy()
        order = np.argsort(-np.abs(beta[1:]), kind="stable") + 1
        self.rank_ = np.zeros(beta.size, dtype=int)
        self.rank_[order] = np.arange(1, beta.size)
        self.analyzed_results = [GreyFactory(self.keys[0], float(abs(beta[0])), 0, float(beta[0]))]
        self.analyzed_results.extend(
            GreyFactory(self.keys[i], float(abs(beta[i])), rank, float(beta[i]))
            for rank, i in enumerate(order, 1)
        )
        self.influence_degrees = [result.name for result in self.analyzed_results[1:]]
