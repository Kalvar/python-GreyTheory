# GreyTheory

[English](README.md) | [繁體中文](README.zh-TW.md) | **日本語**

GreyTheory は、灰色システムによる時系列予測、灰色関連分析、スペクトル解析のための Python ライブラリです。
GM(0,N)、GM(1,N)、GM(1,1)、GRA、PCA 関連手法と、Bruker SPX・一部の BCF ファイルに対応しています。

## サンプルの実行

Python 3.11 以降が必要です。

プロジェクトのディレクトリで、次のコマンドを実行します。

```bash
python3 run.py
```

初回は環境の作成、依存パッケージのインストール、サンプルの実行まで自動で行います。
次回も同じコマンドを使えます。環境の有効化は不要です。
パッケージ設定の変更や依存パッケージの不足があれば、再インストールします。

## ライブラリとしてインストール

```bash
pip install greytheory
```

このコマンドは PyPI の公開版をインストールします。ここで紹介する 2.0 API は開発中です。
現在のソースを使う場合は、プロジェクトのディレクトリで `python -m pip install .` を実行してください。
必要な依存パッケージはまとめてインストールされます。

## 時系列予測

```python
from greytheory import GM11

model = GM11(background_mode="corrected").fit([223.3, 227.3, 230.5, 238.1, 242.9, 251.1])
print(model.predict(2))
```

`fit` はすぐに計算し、`set_data` はバッチ処理のためにデータだけを保存します。
`alpha`、`background_mode`、`ridge_alpha`、`rank_policy` はコンストラクターで指定できます。

`GM11(window_size=4, stride=1).fit(series).predict(2)` で二段階の移動ウィンドウ予測を使えます。
`predict` は元のモデルの結果や予測期間を変更せず、将来の値を返します。

`background_mode="corrected"` は `alpha*current + (1-alpha)*previous` を使います。
初期値の `"legacy"` は、両方の項に `alpha` を掛ける従来式を維持します。
AGO が `[2,5,10]`、`alpha=0.8` の場合、corrected は `[4.4,9.0]`、legacy は `[5.6,12.0]` です。
係数と診断は `coefficients`、`diagnostics` で確認できます。GM(1,1) には三つ以上の観測値が必要です。
結果の属性は fit またはバッチ処理の完了後に利用できます。

## 灰色関連分析（GRA）

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

各位置の係数を `(Δmin + rho*Δmax)/(Δ + rho*Δmax)` で求め、加重平均します。
`rho` は `(0,1]`、重みは非負です。`normalize` は `none`、`minmax`、`zscore`、`initial`、`mean` に対応します。
同じ候補集合から差の最大値・最小値を求めるため、候補を変更すると順位も変わることがあります。
スコア 1 が元の数値の一致を保証するわけではありません。

GM(0,N) と GM(1,N) は `GM0N().fit(X, y)`、`GM1N().fit(X, y)` で計算します。
`X` は `(観測数, 要因数)`、`y` は一次元の目的変数です。
`feature_names=["a", "b"]` で要因名を指定できます。
係数の絶対値による順位は、単位や共線性の影響を受けます。

## 特徴選択と PCA

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

標準化、特徴選択、分解は訓練データだけで fit します。
目的変数を渡すと GRA で成分を評価し、`top_k` 個を残します。`top_k=None` は評価可能な非定数成分を保持します。
目的変数を渡さなければ分解のみを行います。成分 GRA は既定で正負を同一候補集合で比較します。

| `method` | 手法 |
| --- | --- |
| `"pca"` | PCA（初期設定） |
| `"sparse"` | SparsePCA |
| `"kernel"` | KernelPCA |
| `"robust"` | 訓練データを PCP で分解してから PCA 投影を学習 |
| `"robust_sparse"` | Huber／elastic-net RobustSparsePCA |
| `"adv"` | AdvPCA |

