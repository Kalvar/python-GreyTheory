# 完整使用說明

[English](guide.md) | **繁體中文** | [日本語](guide.ja.md)

以下指令都在專案根目錄執行。[文件首頁](README.zh-TW.md) · [專案介紹](../README.zh-TW.md)。

GreyTheory 是一套 Python 資料分析工具，提供灰色預測、灰關聯分析（GRA）和多種 PCA 方法。
可以用來預測時間序列、整理大量特徵，或比較光譜與量測資料。

| 想做什麼 | 從這裡開始 |
| --- | --- |
| 預測接下來幾筆數值 | [GM(1,1)](#時間序列預測) |
| 滑動窗口做兩層預測 | [Convolution](#convolution兩層窗口預測) |
| 看哪些因素與目標較接近 | [GRA](#灰關聯分析gra) |
| 先降維，再篩選特徵 | [GreyPCA](#pca-與特徵篩選) |
| 把望大、望小的品質指標放在一起評分 | [品質評分](#品質評分) |
| 處理多維軌跡或圖片 | [特徵擷取](#軌跡圖片與窗口特徵) |
| 讀入 PNG／JPG 做比較 | [圖片檔範例](#從圖片檔開始分析) |
| 讀取 Bruker 檔案 | [SPX／BCF](#bruker-檔案讀取) |
| 試跑合成光譜與 AI 筆跡 | [兩組 demo](#合成光譜與-ai-筆跡-demo) |

## 先跑起來

需要 Python 3.11 以上。下載或 clone 專案後，在專案目錄執行：

```bash
python3 run.py
```

> [!TIP]
> 第一次會建立 `.venv`、安裝套件並跑範例。
> 之後用同一個指令就好，不用手動啟用環境。

要在自己的程式裡使用，請用該程式的 Python 環境，在專案目錄安裝：

```bash
python -m pip install .
```

## 用瀏覽器操作：光譜、DOE 與圖片

HTML 已放在 [examples/workbench/index.html](../examples/workbench/index.html)，可直接雙擊開啟預覽。內建展示是 Python 預先計算的結果；不會把參數變更冒充成即時計算。

`workbench` 會開啟 GreyTheory 的圖形分析介面，可載入光譜、DOE 或筆跡圖片，選擇方法與參數，執行分析並查看圖表及特徵排序。第一次會建立 `.venv` 並安裝分析與視窗套件，之後沿用同一環境。在專案目錄執行：

```bash
python3 run.py workbench
```

Windows 用 `python run.py workbench`。已有 Python 環境也可以直接跑：

```bash
python -m examples.workbench.desktop
```

這是隨原始碼提供的範例，位於 `examples/workbench/`；不會放進 `greytheory` 的安裝套件。本機視窗以 pywebview 橋接 HTML 和 Python，直接載入專案內的 HTML，不啟動 HTTP server、不開連接埠。直接雙擊 HTML 是預覽模式；需要 Python 的新設定會提示開啟本機視窗或匯出運算請求。圖表使用原生 SVG 與 JavaScript，不需要 CDN 或圖表套件。

介面右上角提供「重整頁面」與「操作手冊」，各區也有對應步驟的入口。[查看操作手冊與檔案格式](README.zh-TW.md#workbench-操作手冊)。重整會清除目前設定與結果，請先下載要保留的 JSON。

1. **先試 DOE**：選 `PVD` 或 `CVD`，按「載入選取資料」。
2. **選目標**：例如膜厚 `thickness_nm`、均勻度誤差 `uniformity_error_pct`。輸入特徵預設只選製程參數；其他量測結果不會自動拿來當參數。
3. **按「執行分析」**：左圖看樣本差異，右邊看特徵排序。勾選／取消特徵，或用「保留前幾名」套用選取；切換 PCA 後可以重跑，並下載分析 JSON。
4. **換成 Bruker**：將檔案放進 `data/test/` 後重新整理網頁，或直接選取 CSV／SPX／BCF。M4 的 `minBcf.bcf` 可選偵測器 `0`、`1` 分開分析；多光譜 SPX 用索引 `0`、`1` 選擇量測或背景；背景可能含小數，是估計強度而非原始光子計數。部分 BCF 編碼尚未支援，讀不到會顯示原因。
5. **看圖片 demo**：切到「圖片比較」，試跑 AI 筆跡，或選一張待比較圖片與 3–30 張參考圖片。距離越小代表特徵越接近，不是作者身分判定。

> [!NOTE]
> 有目標時，排序是原始特徵對目標的 GRA；切換 PCA 改變投影，這個 GRA 排序不會跟著改變。沒有目標時，排序是特徵與保留主成分的最大絕對相關，不是 GRA，也不是因果重要度。PC 軸正負不代表品質望大／望小；此介面沒有把 PC 當成品質評分。

光譜分析先排除負能量通道，將通道加總成最多 64 個區間；預設按各光譜保留區間的總計數正規化，再做 PCA。原始計數曲線仍可看。單筆 SPX 只能看光譜，需要至少 3 筆資料才能跑介面的 PCA。兩個偵測器不直接相加，避免能量刻度不同造成誤用。DOE 會按欄位標準化；不同 PCA 的變異量不一定都能提供或直接比較。

**30 筆半導體模擬 DOE** 放在 [data/demo/doe](../data/demo/doe)：PVD、CVD 各 15 筆，每組含 12 個分層隨機設定與 3 個中心點重複量測。這不是完整因子或正交實驗設計。

| 製程 | 輸入參數 | 模擬量測結果 |
| --- | --- | --- |
| PVD | 功率、壓力、溫度、偏壓、Ar 流量、時間 | 膜厚、均勻度誤差、粗糙度、電阻率 |
| CVD | 溫度、壓力、前驅物流量、載氣流量、電漿功率、時間 | 膜厚、均勻度誤差、折射率、濕蝕刻速率 |

數據由固定種子的簡化公式與雜訊產生，公式、單位（欄名）和用途限制見 [manifest.json](../data/demo/doe/manifest.json)。PVD、CVD 分開分析；這些數字不是實際機台配方或量產建議。15 筆資料適合操作示範，畫面上的排序沒有獨立測試集，不能當成預測準確率或因果證據。膜厚、折射率通常需指定目標值／容許範圍；選作 GRA 參考不表示越大越好。

重新產生同一組數據：

```bash
python -m examples.workbench.doe
```

資料處理也能從 Python 直接呼叫，不必開網頁：

```python
from examples.workbench.analysis import analyze, read_spectrum_file

# 讀取你的本機 M4 地圖；檔案不隨套件提供。
data = read_spectrum_file("data/test/m4_tornado/minBcf.bcf", detector=0)
result = analyze(data, {"method": "pca", "components": 2})
print(result["ranking"][:5])  # 未指定目標：與主成分的相關排序
```

### 更多展示與實測

切到 **「應用實驗室」**，選情境、調參數後執行。本機視窗模式每次都呼叫 Python 計算；直接開 HTML 則是已標示的預覽結果。結果 JSON 包含此次參數與輸入，可以下載核對。

| 情境 | 可以試什麼 | 結果怎麼看 |
| --- | --- | --- |
| 配送路線 | 3–8 個配送點、距離／時間／遲到權重 | 動畫路線、原始順序比較、各成本與灰品質分數 |
| 司機媒合 | 人數、訂單數、接貨距離／準時率／評分權重 | 配對連線與未媒合訂單；先檢查載重、技能、可用時間 |
| 藝術品區域差異 | 六種 PCA、成分數、門檻分位、模擬新增材料強度 | 另一張參考圖擬合後的重建誤差熱圖，旁邊顯示模擬真值供核對 |
| 訂單量預測 | GM11／Convolution、alpha、ridge、窗口、未來期數；也可貼自己的序列 | 先保留最後四期回測，再預測未來；回測預測不使用保留期的觀測值 |
| 多維軌跡 | 2D–4D、重採樣點數、Grey 窗口、PCA 方法 | 顯示前兩維軌跡；全部維度參與特徵擷取，12 條擬合、6 條只轉換 |
| 光譜工具 | NMF、MCR-ALS、MNF、MLPCA、AsLS 基線、擬峰、xraylib 譜線 | 原始／重建曲線與診斷；不同工具使用符合其條件的假資料 |
| 半導體工具 | QualityPLS、Q／T² 監控、GRA rank_features、GP 候選、LHS 設定 | PLS 用 11 筆訓練、4 筆保留；GP 以均勻度誤差望小示範，候選不會送到機台 |
| 圖片比較頁 | 六種 PCA 與其參數、AI 筆跡或自己的圖片 | 區塊 → Grey 窗口 → PCA → 距離；不是作者身分或鑑識結論 |

第一頁的 **「GreyTheory 分析方法」** 可選 GreyPCA、純 GRA、GM0N、GM1N、品質評分、Grey 窗口後 PCA，以及原始計數的 PoissonPCA。GM0N／GM1N 使用累積與列順序，必須確認資料有合理先後；無序 DOE 用 GRA／PCA 較合適。品質模式排名的是樣本，需逐欄設定望大／望小／目標、上下界與權重，並非特徵重要度。

參數會跟著方法顯示填寫提示：

- Kernel PCA：核函數、gamma、多項式次數。
- Sparse／Robust Sparse：稀疏強度、正則化、擾動懲罰。
- AdvPCA：自動／手動 delta、平滑與內外層迭代上限。
- GRA：rho、尺度處理、正向／雙方向比較。`rho` 先用 `0.5`。
- GreyPCA：可設定保留成分數，再用目標的 GRA 選取其中幾個；`0` 關閉成分篩選。主成分分數和原始特徵排序會分開呈現。

> [!NOTE]
> 配送搜尋與媒合指派分別使用完整枚舉、匈牙利演算法，Grey 負責偏好評分。路線是合成平面座標，沒有真實道路、多車、法定工時或硬性時間窗。藝術品異常只能提示進一步查驗；筆跡距離不能判定作者。所有這些展示資料均為模擬，不能當成實務準確率。

可下載的模擬輸入在 [application_scenarios/synthetic_inputs.json](../data/demo/scenarios/synthetic_inputs.json)，包含配送點、司機／訂單、訂單序列與兩張藝術品光譜圖。沒有真實姓名、地址或藝術品資料。重新產生：

```bash
python -m examples.workbench.scenarios
```

不開網頁也能呼叫同一個情境：

```python
from examples.workbench.scenarios import run_scenario

result = run_scenario("routes", {"stops": 6, "objective": "grey"})
print(result["tables"][0]["rows"])
```

不安裝視窗依賴也可以交換檔案：在 HTML 中匯出運算請求，再執行：

```bash
python3 run.py workbench --request greytheory-request.json
```

回到 HTML 匯入產生的 `greytheory-request.result.json`。這條路只需要 Python 分析依賴，沒有本機服務。關閉視窗即結束即時模式。原始 Bruker 資料仍由 `.gitignore` 排除。

## 時間序列預測

用 `fit` 放入資料，`predict(2)` 預測接下來兩筆：

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(background_mode="corrected").fit(series)
print(model.predict(2))
print(model.metrics)
```

至少需要三筆資料。滑動窗口的兩層預測見下方 Convolution 範例。

係數看 `model.coefficients`，求解狀況看 `model.diagnostics`。
`set_data` 可以先存資料、之後再批次計算；`reset()` 清除結果，`reset(clear_data=True)` 連資料一起清除。

<details>
<summary>背景值、正則化與誤差計算</summary>

`background_mode="corrected"` 的背景值為 `alpha * current + (1-alpha) * previous`。
預設 `"legacy"` 保留舊公式，兩項都乘上 `alpha`。`alpha=0.5` 時結果相同。

預設用最小平方法求解。`ridge_alpha` 控制正則化；`rank_policy="raise"` 會在係數無法唯一估計時報錯。
診斷包含矩陣秩、條件數與殘差。

`horizon=0` 只擬合歷史資料。原始值為零時，相對誤差為 `None`，MAE 與 RMSE 仍可使用。
`predict` 不會改動已儲存的擬合結果。

</details>

## Convolution：兩層窗口預測

Convolution 功能由 `window_size` 開啟。先用每個窗口的 GM(1,1) 預測下一筆，再把這些結果交給第二層 GM(1,1)：

**原始序列 → 窗口預測 → 第二層 GM(1,1) → 未來數值**

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(window_size=4, stride=1, background_mode="corrected").fit(series)
print(model.predict(2))
```

| 參數 | 用途 |
| --- | --- |
| `window_size=4` | 每個窗口使用四筆資料；`None` 為一般 GM11 |
| `stride=1` | 每次往前移動一筆 |
| `predict(2)` | 預測未來兩筆 |
| `correction_mode="legacy"` | 預設沿用窗口誤差修正；`"none"` 可關閉修正 |

要跑完整兩層預測，請讓資料能產生至少三個窗口。上例六筆資料、窗口四筆、步長一筆，剛好產生三個窗口。
`coefficients` 和 `metrics` 對應最後一層的擬合結果。最後一個窗口可能多包含尾端資料，沿用原本的處理方式。

執行比較範例，會列出一般 GM11 和 Convolution 的預測值：

```bash
.venv/bin/python examples/convolution_forecast.py
```

比較結果：

```text
Ordinary GM11, next two values: [256.5532, 263.1223]
Convolution GM11, next two values: [265.9278, 274.0119]
```

`GreyWindowFeatures` 則是擷取窗口特徵給 PCA／GRA 使用，不做這個第二層預測。

## 多因素模型

`GM0N` 和 `GM1N` 用來分析多個因素與一個目標之間的關係。每列是一筆資料，每欄是一個因素：

```python
from greytheory import GM0N

factors = [[.75, .5], [1.22, 1], [.2, .7], [1, .66], [1, 1], [1, .5]]
targets = [1, 1, 1, 1, 1, 1]
model = GM0N().fit(factors, targets, feature_names=["factor_a", "factor_b"])
print(model.coefficients)
print(model.influence_degrees)
```

GM(1,N) 改用 `GM1N().fit(factors, targets)`。因素名稱可以省略。
`influence_degrees` 按係數絕對值排序，會受單位和共線性影響。要比較序列與目標的接近程度，可以用 GRA。

## 灰關聯分析（GRA）

給一條參考序列，再放入要比較的序列。分數越高，表示在選定的正規化方式下越接近參考：

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

`normalize` 支援 `none`、`minmax`、`zscore`、`initial`、`mean`。
也可以用 `GreyGRA().score(...)` 或 `GreyGRA().rank(...)`，從 `greytheory.analysis` 匯入即可。

GRA 的分數取決於同批比較的序列，增減候選可能改變排序。它表示灰關聯程度，不代表因果關係或預測準確率。

<details>
<summary>GRA 計算方式</summary>

每個位置先算絕對差異 `Δ`，再用 `(Δmin + rho*Δmax) / (Δ + rho*Δmax)` 得到關聯系數，最後取加權平均。
`rho` 須在 `(0, 1]`，權重須非負。差異極值取自同批候選；分數為 1 不一定表示原始數值完全相同。

</details>

## PCA 與特徵篩選

`GreyFeatureSelector` 直接挑原始欄位；`GreyPCA` 先降維，再用 GRA 挑與目標較接近的主成分。
下面用合成資料示範，實際使用時換成自己的特徵表和目標值即可：

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

`n_components` 是降維後的成分數，`top_k` 是 GRA 要留下的數量。
只做降維時，用 `fit(train_factors)`，省略目標值即可。
> [!IMPORTANT]
> **先分訓練與測試資料。** 所有轉換都用訓練資料 `fit`，測試資料只呼叫 `transform`。

### 切換 PCA 方法

改 `method` 就能切換，其他參數放進 `method_params`：

| `method` | 方法 | `method_params` 範例 |
| --- | --- | --- |
| `"pca"`（預設） | 一般 PCA | `{"whiten": True}` |
| `"sparse"` | SparsePCA | `{"alpha": 0.1}` |
| `"kernel"` | KernelPCA | `{"kernel": "rbf", "gamma": 0.1}` |
| `"robust"` | PCP 低秩分解後建立 PCA 投影 | `{"tol": 1e-6}` |
| `"robust_sparse"` | Huber／elastic-net RobustSparsePCA | `{"alpha": 0.1, "kappa": 1.0}` |
| `"adv"` | AdvPCA | `{"delta": 0.01, "max_iter": 1000}` |

例如切換到 AdvPCA：

```python
analysis = GreyPCA(
    3, method="adv", method_params={"delta": 0.01, "max_iter": 1000},
    top_k=2, standardize=True,
).fit(train_factors, train_targets)
components = analysis.transform(test_factors)
print(analysis.reducer.converged)
print(analysis.reducer.inner_converged)
```

AdvPCA 要確認外層與最終內層都收斂，再評估結果。不同方法的比較見 [grey_pca_methods.py](../examples/grey_pca_methods.py)。

也可以傳入自己的 sklearn 相容模型，成分數改由該模型設定：

```python
from sklearn.decomposition import IncrementalPCA

analysis = GreyPCA(
    estimator=IncrementalPCA(n_components=4, batch_size=12), top_k=2,
).fit(train_factors, train_targets)
```

自訂模型須支援 `fit`、`transform` 和 sklearn clone，輸出每筆一列的二維密集矩陣。
`estimator` 與 `method`／`method_params` 擇一使用。

### 看排名與選取結果

`component_scores` 是各主成分的 GRA 分數，`selected_components` 是選中的索引，從 0 開始。
輸出欄位保留原本的成分順序。要按分數列出排名：

```python
valid = np.flatnonzero(np.isfinite(analysis.component_scores))
ranking = valid[np.argsort(-analysis.component_scores[valid], kind="stable")]
for index in ranking:
    print(f"PC{index + 1}", float(analysis.component_scores[index]))
```

原始欄位的分數看 `selector.scores`。沒有提供目標值時，`component_scores` 為 `None`。
這裡的篩選適用於連續數值目標；作者編號等類別標籤需要另外的分類或比對模型。

### 保留多少個主成分

一般 PCA 可以直接指定要保留的累積變異比例，例如 85%：

```python
ordinary = GreyPCA(n_components=0.85, method="pca", standardize=True).fit(train_factors)
print(ordinary.n_components_fitted)
print(ordinary.explained_variance_ratio.sum())

report = analysis.reconstruction_report(train_factors, threshold=0.85)
print(report.prefix_coverage)
print(report.first_prefix_at_threshold)
print(report.selected_coverage)
```

小數 `n_components` 只支援一般 PCA。AdvPCA、SparsePCA 可改看重建涵蓋率。
80–85% 可以當起點，最後仍要用獨立資料檢查預測效果：品質訊號也可能藏在變異較小的成分裡。

<details>
<summary>獨立使用各種分解方法與光譜 PCA</summary>

以下從 `greytheory.analysis` 匯入，不會自動加上 GRA：

| 呼叫方式 | 用途 |
| --- | --- |
| `PCAAdapter(3, method="pca")` | 一般 PCA |
| `PCAAdapter(3, method="sparse", alpha=0.1)` | SparsePCA |
| `PCAAdapter(3, method="kernel", gamma=0.1)` | KernelPCA |
| `RobustPCA().fit(data)` | 取得 `low_rank` 與 `sparse` 矩陣 |
| `RobustSparsePCA(3).fit(data)` | Huber／elastic-net 稀疏降維 |
| `AdvPCA(3, delta=0.05).fit(data)` | AdvPCA 降維 |

光譜相關方法從 `greytheory.spectroscopy` 匯入：

| 呼叫方式 | 輸入條件 |
| --- | --- |
| `PoissonPCA(3).fit_transform(counts)` | 非負計數，使用近似變異數穩定轉換 |
| `fit_mlpca(data, variances, n_components=3)` | 每個數值都有正的誤差變異數，假設誤差獨立 |
| `fit_mnf(cube, n_components=3)` | 空間 × 空間 × 頻帶，從相鄰像素估計雜訊 |

`PoissonPCA` 可搭配 `GreyPCA(estimator=PoissonPCA(3), standardize=False)`。
計數資料要保持非負，不要先做會產生負數的標準化。

</details>

<details>
<summary>主成分方向、重建與方法差異</summary>

PCA 的正負號可以翻轉。`GreyPCA` 預設 `component_direction="either"`，在同一批 GRA 比較正反方向，取較高分。
常數成分排除並標為 NaN；`top_k=None` 保留所有可評分成分。
`GreyFeatureSelector` 預設只比原方向，需要時可設 `direction="either"`。

有品質目標時，可以在建立 `GreyPCA` 時加上 `align_to_target=True`，讓輸出的正負方向配合參考目標。
方向在訓練時固定，正反分數相同則報錯；`component_directions` 和 `component_direction_ambiguous` 可查看判定結果。
這只處理符號，不保證主成分具有單調的品質意義，也不處理不同訓練結果之間的成分交換或旋轉。
要保留有方向的 GRA 比較，可設 `component_direction="positive"`。

`inverse_transform` 將未選的成分補零再重建；KernelPCA 是近似重建，部分自訂模型不支援逆轉換。
`reconstruction_report` 以 `1 - SSE / SST` 評估指定成分，不調整保留數量。
`standardize=True` 時在標準化空間計算；非一般 PCA 的結果可能為負或不隨成分數遞增。
`first_prefix_at_threshold` 為 `None` 表示所有已評估前綴都未達門檻；GRA 篩選後另看 `selected_coverage`。
報告只將同一模型的後續成分補零，與重新訓練較少成分的結果可能不同。

`"robust"` 用 PCP 的訓練低秩矩陣建立投影，新資料直接套用該投影，不會重新做 PCP 去異常。
AdvPCA 的稀疏編碼與 PCP 的低秩／加法異常分解是不同目標。
RobustSparsePCA 與 AdvPCA 都有非凸最佳化步驟，需檢查收斂狀況。

</details>

## 品質評分

例如翹曲越小越好、剪切力越大越好，可以先統一成 0–1 的偏好值，再計算加權 GRA 分數：

```python
from greytheory.analysis import rank_quality, grade_quality

quality = rank_quality(
    [[80, 10], [40, 20], [20, 25]],  # 每列一個樣本；欄位依序為翹曲、剪切力
    directions=["smaller", "larger"],
    bounds=[(0, 100), (0, 30)],      # 示範用範圍，請換成製程適用的值
    weights=[0.5, 0.5],
)
print(quality.normalized_values)
print(quality.scores)
print(quality.ranking)  # [2, 1, 0]：由好到差的列索引

new_benefits = quality.normalizer.transform([[30, 22]])
new_quality = grade_quality(new_benefits, weights=quality.weights, rho=quality.rho)
print(new_quality.scores)
```

`directions` 支援 `larger`、`smaller`、`target`。
若膜厚要接近 100，可用 `BenefitNormalizer(["target"], bounds=[(80, 120)], targets=[100])`，
再呼叫 `fit_transform` 或 `transform`。這個類別也從 `greytheory.analysis` 匯入。

`bounds` 是正規化範圍，省略時使用訓練資料的最小、最大值。

> [!NOTE]
> **跨批次比較時，沿用同一組範圍、權重和 `rho`。**
> 這樣加入其他樣本時，才不會改變同一筆資料的品質分數。

超界預設報錯；設 `out_of_range="clip"` 才會截到界限，原始超界位置可用 `normalizer.out_of_bounds(data)` 查詢。

> [!WARNING]
> **品質分數不等於良率或合格判定。**
> 分數依指定偏好計算，硬性規格仍要另外檢查。

原始指標都轉成望大，也不代表每個主成分都會越大越好；主成分方向見上方說明。

製程預測的完整範例：[semiconductor_adv_quality.py](../examples/semiconductor_adv_quality.py)。
它把製程特徵與品質目標分開，按 lot 切分資料，比較 AdvPCA／GRA＋Ridge 和均值基準。
用來計算品質目標的翹曲、剪切力，不應再放回預測該目標的輸入欄位。

<details>
<summary>評分公式與輸入檢查</summary>

**計算方式**

`grade_quality` 先計算各指標的關聯系數，再依權重取平均：

```text
coefficient = rho / (1 - benefit + rho)
score       = weighted_mean(coefficients)
```

| 設定 | 使用的值 |
| --- | --- |
| 理想序列 | 全 1 |
| 差異最小值／最大值 | 固定為 0／1 |
| 合併方式 | 加權平均，允許不同指標互補 |

`grey_relation` 則從同批候選計算差異極值。NIST desirability 使用幾何平均，計算方式也不同。

**輸入檢查**

| 檢查項目 | 要求 |
| --- | --- |
| 數值 | 不含 NaN 或無限值 |
| 欄位 | 數量、方向、欄名與順序須一致 |
| 常數欄 | 必須提供有效的正規化界限 |
| `target` | 嚴格落在上下界內，以分段線性方式計算偏好 |
| 權重 | 全部非負，且至少一個為正 |

品質正規化與 AdvPCA 的擾動半徑 `delta` 分別設定。

</details>

## 軌跡、圖片與窗口特徵

可以把資料串成這條流程：

**數值資料 → 軌跡／圖片特徵 → Grey 窗口特徵 → PCA／GRA → 迴歸或距離比對**

| 資料 | 格式 | 使用方式 |
| --- | --- | --- |
| 光譜、一維序列 | `(樣本數, 點數)` | `GreyWindowFeatures`；光譜先對齊能量軸 |
| 二維以上軌跡 | 每份 `(點數, 維度)`，整批放在 list | `TrajectoryFeatures` → `GreyWindowFeatures` |
| 灰階、多通道圖片 | `(樣本數, 高, 寬[, 通道數])` | `ImagePatchFeatures` → `GreyWindowFeatures` |

以下是一份有時間與分筆紀錄的二維軌跡。三維、五維也用同一個類別：

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

圖片可以直接從檔案讀入，完整範例見下方「從圖片檔開始分析」。

要接迴歸模型，可以用 sklearn Pipeline。這裡的 `train_paths`、`test_paths` 是 `Trajectory` 清單，
`train_targets` 是每份訓練軌跡對應的連續數值：

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

完整範例：[grey_feature_pipeline.py](../examples/grey_feature_pipeline.py)。
這些特徵可以作為模型輸入；筆跡作者比對、補畫辨識仍需專用模型與資料驗證。

### 從圖片檔開始分析

準備至少三張參考圖片，以及一張待比對圖片。先裁出相同的文字或簽名，讓方向與背景盡量一致：

```text
data/test/images/
├── reference/
│   ├── sample_a.png
│   ├── sample_b.jpg
│   └── sample_c.png
└── query.png
```

在專案目錄執行一行：

```bash
python3 run.py handwriting data/test/images/query.png data/test/images/reference
```

第一次會自動建立 `.venv` 並安裝讀圖套件；之後用同一行即可。Windows 可將 `python3` 換成 `python`。
圖片預設統一為 288×96，保留比例並補白；參考資料夾也可有子資料夾。查詢圖會自動排除在參考集之外。

終端機會顯示最接近的圖片與報告位置。用瀏覽器開啟 `artifacts/handwriting/index.html`，可直接看兩張圖與完整排名。

| 檔案 | 內容 |
| --- | --- |
| `index.html` | 圖片預覽與排名報告 |
| `ranking.csv` | 參考圖片的距離與排名 |
| `features.csv`、`components.csv` | Grey 窗口特徵與 PCA 座標 |
| `summary.json` | 設定與結果 |

在自己的 Python 程式裡，先用該環境執行 `python -m pip install -e ".[images]"`，之後一個函式就能完成：

```python
from greytheory import compare_handwriting

result = compare_handwriting("data/test/images/query.png", "data/test/images/reference")
print(result.best_match)
print(result.report)
```

想換 AdvPCA，指令尾端加 `--pca adv`，或在函式加 `pca="adv"`。其他選項為 `pca`、`sparse`、`kernel`、`robust`、`robust_sparse`。
輸出資料夾可用 `--output` 或 `output=` 指定。距離越小表示特徵越接近，不是同一作者的機率。

<details>
<summary>手動組合 pipeline 與舊版圖片範例</summary>

```bash
python -m pip install -e ".[images]"
```

`load_images` 接受單一檔案路徑或路徑清單，讀成 0–1 的 RGB 陣列。下面可直接讀入 PNG／JPG，並列出離查詢圖片最近的參考圖：

```python
from pathlib import Path
import numpy as np
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import Pipeline
from greytheory.io import load_images
from greytheory.features import ImagePatchFeatures, GreyWindowFeatures
from greytheory.analysis import GreyPCA

reference_paths = sorted(
    path for path in Path("data/test/images/reference").iterdir()
    if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
)
reference_images = load_images(reference_paths, size=(128, 128))
query_image = load_images("data/test/images/query.png", size=(128, 128))

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

分數是 PCA 特徵空間中的距離，越小越接近。模型只用參考圖片訓練，查詢圖片只做轉換。
它比較的是這組特徵，不能直接當成作者、真偽或補畫判定。

`size=(128, 128)` 依「寬、高」指定尺寸，保留比例並補白邊；省略時所有圖片須有相同尺寸。
讀取時會套用 EXIF 方向、將透明背景補白。灰階可設 `mode="L"`。
裁切區域與位置仍需先對齊；高位元原始強度資料請保留為數值陣列，不經此讀圖轉換。

也可以直接跑範例。第一個指令會產生示範 PNG，第二個讀入自己的圖片：

```bash
.venv/bin/python examples/image_files.py

.venv/bin/python examples/image_files.py \
  --references data/test/images/reference \
  --query data/test/images/query.png \
  --size 128 128
```

結果預設寫入 `artifacts/image_files/`：

| 檔案 | 內容 |
| --- | --- |
| `features.csv` | 各張圖片的 Grey 窗口特徵 |
| `components.csv` | PCA 轉換後的座標 |
| `ranking.csv` | 參考圖片的距離與排名 |

完整程式：[image_files.py](../examples/image_files.py)。

```bash
greytheory handwriting data/test/images/query.png data/test/images/reference
```

</details>

<details>
<summary>軌跡、窗口與圖片的資料要求</summary>

軌跡預設依每筆路徑長度重取樣，保留位置、方向、距離、轉角和分筆標記。
`include_time=True` 改依時間重取樣並計算速度，時間戳須嚴格遞增。
每筆至少兩個原始點，`n_points` 至少為筆數的兩倍。抬筆間隔不算進距離或速度。
`center=True` 移除起點位置，`scale=False` 保留原始尺度；速度為座標單位／時間單位，轉角為弧度。
`scale=True` 時距離與速度使用正規化尺度。時間、筆壓不要混進空間座標；尚無獨立筆壓處理。

Grey 窗口取出幅度、平均、標準差、段內變化、GM 係數、離散方程 RMSE 與涵蓋率，不做未來預測。
各窗各通道先用最大絕對值縮放，並保留原始幅度。少於三點的片段，其 GM 係數與 `gm_coverage` 填零；
`gm_full_rank_coverage` 可檢查滿秩比例。涵蓋率低時，係數需要特別留意。
`boundary_channel=-1` 將最後一欄當分段標記，避免跨筆或跨格子列計算；`stride` 不可大於窗口。

圖片輸入須為數值陣列。格子位置看 `patch_bounds`，窗口位置看 `windows`，特徵名稱用 `get_feature_names_out()`。
圖片特徵不含 OCR、裁字，也無法從靜態照片取得實際速度或筆壓。

</details>

## Bruker 檔案讀取

```python
from greytheory.io.bruker import read_bcf, read_spx

spectrum = read_spx("reference.spx")
image = read_bcf("scan.bcf", lazy=True)
counts = image.get_pixel(y=0, x=0, detector=0)
energy_keV = image.energy_axes[0]
roi = image.get_spectra((0, 0, 2, 2), detector=0)
```

SPX 提供計數、metadata，以及檔案內的能量校正軸。BCF 保留各偵測器的校正資訊。
ROI 使用 `(y0, x0, y1, x1)`，不含上界；計數型別為 `uint64`。

BCF 支援範圍為未壓縮 SFS 中有像素索引的 instructively packed 格式，其他編碼、外層壓縮和 BCF v2 不支援。
不同能量軸不能直接用 `sum_detectors` 合併。讀取自己的檔案時，請先與儀器軟體的結果核對。

## 製程與光譜工具

| 模組 | 功能 |
| --- | --- |
| `greytheory.semiconductor` | PLS 品質迴歸、動態／多維 PCA 監控、GRA 排序、拉丁超立方取樣、GP 預期改善量建議點 |
| `greytheory.spectroscopy` | AsLS 基線校正、NMF、MCR-ALS、MNF、Poisson PCA、加權低秩擬合、X 射線譜線查詢、固定峰位擬合 |

範例：[合成光譜](../examples/hyperspectral_gra_pca.py)、[按製造批次驗證](../examples/semiconductor_quality.py)、
[AdvPCA 品質預測](../examples/semiconductor_adv_quality.py)。
XRF 峰值強度要換算成濃度，還需要儀器、標準品和基質效應校正。

## 批次執行

同一個模型可以換資料後重複加入佇列。`ModelQueue` 會自動深拷貝，保留加入當下的內容：

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

`queue.run()` 預設依序執行，`workers=2` 改用兩個程序，結果維持輸入順序。
GM0N、GM1N、GM11 可以混用；已有模型清單時可呼叫 `run_models(models, workers=2)`。
多程序程式請保留 `if __name__ == "__main__":`。

<details>
<summary>佇列複製與更新方式</summary>

建立佇列、加入或替換項目時都會深拷貝。讀取 `queue[0]` 則取得佇列內的模型，可直接修改。
所有工作成功後才更新佇列；`inplace=False` 回傳完成計算的副本，保留原佇列。

</details>

## 合成光譜與 AI 筆跡 demo

已附上[合成輸入與分析結果](../data/demo/results/)。下載專案後，直接用瀏覽器開啟
`data/demo/results/index.html` 就能看兩組報告，不用先安裝 Python。
GitHub 不會直接顯示 HTML 報告；線上可先看下方圖片與 CSV。

想自己重跑，在專案目錄執行（macOS／Linux）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[demos]"
.venv/bin/python examples/synthetic_demos.py
```

Windows 請將 `.venv/bin/python` 換成 `.venv\Scripts\python.exe`。

| Demo | 輸入與分析 | 結果 |
| --- | --- | --- |
| 合成 XRF | 4 張 6×6 掃描圖、144 組 1024 通道光譜；已知 Ca／Fe／Cu／Zn 譜線混合權重，含背景與 Poisson 雜訊 | 光譜圖、能量 GRA 排名、獨立模擬圖的 PCA／GreyPCA 預測比較 |
| AI 筆跡風格 | 3 種人為設定風格的「春風明月」，共 18 格；12 格參考、6 格查詢 | PCA／Grey 窗口＋PCA 的距離排名、座標與特徵 CSV |

重跑結果會存到 `artifacts/synthetic_demos/`，開啟其中的 `index.html` 即可。
也可以只跑一組：`examples/synthetic_demos.py --demo xrf` 或 `--demo handwriting`。

| 想看什麼 | 已附的檔案 |
| --- | --- |
| 光譜數值、能量軸與模擬真值 | [spectra.csv](../data/demo/results/xrf/spectra.csv)、[samples.csv](../data/demo/results/xrf/samples.csv)；`emsa/` 每個 MSA 檔是一組光譜 |
| 關鍵能量排序與預測比較 | [energy_ranking.csv](../data/demo/results/xrf/energy_ranking.csv)、[predictions.csv](../data/demo/results/xrf/predictions.csv) |
| 筆跡查詢結果與完整排名 | [queries.csv](../data/demo/results/handwriting/queries.csv)、[ranking.csv](../data/demo/results/handwriting/ranking.csv) |

要重新產生專案內附的結果，可執行 `.venv/bin/python examples/synthetic_demos.py --output data/demo/results`。

示範程式放在外層 `examples/demos/`，圖片與生成紀錄放在其中的 `assets/`。
以下呼叫請在專案目錄執行；範例不隨正式套件安裝：

```python
from examples.demos import run_xrf_demo, run_handwriting_demo

xrf = run_xrf_demo("artifacts/synthetic_demos/xrf", seed=7)
handwriting = run_handwriting_demo("artifacts/synthetic_demos/handwriting")
print(xrf["report"])
print(handwriting["report"])
```

XRF 會輸出 `emsa/*.msa`、`spx/*.spx`、`spectra.csv` 和 `dataset.npz`。
EMSA 是 [Bruker 公開支援的交換格式](https://www.bruker.com/it/products-and-solutions/elemental-analyzers/eds-wds-ebsd-SEM-Micro-XRF/software-esprit-family/esprit-reporting-and-data-management.html)，仍需在實際的 M4／ESPRIT 版本測試匯入。
SPX 是本專案讀取用的最小範例，不宣稱等同原廠匯出檔。模擬混合權重也不是校正後的元素 wt%。

筆跡圖由 imagegen 生成，原圖與[提示紀錄](../data/demo/handwriting/handwriting_ai_sheet.json)隨專案附上。
風格標籤來自生成時的欄位設定，不是真實作者。所有樣本都來自同一張合成頁，命中結果只展示流程，不代表跨文件或真人作者辨識準確率。
這裡的 Grey 是窗口特徵，不把風格編號當連續目標送入 GRA。

<details>
<summary>查看光譜分析與 AI 筆跡範例</summary>

![合成光譜與關鍵能量排名](../data/demo/results/xrf/spectra_and_ranking.png)

![AI 生成的三種虛構筆跡風格](../data/demo/handwriting/handwriting_ai_sheet.png)

![PCA 與 Grey 窗口加 PCA 的筆跡風格分布](../data/demo/results/handwriting/style_embeddings.png)

</details>

## 開發與測試

`greytheory/` 放正式程式，`examples/` 放範例與示範資料，`tests/` 放測試及 fixtures。
GitHub 與原始碼包保留範例和測試；wheel 只安裝正式程式。

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

測試資料由程式產生或已附在專案內，不用另外下載。`scripts/verify_full_install.py` 可檢查安裝後的 API。
範例使用合成資料，展示流程，不代表實際製程、化學或鑑識準確率。

需要整理 GitHub 原始碼包時，執行 `python3 scripts/package_github.py`。
ZIP 存在 `artifacts/github_upload/`，包含原始碼與上述合成結果，不含本機環境、快取或外部儀器資料。

效能紀錄見 [benchmarks/results](../benchmarks/results/)，重跑可用[核心測試](../benchmarks/compare_core.py)或[降維比較](../benchmarks/compare_decomposition.py)。
紀錄來自 macOS arm64，執行時間會隨環境改變。
舊的 `GreyTheory`、`GreyGM*`、`add_pattern`／`add_patterns` 和 `grey.run.gm*` 仍可使用。

## 授權

[MIT](../LICENSE)。相依套件依各自的授權使用，詳見[第三方授權聲明](../THIRD_PARTY_NOTICES.md)。

## 參考文獻與實作來源

以下保留已實作演算法、科學資料來源與檔案格式處理的參考資料。

1. Deng, J. L. (1982). [Control problems of grey systems](https://doi.org/10.1016/S0167-6911(82)80025-X). *Systems & Control Letters*, 1(5), 288–294.
2. Liu, S. & Lin, Y. (2011). [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2). Springer. Grey modelling and relational analysis.
3. Kayacan, E., Ulutas, B. & Kaynak, O. (2010). [Grey system theory-based models in time series prediction](https://doi.org/10.1016/j.eswa.2009.07.064). *Expert Systems with Applications*, 37(2), 1784–1789.
4. Jolliffe, I. T. & Cadima, J. (2016). [Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202). *Philosophical Transactions A*, 374, 20150202.
5. scikit-learn. [PCA, SparsePCA and KernelPCA implementations](https://scikit-learn.org/stable/modules/decomposition.html).
6. Candès, E. J., Li, X., Ma, Y. & Wright, J. (2011). [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395). *Journal of the ACM*, 58(3), Article 11. Principal Component Pursuit.
7. Lin, Z., Chen, M. & Ma, Y. (2010). [The Augmented Lagrange Multiplier Method for Exact Recovery of Corrupted Low-Rank Matrices](https://arxiv.org/abs/1009.5055). Inexact ALM solver for PCP.
8. Erichson, N. B. et al. (2020). [Sparse Principal Component Analysis via Variable Projection](https://doi.org/10.1137/18M1211350), [author manuscript](https://arxiv.org/abs/1804.00341). *SIAM Journal on Applied Mathematics*, 80(2), 977–1002. Robust sparse model: equation (17), Algorithm 2.
9. Vävinggren, D. et al. (2026). [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553). AdvPCA: Algorithms 1–2 and Appendix A.3.
10. Lee, D. D. & Seung, H. S. (1999). [Learning the parts of objects by non-negative matrix factorization](https://doi.org/10.1038/44565). *Nature*, 401, 788–791. NMF background; this package delegates fitting to scikit-learn.
11. Camp, C. H. Jr. (2019). [pyMCR: A Python Library for Multivariate Curve Resolution Analysis with Alternating Regression (MCR-AR)](https://doi.org/10.6028/jres.124.018). *Journal of Research of NIST*, 124, 124018.
12. Green, A. A., Berman, M., Switzer, P. & Craig, M. D. (1988). [A transformation for ordering multispectral data in terms of image quality with implications for noise removal](https://doi.org/10.1109/36.3001). *IEEE Transactions on Geoscience and Remote Sensing*, 26(1), 65–74. [Spectral Python MNF API](https://www.spectralpython.net/class_func_ref.html#spectral.mnf).
13. Anscombe, F. J. (1948). [The transformation of Poisson, binomial and negative-binomial data](https://doi.org/10.1093/biomet/35.3-4.246). *Biometrika*, 35(3–4), 246–254. Variance stabilization used by `PoissonPCA`.
14. Wentzell, P. D. et al. (1997). [Maximum likelihood principal component analysis](https://doi.org/10.1002/%28SICI%291099-128X%28199707%2911%3A4%3C339%3A%3AAID-CEM476%3E3.0.CO%3B2-L). *Journal of Chemometrics*, 11(4), 339–366. `fit_mlpca` implements the independent-error, fixed-variance case.
15. pybaselines. [Asymmetric least-squares baseline correction](https://pybaselines.readthedocs.io/en/latest/algorithms/whittaker.html#asymmetric-least-squares-asls). The `baseline_correct` implementation uses `Baseline.asls`.
16. Wold, S., Sjöström, M. & Eriksson, L. (2001). [PLS-regression: a basic tool of chemometrics](https://doi.org/10.1016/S0169-7439(01)00155-1). *Chemometrics and Intelligent Laboratory Systems*, 58(2), 109–130.
17. Rasmussen, C. E. & Williams, C. K. I. (2006). [Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/). MIT Press.
18. Jones, D. R., Schonlau, M. & Welch, W. J. (1998). [Efficient Global Optimization of Expensive Black-Box Functions](https://doi.org/10.1023/A:1008306431147). *Journal of Global Optimization*, 13, 455–492. Expected-improvement acquisition.
19. xraylib. [X-ray interaction data and documentation](https://github.com/tschoonj/xraylib/wiki). Used for characteristic line energies and relative rates.
20. RosettaSciIO community. [Bruker detector-calibration discussion, issue #516](https://github.com/hyperspy/rosettasciio/issues/516). File-format and per-detector energy calibration notes.
21. NIST/SEMATECH. [Multiple responses: the desirability approach](https://www.itl.nist.gov/div898/handbook/pri/section5/pri5322.htm). Engineering preference directions and targets; GreyTheory uses separately documented arithmetic GRA grades, not the geometric-mean desirability function.
