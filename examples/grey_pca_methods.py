"""Compare GreyPCA methods on held-out synthetic rows; no method is declared best."""

import numpy as np
from sklearn.decomposition import IncrementalPCA
from sklearn.model_selection import train_test_split

from greytheory.analysis import GreyPCA


def main():
    random_generator = np.random.default_rng(7)
    factors = random_generator.normal(size=(60, 3)) @ random_generator.normal(size=(3, 8))
    factors += .03 * random_generator.normal(size=factors.shape)
    targets = factors[:, 0] + .05 * random_generator.normal(size=60)
    train_factors, test_factors, train_targets, _ = train_test_split(factors, targets, random_state=7)
    configurations = {
        'pca': {},
        'sparse': {'alpha': .1},
        'kernel': {'kernel': 'rbf', 'gamma': .1},
        'robust': {'tol': 1e-6},
        'robust_sparse': {'alpha': .1, 'ridge': .1, 'max_iter': 2000, 'tol': 1e-5},
        'adv': {'delta': .05, 'max_iter': 500},
    }
    for method, parameters in configurations.items():
        model = GreyPCA(4, top_k=2, standardize=True, method=method, method_params=parameters)
        model.fit(train_factors, train_targets)
        reduced = model.transform(test_factors)
        reconstructed = model.inverse_transform(reduced)
        error = float(np.mean((test_factors - reconstructed) ** 2))
        print(method, 'selected components:', model.selected_components.tolist(),
              'held-out shape:', reduced.shape, 'reconstruction MSE:', round(error, 6))
        if hasattr(model.reducer, 'converged'):
            print('  converged:', model.reducer.converged)
        if hasattr(model.reducer, 'diagnostics'):
            print('  converged:', model.reducer.diagnostics['converged'])
    custom = GreyPCA(estimator=IncrementalPCA(n_components=4, batch_size=12), top_k=2)
    custom.fit(train_factors, train_targets)
    print('custom IncrementalPCA:', custom.transform(test_factors).shape)


if __name__ == '__main__':
    main()
