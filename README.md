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
<summary>Papers, algorithms, and implementation sources</summary>

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

</details>
