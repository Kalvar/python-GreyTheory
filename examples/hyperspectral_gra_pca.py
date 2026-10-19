"""Synthetic 35 x 186 demonstration; no forensic accuracy claims."""

import numpy as np
from sklearn.model_selection import train_test_split

from greytheory.analysis import grey_relation, GreyFeatureSelector, GreyPCA, AdvPCA


def main():
    rng = np.random.default_rng(20261019)
    wavelengths = np.linspace(400, 1000, 186)
    concentration = rng.uniform(0.1, 1, 35)
    peaks = np.exp(-(((wavelengths - 650) / 80) ** 2))
    X = concentration[:, None] * peaks + rng.normal(0, 0.01, (35, 186))
    X_train, X_test, y_train, _ = train_test_split(X, concentration, test_size=0.25, random_state=0)
    selector = GreyFeatureSelector(10).fit(X_train, y_train)
    print("selected bands", wavelengths[selector.get_support()])
    pca = GreyPCA(10).fit(X_train)
    print("PCA explained variance", pca.explained_variance_ratio.sum())
    print("held-out scores shape", pca.transform(X_test).shape)
    print("raw wavelength-space GRA", grey_relation(X_train[0], X_test))
    adv = AdvPCA(3, max_iter=20, inner_max_iter=100).fit(X_train)
    print("AdvPCA encoder near-zero fraction", adv.sparsity)
    print("Synthetic data only; scores do not establish chemistry, authorship or tampering.")


if __name__ == "__main__":
    main()
