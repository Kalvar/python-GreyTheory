# 使い方と API

[English](guide.md) | [繁體中文](guide.zh-TW.md) | **日本語**

以下のコマンドはプロジェクトのルートで実行します。[ドキュメント一覧](README.ja.md) · [プロジェクト概要](../README.ja.md)。

GreyTheory は、灰色予測、灰色関連分析（GRA）、PCA を使える Python ツールキットです。
時系列の予測、特徴量の絞り込み、スペクトルや測定データの比較に使えます。

| やりたいこと | 使う機能 |
| --- | --- |
| 次の数値を予測する | [GM(1,1)](#時系列予測) |
| 二段階のウィンドウ予測 | [Convolution](#convolution二段階のウィンドウ予測) |
| 特徴と目標値を比較する | [GRA](#灰色関連分析gra) |
| 次元を減らして成分を選ぶ | [GreyPCA](#pca-と特徴選択) |
| 大小の好ましい方向を揃えて評点を出す | [品質スコア](#品質スコア) |
| 軌跡や画像から特徴を作る | [特徴抽出](#軌跡画像ウィンドウ特徴) |
| PNG／JPG を読んで比較する | [画像ファイル](#画像ファイルを読み込む) |
| Bruker ファイルを読む | [SPX／BCF](#bruker-ファイルの読み込み) |
| 合成スペクトルと AI 筆跡を試す | [二つのデモ](#合成-xrf-と-ai-筆跡デモ) |

## まず動かす

Python 3.11 以降が必要です。ダウンロードまたは clone 後、プロジェクト内で実行します。

```bash
python3 run.py
```

> [!TIP]
> 初回に `.venv` を作り、依存パッケージを入れてサンプルを実行します。
> 次回も同じコマンドで使えます。環境の有効化は不要です。

自分のプログラムで使う場合は、その Python 環境でプロジェクト内からインストールします。

```bash
python -m pip install .
```

## ブラウザーで光スペクトル・DOE・画像を分析

[examples/workbench/index.html](../examples/workbench/index.html) は直接開いてプレビューできます。内蔵例は Python で事前計算した結果です。パラメーター変更を即時計算したようには表示しません。

`workbench` は GreyTheory の分析画面を開きます。スペクトル、DOE データ、筆跡画像を読み込み、手法とパラメーターを選び、グラフや特徴順位を確認できます。初回は `.venv` を作成し、分析・画面用の依存パッケージをインストールします。次回からは同じ環境を使います。

```bash
python3 run.py workbench
```

Windows は `python run.py workbench`。環境を準備済みの場合：

```bash
python -m examples.workbench.desktop
```

画面は繁体字中国語です。`examples/workbench/` にあり、インストールされる本体とは別です。pywebview が プロジェクトの HTML と Python を直接つなぎます。HTTP server や待ち受けポートは使いません。ブラウザーで直接開くとプレビューとなり、新しい計算はデスクトップかファイル交換を使います。グラフは SVG と JavaScript を使い、CDN は不要です。

1. PVD または CVD を読み込みます。
2. `thickness_nm` などの目標を選びます。初期選択は工程入力だけで、他の測定結果は入力に含みません。
3. 「執行分析」で投影と特徴順位を表示します。上位の特徴を選ぶボタンで絞り込み、PCA を変更して再実行でき、JSON も保存できます。
4. Bruker ファイルは `data/test/` に置いて画面を更新するか、CSV／SPX／BCF を選択します。M4 の `minBcf.bcf` は検出器 0 と 1 を別々に分析します。SPX の索引で測定または背景を選択します。小数を含む背景は推定強度で、元の光子計数ではありません。未対応 BCF はエラーを表示します。
5. 「圖片比較」で AI 筆跡 demo、または画像 1 枚と参照画像 3–30 枚を比較します。距離は特徴の類似度で、作者の判定確率ではありません。

> [!NOTE]
> 目標あり：元の入力特徴を GRA で順位付けします。PCA を切り替えても、この GRA 順位は変わりません。目標なし：保持した主成分との最大絶対相関を表示します。GRA や因果的重要度ではありません。主成分の符号は品質の良否を意味せず、画面では PC を品質スコアとして使いません。

光スペクトルは非負エネルギーの通道を最大 64 区間に合計し、初期設定では各スペクトルの保持区間の総計数で正規化します。表示曲線は元の計数です。SPX 1 本は表示できますが、PCA は 3 件以上が必要です。検出器のエネルギー校正が異なる場合があるため合算しません。DOE は列ごとに標準化します。PCA 手法によって寄与率が得られない場合があります。

[模擬 DOE](../data/demo/doe) は **合計 30 件（PVD 15 件、CVD 15 件）**。各工程は 12 個の層化ランダム設定と中心点の反復 3 件です。完全要因計画や直交表ではありません。PVD は電力・圧力・温度・バイアス・Ar 流量・時間から膜厚などを生成し、CVD は温度・圧力・ガス流量・電漿電力・時間から膜厚などを生成します。

固定乱数と簡単な式を使った架空データで、実機のレシピではありません。式・範囲・単位（列名）は [manifest](../data/demo/doe/manifest.json) に記録しています。工程は別々に分析してください。独立テストを行っていないため、順位は予測精度や因果関係を示しません。膜厚や屈折率には目標値と許容範囲が必要で、GRA の参照に選んでも「大きいほど良い」という意味にはなりません。

再生成：

```bash
python -m examples.workbench.doe
```

Python から直接実行する例：

```python
from examples.workbench.analysis import analyze, read_spectrum_file

# ローカルの M4 ファイルが必要です。パッケージには含まれません。
data = read_spectrum_file("data/test/m4_tornado/minBcf.bcf", detector=0)
result = analyze(data, {"method": "pca", "components": 2})
print(result["ranking"][:5])  # 目標なし：主成分との関連順位
```

### その他の応用例とパラメーター

「應用實驗室」で情境を選び、設定を変更して実行します。デスクトップでは毎回 Python が計算し、直接 HTML を開く場合は事前計算のプレビューを表示します。入力・パラメーター・結果を JSON で保存できます。

| 応用例 | 操作と出力 |
| --- | --- |
| 配送経路 | 3–8 地点、距離・時間・遅延の重み。全順序を比較し、経路をアニメーション表示 |
| ドライバー配車 | 人数・注文数と重み。積載量・技能・利用可能時間を先に確認し、未割当も表示 |
| 美術品の領域差 | 6 種類の PCA、成分数、閾値。別の参照マップで学習し、再構成誤差と模擬正解を表示 |
| 注文数予測 | GM11／Convolution、alpha、ridge、窓、予測期間。最後の 4 期を保留して評価し、将来を予測 |
| 多次元軌跡 | 2D–4D、再標本化、Grey 窓、PCA。12 本で学習し、6 本は変換のみ |
| 光スペクトル | NMF、MCR-ALS、MNF、MLPCA、AsLS、ピーク fitting、xraylib 線。各方法に合う合成入力を使用 |
| 半導体 | QualityPLS、Q/T²、rank_features、GP 候補、LHS。PLS は 11 件で学習し 4 件を保留 |
| 画像比較 | 6 種類の PCA と専用パラメーター、AI 筆跡／自分の画像。作者を断定する機能ではありません |

最初のページでは GreyPCA、GRA、GM0N、GM1N、品質評価、Grey 窓→PCA、元の計数向け PoissonPCA を選択できます。GM0N／GM1N は行順序と累積値に依存するため、意味のある順序か確認が必要です。順序のない DOE は GRA／PCA を使ってください。品質モードは特徴ではなく試料を順位付けし、各列の望大／望小／目標、上下限、重みを指定します。

Kernel PCA は kernel／gamma／degree、疎な PCA はペナルティ、AdvPCA は adaptive／manual delta・平滑・反復回数を表示します。GRA は rho・尺度処理・方向を指定し、rho はまず `0.5`。GreyPCA の目標に基づく主成分選択は `0` で無効です。成分の GRA と入力特徴の順位は分けて表示します。

> [!NOTE]
> 配送は全列挙、配車はハンガリー法を使い、Grey は選好を評価します。架空の平面座標で、実道路・複数車両・法定労働時間・厳密な時間枠は未対応です。美術品の異常は調査の手掛かりで、補彩や年代の証明ではありません。筆跡距離も作者を特定せず、合成例の結果は実務精度を意味しません。

[合成入力](../data/demo/scenarios/synthetic_inputs.json) は地点、架空のドライバーと注文、注文時系列、美術品の参照／観測光スペクトルです。実在の個人・住所・作品は含みません。再生成：

```bash
python -m examples.workbench.scenarios
```

Python から直接実行：

```python
from examples.workbench.scenarios import run_scenario

result = run_scenario("routes", {"stops": 6, "objective": "grey"})
print(result["tables"][0]["rows"])
```

GUI 依存を使わない場合は HTML から計算要求を保存します。

```bash
python3 run.py workbench --request greytheory-request.json
```

生成された `greytheory-request.result.json` を HTML に読み込みます。Python の分析依存だけで実行し、server は不要です。即時モードはウィンドウを閉じて終了します。Bruker 生データは Git 対象外です。

## 時系列予測

`fit` に観測値を渡し、`predict(2)` で次の二点を予測します。

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(background_mode="corrected").fit(series)
print(model.predict(2))
print(model.metrics)
```

三点以上のデータが必要です。二段階のウィンドウ予測は下の Convolution を参照してください。

係数は `model.coefficients`、計算の診断は `model.diagnostics` で確認できます。
`set_data` はバッチ処理用にデータを保存します。`reset()` は結果を消し、
`reset(clear_data=True)` はデータも消します。

<details>
<summary>背景値、正則化、誤差</summary>

`background_mode="corrected"` は `alpha * current + (1-alpha) * previous` を使います。
既定の `"legacy"` は両項に `alpha` を掛けます。`alpha=0.5` なら同じです。

最小二乗法で解き、`ridge_alpha` で正則化を指定できます。
`rank_policy="raise"` は係数を一意に推定できない場合にエラーを返します。
診断にはランク、条件数、残差が含まれます。

`horizon=0` は過去のデータだけを当てはめます。観測値がゼロなら相対誤差は `None` になりますが、
MAE と RMSE は使えます。`predict` は保存済みの結果を変更しません。

</details>

## Convolution：二段階のウィンドウ予測

`window_size` で convolution を有効にします。各窓の GM(1,1) で次の値を予測し、その結果を二段目の GM(1,1) に渡します。

**元の系列 → 各窓の予測 → 二段目の GM(1,1) → 将来の値**

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(window_size=4, stride=1, background_mode="corrected").fit(series)
print(model.predict(2))
```

| 設定 | 意味 |
| --- | --- |
| `window_size=4` | 一窓に四点。`None` は通常の GM11 |
| `stride=1` | 一点ずつ移動 |
| `predict(2)` | 将来の二点を予測 |
| `correction_mode="legacy"` | 既定の窓の誤差補正。`"none"` で無効化 |

二段階の予測には三つ以上の窓を用意します。上の六点、窓幅四、移動幅一なら三つの窓になります。
`coefficients` と `metrics` は最後の段の結果です。元の方式と同じく、最後の窓に末尾の余ったデータを含む場合があります。

通常の予測との比較を実行できます。

```bash
.venv/bin/python examples/convolution_forecast.py
```

出力例：

```text
Ordinary GM11, next two values: [256.5532, 263.1223]
Convolution GM11, next two values: [265.9278, 274.0119]
```

`GreyWindowFeatures` は PCA／GRA 向けに窓の特徴を作る機能で、二段目の予測は行いません。

## 複数要因のモデル

`GM0N` と `GM1N` は複数の要因と一つの目標値を扱います。各行が観測、各列が要因です。

```python
from greytheory import GM0N

factors = [[.75, .5], [1.22, 1], [.2, .7], [1, .66], [1, 1], [1, .5]]
targets = [1, 1, 1, 1, 1, 1]
model = GM0N().fit(factors, targets, feature_names=["factor_a", "factor_b"])
print(model.coefficients)
print(model.influence_degrees)
```

GM(1,N) は `GM1N().fit(factors, targets)` です。要因名は省略できます。
`influence_degrees` は係数の絶対値による順位なので、単位や共線性の影響を受けます。
目標との近さを比較する場合は GRA を使います。

## 灰色関連分析（GRA）

参照系列と比較する系列を渡します。選んだ正規化のもとで参照に近いほど、高いスコアになります。

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

`normalize` は `none`、`minmax`、`zscore`、`initial`、`mean` から選べます。
`greytheory.analysis` の `GreyGRA` を使い、`.score(...)` や `.rank(...)` を呼ぶこともできます。

候補の追加・削除でスコアや順位が変わる場合があります。スコアは灰色関連度で、因果や予測精度を示すものではありません。

<details>
<summary>GRA の式</summary>

絶対差 `Δ` から `(Δmin + rho*Δmax) / (Δ + rho*Δmax)` を計算し、加重平均を取ります。
`rho` は `(0, 1]`、重みは非負です。差の極値は同じ候補集合から求めます。
スコアが 1 でも、元の数値が完全に一致するとは限りません。

</details>

## PCA と特徴選択

`GreyFeatureSelector` は元の列を選びます。`GreyPCA` は次元を減らし、GRA で目標に近い成分を選びます。
以下は合成データの例です。

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

`n_components` は分解の成分数、`top_k` は GRA が残す数です。
次元削減だけなら `fit(train_factors)` とし、目標値を省略します。
> [!IMPORTANT]
> **先に訓練・テストデータを分けます。**
> 変換の `fit` は訓練データで行い、テストデータには `transform` だけを使います。

### PCA を切り替える

`method` を変え、各手法の設定を `method_params` に渡します。

| `method` | 手法 | `method_params` の例 |
| --- | --- | --- |
| `"pca"`（既定） | 通常の PCA | `{"whiten": True}` |
| `"sparse"` | SparsePCA | `{"alpha": 0.1}` |
| `"kernel"` | KernelPCA | `{"kernel": "rbf", "gamma": 0.1}` |
| `"robust"` | PCP の低ランク行列から PCA 射影を作成 | `{"tol": 1e-6}` |
| `"robust_sparse"` | Huber／elastic-net RobustSparsePCA | `{"alpha": 0.1, "kappa": 1.0}` |
| `"adv"` | AdvPCA | `{"delta": 0.01, "max_iter": 1000}` |

AdvPCA に切り替える例です。

```python
analysis = GreyPCA(
    3, method="adv", method_params={"delta": 0.01, "max_iter": 1000},
    top_k=2, standardize=True,
).fit(train_factors, train_targets)
components = analysis.transform(test_factors)
print(analysis.reducer.converged)
print(analysis.reducer.inner_converged)
```

AdvPCA は外側と最終内側の両方の収束を確認してから結果を評価します。
手法の比較は [grey_pca_methods.py](../examples/grey_pca_methods.py) を参照してください。

sklearn 互換モデルを渡すこともできます。この場合はモデル側で成分数を設定します。

```python
from sklearn.decomposition import IncrementalPCA

analysis = GreyPCA(
    estimator=IncrementalPCA(n_components=4, batch_size=12), top_k=2,
).fit(train_factors, train_targets)
```

モデルは `fit`、`transform`、sklearn clone に対応し、一観測一行の二次元密行列を返す必要があります。
`estimator` と `method`／`method_params` はどちらか一方を使います。

### 選んだ成分と順位を見る

`component_scores` が GRA スコア、`selected_components` がゼロ始まりの選択インデックスです。
出力は元の成分順を保ちます。スコアの高い順に見るには：

```python
valid = np.flatnonzero(np.isfinite(analysis.component_scores))
ranking = valid[np.argsort(-analysis.component_scores[valid], kind="stable")]
for index in ranking:
    print(f"PC{index + 1}", float(analysis.component_scores[index]))
```

元の列のスコアは `selector.scores` です。目標値がなければ `component_scores` は `None` です。
この選択は連続値の目標向けです。筆者 ID などのカテゴリには別の分類・照合モデルが必要です。

### 成分数を決める

通常の PCA は、残したい累積寄与率を小数で指定できます。例えば 85%：

```python
ordinary = GreyPCA(n_components=0.85, method="pca", standardize=True).fit(train_factors)
print(ordinary.n_components_fitted)
print(ordinary.explained_variance_ratio.sum())

report = analysis.reconstruction_report(train_factors, threshold=0.85)
print(report.prefix_coverage)
print(report.first_prefix_at_threshold)
print(report.selected_coverage)
```

小数の `n_components` は通常 PCA のみです。AdvPCA や SparsePCA は再構成カバレッジを確認します。
80–85% は出発点です。小さい分散にも品質の情報があり得るため、別のデータで予測性能を確認してください。

<details>
<summary>分解だけを使う場合とスペクトル PCA</summary>

以下は `greytheory.analysis` から読み込みます。GRA は自動で加わりません。

| 呼び出し | 用途 |
| --- | --- |
| `PCAAdapter(3, method="pca")` | 通常 PCA |
| `PCAAdapter(3, method="sparse", alpha=0.1)` | SparsePCA |
| `PCAAdapter(3, method="kernel", gamma=0.1)` | KernelPCA |
| `RobustPCA().fit(data)` | `low_rank` と `sparse` 行列を取得 |
| `RobustSparsePCA(3).fit(data)` | Huber／elastic-net の疎な射影 |
| `AdvPCA(3, delta=0.05).fit(data)` | AdvPCA の射影 |

以下は `greytheory.spectroscopy` から読み込みます。

| 呼び出し | 入力 |
| --- | --- |
| `PoissonPCA(3).fit_transform(counts)` | 非負の計数。近似的な分散安定化を使用 |
| `fit_mlpca(data, variances, n_components=3)` | 誤差は独立で、各要素に正の誤差分散が必要 |
| `fit_mnf(cube, n_components=3)` | 空間 × 空間 × バンド。隣接画素から雑音を推定 |

GRA と組み合わせる場合は `GreyPCA(estimator=PoissonPCA(3), standardize=False)` とします。
計数には、負値を作る標準化を適用しないでください。

</details>

<details>
<summary>成分の符号と再構成の注意点</summary>

`component_direction="either"` は同じ GRA 集合で正負を比べ、高い方を使います。
定数成分は除外され、`top_k=None` は評価可能な全成分を残します。
品質目標に符号を揃えるには `align_to_target=True` を指定します。同点ならエラーです。
物理的な単調性や、再学習による成分の交換・回転を保証するものではありません。

再構成カバレッジは `1 - SSE / SST` です。標準化したモデルでは標準化空間で計算し、
通常 PCA 以外では負値や非単調な変化もあり得ます。GRA 後の値は `selected_coverage` で確認します。
`first_prefix_at_threshold=None` は、評価した成分の組がどれも閾値に達しなかったことを示します。

KernelPCA の逆変換は近似です。`"robust"` は PCP の訓練結果から射影を作り、新しい行は再度 PCP 処理しません。
AdvPCA と PCP は目的が異なります。詳しくは[英語版](guide.md#pca-and-feature-selection)を参照してください。

</details>

## 品質スコア

反りは小さく、せん断力は大きくしたい場合、まず 0–1 の値に揃えて加重 GRA スコアを計算します。

```python
from greytheory.analysis import rank_quality, grade_quality

quality = rank_quality(
    [[80, 10], [40, 20], [20, 25]],  # 行: サンプル、列: 反り・せん断力
    directions=["smaller", "larger"],
    bounds=[(0, 100), (0, 30)],      # 説明用の範囲。工程に合った値に変更
    weights=[0.5, 0.5],
)
print(quality.normalized_values)
print(quality.scores)
print(quality.ranking)  # [2, 1, 0]: よい順の行インデックス

new_benefits = quality.normalizer.transform([[30, 22]])
new_quality = grade_quality(new_benefits, weights=quality.weights, rho=quality.rho)
print(new_quality.scores)
```

`directions` は `larger`、`smaller`、`target` です。
膜厚を 100 に近づけたい場合は、`greytheory.analysis` の
`BenefitNormalizer(["target"], bounds=[(80, 120)], targets=[100])` に
`fit_transform` または `transform` を使います。

`bounds` は正規化の範囲です。省略時は訓練データの最小・最大を使います。

> [!NOTE]
> **ロット間では同じ範囲、重み、`rho` を使います。**
> 他のサンプルを追加しても、同じ行の品質スコアが変わらないようにします。

範囲外は既定でエラーです。`out_of_range="clip"` で境界に丸めても、
`normalizer.out_of_bounds(data)` で元の逸脱を確認できます。

> [!WARNING]
> **品質スコアは歩留まりや合否を示しません。**
> 設定した好みに沿った評点です。必須規格は別に確認してください。

元の列を大きいほどよい値に揃えても、すべての主成分が同じ性質になるわけではありません。

工程の予測例は [semiconductor_adv_quality.py](../examples/semiconductor_adv_quality.py) です。
工程特徴と品質目標を分け、ロットで分割して AdvPCA／GRA＋Ridge と平均値ベースラインを比較します。
目標の算出に使った反り・せん断力を、その目標を予測する入力へ戻さないでください。

<details>
<summary>スコアの式と入力チェック</summary>

**計算方法**

`grade_quality` は各指標の係数を求め、加重平均を取ります。

```text
coefficient = rho / (1 - benefit + rho)
score       = weighted_mean(coefficients)
```

| 設定 | 値 |
| --- | --- |
| 理想系列 | すべて 1 |
| 差の最小値／最大値 | 0／1 に固定 |
| 集約方法 | 加重平均。指標間の補償は可能 |

`grey_relation` は候補集合から差の極値を求めます。
NIST desirability は幾何平均なので、計算方法が異なります。

**入力チェック**

| 項目 | 条件 |
| --- | --- |
| 数値 | NaN・無限大を含まない |
| 列 | 数、方向、名前、順序が一致 |
| 定数列 | 有効な正規化範囲を指定 |
| `target` | 上下限の内側。区分線形のピークを使用 |
| 重み | 非負で、少なくとも一つは正 |

この正規化と AdvPCA の半径 `delta` は別の設定です。

</details>

## 軌跡・画像・ウィンドウ特徴

次の流れでモデルにつなげられます。

**数値データ → 軌跡／画像特徴 → Grey ウィンドウ特徴 → PCA／GRA → 回帰や距離比較**

| 入力 | 形式 | 使うもの |
| --- | --- | --- |
| スペクトル・一次元系列 | `(サンプル数, 点数)` | `GreyWindowFeatures`。先にエネルギー軸を揃える |
| 二次元以上の軌跡 | 各要素が `(点数, 次元数)` の list | `TrajectoryFeatures` → `GreyWindowFeatures` |
| グレー・多チャネル画像 | `(サンプル数, 高さ, 幅[, チャネル数])` | `ImagePatchFeatures` → `GreyWindowFeatures` |

時刻とストローク情報を持つ二次元軌跡の例です。三次元、五次元も同じクラスで扱えます。

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

画像ファイルからの手順は、下の「画像ファイルを読み込む」を参照してください。

回帰を加える場合は sklearn Pipeline を使えます。
`train_paths` と `test_paths` は `Trajectory` の list、`train_targets` は各訓練軌跡に対応する連続値です。

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

実行例は [grey_feature_pipeline.py](../examples/grey_feature_pipeline.py) です。
筆者照合や補彩の検出には、この特徴に加えて専用モデルと検証データが必要です。

### 画像ファイルを読み込む

参照画像を三枚以上と、比較したい画像を一枚用意します。同じ文字や署名を切り出し、向きと背景を揃えてください。

```text
data/test/images/
├── reference/
│   ├── sample_a.png
│   ├── sample_b.jpg
│   └── sample_c.png
└── query.png
```

プロジェクトのディレクトリで一行実行します。

```bash
python3 run.py handwriting data/test/images/query.png data/test/images/reference
```

初回は `.venv` と画像用パッケージを自動で準備します。次回も同じコマンドで使えます。Windows では `python3` を `python` に置き換えてください。
画像は既定で 288×96 に揃え、縦横比を保って白い余白を追加します。参照フォルダーの下位フォルダーも読み、問い合わせ画像は参照から除外します。

最も近い画像と報告のパスが表示されます。`artifacts/handwriting/index.html` をブラウザーで開くと、画像と全順位を確認できます。

| ファイル | 内容 |
| --- | --- |
| `index.html` | 画像と順位の報告 |
| `ranking.csv` | 参照画像の距離と順位 |
| `features.csv`、`components.csv` | Grey 窓特徴と PCA 座標 |
| `summary.json` | 設定と結果 |

Python から使う場合は、その環境で一度 `python -m pip install -e ".[images]"` を実行します。

```python
from greytheory import compare_handwriting

result = compare_handwriting("data/test/images/query.png", "data/test/images/reference")
print(result.best_match)
print(result.report)
```

AdvPCA はコマンドに `--pca adv`、関数に `pca="adv"` を指定します。他には `pca`、`sparse`、`kernel`、`robust`、`robust_sparse` が使えます。
出力先は `--output` または `output=` で変更できます。距離が小さいほど特徴が近い画像ですが、筆者が同じである確率ではありません。

<details>
<summary>自分で pipeline を組む・従来の画像サンプルを使う</summary>

```bash
python -m pip install -e ".[images]"
```

`load_images` は一つのパスまたはパスの list を受け取り、0–1 の RGB 配列を返します。
PNG／JPG を読み、問い合わせ画像に近い順に並べる例です。

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

PCA 特徴空間の距離が小さいほど近い画像です。参照だけで学習し、問い合わせ画像には変換だけを使います。
この距離だけで筆者、真贋、補彩を判定することはできません。

`size=(128, 128)` は幅・高さで、縦横比を保ち白い余白を追加します。省略時は全画像を同じサイズに揃えます。
EXIF の方向と透明部分の白背景処理も行います。グレー画像は `mode="L"` です。
切り出す領域と位置は先に揃えてください。高ビット深度の測定値は、この表示画像用の変換を通さず数値配列で扱います。

直接実行もできます。最初のコマンドはデモ PNG を作り、次のコマンドは自分の画像を読みます。

```bash
.venv/bin/python examples/image_files.py

.venv/bin/python examples/image_files.py \
  --references data/test/images/reference \
  --query data/test/images/query.png \
  --size 128 128
```

結果は既定で `artifacts/image_files/` に出力します。

| ファイル | 内容 |
| --- | --- |
| `features.csv` | 画像ごとの Grey ウィンドウ特徴 |
| `components.csv` | PCA 座標 |
| `ranking.csv` | 参照画像との距離と順位 |

実行コード：[image_files.py](../examples/image_files.py)。

```bash
greytheory handwriting data/test/images/query.png data/test/images/reference
```

</details>

<details>
<summary>入力条件</summary>

軌跡は各ストロークを再標本化します。`include_time=True` では昇順の時刻が必要で、速度も計算します。
各ストロークは二点以上、`n_points` はストローク数の二倍以上にします。ペンを離した区間は距離・速度に含めません。
`center=True` は始点を除き、`scale=False` は元の尺度を保ちます。時刻や筆圧は空間座標に混ぜません。

Grey ウィンドウは GM 係数や統計量を取り出し、未来予測は行いません。
三点未満の断片は係数がゼロになるため、`gm_coverage` と `gm_full_rank_coverage` も確認してください。
`boundary_channel=-1` で境界をまたぐ計算を避け、`stride` は窓幅以下にします。

画像は数値配列で渡します。OCR や文字分割は含まず、静止画像から実際の速度・筆圧は得られません。
詳しい単位や出力項目は[英語版](guide.md#trajectory-image-and-window-features)を参照してください。

</details>

## Bruker ファイルの読み込み

```python
from greytheory.io.bruker import read_bcf, read_spx

spectrum = read_spx("reference.spx")
image = read_bcf("scan.bcf", lazy=True)
counts = image.get_pixel(y=0, x=0, detector=0)
energy_keV = image.energy_axes[0]
roi = image.get_spectra((0, 0, 2, 2), detector=0)
```

SPX は計数、メタデータ、ファイル内のエネルギー校正を読みます。BCF は検出器ごとの校正を保持します。
ROI は上限を含まない `(y0, x0, y1, x1)`、計数は `uint64` です。

BCF は未圧縮 SFS 内の索引付き instructively packed 形式に対応しています。
他の符号化、外部圧縮、BCF v2 は未対応です。エネルギー軸が異なる場合は `sum_detectors` で合算できません。
手元のファイルでは、装置ソフトの結果と照合してください。

## 工程・スペクトル用ツール

| モジュール | 機能 |
| --- | --- |
| `greytheory.semiconductor` | PLS 品質回帰、動的／多元 PCA 監視、GRA 順位、Latin-hypercube サンプリング、GP 期待改善量の候補点 |
| `greytheory.spectroscopy` | AsLS 基線補正、NMF、MCR-ALS、MNF、Poisson PCA、重み付き低ランク近似、X 線情報、固定ピーク位置のフィッティング |

例：[合成スペクトル](../examples/hyperspectral_gra_pca.py)、[製造ロットでの検証](../examples/semiconductor_quality.py)、
[AdvPCA 品質予測](../examples/semiconductor_adv_quality.py)。
XRF ピークの強度を濃度へ換算するには、装置、標準試料、マトリックスの校正が必要です。

## バッチ処理

同じモデルに別のデータを入れて追加できます。`ModelQueue` は追加時に深いコピーを保存します。

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

`queue.run()` の既定は逐次実行です。`workers=2` で二つのプロセスを使い、結果は入力順で返します。
GM0N、GM1N、GM11 を混ぜられます。既存のモデル list には `run_models(models, workers=2)` も使えます。
プロセスを使う場合は `if __name__ == "__main__":` を残してください。

<details>
<summary>コピーとキューの更新</summary>

作成、追加、置換時にモデルを深くコピーします。`queue[0]` は保存済みのモデルを返すため、その場で編集できます。
全件成功してからキューを更新します。`inplace=False` は元のキューを残し、計算済みのコピーを返します。

</details>

## 合成 XRF と AI 筆跡デモ

[合成入力と分析結果](../data/demo/results/)を同梱しています。ダウンロード後、
`data/demo/results/index.html` をブラウザーで開けば、Python なしで報告を見られます。
GitHub 上では HTML を直接表示できません。画像と CSV は下のリンクから確認できます。

再実行する場合は、プロジェクトのディレクトリで次を実行します（macOS／Linux）。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[demos]"
.venv/bin/python examples/synthetic_demos.py
```

Windows では `.venv/bin/python` を `.venv\Scripts\python.exe` に置き換えてください。

| デモ | 入力・分析 | 出力 |
| --- | --- | --- |
| 合成 XRF | 6×6 の四枚のマップ、1024 チャネルの 144 スペクトル。Ca／Fe／Cu／Zn の既知の混合重みと Poisson 雑音 | スペクトル、エネルギー GRA 順位、未使用の模擬マップでの PCA／GreyPCA 予測比較 |
| AI 筆跡の形状 | 春風明月の三つの指定スタイル、18 セル。参照 12、問い合わせ 6 | PCA／Grey ウィンドウ＋PCA の距離、座標、特徴 CSV |

再実行の結果は `artifacts/synthetic_demos/` に保存されます。その中の `index.html` を開いてください。
片方だけなら、スクリプトに `--demo xrf` または `--demo handwriting` を付けます。

| 確認する内容 | 同梱ファイル |
| --- | --- |
| 光譜のカウント、エネルギー軸、合成の正解値 | [spectra.csv](../data/demo/results/xrf/spectra.csv)、[samples.csv](../data/demo/results/xrf/samples.csv)。`emsa/` の MSA は一つにつき一スペクトル |
| エネルギー順位と予測の比較 | [energy_ranking.csv](../data/demo/results/xrf/energy_ranking.csv)、[predictions.csv](../data/demo/results/xrf/predictions.csv) |
| 筆跡の照会結果と全順位 | [queries.csv](../data/demo/results/handwriting/queries.csv)、[ranking.csv](../data/demo/results/handwriting/ranking.csv) |

同梱結果の更新には `.venv/bin/python examples/synthetic_demos.py --output data/demo/results` を使います。

デモは外側の `examples/demos/`、画像と生成記録はその `assets/` にあります。
次のコードはプロジェクトのディレクトリで実行します。サンプルはライブラリと一緒にはインストールされません。

```python
from examples.demos import run_xrf_demo, run_handwriting_demo

xrf = run_xrf_demo("artifacts/synthetic_demos/xrf", seed=7)
handwriting = run_handwriting_demo("artifacts/synthetic_demos/handwriting")
print(xrf["report"])
print(handwriting["report"])
```

XRF は `emsa/*.msa`、`spx/*.spx`、`spectra.csv`、`dataset.npz` を出力します。
[Bruker は EMSA 交換を案内しています](https://www.bruker.com/it/products-and-solutions/elemental-analyzers/eds-wds-ebsd-SEM-Micro-XRF/software-esprit-family/esprit-reporting-and-data-management.html)が、実際の M4／ESPRIT への読み込みは別途確認が必要です。
SPX は本プロジェクトの最小読取り例です。混合重みは校正済みの元素 wt% ではありません。

筆跡は imagegen の生成画像で、[プロンプト](../data/demo/handwriting/handwriting_ai_sheet.json)も同梱しています。
ラベルは指定した形状スタイルで、実際の筆者ではありません。同じ生成ページ内の比較なので、実在の筆者の照合精度は示しません。
Grey は窓特徴の抽出です。スタイル ID を連続値の GRA 目標にはしません。

<details>
<summary>合成光譜と AI 筆跡の結果を見る</summary>

![合成光譜とエネルギー順位](../data/demo/results/xrf/spectra_and_ranking.png)

![AI が生成した三種類の架空の筆跡](../data/demo/handwriting/handwriting_ai_sheet.png)

![PCA と Grey 窓特徴 PCA による筆跡スタイル分布](../data/demo/results/handwriting/style_embeddings.png)

</details>

## 順位安定性・しきい値校正・最適化

プロジェクトのルートで合成データの例を実行します。

```bash
python3 run.py optimize
```

関数は `greytheory.analysis` から利用できます。学習・正常校正・テストの行を分けます。

```python
import numpy as np
from greytheory.analysis import (
    GreyPCA, ranking_stability, DifferenceCalibrator,
    reconstruction_scores, search_grey_pca, optimize_candidates,
)

random = np.random.default_rng(7)
features = random.normal(size=(240, 6))
target = 3 * features[:, 0] - features[:, 1] + random.normal(scale=0.1, size=240)
train, calibration, test = features[:120], features[120:180], features[180:]
train_target, test_target = target[:120], target[180:]
```
### 簡単な関数

一回の呼び出しで元特徴の順位と GreyPCA／Ridge 予測モデルを求めます。`normal_data` を渡すと、学習行だけで構築した別の監視 PCA でしきい値を校正します。一行が試料、各列が同じ順序の数値特徴です。`target` は学習行に対応する実測値です。画像・生のスペクトルには先に特徴抽出を行います。

```python
from greytheory import analyze_features

result = analyze_features(train, train_target, normal_data=calibration)
print(result.ranking)
print(result.best_parameters)
predictions = result.predict(test)
differences = result.find_differences(test)
result.save("artifacts/optimization/quick-report.json")
```
`result.ranking` は特徴名・選択頻度・平均順位・変動を含みます。GRA の標本感度であり PCA loading ではありません。`result.validation_rmse` は調整用のスコアです。`save()` は UTF-8 JSON レポートを保存し、学習モデルの保存ではありません。しきい値 `null` と `insufficient_resolution` は校正数不足を示し、検出フラグは立ちません。

監視 PCA は既定で `min(3, 特徴数 - 1)` 成分とし、全成分を使う予測モデルとは分けます。`monitor_components` で変更できますが、異常検出精度での自動選択ではありません。一特徴の入力は予測のみ対応し、再構成監視は使えません。

順位と予測だけなら `normal_data` を省略できます。後で `result.calibrate(normal_measurements)` を呼びます。校正前の `find_differences()` はエラーになります。再構成差は画像変化の証明ではありません。正常校正は学習・最終テストと独立させます。グループには `groups=sample_ids`、時系列分割には `cv=TimeSeriesSplit(...)` を指定します。順位の再抽出は時間ブロック方式ではありません。

既定は特徴数までの `top=5`、`repeats=40`、通常 PCA 最大八候補・六成分です。調整例：`analyze_features(train, train_target, repeats=100, search_options={"methods": ("pca", "sparse"), "max_trials": 12, "time_budget": 60})`。固定候補は `search_options={"candidates": [...]}`。DataFrame は列名と順序を確認し、名前のない配列は元の列順序を保ってください。

名前付き候補を比較する場合：

```python
from greytheory import choose_options

options = [
    {"name": "A", "cost": 10, "quality": 5, "days": 3},
    {"name": "B", "cost": 12, "quality": 4, "days": 2},
    {"name": "C", "cost": 15, "quality": 8, "days": 4},
]
best_options = choose_options(
    options, smaller=["cost"], larger=["quality"], limits={"days": (None, 4)}
)
print(best_options)
```
A と C が残ります。A は費用が低く、C は品質が高く、B は A に支配されます。制約は境界を含む `(下限, 上限)` で、`None` は片側の制限なしです。指定した数値だけを比較し、同じ非劣解も保持して独立したコピーを返します。唯一解や大域最適を保証しません。

### 1. 特徴順位の安定性

部分標本で GRA を繰り返し、選択頻度・平均順位・順位の変動を確認します。頻度は感度の指標であり、因果関係や筆者の確率ではありません。

```python
stability = ranking_stability(train, train_target, k=2, repeats=100)
print(stability.selection_frequency)
print(stability.mean_rank, stability.rank_std)
print(stability.successful_repeats, stability.skipped_repeats)
```
同点は平均順位と選択枠を分け合い、定数特徴は選択しません。退化した反復は除外して件数を記録します。`groups=sample_ids` で試料・筆者・バッチ単位に抽出できます。時系列には別途ブロック設計が必要です。

### 2. 正常データでしきい値を校正

モデルを固定し、別の正常測定値で校正します。

```python
monitor = GreyPCA(3, standardize=True).fit(train)
calibrator = DifferenceCalibrator(false_alarm_rate=0.05).fit(
    reconstruction_scores(monitor, calibration)
)
flags = calibrator.predict(reconstruction_scores(monitor, test))
print(calibrator.threshold, flags)
```
split-conformal の順序 `ceil((n + 1) * (1 - alpha))` を使い、しきい値を超えた行だけを検出します。校正数が少ない場合は `inf` となり、有限のしきい値を設定できません。周辺的な誤報率制御には正常スコアの交換可能性が必要です。隣接画素・分布変化・多重比較は別途扱います。再構成差は補彩や画像変化の証明ではありません。校正データを学習・調整・最終テストに再利用しないでください。

### 3. GreyPCA の組み合わせを選ぶ

数値目標の回帰に対応します。各分割の学習データだけで標準化・PCA／GRA・Ridge を学習し、有限候補から無作為に選んで同じ分割で比較します。

```python
search = search_grey_pca(
    train, train_target,
    components=(2, 3, 4), top_k=(None, 2), rho=(0.3, 0.5),
    max_trials=8, cv=3, random_state=7,
)
print(search.best_parameters, search.validation_rmse)
predictions = search.predict(test)
print(np.sqrt(np.mean((predictions - test_target) ** 2)))
```
試料やバッチには `groups=sample_ids`、時系列には `cv=TimeSeriesSplit(...)` を指定します。重なる窓には間隔も必要です。最終テストは探索の外に残します。探索 RMSE は独立したテスト結果ではありません。

方式固有の設定は `candidates=[{"method": "pca", "n_components": 3, "standardize": True}, {"method": "sparse", "n_components": 3, "method_params": {"alpha": 0.1}, "standardize": True}]` で指定でき、既存の六方式を利用できます。`search.trials` に分割スコア・時間・失敗・警告を記録し、未収束の候補は採用しません。同じ学習データと分解設定は GRA 設定間でキャッシュします。`memory=".local/search-cache"` で保存できます。`time_budget=60` は候補間で確認し、実行中の学習や最終再学習は超過する場合があります。現版は有限無作為探索で、TPE・段階的打切り・画像しきい値や窓設定の自動探索は未実装です。

### 4. 複数目標の候補を残す

DOE／候補表と実測または予測の目標値を渡します。以下は架空の品質損失・費用モデルです。

```python
parameters = np.array([[0.2], [0.5], [0.8]])

def simulated_process(rows):
    value = rows[:, 0]
    quality_loss = (value - 0.8) ** 2
    cost = 1 + 2 * value
    return np.column_stack([quality_loss, cost]), (cost - 2.5)[:, None]

alternatives = optimize_candidates(
    parameters, simulated_process, directions=["smaller", "smaller"]
)
print(alternatives["parameters"])
print(alternatives["front"].objectives)
```
方向は `smaller` または `larger`。制約値がすべて `<= 0` の行だけを比較します。同じ非劣解はすべて残し、実行可能な行がなければ空の結果を返します。測定表には `pareto_front(objectives, directions, constraints=...)` を直接使えます。入力候補内のパレート前線であり、大域最適の保証ではありません。候補生成には `greytheory.semiconductor.latin_hypercube` を利用できます。予測結果は実測で確認し、目標値型の指標は先に偏差／損失へ変換します。

## 研究モデル：RL-FGM・GINN・Grey–Fuzzy GPR

合成データの比較を実行します。

```bash
python3 run.py research
```

結果は `artifacts/research_models/report.json`。GUI の「応用ラボ → 研究モデル」でも四方式を選べます。直接HTMLには既定の計算結果があり、設定変更はローカルPythonか要求／結果交換で実行します。サーバーや大型深層学習依存は不要です。

### GreyPCA + research models

四つのモデルで `pca`、`sparse`、`kernel`、`robust`、`robust_sparse`、`adv` を併用できます。予測入力は時点×チャネル、出力は元の列です。`method` で GINN/FGINN に変更します。方式別設定は `pca_params={"method_params": {...}}`。

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

```python
from greytheory.research import GreyPCAForecast, GreyPCAQuality

forecast = GreyPCAForecast(
    method="fginn", pca_method="sparse", n_components=2,
    pca_params={"method_params": {"alpha": 0.1}},
    model_params={"order": 0.5, "grey_weight": 0.1},
).fit(history)
print(forecast.predict(3))
regressor = GreyPCAQuality(
    pca_method="pca", n_components=3, pca_params={"top_k": 2}
).fit(features[:40], quality[:40])
print(regressor.predict(features[40:], return_std=True))
```

`GreyPCAForecast` は入力履歴だけで PCA を学習し、各成分から `学習最小値 - max(学習標準偏差, 1e-8)` を引いて正にします。独立予測後に平行移動を戻し元の列へ逆変換します。平行移動と PCA の符号は灰色予測に影響します。これは組合せ設計であり、平行移動不変の多変量灰色方程式ではありません。予測はクリップせず、特に Kernel PCA の復元は近似です。複製可能な独自モデルは `pca_params={"estimator": estimator}` と `pca_method="pca"` で渡せます。時系列では `inverse_transform` も fit 時に検査します。

wrapper 全体を学習行だけで fit し、保留データで確認します。RL 自動次数は投影済み学習系列の末尾を使いますが、PCA は学習履歴全体を見ているため、この内部スコアは一貫した時系列交差検証ではありません。厳密な入れ子検証は各時系列分割で wrapper 全体を再学習し、固定次数の候補を比較します。最終テストはすべての学習から除外してください。

`GreyPCAQuality` は学習特徴・目的値で PCA と任意の GRA 成分選択を学習し、Grey–Fuzzy GPR に渡します。`top_k` は外部目的値がある品質回帰だけです。信頼度は保持成分だけで、捨てた方向の異常を見逃す場合があります。成分分散は望大・望小を示さず、PCA 追加で必ず改善するわけではありません。

非負の生カウントには既存 PoissonPCA を独自 estimator として併用できます。Anscombe 変換前のカウントを維持するため `standardize=False` にします。この adapter 自身の近似逆変換は負カウントをゼロに制限し、wrapper は追加で制限しません。品質回帰では同じ `pca_params` を `GreyPCAQuality` に渡します。

```python
from greytheory.spectroscopy import PoissonPCA

counts_model = GreyPCAForecast(
    pca_params={"estimator": PoissonPCA(2), "standardize": False},
    model_params={"order": 1},
).fit(history)
print(counts_model.predict(3))
```

### 簡単な呼び出し

非負・等間隔・欠測行のない単変量系列を使います。

```python
from greytheory import forecast_series

values = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
future = forecast_series(values, steps=3, method="rlfgm")
print(future)
```
ネットワーク版は `method="ginn"` または `"fginn"`。モデル引数も `forecast_series()` に渡せます。全文未取得の不等間隔再帰モデルではありません。

品質回帰では独立したテストを残します。

```python
import numpy as np
from greytheory import predict_quality

random = np.random.default_rng(7)
features = random.normal(size=(60, 4))
target = 100 + 5 * features[:, 0] + 2 * features[:, 1] ** 2
result = predict_quality(features[:40], target[:40], features[40:])
print(result["prediction"], result["std"])
print(result["reliability"]["grade"])
```
`std` は目標単位のGP予測標準偏差です。信頼度はファジー評価で、正解確率・合格仕様・校正区間ではありません。`model` は追加予測に使えますが、そのままJSONへ保存する値ではありません。

### モデルと診断

```python
from greytheory.research import RLFGM, GINN, FGINN, GreyFuzzyGPR

rl = RLFGM(order=0.5).fit(values)
network = GINN(window=3, grey_weight=0.1).fit(values)
fractional_network = FGINN(window=3, order=0.5, beta=1).fit(values)
print(rl.predict(3), network.predict(3), fractional_network.predict(3))
print(network.diagnostics)
```
RL-FGMは演算子と応答の核、GINN/FGINNは差分を明示した工学版、Grey–Fuzzy GPRは独自設計です。著者実験の完全再現ではありません。

- **RL-FGM**：$w_j=[j^r-(j-1)^r]/\Gamma(r+1)$ の下三角行列と三角解法による復元。$r=0$ は単位行列、$r=1$ は通常AGOです。初期状態は $x_1/\Gamma(r+1)$、発展係数ゼロの極限も扱います。auto次数は学習内の時系列保留区間で有限格子から選び、論文の訓練MAPE／PSOとは異なります。履歴と予測の合計は2048行までです。
- **GINN**：過去窓を使う単層tanhネットワークをSciPy L-BFGS-Bと解析勾配で学習します。損失は `MSE(prediction, truth) + grey_weight * MAE(prediction, teacher) + weight_penalty`。各事前予測はその過去窓だけで学習します。固定の真値対grey誤差はネットワークへの勾配がゼロとなるため、予測対teacherの項を明示します。層数・最適化器・損失は著者実験と異なります。重み0で通常MLP、未収束時は警告します。
- **FGINN**：tM重み $\Gamma(\beta+1)k^{r-1}$ と対応する逆差分を使います。曖昧な応答記法に対し $d\tau_k=w_k$ の重み付き時間を明示した工学版です。order=beta=1でGINNと一致し、RLの畳み込み累積とは異なります。
- **Grey–Fuzzy GPR**：学習内GRAから固定の正のRBF重みを作ります。`grey_strength=0` は同じ設定の通常GPと一致し、GPは振幅・雑音を最適化できます。入力支持度は加重標準空間の最近傍距離を使い、帯域は同一地点を除く学習最近傍の90百分位です。精度隷属度は `1 / (1 + (std / training_target_std)**2)`、評価は支持度との最小値です。ラベル境界は0.75/0.4で、予測値は変更しません。IGF-GPRのカーネル調整やルールの再現ではありません。

### 合成比較の結果

[比較レポート](../benchmarks/results/research_models.json)は三シード、平滑／周期系列の36/12分割、GPの60/40分割（変化10行）です。最終テストは学習や次数選択に使いません。この例でRL-FGMは次数1を選びGM11と一致しました。GINN/FGINNはGM11より長期平均RMSEが大きく、通常ネットワークは二回未収束でした。GRA-GPは三シードで領域内誤差が小さい一方、両GPとも領域外誤差が大きくなりました。実務精度や普遍的優位の証明ではありません。

独自実装で、著者コード・出版社の図文・外部ケースデータは同梱しません。RL-FGM論文はCC BY-NC 4.0で、ここでは再配布しません。自作コードはMITを維持します。

資料：[RL-FGM](https://doi.org/10.1177/00368504261481032)、[GINN/FGINN公開版](https://arxiv.org/html/2403.15027v2)、[2025年論文](https://doi.org/10.1016/j.neucom.2025.130756)、[IGF-GPRの着想](https://doi.org/10.1016/j.engappai.2026.114777)。

## Grey モデル自体の改善

GreyPCA の設定探索とは別に、モデル自体にも研究があります。以下は出版社の要旨・公開説明に基づく整理で、論文の完全再現ではありません。

| 方向 | 数学的な変更 | 現状 |
| --- | --- | --- |
| 背景値 | 累積系列の積分近似や隣接値の重みを改善 | `alpha` と `background_mode="corrected"` は実装済み。時間検証による自動選択や論文固有の積分式は未実装 |
| 離散モデル DGM | 連続応答の近似ではなく離散漸化式を学習 | 未実装 |
| 分数階累積 | 整数階 AGO を可変次数の演算子へ変更 | RL／tM研究版あり。自由度増加による過学習に注意 |
| 安定した係数推定 | Tikhonov／ridge、打切りSVD、GCVなどの選択 | 階数・条件数診断、`lstsq`・`rcond`・ridge は実装済み。R-GMCやGCV／L-curve選択の完全実装ではない |
| 動的 GRA | 識別係数と意思決定の順位付けを変更 | 現在の `rho`・重み・再抽出はDGRAではなく、DGRAは未実装 |

時系列はローリング起点で検証し、直前値・指数平滑などの基準と比較して最後の未来データを残します。分数階累積と分数階微分は異なり、移動窓だけでは実装できません。本プロジェクトの二段GM11 Convolutionも、正則化論文の畳み込み積分GMCとは別です。次は既存のcorrected背景値／ridgeの時間調整、次にDGM、その後に分数階を評価する順序を推奨します。常に精度が向上する保証はありません。

研究資料：

- Xie, N. & Liu, S. (2009). [Discrete grey forecasting model and its optimization](https://doi.org/10.1016/j.apm.2008.01.011).
- Wu, L. et al. (2013). [Grey system model with the fractional order accumulation](https://doi.org/10.1016/j.cnsns.2012.11.017).
- He, Z. et al. (2015). [Regularized multivariable grey model for stable grey coefficients estimation](https://doi.org/10.1016/j.eswa.2014.09.058).
- [Optimization of Background Value in GM(1,1) Model](https://doi.org/10.1016/S1874-8651(09)60011-9).
- [DGRA: Multi-sourcing and supplier classification through Dynamic Grey Relational Analysis method](https://doi.org/10.1016/j.cie.2022.108674).

## 開発とテスト

`greytheory/` はライブラリ、`examples/` はサンプルとデモ資料、`tests/` はテストと fixtures です。
GitHub とソース配布にはサンプルとテストを含め、wheel にはライブラリだけを入れます。

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

テストデータは生成または同梱済みで、別途ダウンロードは不要です。
`scripts/verify_full_install.py` でインストール後の API を確認できます。
サンプルの合成データは手順の説明用で、工程・化学・鑑識の精度検証ではありません。

GitHub 用のソース ZIP は `python3 scripts/package_github.py` で作成できます。
`artifacts/github_upload/` に保存され、ソースと合成結果を含みます。ローカル環境、キャッシュ、外部の装置データは含みません。

測定記録は [benchmarks/results](../benchmarks/results/) にあります。
[コア比較](../benchmarks/compare_core.py)と[降次元比較](../benchmarks/compare_decomposition.py)を再実行できます。
時間の記録は macOS arm64 の値で、環境によって変わります。
従来の `GreyTheory`、`GreyGM*`、`add_pattern`／`add_patterns`、`grey.run.gm*` も使えます。

公開前に `pyproject.toml` のバージョンを設定して commit・push し、3 OS × 2 Python の検証完了を確認します。そのコミットに対応する `v<version>` タグを作り、GitHub Release を公開します。PyPI はそのタグのコードを検証して公開します。既存タグは master の更新に追従しないため、古い Release の再実行には後の修正が含まれません。

## ライセンス

[MIT](../LICENSE)。依存パッケージには各ライセンスが適用されます。[Third-party notices](../THIRD_PARTY_NOTICES.md) を参照してください。

## 参考文献と実装

詳しい文献一覧は[英語版](guide.md#references)または[繁體中文版](guide.zh-TW.md#參考文獻與實作來源)を参照してください。

- Liu & Lin (2011), [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2).
- Candès et al. (2011), [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395).
- Erichson et al. (2020), [Sparse Principal Component Analysis via Variable Projection](https://arxiv.org/abs/1804.00341).
- Vävinggren et al. (2026), [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553).
- Camp (2019), [pyMCR / MCR-AR](https://doi.org/10.6028/jres.124.018).
- [scikit-learn](https://scikit-learn.org/stable/modules/decomposition.html)、[Spectral Python](https://www.spectralpython.net/algorithms.html)、[pybaselines](https://pybaselines.readthedocs.io/en/latest/algorithms/whittaker.html)。
- NIST/SEMATECH. [Multiple responses: the desirability approach](https://www.itl.nist.gov/div898/handbook/pri/section5/pri5322.htm)。方向と目標設定の参考。GRA の加重平均は幾何平均 desirability と異なります。

### 研究モデルの出典と実装対応

以下の論文のモデル定義と着想は原著者の成果です。PCA 接続・固定成分オフセット・簡易関数は本プロジェクトの統合作業であり、論文の提案として扱いません。

- Xu, Zhenguo; Peng, Rui; Pang, Mengyi; Jiang, Jianming; Zhang, Rujing; & Liu, Caixia (2026). [A novel grey system model with discrete Riemann–Liouville fractional derivative and its applications](https://doi.org/10.1177/00368504261481032). *Science Progress*, 109(3). RL-FGM の累加算子と応答式の出典です。本実装は論文の PSO／MAPE と異なり、格子探索と学習末尾の検証で次数を選びます。
- Xie, Wanli; Zhao, Ruibin; Xu, Zhenguo; & Liang, Tingting (2025). [Grey-informed neural network for time-series forecasting](https://doi.org/10.1016/j.neucom.2025.130756). *Neurocomputing*, 649, 130756. [Public preprint, v2 (2024)](https://arxiv.org/abs/2403.15027v2). GINN と FGINN の出典です。公開プレプリントを参照し、ネットワーク・最適化法・予測と事前モデルの損失を変更した工学版で、著者の実験を再現していません。
- Lawal, Ahmad; Yang, Yingjie; Baisa, Nathanael L.; & He, Hongmei (2026). [Reservoir permeability prediction using Integrated Grey-Fuzzy Gaussian Process Regression: A comprehensive framework for uncertainty quantification and interpretability](https://doi.org/10.1016/j.engappai.2026.114777). *Engineering Applications of Artificial Intelligence*, 177, 114777. GRA・GPR・ファジー信頼度を組み合わせる着想の出典です。本実装の核重みと所属規則は独自設計で、著者の IGF-GPR の再現ではありません。
