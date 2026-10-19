# GreyTheory

**English** | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

GreyTheory is a Python library for grey-system forecasting, relational analysis,
and spectral data analysis. It includes GM(0,N), GM(1,N), GM(1,1), GRA, PCA-based
methods, and readers for Bruker SPX and selected BCF files.

## Run the example

Requires Python 3.11 or later.

From the project directory, run:

```bash
python3 run.py
```

The first run creates the local environment, installs the dependencies, and runs
the example. Use the same command next time; there is no activation step.
Setup runs again if the package configuration changes or dependencies are missing.

## Install as a library

```bash
pip install greytheory
```

This installs the latest PyPI release. The 2.0 API described here is still under
development; to use it from this checkout, run `python -m pip install .`.
Scientific dependencies are installed together. Larger modules load when used.

## Forecast a time series

```python
from greytheory import GM11

model = GM11(background_mode="corrected").fit([223.3, 227.3, 230.5, 238.1, 242.9, 251.1])
print(model.predict(2))
```

`fit` computes immediately; `set_data` stores data for a later batch run. Both
return the model. Constructor options include `alpha`, `background_mode`,
`ridge_alpha`, and `rank_policy`.

For the two-level sliding-window forecast, use
`GM11(window_size=4, stride=1).fit(series).predict(2)`. It fits local GM(1,1)
models, then fits a second GM(1,1) model to their predictions. `predict` returns
future values without changing the fitted model or its stored horizon.

### Background weights and solver

`background_mode="corrected"` uses `alpha * current + (1-alpha) * previous`.
The default, `"legacy"`, retains the original `alpha * current + alpha * previous`
formula. At `alpha=0.5` they agree. For AGO values `[2, 5, 10]` and `alpha=0.8`,
corrected backgrounds are `[4.4, 9.0]`; legacy backgrounds are `[5.6, 12.0]`.

The models use least squares with rank and condition diagnostics. Set
`ridge_alpha` to add regularization, or `rank_policy="raise"` to reject
unidentifiable fits. Results are available through `coefficients`,
`diagnostics`, and, for GM(1,1), `metrics`.
These results become available after fitting or completing a batch run.

GM(1,1) needs at least three observations. `horizon=0` fits history without adding
future predictions. Relative error is `None` when the actual observation is zero;
MAE and RMSE remain available. `reset()` clears results; `reset(clear_data=True)`
also clears observations.

## Compare factors with GM(0,N) and GM(1,N)

```python
from greytheory import GM0N

# Rows are observations; columns are factors.
X = [[.75, .5], [1.22, 1], [.2, .7], [1, .66], [1, 1], [1, .5]]
y = [1, 1, 1, 1, 1, 1]
model = GM0N().fit(X, y, feature_names=["factor_a", "factor_b"])
print(model.coefficients)
print(model.influence_degrees)
```

`X` has shape `(observations, factors)` and `y` has shape `(observations,)`.
Names are optional and default to `x0`, `x1`, etc. Use `GM1N().fit(X, y)` for
GM(1,N). Its development and driving coefficients are exposed separately as
`development_coefficient` and `driving_coefficients`.

`influence_degrees` preserves the original ranking by absolute coefficient.
The ranking depends on variable scales and collinearity. GRA provides a separate
comparison against a reference sequence.

## Grey relational analysis

```python
from greytheory.analysis import grey_relation

scores = grey_relation(
    reference=[0.2, 0.5, 0.8],
    candidates=[[0.2, 0.5, 0.8], [0.8, 0.1, 0.2]],
    rho=0.5,
    normalize="none",
)
print(scores)
```

For absolute differences `Δ`, the point coefficient is
`(Δmin + rho*Δmax) / (Δ + rho*Δmax)`. Scores are weighted means of those
coefficients. `rho` is in `(0, 1]`; position weights must be nonnegative.

`normalize` accepts `none`, `minmax`, `zscore`, `initial`, and `mean` and acts
on each sequence. Extrema are calculated over the current candidate batch, so
changing candidates can change scores and ranks. A score of 1 does not, by itself,
prove that the original values are identical. `GreyGRA().score(...)` and
`GreyGRA().rank(...)` are also available from `greytheory.analysis`.

