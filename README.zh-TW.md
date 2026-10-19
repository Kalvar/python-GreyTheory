# GreyTheory

[English](README.md) | **繁體中文** | [日本語](README.ja.md)

GreyTheory 是用於灰色系統預測、灰關聯分析與光譜資料分析的 Python 函式庫。
提供 GM(0,N)、GM(1,N)、GM(1,1)、GRA、PCA 相關方法，以及 Bruker SPX 與部分 BCF 格式的讀取功能。

## 執行範例

需要 Python 3.11 以上版本。

在專案目錄執行這一個指令即可：

```bash
python3 run.py
```

第一次會自動建立環境、安裝相依套件並執行範例。之後使用同一個指令，不需要手動啟用環境。
套件設定變更或相依套件缺漏時，腳本會自動重新安裝。

## 安裝為函式庫

```bash
pip install greytheory
```

這個指令會安裝 PyPI 上已發布的版本。本頁介紹的 2.0 API 尚在開發中；
若要使用目前工作樹的版本，請在專案目錄執行 `python -m pip install .`。
科學運算相依套件會一起安裝，較大的模組則在使用時載入。

## 預測時間序列

```python
from greytheory import GM11

model = GM11(background_mode="corrected").fit([223.3, 227.3, 230.5, 238.1, 242.9, 251.1])
print(model.predict(2))
```

`fit` 會立即計算；`set_data` 只存入資料，留待批次執行。兩者都回傳模型本身，方便串接。
`alpha`、`background_mode`、`ridge_alpha` 與 `rank_policy` 可直接在建立模型時指定。

若要使用兩層滑動視窗預測，可寫成 `GM11(window_size=4, stride=1).fit(series).predict(2)`。
模型先對各個視窗建立 GM(1,1)，再以各視窗的預測值建立第二層 GM(1,1)。
`predict` 回傳未來預測值，不會改動已擬合模型的結果或預測期數設定。

### 背景值與求解器

`background_mode="corrected"` 使用 `alpha * current + (1-alpha) * previous`。
預設的 `"legacy"` 保留原本兩項都乘上 `alpha` 的公式。當 `alpha=0.5` 時兩者相同；
若 AGO 為 `[2, 5, 10]`、`alpha=0.8`，修正模式的背景值為 `[4.4, 9.0]`，舊模式則為 `[5.6, 12.0]`。

模型預設使用最小平方法，並提供矩陣秩、條件數與殘差等診斷。
可設定 `ridge_alpha` 加入正則化，或設定 `rank_policy="raise"` 拒絕無法識別的係數估計。
計算結果可由 `coefficients`、`diagnostics` 取得；GM(1,1) 另提供 `metrics`。
這些結果會在 `fit` 或批次計算完成後產生。

GM(1,1) 至少需要三筆觀測值。`horizon=0` 只擬合歷史資料，不產生未來預測。
原始值為零時，相對誤差為 `None`，仍可查看 MAE 與 RMSE。
`reset()` 清除計算結果；`reset(clear_data=True)` 也會清除觀測資料。

## GM(0,N) 與 GM(1,N) 因素分析

```python
from greytheory import GM0N

# 每列是一筆觀測，每欄是一個因素。
X = [[.75, .5], [1.22, 1], [.2, .7], [1, .66], [1, 1], [1, .5]]
y = [1, 1, 1, 1, 1, 1]
model = GM0N().fit(X, y, feature_names=["factor_a", "factor_b"])
print(model.coefficients)
print(model.influence_degrees)
```

`X` 的形狀為 `(觀測筆數, 因素數)`，`y` 為一維的 `(觀測筆數,)`。
因素名稱可省略，預設為 `x0`、`x1` 等。GM(1,N) 使用 `GM1N().fit(X, y)`，
其發展係數與驅動項係數分別放在 `development_coefficient` 與 `driving_coefficients`。

`influence_degrees` 沿用既有的係數絕對值排序。這種排序會受變數尺度與共線性影響；
若要比較各序列與參考序列的灰關聯程度，請使用下方的 GRA。

## 灰關聯分析

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

以絕對差異 `Δ` 計算各位置的關聯系數：
`(Δmin + rho*Δmax) / (Δ + rho*Δmax)`，再取加權平均作為分數。
`rho` 的範圍為 `(0, 1]`，位置權重必須非負。