各手法の設定は `method_params` に渡します。`estimator` で独自モデルを渡す場合は、
そのモデルが成分数を管理します。fit・transform と sklearn の clone に対応し、
入力の各観測に一行ずつ対応する二次元の密行列を返す必要があります。
渡されたモデルは複製してから学習します。`estimator` と `method`／`method_params` は併用できません。
`PoissonPCA` のように非負の計数が必要なモデルでは、`standardize=False` を使ってください。

学習済みモデルは `analysis.reducer`、GRA の全成分スコアは `component_scores`、
出力する成分の添字は `selected_components` で取得できます。出力は元の成分順を維持します。
逆変換では省略した成分をゼロで補います。KernelPCA の逆変換は近似です。
`explained_variance_ratio` は対応するモデルでのみ利用できます。

`"robust"` は PCP の低ランク訓練行列から投影を学習します。新しいデータの異常を自動除去する処理ではありません。
行列自体の分解には `RobustPCA` を単独で使えます。
RobustSparsePCA と AdvPCA は非凸最適化なので、収束診断も確認してください。

[手法を切り替える実行例](examples/grey_pca_methods.py)もあります。

### スコアの高い順に確認する

`GreyFeatureSelector` は元の特徴を、`GreyPCA` は複数の特徴をまとめた成分を評価します。
上の例は合成データで、一行が一サンプル、一列が一特徴、目的変数は各サンプルの既知の数値です。
同じ訓練データと学習済みの `analysis` を使って順位を確認できます。

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

最初の順位は元の特徴、次は分解後の成分です。GRA スコアは目的変数との関係を表し、
因果的重要度、予測精度、筆者の確率ではありません。目的変数がなければ
`analysis.component_scores` は `None` となり、成分の順位は計算できません。
特徴選択の効果は、別のテストデータで確認してください。

補彩の自動検出や筆者照合は未実装です。一般的な軌跡・画像特徴は下記で利用できますが、筆跡には文字領域の選択と専用の照合処理が必要で、
筆者 ID を連続値の目的変数として使うことはできません。実データと専門家による検証が必要です。

## PCA の選択と品質指標の方向

### 各 PCA の呼び出し

上の訓練／テスト行列で使えます。辞書のキーを選ぶと、同じ `fit`／`transform` で切り替えられます。
AdvPCA は `analysis.reducer.converged`（外側）と `analysis.reducer.inner_converged`（最終内側）の両方を確認します。

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
カスタムモデルは `GreyPCA(estimator=IncrementalPCA(3), top_k=2)` と指定します。
単独利用には `PCAAdapter`、`RobustPCA`、`RobustSparsePCA`、`AdvPCA` があります。
`PCAAdapter(3, method="pca")` の method は `"pca"`、`"sparse"`、`"kernel"`。
`RobustPCA().fit(data)` は低ランク／スパース行列、`RobustSparsePCA(3).fit(data)` と
`AdvPCA(3, delta=0.05).fit(data)` は単独の分解です。GRA や単位のスケーリングは別途指定します。

`greytheory.spectroscopy` には以下もあります。

| 入口 | 呼び出しと入力 |
| --- | --- |
| `PoissonPCA` | `PoissonPCA(3).fit_transform(counts)`；非負の計数、近似変換 |
| `fit_mlpca` | `fit_mlpca(data, variances, n_components=3)`；各値に正の誤差分散 |
| `fit_mnf` | `fit_mnf(cube, n_components=3)`；空間 × 空間 × バンド、隣接画素から雑音を推定 |

計数には `GreyPCA(estimator=PoissonPCA(3), standardize=False)` も使えます。負数になる z-score は適用しません。

### 小さいほどよい指標と大きいほどよい指標

反りを小さく、せん断力を大きくしたい場合は、元の品質値で方向を定義します。以下の値と範囲は説明用です。

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
`bounds` は列ごとの正規化下限／上限です。省略時は fit データの最小／最大で、外れ値に依存します。
異なる範囲で fit したスコアはロット間で直接比較できません。新しい値には同じ
`quality.normalizer.transform(new_quality)` と `grade_quality(benefits, weights=quality.weights, rho=quality.rho)` を使います。