## Feature selection and PCA

Choose the tool according to what you want to rank:

| Comparison | Tool |
| --- | --- |
| Numerical sequences against a reference | `grey_relation` or `GreyGRA` |
| Original features against a known target | `GreyFeatureSelector` |
| Components that summarize many features, scored against a target | `GreyPCA` |

The example uses synthetic data: one sample per row, one original feature per column,
and one known numerical target per sample.

```python
import numpy as np
from sklearn.decomposition import IncrementalPCA
from sklearn.model_selection import train_test_split
from greytheory.analysis import GreyFeatureSelector, GreyPCA

random_generator = np.random.default_rng(7)
factor_values = random_generator.normal(size=(48, 6))
target_values = factor_values[:, 0] + 0.05 * random_generator.normal(size=48)
train_factors, test_factors, train_targets, _ = train_test_split(
    factor_values, target_values, random_state=7
)

selector = GreyFeatureSelector(k=2).fit(train_factors, train_targets)
selected_factors = selector.transform(test_factors)

analysis = GreyPCA(
    n_components=4,
    method="sparse",
    method_params={"alpha": 0.1},
    top_k=2,
    standardize=True,
).fit(train_factors, train_targets)
reduced_factors = analysis.transform(test_factors)
print(analysis.selected_components)
print(analysis.component_scores)

custom_analysis = GreyPCA(
    estimator=IncrementalPCA(n_components=4, batch_size=12),
    top_k=2,
).fit(train_factors, train_targets)
custom_reduced_factors = custom_analysis.transform(test_factors)
```

Fit scaling, selection, and decomposition on training data only. The selector
expects a continuous target. `GreyPCA(...).fit(train_factors)` runs decomposition
without GRA; passing `train_targets` adds supervised GRA scoring. `top_k` keeps
that many scorable components; `None` keeps all nonconstant components. By default both signs are compared in one GRA batch.

| `GreyPCA(method=...)` | Decomposition | Example `method_params` |
| --- | --- | --- |
| `"pca"` (default) | PCA | `{"whiten": True}` |
| `"sparse"` | SparsePCA | `{"alpha": 0.1, "max_iter": 1000}` |
| `"kernel"` | KernelPCA | `{"kernel": "rbf", "gamma": 0.1}` |
| `"robust"` | PCP on training data, then PCA projection | `{"tol": 1e-6}` |
| `"robust_sparse"` | Huber/elastic-net RobustSparsePCA | `{"alpha": 0.1, "kappa": 1.0}` |
| `"adv"` | AdvPCA | `{"delta": 0.05}` |

Set `n_components` on `GreyPCA` and backend options in `method_params`.
Alternatively, pass an `estimator` with `fit`/`transform` and sklearn-compatible
cloning. It must produce a dense matrix with one row per input observation.
The estimator controls its own component count and is cloned before fitting;
choose either `estimator` or `method`/`method_params`. Custom nonnegative-count
models such as `PoissonPCA` should use `standardize=False`, the default.

`analysis.reducer` exposes the fitted backend. `component_scores` contains GRA
scores for all components, and `selected_components` contains zero-based indices
in output order. Selected columns retain their original component order.
`inverse_transform` fills omitted components with zeros before reconstruction;
KernelPCA reconstruction is approximate, and some custom models provide no inverse.
`explained_variance_ratio` is available only when the backend supplies it.

The `"robust"` path learns a PCA projection from PCP's low-rank training matrix.
Both training and new observations are projected with that fitted PCA; new
observations are not automatically PCP-cleaned. `RobustPCA` remains available
for direct low-rank/sparse matrix decomposition. `PCAAdapter`, `RobustSparsePCA`,
and `AdvPCA` can also be used independently. RobustSparsePCA and AdvPCA
solve nonconvex problems; inspect convergence diagnostics at iteration limits.
AdvPCA's sparse-encoding objective differs from PCP's additive outlier model.

Runnable comparison: [choose or supply a decomposition](examples/grey_pca_methods.py).

### Inspect rankings from highest to lowest score

