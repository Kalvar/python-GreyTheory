"""Call every first-version public feature from an installed wheel."""

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import greytheory
from sklearn.decomposition import IncrementalPCA

from _synthetic import make_bcf, make_spx
from greytheory import GM0N, GM1N, GM11, ModelQueue, GreyTheory, run_models
from greytheory.analysis import (
    grey_relation,
    GreyFeatureSelector,
    GreyPCA,
    PCAAdapter,
    AdvPCA,
    RobustPCA,
    RobustSparsePCA,
    rank_quality,
    grade_quality,
)
from greytheory.io.bruker import read_spx, read_bcf
from greytheory.semiconductor import (
    QualityPLS,
    ProcessMonitor,
    rank_features,
    suggest_parameters,
    latin_hypercube,
)
from greytheory.spectroscopy import (
    baseline_correct,
    fit_nmf,
    fit_mcr_als,
    fit_mnf,
    PoissonPCA,
    fit_mlpca,
    element_lines,
    fit_peaks,
)


def main():
    rng = np.random.default_rng(19)
    X = rng.normal(size=(24, 5))
    y = X[:, 0] - X[:, 1]
    g = GreyTheory()
    for model in [g.gm0n, g.gm1n]:
        model.add_outputs([2, 4, 7, 8, 11], "target")
        model.add_patterns([1, 2, 3, 4, 5], "factor")
        model.analyze()
        assert np.isfinite(model.coefficients).all()
    g.gm11.fit([2, 3, 4, 5, 6])
    assert g.gm11.predict(2).shape == (2,)
    queue = ModelQueue([
        GM0N().set_data([[1], [2], [3], [4], [5]], [2, 4, 7, 8, 11]),
        GM1N().set_data([[1], [2], [3], [4], [5]], [2, 4, 7, 8, 11]),
        GM11().set_data([2, 3, 4, 5, 6]),
    ])
    assert len(queue.run(workers=2)) == 3
    assert run_models(queue, inplace=False)[0] is not queue[0]
    assert grey_relation(y, [y])[0] == 1
    assert g.gra.rank(y, [y]).tolist() == [0]
    GreyFeatureSelector(2).fit_transform(X, y)
    GreyPCA(3, top_k=2).fit_transform(X, y)
    for method, parameters in [
        ("pca", {}), ("sparse", {"alpha": .1}), ("kernel", {"gamma": .1}),
        ("robust", {}), ("robust_sparse", {"alpha": .1}), ("adv", {"delta": 0}),
    ]:
        flexible = GreyPCA(3, top_k=2, method=method, method_params=parameters).fit(X, y)
        assert flexible.transform(X[:3]).shape == (3, 2)
        assert flexible.inverse_transform(flexible.transform(X[:3])).shape == (3, X.shape[1])
    custom = GreyPCA(estimator=IncrementalPCA(3, batch_size=8), top_k=2).fit(X, y)
    assert custom.transform(X[:3]).shape == (3, 2)
    for method in ["pca", "sparse", "kernel"]:
        model = PCAAdapter(2, method=method).fit(X)
        model.inverse_transform(model.transform(X))
    a = AdvPCA(2).fit(X)
    a.inverse_transform(a.transform(X))
    quality = rank_quality([[80, 10], [40, 20], [20, 25]], ['smaller', 'larger'],
                           bounds=[(0, 100), (0, 30)])
    np.testing.assert_array_equal(quality.ranking, [2, 1, 0])
    np.testing.assert_allclose(
        grade_quality(quality.normalizer.transform([[20, 25]])).scores, quality.scores[2:]
    )
    safe = GreyPCA(3, method='adv', method_params={'delta': 0}, top_k=2,
                   align_to_target=True).fit(X, y)
    assert safe.transform(X[:3]).shape == (3, 2)
    assert safe.reducer.inner_converged
    assert safe.reconstruction_report(X).prefix_coverage.shape == (3,)
    assert GreyPCA(.85).fit(X).explained_variance_ratio.sum() >= .85
    RobustPCA().fit_transform(X)
    RobustSparsePCA(2).fit_transform(X)
    QualityPLS(2).fit(X, y).predict(X[:2])
    ProcessMonitor(2, lags=1).fit(X).predict(X[:5])
    rank_features(X, y)
    latin_hypercube([[-1, 1]] * 5, 5)
    suggest_parameters(X, y, [[-1, 1]] * 5, n_candidates=8)
    energy = np.linspace(0, 10, 50)
    components = np.vstack((np.exp(-((energy - 3) ** 2)), np.exp(-((energy - 7) ** 2))))
    data = rng.uniform(0.1, 1, (15, 2)) @ components
    baseline_correct(data)
    fit_nmf(data)
    fit_mcr_als(data, components, max_iter=10)
    fit_mlpca(data, np.ones_like(data))
    fit_mnf(rng.normal(size=(8, 8, 3)))
    PoissonPCA().fit_transform(rng.poisson(10, size=(12, 6)))
    element_lines(26)
    fit_peaks(energy, data[0], [3, 7], sigma=0.5)
    with tempfile.TemporaryDirectory() as temp:
        spx, bcf = Path(temp) / "test.spx", Path(temp) / "test.bcf"
        make_spx(spx)
        make_bcf(bcf)
        np.testing.assert_array_equal(read_spx(spx).counts, [1, 2, 3])
        image = read_bcf(bcf)
        np.testing.assert_array_equal(image.get_pixel(0, 0), [1, 2, 3])
        image.get_spectra()
        image.sum_detectors(0, 0)
        list(image.iter_tiles())
        read_bcf(bcf, lazy=False)
    print(
        json.dumps(
            dict(
                status="PASS",
                python=sys.version.split()[0],
                scope="first-version APIs; generated reader samples",
                package_path=greytheory.__file__,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
