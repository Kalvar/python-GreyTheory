# GreyTheory

[English](https://github.com/Kalvar/python-GreyTheory/blob/master/README.md) | **繁體中文** | [日本語](https://github.com/Kalvar/python-GreyTheory/blob/master/README.ja.md)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3977ab)](https://github.com/Kalvar/python-GreyTheory/blob/master/pyproject.toml)
[![MIT License](https://img.shields.io/badge/License-MIT-36a88a)](https://github.com/Kalvar/python-GreyTheory/blob/master/LICENSE)
[![CI](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml/badge.svg)](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml)

![GreyTheory — Grey models, GRA, and PCA](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/greytheory-banner.svg)

<p align="center"><strong>用 Python 做灰色預測、特徵比較與 PCA 分析。</strong></p>
<p align="center"><a href="https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md">Documentation</a> · <a href="#quick-start">快速開始</a> · <a href="https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md#workbench">操作介面</a> · <a href="https://github.com/Kalvar/python-GreyTheory/tree/master/benchmarks/results/">效能測試</a></p>

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

舊用法 `model.forecast(2)` 與 `model.forecast_convolution(1, 4)` 也可使用。只要接下來兩筆數值時用 `predict(2)`；`forecast(2)` 會重新計算已存資料並更新預測期數設定。

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

非負原始計數另有 PoissonPCA。參數、主成分篩選，以及 GRA 和 PCA 排序的差別，都放在完整使用說明裡。 [→ GreyPCA](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#pca-與特徵篩選)

## 用介面試資料

`workbench` 會開啟 GreyTheory 的圖形分析介面。可載入光譜、DOE 或筆跡圖片，選擇分析方法與參數，再查看圖表和特徵排序：

```bash
python3 run.py workbench
```

第一次會建立 `.venv` 並安裝分析與視窗套件，之後沿用同一環境。分析在本機執行，不需要架設伺服器。

也可以雙擊專案附的 HTML 看**離線預覽**；內建展示是預先計算的結果。要套用新設定，請使用上述指令，或交換請求／結果 JSON。

[HTML](https://github.com/Kalvar/python-GreyTheory/blob/master/examples/workbench/index.html) · [看附截圖的操作說明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md#workbench) · [操作手冊與檔案格式](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md#workbench-操作手冊) · [光譜入門](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md#光譜入門一步一步操作)

右上角可切換繁體中文、English、日本語；切換時會保留目前的資料、參數與結果。

![PVD DOE — GreyTheory workbench](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/workbench-doe.zh-TW.png)

*PVD 示範：15 筆合成實驗。左圖看樣本差異，右邊依選取目標比較製程參數。*

[資料入口](https://github.com/Kalvar/python-GreyTheory/blob/master/data/README.md)：`data/demo/` 放展示資料，`data/test/` 放自己的測試檔案（不上傳 GitHub）。

所有展示資料集中在 [data/demo/](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/README.md)。不知道該選哪個檔案時，先開 [Demo 資料包入口](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/index.html)，裡面列出對應的操作頁與步驟。

現場展示：執行 `python3 run.py workbench`，進入「應用實驗室」→「藝術品」情境。先用 seed 7、PCA、3 個成分、門檻分位 0.95、材料強度 0.6 執行。左圖看誤差與圈選位置，右圖核對刻意變更的 18 個位置。接著把門檻改為 0.99 重跑；再恢復 0.95，把強度降為 0.2 重跑。保持相同 seed，逐次下載結果 JSON。介面操作手冊也有完整步驟。

![Artwork differences](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/workbench-art.zh-TW.png)

這是合成光譜地圖的差異展示，不是上傳作品照片。此情境尚無真實參考／待測地圖成對匯入功能；標記區需要由修復專家查驗，不能直接當作補畫或真偽結論。

**AI 絹畫圖片** — 在「應用實驗室」→ 藝術品情境，把「示範資料來源」切到 **AI 絹畫圖片**，按預設值執行。程式會讀取兩張 PNG，經區塊特徵 → Grey 窗口 → GreyPCA 計算。關閉／開啟標記比較畫面，再把門檻改成 0.99 重跑。

[圖片、實際 CSV／JSON 與案例來源](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/artwork/index.html) · `python3 run.py artwork`

[開啟專家查看與實測報告](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/artwork/review/index.html) — 成對圖片用來排查驗順序；光譜用獨立正常資料校準門檻，再搭配實物檢查。實測也加入同圖負對照：舊重建誤差圈選數不能當成變更數。展示可選葉片、花瓣、鳥身與背景，逐區查看觀察、假設和下一步檢查；內容是依公開專業流程撰寫的模擬判讀。

### 更多展示

介面內也有配送路線、司機媒合、藝術品光譜差異、訂單量預測、多維軌跡、光譜與半導體工具；圖片頁可比較 AI 筆跡或自己的圖片。

[看附截圖的操作說明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md#gallery) · [PVD CSV](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/doe/pvd_15.csv) · [CVD CSV](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/doe/cvd_15.csv)

> [!NOTE]
> 展示資料均為合成資料，用來試流程，不能當成實務準確率。配送與媒合由專用演算法搜尋，Grey 負責偏好評分；圖片距離不能判定作者，藝術品異常則是進一步查驗的線索。

## 排序穩定性與最佳化

[GUI 操作與截圖](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md#最佳化四步驟展示)

快速入口：`analyze_features()` 一次完成排名穩定性、GreyPCA 回歸搜尋與選用的正常資料校正；`choose_options()` 用欄位名稱比較多目標方案。

```python
import numpy as np
from greytheory import analyze_features

features = np.random.default_rng(7).normal(size=(120, 4))
target = 2 * features[:60, 0] - features[:60, 1]
result = analyze_features(features[:60], target, normal_data=features[60:90])
predictions = result.predict(features[90:])
```

[快速 function 用法](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#快速-function)

檢查 GRA 排名穩定性、用另一批正常資料校正差異門檻、自動搜尋 GreyPCA 回歸設定，並保留候選方案的多目標折衷解。

```bash
python3 run.py optimize
```

[四步驟 Python 用法](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#排序穩定性門檻校正與最佳化)。合成範例在下載專案後執行。搜尋採有限次隨機試驗與訓練切分快取；驗證分數是調參結果，不是獨立測試準確率。Pareto 結果限於輸入的候選方案。

## Research models

新增研究版等間隔預測與品質回歸：RL-FGM 公式核心、GINN／FGINN 工程版本，以及獨立設計的 Grey–Fuzzy GPR。

```python
from greytheory import forecast_series

values = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
future = forecast_series(values, steps=3, method="rlfgm")
print(future)
```

### GreyPCA + research models

四種模型都能搭配 `pca`、`sparse`、`kernel`、`robust`、`robust_sparse`、`adv`。時序輸入每列是一個時間點、每欄是一個通道，預測會還原原欄位；改 `method` 可換 GINN／FGINN。PCA 專用設定放在 `pca_params={"method_params": {...}}`。

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

GUI 選「研究模型 → 搭配 PCA：on」。時序主成分採訓練資料決定的正值平移，這會影響灰色模型；品質可靠度只反映保留的主成分。

```bash
python3 run.py research
```

[用法、數學差異與實測限制](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#研究模型rl-fgmginn-與-greyfuzzy-gpr)

## Documentation

| 文件 | 內容 |
| --- | --- |
| [看附截圖的操作說明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.zh-TW.md) | 安裝、預覽、即時分析與結果匯入／匯出 |
| [GreyPCA](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#pca-與特徵篩選) | 六種 PCA、參數與主成分篩選 |
| [Images / trajectories](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#從圖片檔開始分析) | 圖片讀取、特徵擷取與比較 |
| [Bruker](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#bruker-檔案讀取) | SPX／BCF 支援範圍與偵測器刻度 |
| [完整使用說明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md) | 預測、GRA、品質評分、批次執行與文獻 |

## 開發與測試

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

[Benchmarks](https://github.com/Kalvar/python-GreyTheory/tree/master/benchmarks/results/) · [Issues](https://github.com/Kalvar/python-GreyTheory/issues)

## 授權

[MIT](https://github.com/Kalvar/python-GreyTheory/blob/master/LICENSE) · [Third-party notices](https://github.com/Kalvar/python-GreyTheory/blob/master/THIRD_PARTY_NOTICES.md)

### 非官方實作與權利聲明

GreyTheory 中依論文參考開發的演算法為**非官方實作（Unofficial implementations）**，與原作者及其所屬機構沒有隸屬關係，也未獲其背書。參考文獻和其演算法價值歸功於原始研究。

若您認為相關實作涉及您的專利、著作權或其他權利，請來信 [ilovekalvar@gmail.com](mailto:ilovekalvar@gmail.com)，說明權利依據及涉及的演算法或檔案；專利疑慮請附專利號與相關權利項。

我們會審查通知，必要時補正引用、修改、暫停使用或下架相關演算法。收到通知或採取預防措施，不表示承認侵權，在開源世界裡都需要尊重參考文獻的作者貢獻。

## 參考文獻與實作來源

<details>
<summary>Grey 與 PCA 核心文獻</summary>

這裡列出 Grey、PCA 與已實作穩健演算法的主要文獻。光譜與製程分析的方法來源見[完整使用說明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.zh-TW.md#參考文獻與實作來源)。

1. Deng, J. L. (1982). [Control problems of grey systems](https://doi.org/10.1016/S0167-6911(82)80025-X). *Systems & Control Letters*, 1(5), 288–294.
2. Liu, S. & Lin, Y. (2011). [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2). Springer. Grey modelling and relational analysis.
3. Kayacan, E., Ulutas, B. & Kaynak, O. (2010). [Grey system theory-based models in time series prediction](https://doi.org/10.1016/j.eswa.2009.07.064). *Expert Systems with Applications*, 37(2), 1784–1789.
4. Jolliffe, I. T. & Cadima, J. (2016). [Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202). *Philosophical Transactions A*, 374, 20150202.
5. Candès, E. J., Li, X., Ma, Y. & Wright, J. (2011). [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395). *Journal of the ACM*, 58(3), Article 11. Principal Component Pursuit.
6. Lin, Z., Chen, M. & Ma, Y. (2010). [The Augmented Lagrange Multiplier Method for Exact Recovery of Corrupted Low-Rank Matrices](https://arxiv.org/abs/1009.5055). Inexact ALM solver for PCP.
7. Erichson, N. B. et al. (2020). [Sparse Principal Component Analysis via Variable Projection](https://doi.org/10.1137/18M1211350), [author manuscript](https://arxiv.org/abs/1804.00341). *SIAM Journal on Applied Mathematics*, 80(2), 977–1002. Robust sparse model: equation (17), Algorithm 2.
8. Vävinggren, D. et al. (2026). [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553). AdvPCA: Algorithms 1–2 and Appendix A.3.

</details>

### 研究模型來源與實作對應

以下論文提供模型定義與研究構想，成果歸原作者。本專案另外加入 PCA 串接、固定主成分平移與快速函式；這些整合設計不冒稱為原論文提出的方法。

- Xu, Zhenguo; Peng, Rui; Pang, Mengyi; Jiang, Jianming; Zhang, Rujing; & Liu, Caixia (2026). [A novel grey system model with discrete Riemann–Liouville fractional derivative and its applications](https://doi.org/10.1177/00368504261481032). *Science Progress*, 109(3). RL-FGM 累加算子與響應核心的來源。本專案以格點搜尋及訓練尾段驗證選階數，與原論文的 PSO／MAPE 選階方式不同。
- Xie, Wanli; Zhao, Ruibin; Xu, Zhenguo; & Liang, Tingting (2025). [Grey-informed neural network for time-series forecasting](https://doi.org/10.1016/j.neucom.2025.130756). *Neurocomputing*, 649, 130756. [Public preprint, v2 (2024)](https://arxiv.org/abs/2403.15027v2). GINN 與 FGINN 的來源。本專案參考公開預印本，使用不同網路、優化器及預測對先驗的損失，屬工程版本，沒有重現作者實驗。
- Lawal, Ahmad; Yang, Yingjie; Baisa, Nathanael L.; & He, Hongmei (2026). [Reservoir permeability prediction using Integrated Grey-Fuzzy Gaussian Process Regression: A comprehensive framework for uncertainty quantification and interpretability](https://doi.org/10.1016/j.engappai.2026.114777). *Engineering Applications of Artificial Intelligence*, 177, 114777. GRA、GPR 與模糊可靠度結合的概念來源。本專案的核權重與隸屬規則為獨立設計，並非原作者 IGF-GPR 的重現。