Using the training data and fitted `analysis` above, rank original features and components separately:

```python
from greytheory.analysis import grey_relation

feature_names = [f"factor_{index + 1}" for index in range(train_factors.shape[1])]
feature_scores = grey_relation(train_targets, train_factors.T, normalize="zscore")
feature_ranking = np.argsort(-feature_scores, kind="stable")
for rank, index in enumerate(feature_ranking, start=1):
    print(rank, feature_names[index], float(feature_scores[index]))

valid_components = np.flatnonzero(np.isfinite(analysis.component_scores))
component_ranking = valid_components[np.argsort(-analysis.component_scores[valid_components], kind="stable")]
for rank, index in enumerate(component_ranking, start=1):
    print(rank, f"component_{index + 1}", float(analysis.component_scores[index]))
```

The first ranking refers to original columns; the second refers to learned components,
each of which may combine several columns. Scores describe grey relation to the chosen
target, not causal importance, prediction accuracy, or writer identity probabilities.
Without a target, `analysis.component_scores` is `None` and component ranking is unavailable.
Use held-out data to check whether GRA selection helps prediction.

Automatic overpainting detection and handwriting authorship comparison are not implemented.
Generic trajectory/image-patch features are available below; handwriting still needs text-region selection
and a dedicated comparison pipeline. Writer IDs should
not be treated as continuous targets. These applications require relevant data and expert validation.

## PCA entry points and quality directions

### Choose a decomposition

These constructors use the training/test matrices above. Choose a dictionary key;
all six backends expose the same `fit`/`transform` workflow.
For AdvPCA inspect both `analysis.reducer.converged` (outer loop) and
`analysis.reducer.inner_converged` (final regressions); an iteration limit is not convergence.

```python
from greytheory.analysis import GreyPCA

models = {
    "pca": GreyPCA(3, method="pca", standardize=True),
    "sparse": GreyPCA(3, method="sparse", method_params={"alpha": 0.1}, standardize=True),
    "kernel": GreyPCA(3, method="kernel", method_params={"gamma": 0.1}, standardize=True),
    "robust": GreyPCA(3, method="robust", standardize=True),
    "robust_sparse": GreyPCA(3, method="robust_sparse", method_params={"alpha": 0.1}, standardize=True),
    "adv": GreyPCA(3, method="adv", method_params={"delta": 0.05, "max_iter": 1000}, standardize=True),
}
analysis = models["adv"].fit(train_factors, train_targets)
components = analysis.transform(test_factors)
```
Custom models use `GreyPCA(estimator=IncrementalPCA(3), top_k=2)` and own their component count.
Standalone imports are `PCAAdapter`, `RobustPCA`, `RobustSparsePCA`, and `AdvPCA`.
Use `PCAAdapter(3, method="pca")`, `method="sparse"`, or `method="kernel"`;
`RobustPCA().fit(data)` exposes low-rank/sparse matrices, while `RobustSparsePCA(3).fit(data)`
and `AdvPCA(3, delta=0.05).fit(data)` provide standalone projections. These entry points do not add GRA or unit scaling.

Related spectral methods are imported from `greytheory.spectroscopy`:

| Entry point | Call and required input |
| --- | --- |
| `PoissonPCA` | `PoissonPCA(3).fit_transform(counts)`; nonnegative counts, approximate variance stabilization |
| `fit_mlpca` | `fit_mlpca(data, variances, n_components=3)`; positive error variance for every entry |
| `fit_mnf` | `fit_mnf(cube, n_components=3)`; spatial cube, noise estimated from neighboring pixels |

`GreyPCA(estimator=PoissonPCA(3), standardize=False)` also supports the count transformer; do not z-score its input into negative values.

### Normalize quality preferences

Warpage may be smaller-is-better while shear force is larger-is-better. Define those
preferences on the original responses. Values and limits below are illustrative.