`normalize` 可選 `none`、`minmax`、`zscore`、`initial` 或 `mean`，分別對每條序列處理。
最大與最小差異取自同一批候選，因此增減候選可能改變分數與排序。
分數為 1 也不一定代表原始數值完全相同。也可從 `greytheory.analysis` 匯入 `GreyGRA`，
使用 `GreyGRA().score(...)` 與 `GreyGRA().rank(...)`。

## 特徵選擇與 PCA

先依你要排序的對象選工具：

| 想比較什麼 | 使用方式 |
| --- | --- |
| 哪條數值序列與參考較接近 | `grey_relation` 或 `GreyGRA` |
| 哪些原始特徵與已知目標較有關 | `GreyFeatureSelector` |
| 先整理大量特徵，再挑選與目標較有關的綜合特徵 | `GreyPCA` |

下例使用合成資料。每列是一筆樣本、每欄是一個原始特徵，目標值是每筆樣本對應的已知數值。

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

標準化、特徵選擇與降維都應只用訓練資料擬合，再將同一轉換套用到測試資料。
特徵選擇器適用於連續型目標。`GreyPCA(...).fit(train_factors)` 只做降維；
加入 `train_targets` 才會計算 GRA 分數。`top_k` 指定保留幾個可評分主成分，`None` 保留所有非常數成分。
預設在同批候選中比較正反方向，避免任意翻號改變排名。

| `GreyPCA(method=...)` | 搭配算法 | `method_params` 範例 |
| --- | --- | --- |
| `"pca"`（預設） | 一般 PCA | `{"whiten": True}` |
| `"sparse"` | SparsePCA | `{"alpha": 0.1, "max_iter": 1000}` |
| `"kernel"` | KernelPCA | `{"kernel": "rbf", "gamma": 0.1}` |
| `"robust"` | 訓練資料先做 PCP，再建立 PCA 投影 | `{"tol": 1e-6}` |
| `"robust_sparse"` | Huber／elastic-net RobustSparsePCA | `{"alpha": 0.1, "kappa": 1.0}` |
| `"adv"` | AdvPCA | `{"delta": 0.05}` |

使用內建算法時，主成分數量設在 `GreyPCA(n_components=...)`，算法參數放入 `method_params`。
也可像上例傳入 `estimator`，由該模型自行設定主成分數量。自訂模型需具備 `fit`、`transform`，
支援 sklearn 的 clone 介面，並回傳每筆觀測一列的二維密集矩陣。
程式會先複製模型再訓練，不會修改你傳入的實例；`estimator` 與 `method`／`method_params` 擇一使用。
`PoissonPCA` 等需要非負計數的模型，請保留預設的 `standardize=False`。

`analysis.reducer` 可取得訓練完成的降維模型；`component_scores` 是所有主成分的 GRA 分數，
`selected_components` 是實際輸出順序對應的主成分索引，從 0 開始。
篩選後保留原本的主成分順序，不會按 GRA 分數重新排列。
`inverse_transform` 會先將未選主成分補零再重建；KernelPCA 的逆轉換是近似值，部分自訂模型不提供逆轉換。
`explained_variance_ratio` 僅在所選算法有提供時才能取得。

`"robust"` 使用 PCP 的訓練低秩矩陣建立 PCA 投影，再以同一投影轉換訓練與新資料；
它不會自動對新資料重新做 PCP 去異常。若要直接取得低秩／稀疏矩陣，仍可單獨使用 `RobustPCA`。
`PCAAdapter`、`RobustSparsePCA` 與 `AdvPCA` 也可獨立使用。
後兩者處理非凸問題，遇到迭代次數上限時應查看收斂診斷。
AdvPCA 的稀疏編碼目標，與 PCP 將資料拆成低秩及加法異常的目標不同。

可執行範例：[切換算法與傳入自訂模型](examples/grey_pca_methods.py)。

### 查看分數由高到低的排名

沿用上例的訓練資料與 `analysis`。以下分別列出原始特徵及綜合特徵的 GRA 排名：

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

第一份排名對應原始欄位；第二份對應降維後的綜合特徵，每組可能混合多個原始欄位。
排名是與指定目標的灰關聯程度，不是因果重要度、預測準確率或作者身分機率。
若未提供目標，`analysis.component_scores` 為 `None`，不能執行上述主成分排名。
GRA 篩選是否有助於預測，需要另外的測試資料驗證。

