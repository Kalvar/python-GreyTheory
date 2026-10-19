import numpy as np
import pytest

from greytheory.semiconductor import QualityPLS, ProcessMonitor, suggest_parameters, latin_hypercube
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


def test_quality_and_process_models():
    rng = np.random.default_rng(22)
    X = rng.normal(size=(40, 4))
    y = X[:, 0] - 2 * X[:, 1]
    model = QualityPLS(3).fit(X[:30], y[:30])
    assert np.sqrt(np.mean((model.predict(X[30:]) - y[30:]) ** 2)) < 0.3
    monitor = ProcessMonitor(2, lags=1).fit(X[:30])
    assert monitor.predict(X[30:]).shape == (9,)
    assert monitor.predict(np.ones((3, 4)) * 100).all()
    multi = ProcessMonitor(2).fit(rng.normal(size=(20, 3, 4)))
    assert multi.predict(rng.normal(size=(4, 3, 4))).shape == (4,)
    design = latin_hypercube([[-1, 1], [-2, 2]], 8)
    assert design.shape == (8, 2)
    suggestion = suggest_parameters(
        X[:, :2], -(X[:, 0] ** 2 + X[:, 1] ** 2), [[-1, 1], [-1, 1]], n_candidates=32
    )
    assert np.all(np.abs(suggestion["parameters"]) <= 1) and suggestion["model_std"] >= 0


def test_spectral_adapters():
    x = np.linspace(0, 10, 80)
    S = np.vstack((np.exp(-((x - 3) ** 2)), np.exp(-((x - 7) ** 2))))
    C = np.column_stack((np.linspace(0.1, 1, 12), np.linspace(1, 0.1, 12)))
    X = C @ S
    corrected, baseline = baseline_correct(X + 0.1 * x)
    assert corrected.shape == X.shape and baseline.shape == X.shape
    nmf = fit_nmf(X, 2, max_iter=1000)
    assert np.linalg.norm(nmf.reconstruction - X) / np.linalg.norm(X) < 0.05
    mcr = fit_mcr_als(X, S, max_iter=20)
    np.testing.assert_allclose(mcr.reconstruction, X, atol=1e-8)
    ml = fit_mlpca(X, np.ones_like(X), 2)
    np.testing.assert_allclose(ml.reconstruction, X, atol=1e-8)
    rng = np.random.default_rng(12)
    counts = rng.poisson(10, size=(20, 8))
    p = PoissonPCA(3).fit(counts)
    assert p.transform(counts[:2]).shape == (2, 3)
    assert np.all(p.inverse_transform(p.transform(counts[:2])) >= 0)
    with pytest.raises(ValueError):
        p.transform(-counts)
    cube = rng.normal(size=(8, 8, 3))
    reduced, _ = fit_mnf(cube, 2)
    assert reduced.shape == (8, 8, 2)
    lines = element_lines(26)
    assert any(line["line"] == "KA1_LINE" and 6 < line["energy_keV"] < 7 for line in lines)
    energy = np.linspace(5, 8, 200)
    signal = 100 * np.exp(-0.5 * ((energy - 6.4) / 0.05) ** 2) + 5
    peaks = fit_peaks(energy, signal, [6.4])
    assert peaks["success"] and peaks["amplitudes"][0] == pytest.approx(100, rel=1e-4)