```python
from greytheory.analysis import rank_quality

# Columns: warpage, shear force. Illustrative values and normalization limits.
quality = rank_quality(
    [[80, 10], [40, 20], [20, 25]],
    directions=["smaller", "larger"],
    bounds=[(0, 100), (0, 30)],
    weights=[0.5, 0.5],
)
print(quality.normalized_values)
print(quality.scores)
print(quality.ranking)  # [2, 1, 0]; zero-based row indices, best first
```
Supply fixed per-column `(lower, upper)` normalization bounds when justified.
Without bounds, only fitted-row extrema are used; these are outlier-sensitive and grades fitted
with different bounds cannot be compared across lots. Reuse `quality.normalizer.transform(new_quality)`
and `grade_quality(benefits, weights=quality.weights, rho=quality.rho)` for new rows.

`grade_quality` compares benefit rows with all ones using fixed difference extrema 0 and 1:
coefficients are `rho / (1 - benefit + rho)`, followed by a weighted mean.
Unlike the candidate-dependent extrema in `grey_relation`, fixed bounds and weights keep a row's
grade unchanged when other candidates are added. Grades are not yield, probabilities, or acceptance decisions.
A weighted mean permits compensation between responses; enforce mandatory specifications separately.

`BenefitNormalizer(directions, bounds=..., targets=...)` also supports `fit_transform` and `transform`.
Directions are `"larger"`, `"smaller"`, or `"target"`. For a nominal thickness, for example, use
`directions=["smaller", "larger", "target"]`, `targets=[None, None, 100]`, and three bound pairs.
A target uses a piecewise linear benefit peak strictly inside its bounds. This is not NIST's geometric-mean desirability grade.

Validation rejects nonfinite inputs, mismatched directions/weights/columns, constant columns without
usable bounds, and out-of-range values. Explicit `out_of_range="clip"` saturates values;
`normalizer.out_of_bounds(data)` still reports the original violations. Named columns must retain their order.
This is preference normalization; AdvPCA's perturbation radius remains a separate `delta` setting.

### Handle component signs against a reference

**Larger-is-better input columns do not make PC1 a larger-is-better quality index.**
Components can mix positive/negative loadings and have arbitrary signs.
`GreyPCA` now defaults to `component_direction="either"`, comparing both signs in one shared GRA
batch and keeping the higher grade. Constant components are excluded with NaN scores;
`top_k=None` keeps all scorable components. Original-feature `GreyFeatureSelector` keeps its signed
default; opt into `direction="either"` where either association is useful.

With a meaningful quality reference, optionally align output signs during training:

```python
analysis = GreyPCA(
    4, method="adv", method_params={"delta": 0.05, "max_iter": 1000},
    standardize=True, top_k=2,
    component_direction="either", align_to_target=True,
).fit(training_process_features, training_quality_scores)
components = analysis.transform(new_process_features)
print(analysis.component_scores)
print(analysis.component_directions)
print(analysis.component_direction_ambiguous)
```
Process/sensor features and measured quality responses serve different roles. If warpage/shear
form the target, do not also feed them into a predictor of that target. With only a quality table,
`rank_quality` is sufficient; PCA is not needed to calculate its grade.
Alignment is frozen at fit, reversed for inverse transforms, and rejects tied sign grades.
The default `align_to_target=False` preserves backend signs. Set `component_direction="positive"`
for the earlier signed comparison. Reference alignment is not physical monotonicity, causation,
or stability across lots; it also does not solve component swaps or rotations.

### Choose how many components to retain

80–85% is a possible starting threshold for ordinary PCA, not a guarantee of retaining that
fraction of process physics or quality information. Low-variance axes can still matter for quality.

```python
# Conventional PCA: choose the number of components using training variance.
ordinary = GreyPCA(n_components=0.85, method="pca", standardize=True).fit(train_factors)
print(ordinary.n_components_fitted)
print(ordinary.explained_variance_ratio.sum())

# AdvPCA: inspect actual reconstruction, without claiming additive variance.
adv = GreyPCA(4, method="adv", method_params={"delta": 0.05}, standardize=True).fit(train_factors)
report = adv.reconstruction_report(train_factors, threshold=0.85)
print(report.prefix_coverage)
print(report.first_prefix_at_threshold)  # None if no evaluated prefix reaches it
print(report.selected_coverage)         # Coverage after optional GRA selection
```
Fractional `n_components` is supported only for ordinary `method="pca"`.
AdvPCA/SparsePCA do not report a fabricated ordinary-PCA cumulative variance ratio.
Reconstruction coverage is `1 - SSE / SST` in the fitted input space (standardized when requested).
It can be negative or nonmonotone for other decompositions, and is not explained variance.
Prefixes zero later components of one fitted model; fitting a smaller model may give different results.
GRA selection can lower coverage below the original threshold; inspect `selected_coverage` separately.
The report never silently adds components to meet a threshold.

