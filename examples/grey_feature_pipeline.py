"""Multidimensional inputs -> local features -> Grey windows -> PCA/GRA -> model.

All default inputs are synthetic. Predictions and reference distances are
engineering demonstrations, not handwriting, chemistry, or overpainting results.
"""

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import Pipeline

from greytheory.analysis import GreyPCA
from greytheory.features import GreyWindowFeatures, ImagePatchFeatures, Trajectory, TrajectoryFeatures


def make_trajectory_regressor():
    return Pipeline(
        [
            ("trajectory", TrajectoryFeatures(n_points=32, include_time=True)),
            ("windows", GreyWindowFeatures(window_size=8, stride=4, boundary_channel=-1)),
            ("reducer", GreyPCA(n_components=4, top_k=2, standardize=True)),
            ("model", Ridge(alpha=1)),
        ]
    )


def main():
    random_generator = np.random.default_rng(7)
    times = np.linspace(0, 1, 24)
    amplitudes = random_generator.uniform(0.5, 2, 36)
    paths = [
        Trajectory(
            np.column_stack((times, amplitude * np.sin(np.pi * times))),
            timestamps=times,
        )
        for amplitude in amplitudes
    ]
    # The target is a known simulation parameter, never an author ID.
    regressor = make_trajectory_regressor().fit(paths[:28], amplitudes[:28])
    predicted = regressor.predict(paths[28:])
    print("Synthetic 2D trajectory target MAE:", round(mean_absolute_error(amplitudes[28:], predicted), 4))
    print(
        "Training-mean target MAE:",
        round(mean_absolute_error(amplitudes[28:], np.full(8, amplitudes[:28].mean())), 4),
    )
    print("GRA-selected components:", regressor.named_steps["reducer"].selected_components.tolist())

    for dimensions in (2, 3, 5):
        trajectories = [
            np.column_stack([np.sin((axis + 1) * times + offset) for axis in range(dimensions)])
            for offset in np.linspace(0, 1, 8)
        ]
        extractor = Pipeline(
            [
                ("trajectory", TrajectoryFeatures(n_points=32)),
                ("windows", GreyWindowFeatures(8, stride=4, boundary_channel=-1)),
            ]
        )
        features = extractor.fit_transform(trajectories)
        print(f"{dimensions}D trajectories -> feature matrix:", features.shape)

    # Separate strokes: the 99-unit pen-up jump is not counted as travel or speed.
    split_path = Trajectory(
        points=[[0, 0], [1, 0], [100, 0], [101, 0]],
        timestamps=[0, 1, 20, 21],
        stroke_ids=[0, 0, 1, 1],
    )
    extractor = TrajectoryFeatures(n_points=16, include_time=True)
    sequence = extractor.fit_transform([split_path])
    distance_index = extractor.get_feature_names_out().tolist().index("step_distance")
    print("Recorded pen-down travel distance:", round(float(sequence[0, :, distance_index].sum()), 6))

    # Unsupervised reference ranking: fit the representation on references only.
    reference_pipeline = Pipeline(
        [
            ("trajectory", TrajectoryFeatures(n_points=32)),
            ("windows", GreyWindowFeatures(8, stride=4, boundary_channel=-1)),
            ("reducer", GreyPCA(n_components=4, standardize=True)),
        ]
    )
    references = reference_pipeline.fit_transform(paths[:28])
    query = reference_pipeline.transform(paths[28:29])
    distances = pairwise_distances(query, references)[0]
    ranking = np.argsort(distances, kind="stable")
    print(
        "Nearest reference indices/distances:", [(int(i), round(float(distances[i]), 4)) for i in ranking[:3]]
    )
    print("Distances describe this representation; they are not writer identity probabilities.")

    # Pixel values are supplied as arrays. Grid-row boundaries survive extraction.
    images = random_generator.uniform(size=(12, 16, 32, 3))
    image_pipeline = Pipeline(
        [
            ("patches", ImagePatchFeatures(grid_shape=(4, 8))),
            ("windows", GreyWindowFeatures(8, stride=8, boundary_channel=-1)),
            ("reducer", GreyPCA(n_components=3, standardize=True)),
        ]
    )
    image_pipeline.fit(images[:9])
    print("Held-out RGB images -> components:", image_pipeline.transform(images[9:]).shape)

    # Aligned one-dimensional spectra need no image or trajectory adapter.
    energy = np.linspace(0.5, 10, 64)
    profile = np.exp(-(((energy - 3) / 0.4) ** 2)) + 0.2 * np.exp(-(((energy - 7) / 0.8) ** 2))
    spectra = random_generator.poisson(30 + amplitudes[:, None] * 200 * profile)
    spectral_pipeline = Pipeline(
        [
            ("windows", GreyWindowFeatures(8, stride=4)),
            ("reducer", GreyPCA(n_components=4, top_k=2, standardize=True)),
            ("model", Ridge(alpha=1)),
        ]
    )
    spectral_pipeline.fit(spectra[:28], amplitudes[:28])
    error = mean_absolute_error(amplitudes[28:], spectral_pipeline.predict(spectra[28:]))
    print("Synthetic spectral target MAE:", round(error, 4))

    print("Synthetic demonstrations do not establish forensic or conservation accuracy.")


if __name__ == "__main__":
    main()
