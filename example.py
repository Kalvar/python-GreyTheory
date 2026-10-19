"""Fit and batch grey models. Run python3 run.py to set up and execute."""

import numpy as np

from greytheory import GM0N, GM1N, GM11, ModelQueue


def main(workers=1):
    factors_0 = np.array([
        [.75, 1.22, .2, 1., 1., 1.],
        [.5, 1., .7, .66, 1., .5],
        [1., 1.09, .4, .33, .66, .25],
        [.25, .99, 1., .66, .33, .25],
    ]).T
    factors_1 = np.array([
        [3., 13.5, 1., 3., 3., 4.],
        [2., 11., 3.5, 2., 3., 2.],
        [4., 12., 2., 1., 2., 1.],
        [1., 10., 5., 2., 1., 1.],
    ]).T
    names = ["x2", "x3", "x4", "x5"]
    series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]

    # set_data defers fitting until run(); fit(X, y) computes immediately.
    gm0n = GM0N().set_data(factors_0, [1.] * 6, feature_names=names, target_name="x1")
    gm1n = GM1N().set_data(
        factors_1, [2., 11., 1.5, 2., 2.2, 3.], feature_names=names, target_name="x1"
    )
    gm11 = GM11(window_size=4).set_data(series)

    # Each insertion owns a separate snapshot. Mixed model types share one run.
    queue = ModelQueue([gm0n, gm1n])
    queue.append(gm11)
    results = queue.run(workers=workers)
    for model in results[:2]:
        print(model.influence_degrees)
    print(results[2].predict(2))
    return dict(zip(("gm0n", "gm1n", "gm11"), results))


if __name__ == "__main__":
    main(workers=2)