A runnable synthetic example separates responses from process features, splits by lot,
compares held-out Ridge predictions with a training-mean baseline, and reports coverage:

```bash
.venv/bin/python examples/semiconductor_adv_quality.py
```

Choose bounds, directions, and weights from engineering knowledge. Fit transformations and tune
`delta`, component counts, and `top_k` on training-side validation only. Compare ordinary PCA and
AdvPCA on unseen lots/wafers/time periods before drawing process conclusions.

## Multidimensional trajectories and Grey window features

**Numerical input → trajectory/image-patch features → Grey window features → PCA/GRA → regression or reference distances.**

| Input | Shape | Entry point |
| --- | --- | --- |
| Spectra or scalar sequences | `(samples, points)`; align spectral energy axes first | `GreyWindowFeatures` |
| 2D, 3D, or higher-dimensional paths | List of `(points, dimensions)` arrays; lengths may differ | `TrajectoryFeatures` → `GreyWindowFeatures` |
| Grayscale/multichannel image arrays | `(samples, height, width)` or `(samples, height, width, channels)` | `ImagePatchFeatures` → `GreyWindowFeatures` |

This example contains two recorded strokes with timestamps. Each row is one ordered spatial point.

```python
from greytheory.features import Trajectory, TrajectoryFeatures, GreyWindowFeatures

path = Trajectory(
    points=[[0, 0], [1, 1], [2, 1], [10, 10], [11, 10], [12, 11]],
    timestamps=[0, 0.5, 1, 3, 3.5, 4],
    stroke_ids=[0, 0, 0, 1, 1, 1],
)
extractor = TrajectoryFeatures(n_points=16, include_time=True)
sequences = extractor.fit_transform([path])  # Wrap even a single path in a list.
windows = GreyWindowFeatures(window_size=8, stride=4, boundary_channel=-1)
features = windows.fit_transform(sequences)
print(features.shape)
print(windows.get_feature_names_out())

paths_3d = [[[0, 0, 0], [1, 2, 1], [2, 2, 3]]]
sequences_3d = TrajectoryFeatures(n_points=16).fit_transform(paths_3d)
paths_5d = [[[0, 0, 0, 0, 0], [1, 2, 1, 3, 2], [2, 2, 3, 4, 5]]]
sequences_5d = TrajectoryFeatures(n_points=16).fit_transform(paths_5d)
```

Trajectory channels retain positions, step directions, step distance, turn angle, and stroke starts.
Default resampling is by arc length within each stroke. `include_time=True` resamples by time
and adds speed; strictly increasing timestamps are required for every sample. Changes between
consecutive integer `stroke_ids` start new strokes. Each stroke needs at least two recorded points
and two output points. Pen-up gaps contribute neither travel distance nor speed.
`center=True` removes the starting position; `scale=False` preserves spatial scale by default.
Speed uses coordinate units per timestamp unit, and turn angles are in radians.
With `scale=True`, distances and speeds use normalized spatial units. Coordinate columns are spatial
dimensions: do not append timestamps or pressure as coordinates. Dedicated pressure-channel handling
is not implemented, and actual timing/pressure cannot be recovered from a static image.

For each modeled channel/window, `GreyWindowFeatures` emits amplitude, mean, std, mean within-segment
change, GM coefficients, discrete-equation RMSE, full-rank coverage, and GM coverage; each window
also has a segment count. It uses the existing AGO/solver core without future extrapolation or
second-level forecasting. By default each window/channel is scaled by its maximum absolute value,
with the original amplitude retained. `gm_equation_rmse` is not a forecast error.
`gm_coverage` is the fraction of points in fragments with at least three points; shorter fragments
contribute zero coefficients and zero coverage. `gm_full_rank_coverage` counts points in full-rank
fragments. Do not interpret coefficients alone when coverage or full-rank coverage is low.
Use `boundary_channel=-1` for the adapters above: the final channel marks boundaries and is not
modeled. Fits and differences never bridge boundaries. Stride cannot exceed window size; a final
full-width window covers the tail, potentially adding overlap.