目前沒有自動辨識補畫或筆跡作者的功能。下方提供一般軌跡與圖片區塊特徵；筆跡仍需字區選取與專用比對流程。
作者編號不能直接當成連續型目標。這些應用仍需對應資料與專業判讀驗證。

## PCA 的取用方式與品質方向

### 切換六種方法

下列入口使用前例的訓練與測試資料；主成分數不可超過所選模型允許的資料維度。
AdvPCA 請同時檢查 `analysis.reducer.converged`（外層）及 `analysis.reducer.inner_converged`（最終內層）；
迭代到上限不代表已收斂，`delta` 與迭代設定需在訓練側驗證。
把 `models["adv"]` 換成其他鍵即可切換，不需要改後面的 `fit`／`transform`。

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
自訂模型沿用 `GreyPCA(estimator=IncrementalPCA(3), top_k=2)`，由 estimator 自行指定成分數。
單獨取用時可匯入 `PCAAdapter`、`RobustPCA`、`RobustSparsePCA`、`AdvPCA`：
`PCAAdapter(3, method="pca")`、`method="sparse"`、`method="kernel"` 提供三種分解；
`RobustPCA().fit(data)` 提供低秩／稀疏矩陣；`RobustSparsePCA(3).fit(data)` 與 `AdvPCA(3, delta=0.05).fit(data)` 可直接降維。
這些獨立入口不自動加入 GRA，也不替你處理不同單位的縮放。

光譜用的 PCA 相關入口在 `greytheory.spectroscopy`：

| 入口 | 使用方式與條件 |
| --- | --- |
| `PoissonPCA` | `PoissonPCA(3).fit_transform(counts)`；非負計數、近似變異數穩定轉換 |
| `fit_mlpca` | `fit_mlpca(data, variances, n_components=3)`；每個數值都要有正的誤差變異數 |
| `fit_mnf` | `fit_mnf(cube, n_components=3)`；像素 × 像素 × 頻帶，依相鄰位置估計雜訊 |

`PoissonPCA` 也可傳給 `GreyPCA(estimator=PoissonPCA(3), standardize=False)`；計數資料不應先 z-score 成負數。

### 翹曲望小、剪切力望大

先在原始品質指標定義偏好，再評分。以下數值與範圍僅為示範，不是半導體規格。

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
`bounds` 是每欄的正規化下、上界；有工程依據時應固定使用。未提供時只用這次 `fit` 資料的最小、最大值，
會受離群值影響，不能拿不同擬合範圍的分數直接跨批次比較。新資料使用同一個 `quality.normalizer.transform(new_quality)`，
再呼叫 `grade_quality(benefits, weights=quality.weights, rho=quality.rho)`，不重新估計上下界。

`grade_quality` 以全 1 為理想序列，固定差異極值為 0 與 1，係數為 `rho / (1 - benefit + rho)`，再依權重平均。
這與 `grey_relation` 依當批候選計算極值的用途不同；固定界限與權重可讓相同樣本的品質分數不受其他候選增減影響。
分數不是良率、機率或合格判定。加權平均容許指標互補，必要的硬性規格應先另外檢查。

也可單獨使用 `BenefitNormalizer(directions, bounds=..., targets=...)` 的 `fit_transform`／`transform`。
方向接受 `"larger"`、`"smaller"`、`"target"`；例如膜厚接近指定值較好，可設
`directions=["smaller", "larger", "target"]`、`targets=[None, None, 100]`，並提供三欄的 bounds。
`target` 使用上下界到目標值的分段線性偏好，目標必須嚴格位於界限內。這不是 NIST desirability 的幾何平均評分。

防呆包含非有限值、方向／權重／欄位數錯誤、常數欄沒有可用界限，以及新資料超出擬合界限。
超界預設報錯；明確指定 `out_of_range="clip"` 才會飽和到界限，`normalizer.out_of_bounds(data)` 仍可查出原始超界位置。
帶欄名的資料也會核對名稱與順序。這裡處理偏好正規化；AdvPCA 的擾動半徑仍由 `delta` 控制。

### 主成分翻號與參考方向

**原始指標統一方向，不代表 PC1 就是越大越好的品質指標。** PCA 的正負號可翻轉，載荷也可能混合正負；
例如同時改善翹曲與剪切力的共同變化可能在一軸，而兩者的取捨在另一軸。把每個 PC 都設成望大會混淆這些含義。

