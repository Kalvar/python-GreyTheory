import numpy as np
import pytest
from sklearn.decomposition import PCA

from greytheory.analysis import (
    grey_relation,
    GreyFeatureSelector,
    GreyPCA,
    PCAAdapter,
    AdversarialPCA,
    RobustPCA,
    RobustSparsePCA,
)
from greytheory.analysis.adversarial import eta_regression, adversarial_objective


def test_gra_formula():
    scores, coefficients = grey_relation([0, 0], [[0, 3], [1, 1]], return_coefficients=True)
    np.testing.assert_allclose(scores, [2 / 3, 0.6])
    np.testing.assert_allclose(coefficients, [[1, 1 / 3], [0.6, 0.6]])
    np.testing.assert_allclose(grey_relation([2, 2], [[2, 2]], normalize="zscore"), 1)
    np.testing.assert_allclose(grey_relation([0, 0], [[0, 3]], weights=[1, 0]), 1)
    for kwargs in ({"rho": 0}, {"rho": 2}, {"weights": [0, 0]}, {"normalize": "initial"}):
        with pytest.raises(ValueError):
            grey_relation([0, 0], [[0, 3]], **kwargs)


def test_selection_and_pipeline():
    rng = np.random.default_rng(2)
    y = np.linspace(-2, 2, 30)
    X = np.column_stack((y, -y, rng.normal(size=30)))
    selector = GreyFeatureSelector(1).fit(X, y)
    assert selector.selected_indices_.tolist() == [0]
    np.testing.assert_array_equal(selector.get_support(indices=True), [0])
    assert selector.get_feature_names_out().tolist() == ["x0"]
    fitted = selector.scores_.copy()
    assert selector.transform(X[:2]).shape == (2, 1)
    np.testing.assert_array_equal(selector.scores_, fitted)
    p = GreyPCA(2, top_k=1).fit(X, y)
    assert p.transform(X[:4]).shape == (4, 1)
    with pytest.raises(ValueError):
        GreyPCA(2, top_k=1).fit(X)


@pytest.mark.parametrize("method", ["pca", "sparse", "kernel"])
def test_pca_adapters(method):
    X = np.random.default_rng(5).normal(size=(12, 7))
    m = PCAAdapter(2, method=method).fit(X)
    Z = m.transform(X[:3])
    assert Z.shape == (3, 2)
    assert m.inverse_transform(Z).shape == (3, 7)
    if method == "pca":
        expected = PCA(2, svd_solver="full").fit(X)
        np.testing.assert_allclose(
            m.components_.T @ m.components_, expected.components_.T @ expected.components_, atol=1e-12
        )
        np.testing.assert_allclose(m.explained_variance_ratio_, expected.explained_variance_ratio_)


def test_adversarial_zero_radius_and_objective():
    X = np.random.default_rng(3).normal(size=(18, 7))
    m = AdversarialPCA(3, delta=0).fit(X)
    p = PCA(3).fit(X)
    np.testing.assert_allclose(m.decoder_ @ m.decoder_.T, p.components_.T @ p.components_, atol=1e-12)
    np.testing.assert_allclose(
        m.inverse_transform(m.transform(X)), p.inverse_transform(p.transform(X)), atol=1e-12
    )
    A = m.decoder_
    B = m.encoder_ * 0.8
    delta = np.array([0.1, 0.2, 0.3])
    C = X - X.mean(0)
    from itertools import product

    brute = sum(
        max(
            np.sum((x - A @ (B.T @ x + np.array(sign) * delta * np.abs(B).sum(0))) ** 2)
            for sign in product([-1, 1], repeat=3)
        )
        for x in C
    )
    assert adversarial_objective(C, A, B, delta) == pytest.approx(brute)


def test_eta_against_convex_reference():
    import cvxpy as cp

    rng = np.random.default_rng(44)
    X = rng.normal(size=(25, 6))
    a = rng.normal(size=6)
    a /= np.linalg.norm(a)
    delta = 0.25
    b, d = eta_regression(X, a, delta, max_iter=2000, tol=1e-11)
    beta = cp.Variable(6)
    objective = cp.sum_squares(cp.abs(X @ a - X @ beta) + delta * cp.norm1(beta))
    problem = cp.Problem(cp.Minimize(objective))
    problem.solve(solver="CLARABEL")
    actual = np.sum((np.abs(X @ a - X @ b) + delta * np.linalg.norm(b, 1)) ** 2)
    assert actual == pytest.approx(problem.value, rel=2e-5, abs=1e-6)
    assert d["converged"]


def test_adversarial_nonzero_and_constant():
    X = np.random.default_rng(6).normal(size=(20, 5))
    m = AdversarialPCA(2, max_iter=100).fit(X)
    np.testing.assert_allclose(m.decoder_.T @ m.decoder_, np.eye(2), atol=1e-12)
    assert np.isfinite(m.objective_history_).all()
    assert m.transform(X[:2]).shape == (2, 2)
    m = AdversarialPCA(2).fit(np.ones((5, 4)))
    np.testing.assert_allclose(m.inverse_transform(m.transform(np.ones((2, 4)))), 1)


def test_robust_decomposition():
    rng = np.random.default_rng(10)
    L = rng.normal(size=(30, 2)) @ rng.normal(size=(2, 25))
    S = np.zeros_like(L)
    S[1, 2] = 100
    S[9, 5] = -80
    m = RobustPCA().fit(L + S)
    np.testing.assert_allclose(m.low_rank_ + m.sparse_, L + S, atol=2e-5)
    assert np.linalg.norm(m.low_rank_ - L) / np.linalg.norm(L) < 0.1
    sparse = RobustSparsePCA(2).fit(L + S)
    assert sparse.transform(L[:2]).shape == (2, 2)