`ImagePatchFeatures(grid_shape=(4, 8))` retains each channel's mean/std and mean absolute horizontal/
vertical pixel differences per grid cell. It accepts arrays, without OCR, character segmentation,
or pigment identification. Its final channel marks grid-row starts. Use `boundary_channel=-1`
downstream to avoid modeling artificial row-wrap transitions. Inspect `patch_bounds`, `windows`,
and feature names to trace descriptors. Extractors fit input schemas only; PCA/GRA/regression must
still be fitted on training data only.

With training paths, one known continuous target per path, and independent test paths:

```python
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from greytheory.analysis import GreyPCA
from greytheory.features import TrajectoryFeatures, GreyWindowFeatures

model = Pipeline([
    ("trajectory", TrajectoryFeatures(n_points=32, include_time=True)),
    ("windows", GreyWindowFeatures(8, stride=4, boundary_channel=-1)),
    ("reducer", GreyPCA(n_components=4, top_k=2, standardize=True)),
    ("model", Ridge(alpha=1)),
])
model.fit(train_paths, train_targets)
predictions = model.predict(test_paths)
```

`train_paths` and `test_paths` are lists of `Trajectory` objects as above; `train_targets` contains
one measured numerical target per training path. Without a continuous target, use
`GreyPCA(n_components=4, standardize=True)` without `top_k`, then compare reference distances.
Generic regression/reference ranking does not establish authorship or overpainting; dedicated data,
models, and validation remain necessary. Component GRA compares both signs by default; still compare against an
unselected baseline.

Run the complete [synthetic example](examples/grey_feature_pipeline.py) for 2D/3D/5D paths, pen-up
boundaries, images, spectra, regression, and reference ranking:

```bash
.venv/bin/python examples/grey_feature_pipeline.py
```

Run `python3 run.py` first to set up the environment if needed. All inputs are generated locally.
Synthetic prediction errors do not establish forensic or chemical accuracy.

## Bruker file readers

```python
from greytheory.io.bruker import read_bcf, read_spx

spectrum = read_spx("reference.spx")
image = read_bcf("scan.bcf", lazy=True)
counts = image.get_pixel(y=0, x=0, detector=0)
energy_keV = image.energy_axes[0]
roi = image.get_spectra((0, 0, 2, 2), detector=0)
```

SPX exposes counts, metadata, and a calibrated energy axis when present.
BCF support is limited to uncompressed SFS streams with indexed, instructively
packed pixels. Other packed encodings, outer compression, and BCF v2 are not supported.
Counts use `uint64`; ROI bounds are `(y0, x0, y1, x1)`, excluding the upper bounds.
Each detector retains its own energy calibration; `sum_detectors` rejects mismatched axes.

Reader tests generate small SPX/BCF files in temporary directories and require no
external instrument dataset.
Generated fixtures check the implemented layout; they do not establish compatibility
with every instrument/software version. Check your own files before using the reader.

## Process and spectroscopy tools

| Module | Available tools |
| --- | --- |
| `greytheory.semiconductor` | PLS quality regression, dynamic/multiway PCA monitoring, GRA feature ranking, Latin-hypercube sampling, GP expected-improvement proposals |
| `greytheory.spectroscopy` | AsLS baseline correction, NMF, MCR-ALS, MNF, Anscombe-based Poisson PCA, fixed-variance weighted low-rank fitting, X-ray line lookup, fixed-center peak fitting |

Poisson PCA uses an approximate variance-stabilizing transform. `fit_mlpca` assumes
independent errors with supplied, positive variances. XRF line amplitudes require
further instrument and matrix calibration before being interpreted as concentrations.