`GreyPCA` 預設 `component_direction="either"`，會在同一候選批次比較每個成分的正反方向，取較高 GRA 分數，
避免任意翻號改變排名；常數成分排除並標為 NaN，`top_k=None` 保留所有可評分成分。
原始特徵的 `GreyFeatureSelector` 預設仍只比較原方向，可另外設 `direction="either"`。

有可信的品質參考時，可再要求輸出沿較接近參考的方向排列：

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
`training_process_features` 是製程／感測特徵，`training_quality_scores` 是對應樣本的品質參考。
翹曲、剪切力若用來產生品質目標，就不要再放回預測該目標的輸入欄位。
只有品質量測表時，直接使用 `rank_quality` 即可，不需要為了評分而強接 PCA。

`align_to_target` 的方向在訓練時固定，重建時自動還原；正反分數平手會報錯，避免假裝已辨認品質方向。
預設 `align_to_target=False`，不改輸出的正負方向。舊式有方向成分比較可設 `component_direction="positive"`。
對齊僅表示此 GRA 定義下較接近參考，不能保證物理單調、因果或跨批次穩定；主成分交換／旋轉也不是翻號防呆能解決的。

### 保留多少個成分

80–85% 可作為一般 PCA 的起始檢查門檻，無法保證保留同等比例的物理或品質資訊。
品質相關訊號可能藏在小變異方向；半導體製程還需檢查批次／晶圓／時間切分下的預測誤差與製程判讀。

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
小數 `n_components` 只支援一般 `method="pca"`。AdvPCA、SparsePCA 等不會冒用一般 PCA 的累積變異率。
重建涵蓋率是 `1 - SSE / SST`，在模型的輸入空間計算；`standardize=True` 時就是標準化空間。
對非一般 PCA 方法，數值可為負、也不保證隨成分增加而遞增。它不是一般 PCA 的變異貢獻率。
前綴報告使用同一個已訓練模型，將後面的成分補零；重新訓練較少成分可能產生不同模型。
GRA 篩選後可能低於原先門檻，應另看 `selected_coverage`；不會為了湊足門檻而偷偷多留成分。

完整合成範例含品質方向、依 lot 切分、AdvPCA／GRA、Ridge 預測與訓練均值基準：

```bash
.venv/bin/python examples/semiconductor_adv_quality.py
```

依製程選定方向、界限及權重後，只在訓練資料擬合轉換；`delta`、成分數和 `top_k` 也應在訓練側的驗證切分中選擇。
一般 PCA 可作為基準，AdvPCA 是否有益需用未參與選參的批次驗證，不能由方法名稱推定。

## 多維軌跡、圖片與 Grey 窗口特徵

目前可串接的流程是：

**原始數值資料 → 軌跡／圖片區塊特徵 → Grey 窗口特徵 → PCA／GRA → 一般迴歸或參考距離比對。**

| 輸入 | 資料格式 | 特徵入口 |
| --- | --- | --- |
| 光譜或一維序列 | `(樣本數, 點數)`；光譜需先對齊能量軸 | `GreyWindowFeatures` |
| 二維、三維或更多維的軌跡 | 每份為 `(點數, 維度)`，整批放在 list；各份可有不同點數 | `TrajectoryFeatures` → `GreyWindowFeatures` |
| 灰階／多通道圖片陣列 | `(樣本數, 高, 寬)` 或 `(樣本數, 高, 寬, 通道數)` | `ImagePatchFeatures` → `GreyWindowFeatures` |

以下是有兩筆、帶時間紀錄的二維軌跡。每列是依序量到的一個位置；維度可擴充為 3、5 或更多。

```python
from greytheory.features import Trajectory, TrajectoryFeatures, GreyWindowFeatures

path = Trajectory(
    points=[[0, 0], [1, 1], [2, 1], [10, 10], [11, 10], [12, 11]],
    timestamps=[0, 0.5, 1, 3, 3.5, 4],
    stroke_ids=[0, 0, 0, 1, 1, 1],
)
extractor = TrajectoryFeatures(n_points=16, include_time=True)
sequences = extractor.fit_transform([path])  # 一份軌跡也要放在 list 中。
windows = GreyWindowFeatures(window_size=8, stride=4, boundary_channel=-1)
features = windows.fit_transform(sequences)
print(features.shape)
print(windows.get_feature_names_out())

paths_3d = [[[0, 0, 0], [1, 2, 1], [2, 2, 3]]]
sequences_3d = TrajectoryFeatures(n_points=16).fit_transform(paths_3d)
paths_5d = [[[0, 0, 0, 0, 0], [1, 2, 1, 3, 2], [2, 2, 3, 4, 5]]]
sequences_5d = TrajectoryFeatures(n_points=16).fit_transform(paths_5d)
```

