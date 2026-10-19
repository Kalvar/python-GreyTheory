"""Synthetic quality regression with held-out manufacturing lots."""

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from greytheory.semiconductor import QualityPLS, rank_features


def main():
    rng = np.random.default_rng(17)
    X = rng.normal(size=(100, 8))
    y = X[:, 0] - 2 * X[:, 1] + rng.normal(0, 0.1, 100)
    lots = np.repeat(np.arange(10), 10)
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=0).split(X, y, lots))
    model = QualityPLS(3).fit(X[train], y[train])
    print("held-out lot RMSE", np.sqrt(np.mean((model.predict(X[test]) - y[test]) ** 2)))
    print("training-only GRA ranking", rank_features(X[train], y[train])["indices"])


if __name__ == "__main__":
    main()
