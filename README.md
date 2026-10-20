# GreyTheory

**English** | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3977ab)](pyproject.toml)
[![MIT License](https://img.shields.io/badge/License-MIT-36a88a)](LICENSE)
[![CI](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml/badge.svg)](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml)

![GreyTheory — Grey models, GRA, and PCA](docs/images/greytheory-banner.svg)

<p align="center"><strong>Grey forecasting, feature comparison, and PCA for Python.</strong></p>
<p align="center"><a href="docs/README.md">Documentation</a> · <a href="#quick-start">Getting started</a> · <a href="docs/README.md#workbench">Workbench</a> · <a href="benchmarks/results/">Benchmarks</a></p>

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

For nonnegative raw counts, use the PoissonPCA adapter. Component selection, parameters, and the distinction between GRA and PCA rankings are in the usage guide. [→ GreyPCA](docs/guide.md#pca-and-feature-selection)

## Explore with the workbench

`workbench` opens the GreyTheory graphical analysis interface. Load spectra, DOE data, or handwriting images, choose methods and parameters, then inspect charts and feature rankings:

```bash
python3 run.py workbench
```

The first launch creates `.venv` and installs the analysis and desktop dependencies; later launches reuse it. Analysis runs locally without a server.

You can also open the bundled HTML directly for **offline previews** of precomputed results. New settings require the command above or request/result JSON exchange.

[HTML](examples/workbench/index.html) · [Read the illustrated walkthrough](docs/README.md#workbench)

![PVD DOE — GreyTheory workbench](docs/images/workbench-doe.png)

*PVD demo: 15 synthetic runs. The projection shows sample differences; the ranking compares process inputs with the selected target.*

All demo inputs and results are in [data/demo/](data/demo/README.md). Open the [demo data browser](data/demo/index.html) to choose files and find the matching workbench actions.

### More demos

Try delivery routes, driver assignment, artwork spectral differences, order forecasting, 2D–4D trajectories, spectroscopy, and semiconductor tools. The image tab also compares AI-generated or uploaded handwriting images.

[Read the illustrated walkthrough](docs/README.md#gallery) · [PVD CSV](data/demo/doe/pvd_15.csv) · [CVD CSV](data/demo/doe/cvd_15.csv)

> [!NOTE]
> These examples use synthetic data. They demonstrate the workflow, not production, chemical, or forensic accuracy. Route search and assignment use dedicated optimizers; Grey supplies preference scores. Image distances do not identify writers, and artwork anomalies are investigation leads.

## Documentation

| Guide | Contents |
| --- | --- |
| [Read the illustrated walkthrough](docs/README.md) | Installation, previews, live analysis, and result files |
| [GreyPCA](docs/guide.md#pca-and-feature-selection) | All six PCA backends, parameters, and component selection |
| [Images / trajectories](docs/guide.md#start-with-image-files) | Loading images, feature extraction, and comparison |
| [Bruker](docs/guide.md#bruker-file-readers) | SPX / BCF support and detector calibration |
| [Usage guide](docs/guide.md) | Forecasting, GRA, quality scores, batch jobs, and references |

## Development

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

[Benchmarks](benchmarks/results/) · [Issues](https://github.com/Kalvar/python-GreyTheory/issues)

## License

[MIT](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

## References

<details>
<summary>Core Grey and PCA papers</summary>

Core references for Grey modelling, PCA, and the implemented robust solvers. Spectral and process-analysis references are in the [usage guide](docs/guide.md#references).

1. Deng, J. L. (1982). [Control problems of grey systems](https://doi.org/10.1016/S0167-6911(82)80025-X). *Systems & Control Letters*, 1(5), 288–294.
2. Liu, S. & Lin, Y. (2011). [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2). Springer. Grey modelling and relational analysis.
3. Kayacan, E., Ulutas, B. & Kaynak, O. (2010). [Grey system theory-based models in time series prediction](https://doi.org/10.1016/j.eswa.2009.07.064). *Expert Systems with Applications*, 37(2), 1784–1789.
4. Jolliffe, I. T. & Cadima, J. (2016). [Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202). *Philosophical Transactions A*, 374, 20150202.
5. Candès, E. J., Li, X., Ma, Y. & Wright, J. (2011). [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395). *Journal of the ACM*, 58(3), Article 11. Principal Component Pursuit.
6. Lin, Z., Chen, M. & Ma, Y. (2010). [The Augmented Lagrange Multiplier Method for Exact Recovery of Corrupted Low-Rank Matrices](https://arxiv.org/abs/1009.5055). Inexact ALM solver for PCP.
7. Erichson, N. B. et al. (2020). [Sparse Principal Component Analysis via Variable Projection](https://doi.org/10.1137/18M1211350), [author manuscript](https://arxiv.org/abs/1804.00341). *SIAM Journal on Applied Mathematics*, 80(2), 977–1002. Robust sparse model: equation (17), Algorithm 2.
8. Vävinggren, D. et al. (2026). [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553). AdvPCA: Algorithms 1–2 and Appendix A.3.

</details>