理想を全 1、差の極値を固定の 0 と 1 として、`rho / (1 - benefit + rho)` の加重平均を計算します。
これは候補集合から極値を得る `grey_relation` と異なり、固定範囲・重みなら他の候補を追加しても同じ値です。
歩留まり、確率、合否ではありません。指標間の補償が可能なので、必須規格は別に確認します。

`BenefitNormalizer(directions, bounds=..., targets=...)` の `fit_transform`／`transform` も使えます。
方向は `"larger"`、`"smaller"`、`"target"`。目標膜厚なら、例えば
`directions=["smaller", "larger", "target"]`、`targets=[None, None, 100]` と三列分の bounds を指定します。
目標は上下限の内側に置き、区分線形のピークを使います。NIST の幾何平均 desirability とは別の評点です。

NaN／無限大、方向・重み・列数の不一致、範囲のない定数列、範囲外の新値を拒否します。
明示的な `out_of_range="clip"` で飽和させた場合も、`normalizer.out_of_bounds(data)` で元の逸脱を確認できます。
列名のある入力は順序も確認します。これは正規化で、AdvPCA の `delta` は別設定です。

### 主成分の符号と参照方向

**元の列を「大きいほどよい」に揃えても、PC1 が品質の良さを示すとは限りません。**
正負の荷重が混在し、成分の符号も反転できます。`GreyPCA` の既定値 `component_direction="either"` は
正負を同一 GRA 候補集合で比較し、高いスコアを採用します。定数成分は NaN として除外し、
`top_k=None` は評価可能な全成分を保持します。元の特徴の `GreyFeatureSelector` は有方向の既定値を保持し、
必要なら `direction="either"` を指定します。

意味のある品質参照がある場合は、出力の符号を訓練時に揃えることもできます。

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
製造／センサ特徴と品質応答を分けます。反り・せん断力から品質目標を作った場合、それらを目標予測の入力へ戻さないでください。
品質表だけなら `rank_quality` で十分です。符号は fit 時に固定し、逆変換で戻します。
正負の評点が同点なら対処を求めて停止します。標準の `align_to_target=False` は元の符号を保持します。
従来の有方向比較は `component_direction="positive"` です。参照への整合は物理的な単調性や因果を保証せず、成分の交換・回転にも対応しません。

### 保持する成分数

80–85% は通常 PCA の検討開始点で、同じ割合の物理情報・品質情報を保証しません。
小さな分散にも品質情報があり得ます。

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
小数の `n_components` は通常の `method="pca"` のみです。AdvPCA／SparsePCA に通常 PCA の累積寄与率を当てはめません。
再構成カバレッジは `1 - SSE / SST`。モデル入力空間で計算し、標準化時は標準化空間です。
負値や非単調な増減もあり、説明分散とは異なります。同一モデルで後続成分をゼロにする検査で、成分数を減らして再学習した結果とは限りません。
GRA 後は元の閾値を下回る場合があるため `selected_coverage` も確認します。自動で成分を追加しません。

ロットを分けた合成データの実行例です。

```bash
.venv/bin/python examples/semiconductor_adv_quality.py
```

方向・範囲・重みは工程知識で設定し、`delta`、成分数、`top_k` は訓練側で選びます。
未使用ロット／ウエハ／期間で通常 PCA と比較してから判断してください。

## 多次元軌跡と Grey ウィンドウ特徴

**数値データ → 軌跡／画像特徴 → Grey ウィンドウ特徴 → PCA／GRA → 回帰または参照距離の比較。**

| 入力 | 形式 | 入口 |
| --- | --- | --- |
| スペクトル／一次元系列 | `(サンプル数, 点数)`。エネルギー軸を先に揃える | `GreyWindowFeatures` |
| 二次元・三次元以上の軌跡 | 各要素が `(点数, 次元数)` の list。点数は異なっても可 | `TrajectoryFeatures` → `GreyWindowFeatures` |
| グレースケール／多チャネル画像 | `(サンプル数, 高さ, 幅[, チャネル数])` の配列 | `ImagePatchFeatures` → `GreyWindowFeatures` |