Runnable examples: [time-series models](example.py),
[synthetic spectra](examples/hyperspectral_gra_pca.py),
[held-out manufacturing lots](examples/semiconductor_quality.py).

## Batch execution

```python
from greytheory import GM0N, GM11, ModelQueue

if __name__ == "__main__":
    queue = ModelQueue()
    model = GM11(background_mode="corrected")
    for series in ([2, 3, 4, 5, 6], [3, 4, 6, 8, 11]):
        model.set_data(series)
        queue.append(model)  # Saves a deep copy at this point.

    queue.append(GM0N().set_data([[1], [2], [3], [4]], [2, 4, 7, 8]))
    results = queue.run(workers=2)
    print([m.predict(2) for m in results[:2]])
    print(results[2].influence_degrees)
```

`ModelQueue` deep-copies models on construction, `append`, `extend`, `insert`,
and item or slice assignment. You can reuse one model for several datasets;
each entry keeps the data and settings present when it was added. Reading an
entry returns its stored model, which you can edit. A plain Python list retains
its normal reference behavior.

`queue.run()` chooses the computation for each model, so GM(0,N), GM(1,N), and
GM(1,1) can share a batch. It is sequential by default; set `workers` to use
processes. Results retain input order and update the queued models only after
all jobs succeed. `inplace=False` returns fitted copies and leaves the queue
unchanged. `run_models(models, workers=2)` offers the same execution for an
existing iterable. Keep the main guard for process execution on Windows and macOS.

## Development

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

Tests cover the original examples, numerical edge cases, decomposition objectives,
multidimensional features, and readers. All test inputs are generated locally or
included as numerical fixtures; no external download is needed.
`scripts/verify_full_install.py` exercises the APIs from an installed wheel.

Synthetic benchmark records are in [benchmarks/results](benchmarks/results/).
The [core benchmark](benchmarks/compare_core.py) generates its input from a fixed
seed; its optional `--baseline` takes a separate original checkout for comparison.
The [decomposition benchmark](benchmarks/compare_decomposition.py) generates clean
and contaminated data, then compares held-out reconstruction on the same split.
The recorded timings are from macOS arm64 and depend on the machine and runtime;
the scores describe these synthetic cases.

The older `GreyTheory` facade, `GreyGM*` names, `add_pattern`/`add_patterns`,
and `grey.run.gm*` entry points remain available. New code can import `GM0N`,
`GM1N`, `GM11`, `ModelQueue`, and `run_models` directly.

## License

GreyTheory is released under the [MIT License](LICENSE).
Runtime dependencies are installed separately and retain their own licenses;
see [Third-party notices](THIRD_PARTY_NOTICES.md).

## References

The references below distinguish the implemented methods, upstream implementations,
and related research. SCRAMBLE is included as background rather than a supplied estimator.