@pytest.mark.parametrize(
    "reference,candidates", [([], [[1]]), ([1], []), ([1], [[1, 2]]), ([np.nan], [[1]]), ([1], [[np.inf]])]
)
def test_gra_invalid_inputs(reference, candidates):
    with pytest.raises((ValueError, TypeError)):
        grey_relation(reference, candidates)


@pytest.mark.parametrize("normalization", ["none", "minmax", "zscore", "mean", "initial"])
def test_gra_identity_and_stable_rank(normalization):
    from greytheory import GreyTheory

    values = [1, 2, 3]
    g = GreyTheory().gra
    np.testing.assert_allclose(g.score(values, [values, values], normalization=normalization), 1)
    np.testing.assert_array_equal(g.rank(values, [values, values], normalization=normalization), [0, 1])


def test_selection_rejects_constant_and_shape_change():
    X = np.arange(20).reshape(5, 4)
    with pytest.raises(ValueError):
        GreyFeatureSelector(2).fit(X, np.ones(5))
    with pytest.raises(ValueError):
        GreyFeatureSelector(5).fit(X, np.arange(5))
    m = GreyFeatureSelector(2).fit(X, np.arange(5))
    with pytest.raises(ValueError):
        m.transform(np.ones((2, 3)))


def test_pca_training_statistics_unchanged():
    X = np.random.default_rng(12).normal(size=(12, 6))
    p = PCAAdapter(3, standardize=True).fit(X[:8])
    mean = p.mean_.copy()
    components = p.components_.copy()
    p.transform(X[8:] + 1000)
    np.testing.assert_array_equal(p.mean_, mean)
    np.testing.assert_array_equal(p.components_, components)
    np.testing.assert_allclose(mean, X[:8].mean(0))


def test_wide_eta_and_zero_encoder_reference():
    rng = np.random.default_rng(31)
    X = rng.normal(size=(7, 12))
    a = rng.normal(size=12)
    a /= np.linalg.norm(a)
    b, d = eta_regression(X, a, 0.2, max_iter=2000, tol=1e-10)
    import cvxpy as cp

    beta = cp.Variable(12)
    problem = cp.Problem(cp.Minimize(cp.sum_squares(cp.abs(X @ a - X @ beta) + 0.2 * cp.norm1(beta))))
    problem.solve(solver="CLARABEL")
    value = np.sum((np.abs(X @ a - X @ b) + 0.2 * np.linalg.norm(b, 1)) ** 2)
    assert value == pytest.approx(problem.value, rel=1e-4, abs=1e-5)
    zero, _ = eta_regression(X, a, 1e6)
    np.testing.assert_array_equal(zero, np.zeros(12))


def test_joint_robust_sparse_objective():
    from greytheory.analysis.robust import robust_sparse_objective

    rng = np.random.default_rng(15)
    X = rng.normal(size=(25, 6))
    X[2, 3] = 15
    m = RobustSparsePCA(2, alpha=0.5, kappa=0.8, max_iter=2000, tol=1e-8).fit(X)
    history = m.diagnostics_["objective_history"]
    assert np.all(np.diff(history) <= 1e-8)
    np.testing.assert_allclose(m.decoder_.T @ m.decoder_, np.eye(2), atol=1e-12)
    assert np.any(m.encoder_ == 0) and np.any(m.sparse_ != 0)
    centered = X - m.mean_
    residual = centered - (centered @ m.encoder_) @ m.decoder_.T
    expected = np.sign(residual) * np.maximum(np.abs(residual) - m.kappa, 0)
    np.testing.assert_allclose(m.sparse_, expected, atol=1e-10)
    huber = np.where(
        np.abs(residual) <= m.kappa, 0.5 * residual**2, m.kappa * np.abs(residual) - 0.5 * m.kappa**2
    ).sum()
    penalty = m.alpha * np.abs(m.encoder_).sum() + 0.5 * m.ridge * np.sum(m.encoder_**2)
    assert robust_sparse_objective(
        centered, m.decoder_, m.encoder_, m.sparse_, m.alpha, m.ridge, m.kappa
    ) == pytest.approx(huber + penalty)
    np.testing.assert_allclose(m.inverse_transform(m.transform(X)), m.low_rank_)


def test_gra_exact_identity_and_overflow_policy():
    y = np.random.default_rng(19).normal(size=24)
    assert grey_relation(y, [y])[0] == 1.0
    with pytest.raises(ValueError, match="overflow"):
        grey_relation([1e308], [[-1e308]])


def test_pca_constant_feature_and_zero_variance_policy():
    X = np.column_stack((np.arange(6), np.ones(6)))
    m = PCAAdapter(1, standardize=True).fit(X)
    assert np.isfinite(m.transform(X)).all()
    assert np.isfinite(m.explained_variance_ratio_).all()
    with pytest.raises(ValueError, match="variance"):
        PCAAdapter(1).fit(np.ones((4, 3)))


def test_adversarial_single_feature_adaptive_radius():
    X = np.arange(8, dtype=float)[:, None]
    m = AdversarialPCA(1).fit(X)
    np.testing.assert_array_equal(m.delta_, [0])
    np.testing.assert_allclose(m.inverse_transform(m.transform(X)), X, atol=1e-12)