```python
from greytheory.features import Trajectory, TrajectoryFeatures, GreyWindowFeatures

path = Trajectory(
    points=[[0, 0], [1, 1], [2, 1], [10, 10], [11, 10], [12, 11]],
    timestamps=[0, 0.5, 1, 3, 3.5, 4],
    stroke_ids=[0, 0, 0, 1, 1, 1],
)
extractor = TrajectoryFeatures(n_points=16, include_time=True)
sequences = extractor.fit_transform([path])
windows = GreyWindowFeatures(window_size=8, stride=4, boundary_channel=-1)
features = windows.fit_transform(sequences)
print(features.shape)
print(windows.get_feature_names_out())

paths_3d = [[[0, 0, 0], [1, 2, 1], [2, 2, 3]]]
sequences_3d = TrajectoryFeatures(n_points=16).fit_transform(paths_3d)
paths_5d = [[[0, 0, 0, 0, 0], [1, 2, 1, 3, 2], [2, 2, 3, 4, 5]]]
sequences_5d = TrajectoryFeatures(n_points=16).fit_transform(paths_5d)
```

位置、移動方向、距離、曲がり角、ストローク開始を保持します。標準では各ストロークを弧長で再標本化します。
`include_time=True` は厳密に増加する時刻が必要で、時間で再標本化して速度も計算します。
連続する整数 `stroke_ids` の変更を境界とし、各ストロークには元の点・出力点が各二点以上必要です。
ペンを離した間隔は移動距離・速度に含めません。`center=True` は始点を除き、`scale=False` は空間尺度を保持します。
速度は座標単位／時刻単位、角度はラジアンです。
`scale=True` の距離・速度は正規化した空間単位です。座標列に時刻や筆圧を混ぜないでください。
専用の筆圧チャネル処理は未実装で、静止画像から実際の速度や筆圧は取得できません。

Grey ウィンドウは振幅、平均、標準偏差、区間内変化、GM 係数、離散方程式 RMSE、満ランクの割合、
GM を計算できた点の割合、区間数を返します。各窓・チャネルを最大絶対値で正規化し、元の振幅も保持します。
既存の AGO／ソルバーを使いますが、未来予測や二段階予測は行いません。RMSE は未来予測の誤差ではありません。
三点未満の断片は係数ゼロ・`gm_coverage` ゼロとなります。`gm_full_rank_coverage` も確認し、
低い割合の係数だけで判断しないでください。`boundary_channel=-1` で最終チャネルを境界として扱い、
境界をまたぐ GM 計算や差分を避けます。stride は窓幅以下とし、末尾にも完全な窓を追加します。

`ImagePatchFeatures(grid_shape=(4, 8))` は各セルのチャネル別平均・標準偏差・水平／垂直変化を返します。
画像は配列で入力し、OCR や文字分割は行いません。最終チャネルが格子の行開始を示すため、
下流で同じく `boundary_channel=-1` を使ってください。`patch_bounds`・`windows`・特徴名で位置を確認できます。

訓練軌跡 `train_paths`、各軌跡の既知の連続値 `train_targets`、別のテスト軌跡 `test_paths` を用意したら：

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

軌跡は上記 `Trajectory` の list です。連続値がなければ `top_k` なしの PCA で参照距離を比較します。
PCA／GRA／回帰は訓練データだけで fit し、成分選択なしの基準とも比較してください。
これらの一般的な回帰・距離比較は、筆者や補彩の判定モデルではありません。

二次元／三次元／五次元、画像、スペクトル、回帰・参照順位の[実行例](examples/grey_feature_pipeline.py)：

```bash
.venv/bin/python examples/grey_feature_pipeline.py
```

必要なら先に `python3 run.py` で環境を準備します。すべての入力は生成データです。
合成データの誤差は、化学・鑑識精度の検証ではありません。

## Bruker ファイルの読み込み

```python
from greytheory.io.bruker import read_bcf, read_spx

spectrum = read_spx("reference.spx")
image = read_bcf("scan.bcf", lazy=True)
counts = image.get_pixel(y=0, x=0, detector=0)
energy_keV = image.energy_axes[0]
roi = image.get_spectra((0, 0, 2, 2), detector=0)
```