軌跡會保留位置、移動方向、每步距離、轉角與分筆標記。預設依每筆的路徑長度重取樣；
`include_time=True` 改依時間重取樣並計算速度，每份都必須有嚴格遞增的時間戳。
`stroke_ids` 連續值改變時視為新的一筆，每筆至少需兩個原始點，且 `n_points` 至少為筆數的兩倍。
抬筆間隔不計入移動距離或速度。`center=True` 預設移除起點位置；`scale=False` 預設保留空間尺度。
速度單位是座標單位／時間戳單位，轉角使用弧度。
若使用 `scale=True`，距離與速度也會變成正規化空間單位。座標欄位都是空間維度；時間和筆壓不要混成座標。
此版本沒有獨立的筆壓通道處理；照片本身也無法提供實際速度或筆壓。

`GreyWindowFeatures` 對各通道的完整窗口輸出幅度、平均、標準差、段內平均變化、GM 係數、
離散方程 RMSE、滿秩涵蓋率與 GM 涵蓋率，另附每窗的段數。它使用既有 AGO／求解核心，
不做未來外推或第二層預測。預設各窗各通道以最大絕對值縮放，原始幅度仍保留；
`gm_equation_rmse` 是離散方程殘差，不是未來預測誤差。
`gm_coverage` 為可擬合片段的點數比例；片段少於三點時，係數填零並以涵蓋率標出。
`gm_full_rank_coverage` 標出其中滿秩片段的點數比例。低涵蓋率或低滿秩涵蓋率時，不宜單看係數排名。
窗口不跨段擬合；`boundary_channel=-1` 讓最後一欄作為分段標記，該欄不當成一般通道建模。
`stride` 不可大於窗口，尾端會補一個完整窗口，因此邊緣仍可能重疊。

`ImagePatchFeatures(grid_shape=(4, 8))` 將圖片分成固定格子，保留各通道的平均、標準差、水平／垂直亮度變化。
它接收已讀入的陣列，沒有 OCR、裁字或顏料辨識。輸出最後一欄標記每列格子的起點；
接 Grey 窗口時同樣使用 `boundary_channel=-1`，避免把跨列位置當成連續訊號。
可用 `patch_bounds`、`windows` 與特徵名稱回查區域。預設軌跡、圖片與窗口都只記錄輸入結構，
PCA／GRA／迴歸仍須只用訓練資料擬合。

準備好訓練軌跡、對應的連續數值目標，以及獨立測試軌跡後，可接成：

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

此例中的 `train_paths`／`test_paths` 是上方 `Trajectory` 物件的 list，`train_targets` 是每份訓練軌跡的一個已知數值。
若沒有連續目標，就用 `GreyPCA(n_components=4, standardize=True)` 做無監督降維，再比較參考距離。
一般迴歸與距離比對不會自動變成筆跡作者或補畫判定；這兩種應用還需要專用資料、模型與驗證。
主成分 GRA 預設已比較正反方向；仍需要與不篩選的基準比較。

完整可執行範例含二維／三維／五維、分筆、圖片、光譜、迴歸與參考排名：

```bash
.venv/bin/python examples/grey_feature_pipeline.py
```

初次使用可先執行 `python3 run.py` 建立環境。範例的預測目標來自合成資料，沒有化學或鑑識準確率的含義。
來源程式：[多種輸入的完整流程](examples/grey_feature_pipeline.py)。

## Bruker 檔案讀取

```python
from greytheory.io.bruker import read_bcf, read_spx

spectrum = read_spx("reference.spx")
image = read_bcf("scan.bcf", lazy=True)
counts = image.get_pixel(y=0, x=0, detector=0)
energy_keV = image.energy_axes[0]
roi = image.get_spectra((0, 0, 2, 2), detector=0)
```

