# GreyTheory

[English](README.md) | **繁體中文** | [日本語](README.ja.md)

GreyTheory 是一套 Python 資料分析工具，提供灰色預測、灰關聯分析（GRA）和多種 PCA 方法。
可以用來預測時間序列、整理大量特徵，或比較光譜與量測資料。

| 想做什麼 | 從這裡開始 |
| --- | --- |
| 預測接下來幾筆數值 | [GM(1,1)](#時間序列預測) |
| 看哪些因素與目標較接近 | [GRA](#灰關聯分析gra) |
| 先降維，再篩選特徵 | [GreyPCA](#pca-與特徵篩選) |
| 把望大、望小的品質指標放在一起評分 | [品質評分](#品質評分) |
| 處理多維軌跡或圖片 | [特徵擷取](#軌跡圖片與窗口特徵) |
| 讀取 Bruker 檔案 | [SPX／BCF](#bruker-檔案讀取) |

## 先跑起來

需要 Python 3.11 以上。下載或 clone 專案後，在專案目錄執行：

```bash
python3 run.py
```

第一次會建立 `.venv`、安裝套件並跑範例。之後用同一個指令就好，不用手動啟用環境。

要在自己的程式裡使用，請用該程式的 Python 環境，在專案目錄安裝：

```bash
python -m pip install .
```

## 時間序列預測

用 `fit` 放入資料，`predict(2)` 預測接下來兩筆：

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(background_mode="corrected").fit(series)
print(model.predict(2))
print(model.metrics)
```

至少需要三筆資料。想用兩層滑動窗口，可以改成：

```python
model = GM11(background_mode="corrected", window_size=4, stride=1).fit(series)
print(model.predict(2))
```

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
所有轉換都先用訓練資料 `fit`，測試資料只呼叫 `transform`。

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

AdvPCA 要確認外層與最終內層都收斂，再評估結果。不同方法的比較見 [grey_pca_methods.py](examples/grey_pca_methods.py)。

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

`bounds` 是正規化範圍，省略時使用訓練資料的最小、最大值。跨批次比較要沿用同一組範圍、權重和 `rho`。
超界預設報錯；設 `out_of_range="clip"` 才會截到界限，原始超界位置可用 `normalizer.out_of_bounds(data)` 查詢。

品質分數是依指定偏好算出的評分，不代表良率或合格判定。硬性規格要另外檢查。
原始指標都轉成望大，也不代表每個主成分都會越大越好；主成分方向見上方說明。

製程預測的完整範例：[semiconductor_adv_quality.py](examples/semiconductor_adv_quality.py)。
它把製程特徵與品質目標分開，按 lot 切分資料，比較 AdvPCA／GRA＋Ridge 和均值基準。
用來計算品質目標的翹曲、剪切力，不應再放回預測該目標的輸入欄位。

<details>
<summary>評分公式與輸入檢查</summary>

`grade_quality` 以全 1 為理想序列，固定差異極值為 0 和 1，再對 `rho / (1 - benefit + rho)` 取加權平均。
固定範圍和權重時，加入其他樣本不會改變同一筆的分數。這與按同批候選計算極值的 `grey_relation` 不同，
也與 NIST desirability 的幾何平均不同。加權平均允許不同指標互補。

`BenefitNormalizer` 會檢查 NaN、無限值、欄位／方向不符、無可用界限的常數欄，以及欄名順序。
`target` 必須嚴格落在上下界內，使用分段線性偏好。評分另會檢查權重，所有權重須非負且至少一個為正。
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

圖片用 `ImagePatchFeatures(grid_shape=(4, 8)).fit_transform(images)`，從 `greytheory.features` 匯入。
它會把圖片切成格子，取平均、標準差與水平／垂直亮度變化。接窗口時也設 `boundary_channel=-1`。

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

完整範例：[grey_feature_pipeline.py](examples/grey_feature_pipeline.py)。
這些特徵可以作為模型輸入；筆跡作者比對、補畫辨識仍需專用模型與資料驗證。

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

範例：[合成光譜](examples/hyperspectral_gra_pca.py)、[按製造批次驗證](examples/semiconductor_quality.py)、
[AdvPCA 品質預測](examples/semiconductor_adv_quality.py)。
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

## 開發與測試

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

測試資料由程式產生或已附在專案內，不用另外下載。`scripts/verify_full_install.py` 可檢查安裝後的 API。
範例使用合成資料，展示流程，不代表實際製程、化學或鑑識準確率。

效能紀錄見 [benchmarks/results](benchmarks/results/)，重跑可用[核心測試](benchmarks/compare_core.py)或[降維比較](benchmarks/compare_decomposition.py)。
紀錄來自 macOS arm64，執行時間會隨環境改變。
舊的 `GreyTheory`、`GreyGM*`、`add_pattern`／`add_patterns` 和 `grey.run.gm*` 仍可使用。

## 授權

[MIT](LICENSE)。相依套件依各自的授權使用，詳見[第三方授權聲明](THIRD_PARTY_NOTICES.md)。

## 參考文獻與實作來源

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
