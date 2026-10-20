# GreyTheory

[English](README.md) | **繁體中文** | [日本語](README.ja.md)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3977ab)](pyproject.toml)
[![MIT License](https://img.shields.io/badge/License-MIT-36a88a)](LICENSE)
[![CI](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml/badge.svg)](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml)

![GreyTheory — Grey models, GRA, and PCA](docs/images/greytheory-banner.svg)

<p align="center"><strong>用 Python 做灰色預測、特徵比較與 PCA 分析。</strong></p>
<p align="center"><a href="docs/README.zh-TW.md">Documentation</a> · <a href="#quick-start">快速開始</a> · <a href="docs/README.zh-TW.md#workbench">操作介面</a> · <a href="benchmarks/results/">效能測試</a></p>

預測一段數值、找出與目標較相關的特徵，或整理光譜與製程量測。可以直接寫 Python，也可以從專案附的 HTML 介面開始。

## 能做什麼

- **Grey + PCA 整合分析**：`GreyPCA` 結合六種 PCA 與 GRA 主成分篩選。先用 PCA 整理樣本差異；有參考目標時，再用 GRA 評分、篩選較相關的主成分。光譜、圖片與軌跡也能先擷取 Grey 窗口特徵，再交給 PCA，將局部變化一起納入分析。
- **預測數值**：GM11 與兩層 Convolution；有序多變量資料可用 GM0N／GM1N。
- **比較與排序**：GRA 特徵排序，以及望大／望小／目標值的品質評分。
- **整理大量特徵**：六種 PCA、原始計數的 PoissonPCA、Grey 窗口、圖片與多維軌跡。

<a id="quick-start"></a>

## 快速開始

需要 **Python 3.11 以上**。下載或 clone 專案後，在專案目錄執行：

```bash
python3 run.py
```

> [!TIP]
> 第一次會建立 `.venv` 並安裝相依套件；之後用同一個指令即可。Windows 將 `python3` 改成 `python`。

### 在 Python 裡使用

先安裝到你自己的程式所使用的 Python 環境：

```bash
python -m pip install .
```

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(background_mode="corrected").fit(series)
print(model.predict(2))
```

## 選擇 PCA 方法

在 `GreyPCA` 指定 `method`，操作介面也能選同樣的方法。

```python
from greytheory.analysis import GreyPCA

features = [[1.0, 2.0, 0.8], [1.5, 2.4, 1.2],
            [2.0, 3.1, 1.1], [2.5, 3.4, 1.8]]
model = GreyPCA(n_components=2, method="pca", standardize=True)
components = model.fit_transform(features)
print(components)
```

| 方法 | 適合先試的情況 |
| --- | --- |
| `"pca"` | 標準線性投影；不知道選什麼先用它。 |
| `"sparse"` | 希望成分係數較稀疏。 |
| `"kernel"` | 想探索非線性的資料關係。 |
| `"robust"` | 先做 PCP 低秩拆解，再投影。 |
| `"robust_sparse"` | 同時考慮稀疏編碼與訓練擾動。 |
| `"adv"` | 想測試指定擾動條件下的投影。 |

非負原始計數另有 PoissonPCA。參數、主成分篩選，以及 GRA 和 PCA 排序的差別，都放在完整使用說明裡。 [→ GreyPCA](docs/guide.zh-TW.md#pca-與特徵篩選)

## 用介面試資料

`workbench` 會開啟 GreyTheory 的圖形分析介面。可載入光譜、DOE 或筆跡圖片，選擇分析方法與參數，再查看圖表和特徵排序：

```bash
python3 run.py workbench
```

第一次會建立 `.venv` 並安裝分析與視窗套件，之後沿用同一環境。分析在本機執行，不需要架設伺服器。

也可以雙擊專案附的 HTML 看**離線預覽**；內建展示是預先計算的結果。要套用新設定，請使用上述指令，或交換請求／結果 JSON。

[HTML](examples/workbench/index.html) · [看附截圖的操作說明](docs/README.zh-TW.md#workbench) · [操作手冊與檔案格式](docs/README.zh-TW.md#workbench-操作手冊) · [光譜入門](docs/README.zh-TW.md#光譜入門一步一步操作)

![PVD DOE — GreyTheory workbench](docs/images/workbench-doe.png)

*PVD 示範：15 筆合成實驗。左圖看樣本差異，右邊依選取目標比較製程參數。*

[資料入口](data/README.md)：`data/demo/` 放展示資料，`data/test/` 放自己的測試檔案（不上傳 GitHub）。

所有展示資料集中在 [data/demo/](data/demo/README.md)。不知道該選哪個檔案時，先開 [Demo 資料包入口](data/demo/index.html)，裡面列出對應的操作頁與步驟。

### 更多展示

介面內也有配送路線、司機媒合、藝術品光譜差異、訂單量預測、多維軌跡、光譜與半導體工具；圖片頁可比較 AI 筆跡或自己的圖片。

[看附截圖的操作說明](docs/README.zh-TW.md#gallery) · [PVD CSV](data/demo/doe/pvd_15.csv) · [CVD CSV](data/demo/doe/cvd_15.csv)

> [!NOTE]
> 展示資料均為合成資料，用來試流程，不能當成實務準確率。配送與媒合由專用演算法搜尋，Grey 負責偏好評分；圖片距離不能判定作者，藝術品異常則是進一步查驗的線索。

## Documentation

| 文件 | 內容 |
| --- | --- |
| [看附截圖的操作說明](docs/README.zh-TW.md) | 安裝、預覽、即時分析與結果匯入／匯出 |
| [GreyPCA](docs/guide.zh-TW.md#pca-與特徵篩選) | 六種 PCA、參數與主成分篩選 |
| [Images / trajectories](docs/guide.zh-TW.md#從圖片檔開始分析) | 圖片讀取、特徵擷取與比較 |
| [Bruker](docs/guide.zh-TW.md#bruker-檔案讀取) | SPX／BCF 支援範圍與偵測器刻度 |
| [完整使用說明](docs/guide.zh-TW.md) | 預測、GRA、品質評分、批次執行與文獻 |

## 開發與測試

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

[Benchmarks](benchmarks/results/) · [Issues](https://github.com/Kalvar/python-GreyTheory/issues)

## 授權

[MIT](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

## 參考文獻與實作來源

<details>
<summary>展開參考文獻與實作來源</summary>

演算法、套件與延伸閱讀如下。SCRAMBLE 僅列為相關研究，未提供實作。

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

24. Pillow. [Image.open](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open) 與 [ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html)。用於讀圖、EXIF 方向與保留比例的補邊；透過 `images` 選用套件安裝。

</details>