SPX 讀取結果包含計數、metadata，以及檔案提供的能量校正軸。
BCF 僅支援未壓縮 SFS 串流內、具有像素索引的 instructively packed 格式。
其他 packed 編碼、外層壓縮與 BCF v2 尚未支援。
計數使用 `uint64`；ROI 為 `(y0, x0, y1, x1)`，不包含上界。
各偵測器分別保留能量校正，能量軸不相容時，`sum_detectors` 會拒絕合併。

讀取測試會在暫存目錄自行產生小型 SPX／BCF 檔，不需要外部儀器資料包。
自產檔案只驗證已實作的格式，不能代表所有儀器或軟體版本；
使用自己的檔案前，仍需核對讀取結果。

## 製程與光譜分析工具

| 模組 | 提供功能 |
| --- | --- |
| `greytheory.semiconductor` | PLS 品質迴歸、動態／多維 PCA 監控、GRA 因素排序、拉丁超立方取樣與 GP 預期改善量建議點 |
| `greytheory.spectroscopy` | AsLS 基線校正、NMF、MCR-ALS、MNF、Anscombe Poisson PCA、固定變異數的加權低秩擬合、X 射線譜線查詢與固定峰位擬合 |

Poisson PCA 使用近似的變異數穩定轉換；`fit_mlpca` 假設誤差彼此獨立，且需要提供正的變異數。
XRF 峰值強度若要換算為濃度，還需要設備響應、標準品與基質效應等校正。

可執行範例：[時間序列](example.py)、[合成光譜](examples/hyperspectral_gra_pca.py)、
[依製造批次切分資料](examples/semiconductor_quality.py)。

## 批次執行

```python
from greytheory import GM0N, GM11, ModelQueue

if __name__ == "__main__":
    queue = ModelQueue()
    model = GM11(background_mode="corrected")
    for series in ([2, 3, 4, 5, 6], [3, 4, 6, 8, 11]):
        model.set_data(series)
        queue.append(model)  # 在加入當下自動深拷貝。

    queue.append(GM0N().set_data([[1], [2], [3], [4]], [2, 4, 7, 8]))
    results = queue.run(workers=2)
    print([m.predict(2) for m in results[:2]])
    print(results[2].influence_degrees)
```

`ModelQueue` 在建立佇列、`append`、`extend`、`insert`、單筆或切片賦值時，都會自動深拷貝。
同一個模型可反覆換入不同資料，每筆佇列項目仍保留加入當下的資料與設定。
讀取 `queue[0]` 會取得佇列內的模型，可直接調整；一般 Python `list` 則維持原本的參照行為。

`queue.run()` 會自動選擇各模型的計算方法，GM(0,N)、GM(1,N) 與 GM(1,1) 可以放在同一批。
預設循序執行，需要多程序時再指定 `workers`。結果維持輸入順序，所有工作成功後才更新佇列內的模型。
若使用 `inplace=False`，會回傳完成計算的新副本，佇列保持原狀。
已有模型清單時也可直接呼叫 `run_models(models, workers=2)`。
Windows 與 macOS 的多程序程式需保留上述 main guard。

## 開發與測試

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

測試涵蓋既有範例、數值邊界、降維目標函數、多維特徵與資料讀取。
測試輸入由程式自行產生，或包含於數值測試檔中，不需要另外下載資料包。
`scripts/verify_full_install.py` 可檢查安裝後的各項 API。

合成資料的實測紀錄放在 [benchmarks/results](benchmarks/results/)。
[核心效能測試](benchmarks/compare_core.py) 使用固定種子產生輸入；可選的 `--baseline` 需另提供舊版專案目錄。
[降維方法比較](benchmarks/compare_decomposition.py) 會產生乾淨與受干擾的資料，以相同切分比較未參與訓練資料的重建誤差。
現有時間紀錄來自 macOS arm64，會隨機器與執行環境改變；分數只描述這些合成測試情境。

舊有的 `GreyTheory`、`GreyGM*`、`add_pattern`／`add_patterns` 與 `grey.run.gm*` 仍可使用。
新程式可直接匯入 `GM0N`、`GM1N`、`GM11`、`ModelQueue` 與 `run_models`。

## 授權

GreyTheory 維持 [MIT 授權](LICENSE)。相依套件另外安裝，並保留各自授權；
詳見[第三方授權聲明](THIRD_PARTY_NOTICES.md)。

## 參考文獻與實作來源

以下區分實作依據、上游套件與相關研究。SCRAMBLE 列為延伸閱讀，目前沒有提供該 estimator。

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
