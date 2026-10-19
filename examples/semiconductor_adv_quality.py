"""Synthetic process features -> AdvPCA/GRA -> held-out-lot quality prediction.

Warpage/shear are measured responses used to define the target. They are never
fed back into the process-feature matrix. All values and limits are illustrative.
"""

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

from greytheory.analysis import GreyPCA, grade_quality, rank_quality


def main():
    random_generator = np.random.default_rng(21)
    lots = np.repeat(np.arange(12), 10)
    latent = random_generator.uniform(-1, 1, (len(lots), 2))
    process_features = latent @ random_generator.normal(size=(2, 8))
    process_features += random_generator.normal(0, .03, process_features.shape)
    warpage = 40 - 10 * latent[:, 0] + random_generator.normal(0, .2, len(lots))
    shear = 15 + 4 * latent[:, 1] + random_generator.normal(0, .1, len(lots))
    responses = np.column_stack((warpage, shear))
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=7).split(
        process_features, groups=lots
    ))
    quality = rank_quality(
        responses[train], ['smaller', 'larger'],
        bounds=[(0, 100), (0, 30)], weights=[.5, .5],
    )
    held_out_quality = grade_quality(
        quality.normalizer.transform(responses[test]), weights=quality.weights, rho=quality.rho,
    ).scores
    reducer = GreyPCA(
        3, method='adv', method_params={'delta': .01, 'max_iter': 1000},
        top_k=2, standardize=True, component_direction='either', align_to_target=True,
    )
    predictor = Pipeline([('features', reducer), ('regression', Ridge(alpha=.1))])
    predictor.fit(process_features[train], quality.scores)
    if not reducer.reducer.converged or not reducer.reducer.inner_converged:
        raise RuntimeError('AdvPCA did not converge; review training settings before evaluating predictions')
    predicted = predictor.predict(process_features[test])
    report = reducer.reconstruction_report(process_features[train], threshold=.85)
    print('Quality response directions: warpage=smaller, shear=larger')
    print('Train lots:', sorted(set(lots[train].tolist())))
    print('Test lots:', sorted(set(lots[test].tolist())))
    print('Selected components:', reducer.selected_components.tolist())
    print('GRA comparison signs:', reducer.component_directions.tolist())
    print('AdvPCA outer convergence:', reducer.reducer.converged)
    print('AdvPCA final inner convergence:', reducer.reducer.inner_converged)
    print('Prefix reconstruction coverage:', np.round(report.prefix_coverage, 4).tolist())
    print('Coverage after GRA selection:', round(report.selected_coverage, 4))
    print('Held-out-lot target MAE:', round(mean_absolute_error(held_out_quality, predicted), 5))
    baseline = np.full(len(test), quality.scores.mean())
    print('Training-mean target MAE:', round(mean_absolute_error(held_out_quality, baseline), 5))
    conventional = GreyPCA(.85, method='pca', standardize=True).fit(process_features[train])
    print('Conventional PCA component count for 85%:', conventional.n_components_fitted)
    print('Synthetic demonstration only. Quality grades are not yield or pass/fail probabilities.')


if __name__ == '__main__':
    main()
