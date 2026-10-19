# GreyTheory

**English** | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

GreyTheory is a Python toolkit for grey forecasting, grey relational analysis (GRA), and PCA.
Use it to forecast sequences, reduce feature tables, or compare spectra and measurements.

| Task | Start here |
| --- | --- |
| Forecast the next few values | [GM(1,1)](#time-series-forecasting) |
| Forecast with two levels of windows | [Convolution](#convolution-forecasting) |
| Compare features with a target | [GRA](#grey-relational-analysis-gra) |
| Reduce dimensions, then select components | [GreyPCA](#pca-and-feature-selection) |
| Score mixed quality preferences | [Quality scoring](#quality-scoring) |
| Work with paths or images | [Feature extraction](#trajectory-image-and-window-features) |
| Read PNG/JPG files for comparison | [Image-file example](#start-with-image-files) |
| Read Bruker files | [SPX/BCF](#bruker-file-readers) |
| Run synthetic spectra and AI handwriting | [Both demos](#synthetic-xrf-and-ai-handwriting-demos) |

## Get started

Requires Python 3.11 or later. Download or clone the repository, then run from its directory:

```bash
python3 run.py
```

> [!TIP]
> The first run creates `.venv`, installs dependencies, and runs the example.
> Use the same command next time; no environment activation is needed.

To use GreyTheory in your own program, install it from the project directory
with that program's Python environment:

```bash
python -m pip install .
```

## Time-series forecasting

Pass observations to `fit`, then call `predict(2)` for the next two values:

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(background_mode="corrected").fit(series)
print(model.predict(2))
print(model.metrics)
```

Use at least three observations. See Convolution below for two-level window forecasting.

Read coefficients from `model.coefficients` and solver diagnostics from `model.diagnostics`.
`set_data` stores observations for a later batch run. `reset()` clears results;
`reset(clear_data=True)` also clears the data.

<details>
<summary>Background weights, regularization, and errors</summary>

`background_mode="corrected"` uses `alpha * current + (1-alpha) * previous`.
The default `"legacy"` mode multiplies both terms by `alpha`. They agree at `alpha=0.5`.

The solver uses least squares. Set `ridge_alpha` for regularization or
`rank_policy="raise"` to reject fits without uniquely identifiable coefficients.
Diagnostics include rank, condition number, and residuals.

`horizon=0` fits history only. Relative error is `None` for a zero observation;
MAE and RMSE remain available. `predict` leaves stored fit results unchanged.

</details>

## Convolution forecasting

Set `window_size` to enable convolution. Each window uses GM(1,1) to predict its next value;
a second GM(1,1) then fits those predictions:

**Sequence → window predictions → second-level GM(1,1) → future values**

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(window_size=4, stride=1, background_mode="corrected").fit(series)
print(model.predict(2))
```

| Setting | Meaning |
| --- | --- |
| `window_size=4` | Four observations per window; `None` uses ordinary GM11 |
| `stride=1` | Advance one observation at a time |
| `predict(2)` | Forecast two future values |
| `correction_mode="legacy"` | Keep the default window-error correction; `"none"` disables it |

For the full two-level method, provide enough data for at least three windows.
The six observations above, with width four and stride one, produce three windows.
`coefficients` and `metrics` describe the final fitted level. The last window can include extra tail observations, matching the original method.

Run the comparison to see both ordinary and convolution forecasts:

```bash
.venv/bin/python examples/convolution_forecast.py
```

Example output:

```text
Ordinary GM11, next two values: [256.5532, 263.1223]
Convolution GM11, next two values: [265.9278, 274.0119]
```

`GreyWindowFeatures` instead extracts local descriptors for PCA/GRA; it does not run the second forecast level.

## Multiple-factor models

`GM0N` and `GM1N` model several factors against one target.
Each row is an observation and each column is a factor:

```python
from greytheory import GM0N

factors = [[.75, .5], [1.22, 1], [.2, .7], [1, .66], [1, 1], [1, .5]]
targets = [1, 1, 1, 1, 1, 1]
model = GM0N().fit(factors, targets, feature_names=["factor_a", "factor_b"])
print(model.coefficients)
print(model.influence_degrees)
```

For GM(1,N), use `GM1N().fit(factors, targets)`. Feature names are optional.
`influence_degrees` ranks absolute coefficients, which depend on units and collinearity.
Use GRA below to compare sequences with a reference.

## Grey relational analysis (GRA)

Supply a reference sequence and candidate sequences. Higher scores mean closer matches
under the chosen normalization:

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

`normalize` accepts `none`, `minmax`, `zscore`, `initial`, or `mean`.
You can also import `GreyGRA` from `greytheory.analysis` and use `.score(...)` or `.rank(...)`.

Scores depend on the candidate batch, so adding or removing candidates can change the ranking.
They measure grey relation, not causal importance or prediction accuracy.

<details>
<summary>GRA formula</summary>

For each absolute difference `Δ`, the coefficient is
`(Δmin + rho*Δmax) / (Δ + rho*Δmax)`. The score is a weighted mean.
`rho` must be in `(0, 1]`; weights must be nonnegative.
Difference extrema come from the same candidate batch. A score of 1 need not mean identical raw values.

</details>

## PCA and feature selection

`GreyFeatureSelector` selects original columns. `GreyPCA` reduces dimensions, then uses
GRA to select components against a target. This example uses synthetic data:

```python
import numpy as np
from sklearn.model_selection import train_test_split
from greytheory.analysis import GreyFeatureSelector, GreyPCA

random_generator = np.random.default_rng(7)
factors = random_generator.normal(size=(48, 6))
targets = factors[:, 0] + 0.05 * random_generator.normal(size=48)
train_factors, test_factors, train_targets, _ = train_test_split(
    factors, targets, random_state=7
)

selector = GreyFeatureSelector(k=2).fit(train_factors, train_targets)
selected_factors = selector.transform(test_factors)

analysis = GreyPCA(
    n_components=4, method="sparse", method_params={"alpha": 0.1},
    top_k=2, standardize=True,
).fit(train_factors, train_targets)
components = analysis.transform(test_factors)
print(analysis.selected_components)
print(analysis.component_scores)
```

`n_components` sets the decomposition size; `top_k` sets how many components GRA keeps.
Omit the target in `fit(train_factors)` to run dimensionality reduction alone.
> [!IMPORTANT]
> **Split training and test data first.** Fit every transform on training data;
> use only `transform` on test data.

### Switch PCA methods

Change `method` and pass its settings in `method_params`:

| `method` | Decomposition | Example `method_params` |
| --- | --- | --- |
| `"pca"` (default) | PCA | `{"whiten": True}` |
| `"sparse"` | SparsePCA | `{"alpha": 0.1}` |
| `"kernel"` | KernelPCA | `{"kernel": "rbf", "gamma": 0.1}` |
| `"robust"` | PCA projection learned from a PCP low-rank matrix | `{"tol": 1e-6}` |
| `"robust_sparse"` | Huber/elastic-net RobustSparsePCA | `{"alpha": 0.1, "kappa": 1.0}` |
| `"adv"` | AdvPCA | `{"delta": 0.01, "max_iter": 1000}` |

For example, switch to AdvPCA:

```python
analysis = GreyPCA(
    3, method="adv", method_params={"delta": 0.01, "max_iter": 1000},
    top_k=2, standardize=True,
).fit(train_factors, train_targets)
components = analysis.transform(test_factors)
print(analysis.reducer.converged)
print(analysis.reducer.inner_converged)
```

Check both outer and final inner convergence before evaluating AdvPCA results.
See [grey_pca_methods.py](examples/grey_pca_methods.py) for a comparison of the methods.

You can also supply a sklearn-compatible model with its own component count:

```python
from sklearn.decomposition import IncrementalPCA

analysis = GreyPCA(
    estimator=IncrementalPCA(n_components=4, batch_size=12), top_k=2,
).fit(train_factors, train_targets)
```

Custom models need `fit`, `transform`, and sklearn clone support, and must return a dense
2D matrix with one row per observation. Use either `estimator` or `method`/`method_params`.

### Inspect selected components and rankings

`component_scores` contains GRA scores. `selected_components` contains zero-based indices;
output columns retain their original component order. To list scores from highest to lowest:

```python
valid = np.flatnonzero(np.isfinite(analysis.component_scores))
ranking = valid[np.argsort(-analysis.component_scores[valid], kind="stable")]
for index in ranking:
    print(f"PC{index + 1}", float(analysis.component_scores[index]))
```

Original-column scores are in `selector.scores`. Without a target, `component_scores` is `None`.
This selection works with continuous targets. Writer IDs and other categorical labels need
a separate classification or comparison model.

### Choose the component count

For ordinary PCA, you can specify the cumulative variance to retain, such as 85%:

```python
ordinary = GreyPCA(n_components=0.85, method="pca", standardize=True).fit(train_factors)
print(ordinary.n_components_fitted)
print(ordinary.explained_variance_ratio.sum())

report = analysis.reconstruction_report(train_factors, threshold=0.85)
print(report.prefix_coverage)
print(report.first_prefix_at_threshold)
print(report.selected_coverage)
```

Fractional `n_components` is supported only for ordinary PCA. For AdvPCA or SparsePCA,
inspect reconstruction coverage instead. An 80–85% threshold is a starting point;
use held-out data to check prediction performance, since low-variance components can still carry quality signals.

<details>
<summary>Standalone decompositions and spectral PCA</summary>

Import these from `greytheory.analysis` to use them without GRA:

| Call | Purpose |
| --- | --- |
| `PCAAdapter(3, method="pca")` | PCA |
| `PCAAdapter(3, method="sparse", alpha=0.1)` | SparsePCA |
| `PCAAdapter(3, method="kernel", gamma=0.1)` | KernelPCA |
| `RobustPCA().fit(data)` | Exposes `low_rank` and `sparse` matrices |
| `RobustSparsePCA(3).fit(data)` | Huber/elastic-net sparse projection |
| `AdvPCA(3, delta=0.05).fit(data)` | AdvPCA projection |

Import spectral methods from `greytheory.spectroscopy`:

| Call | Required input |
| --- | --- |
| `PoissonPCA(3).fit_transform(counts)` | Nonnegative counts; approximate variance stabilization |
| `fit_mlpca(data, variances, n_components=3)` | Independent errors with positive variance for each entry |
| `fit_mnf(cube, n_components=3)` | Spatial cube; noise estimated from neighboring pixels |

Use `GreyPCA(estimator=PoissonPCA(3), standardize=False)` to combine PoissonPCA with GRA.
Keep counts nonnegative; do not apply standardization that produces negative values.

</details>

<details>
<summary>Component signs, reconstruction, and method differences</summary>

PCA component signs can flip. By default, `component_direction="either"` compares both signs
in one GRA batch and keeps the higher score. Constant components get NaN scores and are excluded;
`top_k=None` keeps all scorable components. `GreyFeatureSelector` compares the original direction
by default; set `direction="either"` to compare both.

With a quality target, add `align_to_target=True` to orient output signs toward the reference.
Signs are fixed during training; tied scores raise an error.
Inspect `component_directions` and `component_direction_ambiguous` for the decisions.
This handles sign choices, not physical monotonicity or component swaps/rotations across refits.
Set `component_direction="positive"` for signed GRA comparison.

`inverse_transform` fills omitted components with zeros. KernelPCA reconstruction is approximate;
some custom models have no inverse. `reconstruction_report` measures `1 - SSE / SST` for the
specified components without changing their count. With `standardize=True`, it uses standardized space.
For other decompositions, coverage can be negative or nonmonotone.
`first_prefix_at_threshold=None` means no evaluated prefix reached the threshold;
check `selected_coverage` separately after GRA selection.
Prefixes zero later components of one fitted model; refitting fewer components may give different results.

`"robust"` learns its projection from PCP's low-rank training matrix. New rows use that projection
without another PCP cleanup. AdvPCA's sparse-encoding objective differs from PCP's low-rank/additive-outlier split.
RobustSparsePCA and AdvPCA involve nonconvex optimization; check convergence diagnostics.

</details>

## Quality scoring

For example, lower warpage and higher shear force can both be desirable.
Convert them to 0–1 benefit values, then compute a weighted GRA grade:

```python
from greytheory.analysis import rank_quality, grade_quality

quality = rank_quality(
    [[80, 10], [40, 20], [20, 25]],  # Rows: samples. Columns: warpage, shear force.
    directions=["smaller", "larger"],
    bounds=[(0, 100), (0, 30)],      # Example bounds; replace with process-specific values.
    weights=[0.5, 0.5],
)
print(quality.normalized_values)
print(quality.scores)
print(quality.ranking)  # [2, 1, 0]: row indices, best first

new_benefits = quality.normalizer.transform([[30, 22]])
new_quality = grade_quality(new_benefits, weights=quality.weights, rho=quality.rho)
print(new_quality.scores)
```

`directions` accepts `larger`, `smaller`, or `target`.
For thickness near 100, use `BenefitNormalizer(["target"], bounds=[(80, 120)], targets=[100])`
with `fit_transform` or `transform`. Import it from `greytheory.analysis`.

`bounds` sets the normalization range. If omitted, it uses training minima and maxima.

> [!NOTE]
> **Reuse the same ranges, weights, and `rho` across lots.**
> This keeps a row's quality grade unchanged when other samples are added.

Out-of-range values raise by default; `out_of_range="clip"` clips them to the bounds.
Use `normalizer.out_of_bounds(data)` to locate the original violations.

> [!WARNING]
> **A quality grade is not yield or a pass/fail decision.**
> It reflects the chosen preferences. Check mandatory specifications separately.

Making original columns larger-is-better does not make
every PCA component larger-is-better; see the component-sign notes above.

See [semiconductor_adv_quality.py](examples/semiconductor_adv_quality.py) for process prediction.
It keeps process features separate from quality targets, splits by lot, and compares
AdvPCA/GRA + Ridge against a mean baseline. Do not feed warpage/shear values used to define
the target back into the predictor's inputs.

<details>
<summary>Scoring formula and input checks</summary>

**Calculation**

`grade_quality` computes a coefficient for each response, then takes a weighted mean:

```text
coefficient = rho / (1 - benefit + rho)
score       = weighted_mean(coefficients)
```

| Setting | Value |
| --- | --- |
| Ideal sequence | All ones |
| Minimum / maximum difference | Fixed at 0 / 1 |
| Aggregation | Weighted mean; responses can compensate for each other |

`grey_relation` instead takes difference extrema from the candidate batch.
NIST desirability uses a geometric mean, so its calculation also differs.

**Input checks**

| Check | Requirement |
| --- | --- |
| Values | No NaN or infinity |
| Columns | Matching count, directions, names, and order |
| Constant columns | Valid normalization bounds must be supplied |
| `target` | Strictly inside its bounds; uses a piecewise linear benefit peak |
| Weights | Nonnegative, with at least one positive weight |

Quality normalization is separate from AdvPCA's perturbation radius `delta`.

</details>

## Trajectory, image, and window features

Build a pipeline from numeric inputs:

**Data → trajectory/image features → Grey window features → PCA/GRA → regression or distance comparison**

| Input | Shape | Use |
| --- | --- | --- |
| Spectra or scalar sequences | `(samples, points)` | `GreyWindowFeatures`; align spectral energy axes first |
| 2D and higher-dimensional paths | List of `(points, dimensions)` arrays | `TrajectoryFeatures` → `GreyWindowFeatures` |
| Grayscale/multichannel images | `(samples, height, width[, channels])` | `ImagePatchFeatures` → `GreyWindowFeatures` |

Here is a 2D path with timestamps and stroke IDs. The same class handles 3D and 5D paths:

```python
from greytheory.features import Trajectory, TrajectoryFeatures, GreyWindowFeatures

path = Trajectory(
    points=[[0, 0], [1, 1], [2, 1], [10, 10], [11, 10], [12, 11]],
    timestamps=[0, 0.5, 1, 3, 3.5, 4],
    stroke_ids=[0, 0, 0, 1, 1, 1],
)
sequences = TrajectoryFeatures(n_points=16, include_time=True).fit_transform([path])
windows = GreyWindowFeatures(window_size=8, stride=4, boundary_channel=-1)
features = windows.fit_transform(sequences)
print(features.shape)

paths_3d = [[[0, 0, 0], [1, 2, 1], [2, 2, 3]]]
sequences_3d = TrajectoryFeatures(n_points=16).fit_transform(paths_3d)
paths_5d = [[[0, 0, 0, 0, 0], [1, 2, 1, 3, 2], [2, 2, 3, 4, 5]]]
sequences_5d = TrajectoryFeatures(n_points=16).fit_transform(paths_5d)
```

To read image files directly, see “Start with image files” below.

To add regression, use sklearn's Pipeline. Here, `train_paths` and `test_paths` are lists of
`Trajectory` objects; `train_targets` contains one continuous value per training path:

```python
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from greytheory.analysis import GreyPCA

model = Pipeline([
    ("trajectory", TrajectoryFeatures(n_points=32, include_time=True)),
    ("windows", GreyWindowFeatures(8, stride=4, boundary_channel=-1)),
    ("reducer", GreyPCA(4, top_k=2, standardize=True)),
    ("model", Ridge(alpha=1)),
])
model.fit(train_paths, train_targets)
predictions = model.predict(test_paths)
```

See [grey_feature_pipeline.py](examples/grey_feature_pipeline.py) for a runnable example.
These features can feed a model; handwriting authorship and overpainting detection still need
dedicated models and validation data.

### Start with image files

Install image support once:

```bash
.venv/bin/python -m pip install -e ".[images]"
```

Supply at least three reference images and a separate query image. Choose any directory;
this example uses:

```text
test_data/images/
├── reference/
│   ├── sample_a.png
│   ├── sample_b.jpg
│   └── sample_c.png
└── query.png
```

`load_images` accepts one path or a list of paths and returns an RGB batch in [0, 1].
Read PNG/JPG files and rank references by their distance from the query:

```python
from pathlib import Path
import numpy as np
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import Pipeline
from greytheory.io import load_images
from greytheory.features import ImagePatchFeatures, GreyWindowFeatures
from greytheory.analysis import GreyPCA

reference_paths = sorted(
    path for path in Path("test_data/images/reference").iterdir()
    if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
)
reference_images = load_images(reference_paths, size=(128, 128))
query_image = load_images("test_data/images/query.png", size=(128, 128))

pipeline = Pipeline([
    ("patches", ImagePatchFeatures(grid_shape=(4, 8))),
    ("windows", GreyWindowFeatures(8, stride=8, boundary_channel=-1)),
    ("pca", GreyPCA(2, standardize=True)),
])
reference_components = pipeline.fit_transform(reference_images)
query_components = pipeline.transform(query_image)
distances = pairwise_distances(query_components, reference_components)[0]
for index in np.argsort(distances, kind="stable"):
    print(reference_paths[index].name, float(distances[index]))
```

Distances are measured in PCA feature space; smaller means closer.
Fit on reference images only, then transform the query. These distances do not establish
authorship, authenticity, or overpainting.

`size=(128, 128)` is `(width, height)` and preserves aspect ratio with white padding.
Without it, all image dimensions must match. Loading applies EXIF orientation and composites
transparency over white; use `mode="L"` for grayscale.
Align crops and positions beforehand. Keep high-bit-depth scientific intensities as numeric arrays
rather than converting them through this display-image loader.

Or run the script directly. The first command generates demo PNGs; the second uses your files:

```bash
.venv/bin/python examples/image_files.py

.venv/bin/python examples/image_files.py \
  --references test_data/images/reference \
  --query test_data/images/query.png \
  --size 128 128
```

Results are written to `artifacts/image_files/` by default:

| File | Contents |
| --- | --- |
| `features.csv` | Grey window descriptors for each image |
| `components.csv` | PCA coordinates |
| `ranking.csv` | Reference distances and ranking |

Full example: [image_files.py](examples/image_files.py).

<details>
<summary>Path, window, and image input requirements</summary>

Paths are resampled by stroke arc length by default, keeping position, direction, distance,
turning angle, and stroke boundaries. `include_time=True` resamples by time and adds speed;
timestamps must increase strictly. Each stroke needs at least two input points, and
`n_points` must be at least twice the stroke count. Pen-up gaps are excluded from distance and speed.
`center=True` removes the start position; `scale=False` keeps spatial units. Speed uses coordinate/time units
and angles use radians. With `scale=True`, distances and speeds use normalized units.
Keep time and pressure out of spatial coordinates; dedicated pressure handling is not provided.

Grey windows extract amplitude, mean, standard deviation, within-segment changes, GM coefficients,
equation RMSE, and coverage. They do not forecast. Each window/channel is scaled by its maximum absolute value,
with original amplitude retained. Fragments shorter than three points get zero GM coefficients and `gm_coverage`;
check `gm_full_rank_coverage` too. Low coverage makes coefficients less informative.
`boundary_channel=-1` prevents fits across strokes or image-grid rows. Keep `stride` no larger than the window.

Images must be numeric arrays. Inspect positions with `patch_bounds` and `windows`, and names with
`get_feature_names_out()`. Image features do not include OCR or character segmentation;
static images cannot provide actual writing speed or pressure.

</details>

## Bruker file readers

```python
from greytheory.io.bruker import read_bcf, read_spx

spectrum = read_spx("reference.spx")
image = read_bcf("scan.bcf", lazy=True)
counts = image.get_pixel(y=0, x=0, detector=0)
energy_keV = image.energy_axes[0]
roi = image.get_spectra((0, 0, 2, 2), detector=0)
```

SPX exposes counts, metadata, and energy calibration when present. BCF keeps each detector's calibration.
ROI bounds are `(y0, x0, y1, x1)`, excluding the upper bounds; counts use `uint64`.

BCF support covers indexed, instructively packed pixels in uncompressed SFS streams.
Other encodings, outer compression, and BCF v2 are unsupported. `sum_detectors` rejects mismatched energy axes.
Check readings against the instrument software for your files.

## Process and spectroscopy tools

| Module | Tools |
| --- | --- |
| `greytheory.semiconductor` | PLS quality regression, dynamic/multiway PCA monitoring, GRA ranking, Latin-hypercube sampling, GP expected-improvement proposals |
| `greytheory.spectroscopy` | AsLS baseline correction, NMF, MCR-ALS, MNF, Poisson PCA, weighted low-rank fitting, X-ray line lookup, fixed-center peak fitting |

Examples: [synthetic spectra](examples/hyperspectral_gra_pca.py),
[held-out manufacturing lots](examples/semiconductor_quality.py),
[AdvPCA quality prediction](examples/semiconductor_adv_quality.py).
Converting XRF peak amplitudes to concentrations requires instrument, standard-sample, and matrix calibration.

## Batch execution

Reuse a model with different data. `ModelQueue` saves a deep copy when each entry is added:

```python
from greytheory import GM11, ModelQueue

if __name__ == "__main__":
    queue = ModelQueue()
    model = GM11(background_mode="corrected")
    for series in ([2, 3, 4, 5, 6], [3, 4, 6, 8, 11]):
        queue.append(model.set_data(series))
    results = queue.run(workers=2)
    print([item.predict(2) for item in results])
```

`queue.run()` is sequential by default. Set `workers=2` for two processes; results keep input order.
You can mix GM0N, GM1N, and GM11. For an existing model list, use `run_models(models, workers=2)`.
Keep the `if __name__ == "__main__":` guard when using processes.

<details>
<summary>Queue copying and updates</summary>

Construction, insertion, and replacement deep-copy models. Reading `queue[0]` returns the stored model,
which can be edited. The queue updates only after all jobs succeed.
Use `inplace=False` to return fitted copies without changing the queue.

</details>

## Synthetic XRF and AI handwriting demos

The [synthetic inputs and results](examples/results/synthetic_demos/) are included.
Download the project and open `examples/results/synthetic_demos/index.html` in a browser; Python is not needed to view them.
GitHub does not render the HTML reports directly; use the images and CSV links below for an online preview.

To rerun both demos, run these commands in the project directory (macOS/Linux):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[demos]"
.venv/bin/python examples/synthetic_demos.py
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

| Demo | Input and analysis | Output |
| --- | --- | --- |
| Synthetic XRF | Four 6×6 maps, 144 spectra with 1024 channels; known Ca/Fe/Cu/Zn line-template weights, continuum, and Poisson noise | Spectra, energy-channel GRA ranking, and PCA/GreyPCA prediction on a held-out simulated map |
| AI handwriting styles | 18 cells of 春風明月 in three prompt-defined styles; 12 references and 6 queries | Patch/PCA versus Grey-window/PCA distances, coordinates, and numeric feature exports |

New results go to `artifacts/synthetic_demos/`; open its `index.html`.
For one demo, append `--demo xrf` or `--demo handwriting` to the script command.

| What to inspect | Included files |
| --- | --- |
| Spectral counts, energy axis, and synthetic truth | [spectra.csv](examples/results/synthetic_demos/xrf/spectra.csv), [samples.csv](examples/results/synthetic_demos/xrf/samples.csv); each MSA in `emsa/` contains one spectrum |
| Energy ranking and prediction comparison | [energy_ranking.csv](examples/results/synthetic_demos/xrf/energy_ranking.csv), [predictions.csv](examples/results/synthetic_demos/xrf/predictions.csv) |
| Handwriting queries and complete ranking | [queries.csv](examples/results/synthetic_demos/handwriting/queries.csv), [ranking.csv](examples/results/synthetic_demos/handwriting/ranking.csv) |

To refresh the bundled results, run `.venv/bin/python examples/synthetic_demos.py --output examples/results/synthetic_demos`.

Or call the modules directly:

```python
from greytheory.demos import run_xrf_demo, run_handwriting_demo

xrf = run_xrf_demo("artifacts/synthetic_demos/xrf", seed=7)
handwriting = run_handwriting_demo("artifacts/synthetic_demos/handwriting")
print(xrf["report"])
print(handwriting["report"])
```

XRF exports `emsa/*.msa`, `spx/*.spx`, `spectra.csv`, and `dataset.npz`.
[Bruker documents EMSA exchange](https://www.bruker.com/it/products-and-solutions/elemental-analyzers/eds-wds-ebsd-SEM-Micro-XRF/software-esprit-family/esprit-reporting-and-data-management.html), but importing these files still needs testing with your actual M4/ESPRIT version.
The SPX files are minimal fixtures for this project's reader, not guaranteed vendor exports.
Synthetic mixing weights are not calibrated elemental wt%.

The handwriting sheet was created with imagegen; the image and [prompt record](greytheory/demos/assets/handwriting_ai_sheet.json) are bundled.
Labels describe prompt-assigned styles, not human writers. All samples share one generated sheet;
style matches demonstrate the workflow, not cross-document or human-authorship accuracy.
Grey means window descriptors here; categorical style IDs are never used as continuous GRA targets.

<details>
<summary>Preview the spectra and AI handwriting results</summary>

![Synthetic spectra and energy ranking](examples/results/synthetic_demos/xrf/spectra_and_ranking.png)

![Three fictional AI-generated handwriting styles](greytheory/demos/assets/handwriting_ai_sheet.png)

![Handwriting styles with PCA and Grey window PCA](examples/results/synthetic_demos/handwriting/style_embeddings.png)

</details>

## Development and tests

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

Test inputs are generated or included in the repository; no dataset download is needed.
`scripts/verify_full_install.py` checks the installed APIs. Examples use synthetic data to demonstrate
the workflow, not establish process, chemical, or forensic accuracy.

To prepare a GitHub source ZIP, run `python3 scripts/package_github.py`.
The archive in `artifacts/github_upload/` includes source and synthetic results, excluding local environments, caches, and external instrument datasets.

Benchmark records are in [benchmarks/results](benchmarks/results/).
Rerun the [core benchmark](benchmarks/compare_core.py) or [decomposition comparison](benchmarks/compare_decomposition.py).
Recorded timings are from macOS arm64 and depend on the environment.
The older `GreyTheory`, `GreyGM*`, `add_pattern`/`add_patterns`, and `grey.run.gm*` APIs remain available.

## License

[MIT](LICENSE). Dependencies retain their own licenses; see [Third-party notices](THIRD_PARTY_NOTICES.md).

## References

Algorithms, upstream tools, and further reading. SCRAMBLE is related research, not an included implementation.

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

24. Pillow. [Image.open](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open) and [ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html). File loading, EXIF orientation, and aspect-preserving padding; installed with the `images` extra.