SPX は計数、メタデータ、校正値があればエネルギー軸を返します。
BCF は非圧縮 SFS 内の索引付き instructively packed 形式に限ります。
他の符号化、外部圧縮、BCF v2 は未対応です。計数は `uint64`、ROI は上限を含まない `(y0, x0, y1, x1)` です。
検出器ごとの校正を保持し、異なるエネルギー軸の `sum_detectors` は拒否します。

テストは一時ディレクトリに小さな SPX／BCF を生成し、外部データを必要としません。
生成ファイルの検証は、すべての装置・ソフトの互換性を保証しません。
手元の測定ファイルでは、読み込み結果を確認してください。

製造工程向け PLS・PCA 監視・実験計画は `greytheory.semiconductor`、
基線補正、NMF、MCR-ALS、MNF、Poisson PCA、X 線情報は `greytheory.spectroscopy` にあります。
[合成スペクトル](examples/hyperspectral_gra_pca.py)と[製造ロットによる検証](examples/semiconductor_quality.py)の実行例があります。

## バッチ処理

```python
from greytheory import GM0N, GM11, ModelQueue

if __name__ == "__main__":
    queue = ModelQueue()
    model = GM11(background_mode="corrected")
    for series in ([2, 3, 4, 5, 6], [3, 4, 6, 8, 11]):
        model.set_data(series)
        queue.append(model)  # 追加時に自動で深いコピーを保存します。

    queue.append(GM0N().set_data([[1], [2], [3], [4]], [2, 4, 7, 8]))
    results = queue.run(workers=2)
    print([m.predict(2) for m in results[:2]])
    print(results[2].influence_degrees)
```

`ModelQueue` は追加・置換時にモデルを深くコピーします。同じモデルを別のデータで再利用しても、
既存の項目は変わりません。通常の Python リストには、この自動コピー機能はありません。
`queue.run()` はモデルの種類を自動判定し、入力順に結果を返します。初期設定は逐次実行です。
`workers=2` でプロセス並列処理、`inplace=False` で元のキューを変えずに結果のコピーを取得できます。
すべての処理が成功してからキュー内のモデルを更新します。
既存のリストには `run_models(models)` も使えます。

従来の `GreyTheory` と `GreyGM*` も引き続き利用できます。

## 開発とテスト

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

入力は生成データまたは同梱の数値データで、外部データのダウンロードは不要です。
合成データの測定結果は [benchmarks/results](benchmarks/results/) にあります。
[コアの比較](benchmarks/compare_core.py)と[降次元の比較](benchmarks/compare_decomposition.py)で入力を生成できます。
既存の時間記録は macOS arm64 の値で、環境に依存します。スコアはこれらの合成データに限られます。

## ライセンス

GreyTheory は [MIT License](LICENSE) です。依存パッケージは別途インストールし、
それぞれのライセンスが適用されます。[Third-party notices](THIRD_PARTY_NOTICES.md) を参照してください。

## 参考文献と実装

実装手法と参考文献の一覧は、[英語版 References](README.md#references) または
[繁體中文版](README.zh-TW.md#參考文獻與實作來源)をご覧ください。主な資料は以下の通りです。

- Liu & Lin (2011), [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2).
- Candès et al. (2011), [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395).
- Erichson et al. (2020), [Sparse Principal Component Analysis via Variable Projection](https://arxiv.org/abs/1804.00341).
- Vävinggren et al. (2026), [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553).
- Camp (2019), [pyMCR / MCR-AR](https://doi.org/10.6028/jres.124.018).
- [scikit-learn](https://scikit-learn.org/stable/modules/decomposition.html)、[Spectral Python](https://www.spectralpython.net/algorithms.html)、[pybaselines](https://pybaselines.readthedocs.io/en/latest/algorithms/whittaker.html)。

- NIST/SEMATECH. [Multiple responses: the desirability approach](https://www.itl.nist.gov/div898/handbook/pri/section5/pri5322.htm)。方向と目標設定の参考。GRA の加重平均は幾何平均 desirability と異なります。