1. Deng, J. L. (1982). [Control problems of grey systems](https://doi.org/10.1016/S0167-6911(82)80025-X). *Systems & Control Letters*, 1(5), 288–294.
2. Liu, S. & Lin, Y. (2011). [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2). Springer. Grey modelling and relational analysis.
3. Kayacan, E., Ulutas, B. & Kaynak, O. (2010). [Grey system theory-based models in time series prediction](https://doi.org/10.1016/j.eswa.2009.07.064). *Expert Systems with Applications*, 37(2), 1784–1789.
4. NumPy. [Least-squares solver and rank diagnostics](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html); [accurate evaluation of exp(x) − 1](https://numpy.org/doc/stable/reference/generated/numpy.expm1.html).
5. Jolliffe, I. T. & Cadima, J. (2016). [Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202). *Philosophical Transactions A*, 374, 20150202.
6. scikit-learn. [PCA, SparsePCA and KernelPCA implementations](https://scikit-learn.org/stable/modules/decomposition.html); [training/test preprocessing](https://scikit-learn.org/stable/common_pitfalls.html); [custom estimator cloning](https://scikit-learn.org/stable/modules/generated/sklearn.base.clone.html).
7. Candès, E. J., Li, X., Ma, Y. & Wright, J. (2011). [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395). *Journal of the ACM*, 58(3), Article 11. Principal Component Pursuit.
8. Lin, Z., Chen, M. & Ma, Y. (2010). [The Augmented Lagrange Multiplier Method for Exact Recovery of Corrupted Low-Rank Matrices](https://arxiv.org/abs/1009.5055). Inexact ALM solver for PCP.
9. Erichson, N. B. et al. (2020). [Sparse Principal Component Analysis via Variable Projection](https://doi.org/10.1137/18M1211350), [author manuscript](https://arxiv.org/abs/1804.00341). *SIAM Journal on Applied Mathematics*, 80(2), 977–1002. Robust sparse model: equation (17), Algorithm 2.
10. Vävinggren, D. et al. (2026). [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553). AdvPCA: Algorithms 1–2 and Appendix A.3.
11. Pfeiffer, P., Vana-Gür, L. & Filzmoser, P. (2025). [Cellwise robust and sparse principal component analysis](https://doi.org/10.1007/s11634-025-00656-3). SCRAMBLE; related work, not the algorithm used by `RobustSparsePCA`.
12. Lee, D. D. & Seung, H. S. (1999). [Learning the parts of objects by non-negative matrix factorization](https://doi.org/10.1038/44565). *Nature*, 401, 788–791. NMF background; this package delegates fitting to scikit-learn.
13. Camp, C. H. Jr. (2019). [pyMCR: A Python Library for Multivariate Curve Resolution Analysis with Alternating Regression (MCR-AR)](https://doi.org/10.6028/jres.124.018). *Journal of Research of NIST*, 124, 124018.
14. Green, A. A., Berman, M., Switzer, P. & Craig, M. D. (1988). [A transformation for ordering multispectral data in terms of image quality with implications for noise removal](https://doi.org/10.1109/36.3001). *IEEE Transactions on Geoscience and Remote Sensing*, 26(1), 65–74. [Spectral Python MNF API](https://www.spectralpython.net/class_func_ref.html#spectral.mnf).
15. Anscombe, F. J. (1948). [The transformation of Poisson, binomial and negative-binomial data](https://doi.org/10.1093/biomet/35.3-4.246). *Biometrika*, 35(3–4), 246–254. Variance stabilization used by `PoissonPCA`.
16. Wentzell, P. D. et al. (1997). [Maximum likelihood principal component analysis](https://doi.org/10.1002/%28SICI%291099-128X%28199707%2911%3A4%3C339%3A%3AAID-CEM476%3E3.0.CO%3B2-L). *Journal of Chemometrics*, 11(4), 339–366. `fit_mlpca` implements the independent-error, fixed-variance case.
17. pybaselines. [Asymmetric least-squares baseline correction](https://pybaselines.readthedocs.io/en/latest/algorithms/whittaker.html#asymmetric-least-squares-asls). The `baseline_correct` implementation uses `Baseline.asls`.
18. Wold, S., Sjöström, M. & Eriksson, L. (2001). [PLS-regression: a basic tool of chemometrics](https://doi.org/10.1016/S0169-7439(01)00155-1). *Chemometrics and Intelligent Laboratory Systems*, 58(2), 109–130.
19. Rasmussen, C. E. & Williams, C. K. I. (2006). [Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/). MIT Press. [SciPy Latin-hypercube sampling](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html).
20. Jones, D. R., Schonlau, M. & Welch, W. J. (1998). [Efficient Global Optimization of Expensive Black-Box Functions](https://doi.org/10.1023/A:1008306431147). *Journal of Global Optimization*, 13, 455–492. Expected-improvement acquisition.
21. xraylib. [X-ray interaction data and documentation](https://github.com/tschoonj/xraylib/wiki). Used for characteristic line energies and relative rates.
22. RosettaSciIO community. [Bruker detector-calibration discussion, issue #516](https://github.com/hyperspy/rosettasciio/issues/516). File-format and per-detector energy calibration notes.
23. NIST/SEMATECH. [Multiple responses: the desirability approach](https://www.itl.nist.gov/div898/handbook/pri/section5/pri5322.htm). Engineering preference directions and targets; GreyTheory uses separately documented arithmetic GRA grades, not the geometric-mean desirability function.
