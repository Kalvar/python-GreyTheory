# GreyTheory

**English** | [繁體中文](https://github.com/Kalvar/python-GreyTheory/blob/master/README.zh-TW.md) | [日本語](https://github.com/Kalvar/python-GreyTheory/blob/master/README.ja.md)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3977ab)](https://github.com/Kalvar/python-GreyTheory/blob/master/pyproject.toml)
[![MIT License](https://img.shields.io/badge/License-MIT-36a88a)](https://github.com/Kalvar/python-GreyTheory/blob/master/LICENSE)
[![CI](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml/badge.svg)](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml)

![GreyTheory — Grey models, GRA, and PCA](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/greytheory-banner.svg)

<p align="center"><strong>Grey forecasting, feature comparison, and PCA for Python.</strong></p>
<p align="center"><a href="https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.md">Documentation</a> · <a href="#quick-start">Getting started</a> · <a href="https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.md#workbench">Workbench</a> · <a href="https://github.com/Kalvar/python-GreyTheory/tree/master/benchmarks/results/">Benchmarks</a></p>

Forecast a short sequence, rank features against a target, or explore spectra and process measurements. Start with a few lines of Python, or use the bundled HTML workbench.

## What you can do

- **Combine Grey + PCA:** `GreyPCA` brings six PCA backends together with GRA component selection. PCA summarizes sample differences; with a reference target, GRA scores and selects related components. For spectra, images, and paths, add Grey-window features before PCA to include local patterns.
- **Forecast:** GM11 and two-level Convolution; GM0N / GM1N for ordered multivariate data.
- **Compare:** GRA feature ranking and mixed larger / smaller / target quality preferences.
- **Explore:** six PCA backends, raw-count PoissonPCA, Grey windows, images, and multidimensional paths.

<a id="quick-start"></a>

## Quick start

Requires **Python 3.11+**. Download or clone the repository, then run:

```bash
python3 run.py
```

> [!TIP]
> The first run prepares `.venv` and installs dependencies. On Windows, use `python` in place of `python3`.

### Use the library

Install into the Python environment used by your own program:

```bash
python -m pip install .
```

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(background_mode="corrected").fit(series)
print(model.predict(2))
```

Legacy calls `model.forecast(2)` and `model.forecast_convolution(1, 4)` are also supported. Use `predict(2)` when you only need the next two numeric values; `forecast(2)` refits stored data and updates the configured horizon.

## Choose a PCA method

Set `method` on `GreyPCA`. The same choices are available in the workbench.

```python
from greytheory.analysis import GreyPCA

features = [[1.0, 2.0, 0.8], [1.5, 2.4, 1.2],
            [2.0, 3.1, 1.1], [2.5, 3.4, 1.8]]
model = GreyPCA(n_components=2, method="pca", standardize=True)
components = model.fit_transform(features)
print(components)
```

| Method | When to try it |
| --- | --- |
| `"pca"` | A standard linear projection; start here. |
| `"sparse"` | Sparse component coefficients. |
| `"kernel"` | Nonlinear structure through a kernel. |
| `"robust"` | PCP low-rank decomposition followed by PCA. |
| `"robust_sparse"` | Joint robust and sparse projection. |
| `"adv"` | Projection under a configurable perturbation model. |

For nonnegative raw counts, use the PoissonPCA adapter. Component selection, parameters, and the distinction between GRA and PCA rankings are in the usage guide. [→ GreyPCA](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#pca-and-feature-selection)

## Explore with the workbench

`workbench` opens the GreyTheory graphical analysis interface. Load spectra, DOE data, or handwriting images, choose methods and parameters, then inspect charts and feature rankings:

```bash
python3 run.py workbench
```

The first launch creates `.venv` and installs the analysis and desktop dependencies; later launches reuse it. Analysis runs locally without a server.

You can also open the bundled HTML directly for **offline previews** of precomputed results. New settings require the command above or request/result JSON exchange.

[HTML](https://github.com/Kalvar/python-GreyTheory/blob/master/examples/workbench/index.html) · [Read the illustrated walkthrough](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.md#workbench)

Use the language selector in the header for English, 繁體中文 or 日本語. Switching language keeps your current inputs and results.

![PVD DOE — GreyTheory workbench](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/workbench-doe.en.png)

*PVD demo: 15 synthetic runs. The projection shows sample differences; the ranking compares process inputs with the selected target.*

All demo inputs and results are in [data/demo/](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/README.md). Open the [demo data browser](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/index.html) to choose files and find the matching workbench actions.

For a live artwork demonstration, open Application lab → Artwork differences. Run with seed 7, PCA, 3 components, quantile 0.95 and strength 0.6. Compare the error map with the 18 simulated changed positions. Raise quantile to 0.99 and rerun; then restore 0.95 and lower strength to 0.2. Keep the seed fixed and download each result JSON. The in-app manual includes these steps.

![Artwork differences](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/workbench-art.en.png)

This example uses synthetic spectral maps, not artwork photographs. Real paired-map upload is not available in this lab. A flagged region is a lead for examination, not evidence of retouching or authenticity.

**AI silk-painting images** — In Application lab → Artwork, choose **AI silk-painting images** and run the defaults. This reads the two bundled PNGs through patch features → Grey windows → GreyPCA. Hide/show the overlay, then raise quantile to 0.99 and rerun.

[Images, computed CSV / JSON and case sources](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/artwork/index.html) · `python3 run.py artwork`

[Open the interactive review and experiment results](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/artwork/review/index.html) — The paired-image view ranks corresponding feature changes for human inspection. The spectral view compares six methods with separate normal calibration and held-out simulation. An identical-PNG control shows why legacy reconstruction flags are not change counts. The region cards demonstrate observations, alternative explanations and next examinations; they are not an expert endorsement.

### More demos

Try delivery routes, driver assignment, artwork spectral differences, order forecasting, 2D–4D trajectories, spectroscopy, and semiconductor tools. The image tab also compares AI-generated or uploaded handwriting images.

[Read the illustrated walkthrough](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.md#gallery) · [PVD CSV](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/doe/pvd_15.csv) · [CVD CSV](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/doe/cvd_15.csv)

> [!NOTE]
> These examples use synthetic data. They demonstrate the workflow, not production, chemical, or forensic accuracy. Route search and assignment use dedicated optimizers; Grey supplies preference scores. Image distances do not identify writers, and artwork anomalies are investigation leads.

## Stability and optimization

[GUI walkthrough](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.md#four-step-optimization-demo)

Quick entry point: `analyze_features()` combines ranking stability, GreyPCA regression search and optional normal-data calibration. `choose_options()` compares named multi-objective alternatives.

```python
import numpy as np
from greytheory import analyze_features

features = np.random.default_rng(7).normal(size=(120, 4))
target = 2 * features[:60, 0] - features[:60, 1]
result = analyze_features(features[:60], target, normal_data=features[60:90])
predictions = result.predict(features[90:])
```

[Quick functions](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#quick-functions)

Check GRA ranking stability, calibrate difference thresholds on separate normal data, search GreyPCA regression settings, and keep Pareto trade-offs among candidate designs.

```bash
python3 run.py optimize
```

[Four-step Python guide](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#stability-calibration-and-optimization). The synthetic example needs a repository checkout. Search uses finite random trials and fold-local caching; validation scores are tuning results, not independent test accuracy. Pareto results apply to supplied candidates.

## Research models

Experimental equal-step forecasting and quality regression: RL-FGM core, GINN/FGINN engineering variants and independently designed Grey–Fuzzy GPR.

```python
from greytheory import forecast_series

values = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
future = forecast_series(values, steps=3, method="rlfgm")
print(future)
```

### GreyPCA + research models

All four models can use `pca`, `sparse`, `kernel`, `robust`, `robust_sparse` or `adv`. Forecast input is a time-by-channel matrix; output restores the original columns. For GINN/FGINN, change `method`. Backend options go in `pca_params={"method_params": {...}}`.

```python
import numpy as np
from greytheory import forecast_series, predict_quality

time = np.arange(24.)
history = np.column_stack([20 + time + np.sin(time), 40 + 0.3*time + np.cos(time)])
future = forecast_series(history, steps=3, method="rlfgm",
                         pca_method="adv", n_components=2, order=1)

random = np.random.default_rng(7)
features = random.normal(size=(60, 4))
quality = 100 + 5*features[:, 0] + 2*features[:, 1]**2
result = predict_quality(features[:40], quality[:40], features[40:],
                         pca_method="pca", n_components=2)
print(future, result["prediction"])
```

In Workbench, choose Research models → Use PCA: on. Forecast components need a declared training-only positive shift; this affects grey models. Quality reliability applies only to retained components.

```bash
python3 run.py research
```

[Methods, differences and measured limitations](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#experimental-research-models)

## Documentation

| Guide | Contents |
| --- | --- |
| [Read the illustrated walkthrough](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.md) | Installation, previews, live analysis, and result files |
| [GreyPCA](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#pca-and-feature-selection) | All six PCA backends, parameters, and component selection |
| [Images / trajectories](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#start-with-image-files) | Loading images, feature extraction, and comparison |
| [Bruker](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#bruker-file-readers) | SPX / BCF support and detector calibration |
| [Usage guide](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md) | Forecasting, GRA, quality scores, batch jobs, and references |

## Development

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

[Benchmarks](https://github.com/Kalvar/python-GreyTheory/tree/master/benchmarks/results/) · [Issues](https://github.com/Kalvar/python-GreyTheory/issues)

## License

[MIT](https://github.com/Kalvar/python-GreyTheory/blob/master/LICENSE) · [Third-party notices](https://github.com/Kalvar/python-GreyTheory/blob/master/THIRD_PARTY_NOTICES.md)

### Unofficial implementations and rights notices

Paper-based algorithms in GreyTheory are **unofficial implementations**. They are not affiliated with, approved by, or endorsed by the papers’ authors or their institutions. References credit the original research; implementation differences and independently designed extensions are documented separately.

MIT covers the rights granted by this project’s contributors. It does not establish permission under third-party patents or confirm freedom to operate. Users should assess applicable rights and obtain any necessary permissions for their use and deployment regions. The software is provided “as is” under MIT; this notice does not alter that license or exclude liability that cannot lawfully be excluded.

If you believe an implementation infringes your patent, copyright or other rights, please email [ilovekalvar@gmail.com](mailto:ilovekalvar@gmail.com) with your contact details, the right claimed, and the affected algorithm or files. For patent concerns, include the patent number, jurisdiction and relevant claims, and explain how the implementation relates to them. Rights holders or authorized representatives may submit notices privately; do not post confidential information in public issues.

The maintainer will review substantiated notices and, where warranted, correct the attribution, modify, temporarily disable, remove, or withdraw the affected implementation from project-controlled code and distributions. Receiving a notice or taking precautionary action is not an admission of infringement.

## References

<details>
<summary>Core Grey and PCA papers</summary>

Core references for Grey modelling, PCA, and the implemented robust solvers. Spectral and process-analysis references are in the [usage guide](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.md#references).

1. Deng, J. L. (1982). [Control problems of grey systems](https://doi.org/10.1016/S0167-6911(82)80025-X). *Systems & Control Letters*, 1(5), 288–294.
2. Liu, S. & Lin, Y. (2011). [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2). Springer. Grey modelling and relational analysis.
3. Kayacan, E., Ulutas, B. & Kaynak, O. (2010). [Grey system theory-based models in time series prediction](https://doi.org/10.1016/j.eswa.2009.07.064). *Expert Systems with Applications*, 37(2), 1784–1789.
4. Jolliffe, I. T. & Cadima, J. (2016). [Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202). *Philosophical Transactions A*, 374, 20150202.
5. Candès, E. J., Li, X., Ma, Y. & Wright, J. (2011). [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395). *Journal of the ACM*, 58(3), Article 11. Principal Component Pursuit.
6. Lin, Z., Chen, M. & Ma, Y. (2010). [The Augmented Lagrange Multiplier Method for Exact Recovery of Corrupted Low-Rank Matrices](https://arxiv.org/abs/1009.5055). Inexact ALM solver for PCP.
7. Erichson, N. B. et al. (2020). [Sparse Principal Component Analysis via Variable Projection](https://doi.org/10.1137/18M1211350), [author manuscript](https://arxiv.org/abs/1804.00341). *SIAM Journal on Applied Mathematics*, 80(2), 977–1002. Robust sparse model: equation (17), Algorithm 2.
8. Vävinggren, D. et al. (2026). [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553). AdvPCA: Algorithms 1–2 and Appendix A.3.

</details>

### Research-model sources and implementation attribution

The papers below provide the model definitions and ideas credited to their authors. GreyTheory’s PCA composition, fixed component offsets and quick functions are project integration work; they are not presented as methods proposed by these papers.

- Xu, Zhenguo; Peng, Rui; Pang, Mengyi; Jiang, Jianming; Zhang, Rujing; & Liu, Caixia (2026). [A novel grey system model with discrete Riemann–Liouville fractional derivative and its applications](https://doi.org/10.1177/00368504261481032). *Science Progress*, 109(3). Source of the RL-FGM accumulation and response core. GreyTheory uses grid search with a training-tail validation score instead of the paper’s PSO/MAPE selection.
- Xie, Wanli; Zhao, Ruibin; Xu, Zhenguo; & Liang, Tingting (2025). [Grey-informed neural network for time-series forecasting](https://doi.org/10.1016/j.neucom.2025.130756). *Neurocomputing*, 649, 130756. [Public preprint, v2 (2024)](https://arxiv.org/abs/2403.15027v2). Source of GINN and FGINN. GreyTheory consulted the public preprint and implements engineering variants with a different network, optimizer and prediction-to-teacher loss; it does not reproduce the authors’ experiments.
- Lawal, Ahmad; Yang, Yingjie; Baisa, Nathanael L.; & He, Hongmei (2026). [Reservoir permeability prediction using Integrated Grey-Fuzzy Gaussian Process Regression: A comprehensive framework for uncertainty quantification and interpretability](https://doi.org/10.1016/j.engappai.2026.114777). *Engineering Applications of Artificial Intelligence*, 177, 114777. Conceptual inspiration for combining GRA, GPR and fuzzy reliability. GreyTheory’s kernel weights and membership rules are independently designed, not a reproduction of the authors’ IGF-GPR.
