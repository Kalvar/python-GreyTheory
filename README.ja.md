# GreyTheory

[English](https://github.com/Kalvar/python-GreyTheory/blob/master/README.md) | [繁體中文](https://github.com/Kalvar/python-GreyTheory/blob/master/README.zh-TW.md) | **日本語**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3977ab)](https://github.com/Kalvar/python-GreyTheory/blob/master/pyproject.toml)
[![MIT License](https://img.shields.io/badge/License-MIT-36a88a)](https://github.com/Kalvar/python-GreyTheory/blob/master/LICENSE)
[![CI](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml/badge.svg)](https://github.com/Kalvar/python-GreyTheory/actions/workflows/ci.yml)

![GreyTheory — Grey models, GRA, and PCA](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/greytheory-banner.svg)

<p align="center"><strong>Python で灰色予測・特徴比較・PCA を使う。</strong></p>
<p align="center"><a href="https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.ja.md">Documentation</a> · <a href="#quick-start">クイックスタート</a> · <a href="https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.ja.md#workbench">操作画面</a> · <a href="https://github.com/Kalvar/python-GreyTheory/tree/master/benchmarks/results/">ベンチマーク</a></p>

時系列を予測し、目標と関連する特徴を比較し、光スペクトルや工程データを整理できます。Python から使うか、付属の HTML 画面で試せます。

## できること

- **Grey + PCA の統合分析**：`GreyPCA` は 6 種類の PCA と GRA による主成分選択を組み合わせます。PCA で試料間の違いを整理し、参照する目標があれば GRA で関連する成分を評価・選択します。スペクトル・画像・軌跡には、PCA の前に Grey 窓特徴を加えて局所的な変化も扱えます。
- **予測**：GM11 と二段階 Convolution。有序の多変量データは GM0N／GM1N。
- **比較**：GRA 特徴順位と、望大／望小／目標値を指定する品質評価。
- **特徴の整理**：6 種類の PCA、PoissonPCA、Grey 窓、画像、多次元軌跡。

<a id="quick-start"></a>

## クイックスタート

**Python 3.11 以上**が必要です。ソースをダウンロードまたは clone して実行します。

```bash
python3 run.py
```

> [!TIP]
> 初回は `.venv` と依存パッケージを準備します。Windows は `python3` を `python` に置き換えてください。

### Python から使う

自分のプログラムの Python 環境にインストールします。

```bash
python -m pip install .
```

```python
from greytheory import GM11

series = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]
model = GM11(background_mode="corrected").fit(series)
print(model.predict(2))
```

従来の `model.forecast(2)` と `model.forecast_convolution(1, 4)` も利用できます。次の二点の数値だけなら `predict(2)` を使います。`forecast(2)` は保存データを再計算し、予測期間の設定を更新します。

## PCA を選ぶ

`GreyPCA` の `method` を指定します。画面でも同じ方法を選べます。

```python
from greytheory.analysis import GreyPCA

features = [[1.0, 2.0, 0.8], [1.5, 2.4, 1.2],
            [2.0, 3.1, 1.1], [2.5, 3.4, 1.8]]
model = GreyPCA(n_components=2, method="pca", standardize=True)
components = model.fit_transform(features)
print(components)
```

| 方法 | 試す場面 |
| --- | --- |
| `"pca"` | 標準の線形投影。まずはこれから。 |
| `"sparse"` | 疎な成分係数を使いたいとき。 |
| `"kernel"` | 非線形の構造を調べるとき。 |
| `"robust"` | PCP の低ランク分解後に投影。 |
| `"robust_sparse"` | 頑健性と疎な符号化を組み合わせる。 |
| `"adv"` | 指定した摂動条件での投影を調べる。 |

非負の元計数には PoissonPCA もあります。パラメーター、成分選択、GRA と PCA の順位の違いは詳細ガイドを参照してください。 [→ GreyPCA](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#pca-と特徴選択)

## 操作画面で試す

`workbench` は GreyTheory の分析画面を開きます。スペクトル、DOE データ、筆跡画像を読み込み、手法とパラメーターを選び、グラフや特徴の順位を確認できます。

```bash
python3 run.py workbench
```

初回は `.venv` を作成し、分析・画面用の依存パッケージをインストールします。次回からは同じ環境を使います。分析はローカルで実行され、サーバーは不要です。

付属 HTML を直接開くと、事前計算した結果の**オフラインプレビュー**を表示します。新しい設定での計算には上記コマンドか要求／結果 JSON 交換を使います。

[HTML](https://github.com/Kalvar/python-GreyTheory/blob/master/examples/workbench/index.html) · [スクリーンショット付きの操作説明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.ja.md#workbench)

右上の言語選択で English・繁體中文・日本語を切り替えます。入力、設定、結果は保持されます。

![PVD DOE — GreyTheory workbench](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/workbench-doe.ja.png)

*PVD の模擬実験 15 件。左は試料差の投影、右は目標に対する工程入力の比較です。*

デモの入力と結果は [data/demo/](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/README.md) にまとめています。[データ選択ページ](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/index.html)でファイルと操作手順を確認できます。

実演では `python3 run.py workbench` で起動し、応用ラボの作品の領域差を選びます。シード 7、PCA、成分数 3、分位点 0.95、強度 0.6 で実行します。誤差マップを、意図的に変更した 18 位置と照合します。分位点を 0.99 にして再実行し、次に 0.95 に戻して強度を 0.2 に下げます。シードを固定し、各結果 JSON を保存します。操作ガイドにも手順があります。

![Artwork differences](https://raw.githubusercontent.com/Kalvar/python-GreyTheory/master/docs/images/workbench-art.ja.png)

合成スペクトルマップの比較で、作品写真の分析ではありません。このラボは実マップ対の読み込みに未対応です。検出領域は調査の手掛かりで、補彩や真贋の証明にはなりません。

**AI 絹画画像** — 応用ラボの作品情境で入力を **AI 絹画画像** にし、初期設定で実行します。PNG 2 枚 → 区画特徴 → Grey 窓 → GreyPCA の計算です。枠を切り替えて比較し、分位点 0.99 でも再実行します。

[画像・計算 CSV / JSON・事例の出典](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/artwork/index.html) · `python3 run.py artwork`

[対話式の専門確認と実験報告を開く](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/artwork/review/index.html) — 対応画像は確認順序を付け、スペクトルは独立した正常校準と実物調査を組み合わせます。同一 PNG の負の対照が、従来の再構成誤差数は変更数ではないことを示します。領域別の観察・仮説・次の調査は公開資料による模擬判読で、専門家の実審査ではありません。

### その他のデモ

配送、ドライバー配車、美術品の光スペクトル差、注文予測、多次元軌跡、光スペクトル・半導体ツールを試せます。画像ページは AI 筆跡や自分の画像も比較できます。

[スクリーンショット付きの操作説明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.ja.md#gallery) · [PVD CSV](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/doe/pvd_15.csv) · [CVD CSV](https://github.com/Kalvar/python-GreyTheory/blob/master/data/demo/doe/cvd_15.csv)

> [!NOTE]
> デモは合成データで、実務精度を示しません。配送と配車は専用の最適化を使い、Grey は選好を評価します。画像距離は作者を特定せず、美術品の異常は調査の手掛かりです。

## 順位安定性と最適化

[GUI の操作と画面](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.ja.md#四段階の最適化デモ)

`analyze_features()` で順位安定性・GreyPCA 回帰探索・任意の正常データ校正をまとめて実行できます。`choose_options()` は名前付き多目標候補を比較します。

```python
import numpy as np
from greytheory import analyze_features

features = np.random.default_rng(7).normal(size=(120, 4))
target = 2 * features[:60, 0] - features[:60, 1]
result = analyze_features(features[:60], target, normal_data=features[60:90])
predictions = result.predict(features[90:])
```

[簡単な関数](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#簡単な関数)

GRA 順位の安定性、独立した正常データによるしきい値校正、GreyPCA 回帰設定の探索、候補内のパレート前線を利用できます。

```bash
python3 run.py optimize
```

[四段階の Python ガイド](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#順位安定性しきい値校正最適化)。合成例はリポジトリで実行します。探索は有限無作為試行と分割内キャッシュを使います。検証スコアは調整用で、独立テスト精度ではありません。パレート結果は入力候補内に限られます。

## Research models

等間隔予測と品質回帰の研究版：RL-FGMの核、GINN/FGINN工学版、独自設計Grey–Fuzzy GPRを利用できます。

```python
from greytheory import forecast_series

values = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
future = forecast_series(values, steps=3, method="rlfgm")
print(future)
```

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

GUI は研究モデル → PCA を併用：on。予測成分は学習データから決めた正の平行移動を使い、灰色モデルの結果に影響します。品質信頼度は保持成分だけです。

```bash
python3 run.py research
```

[用法・差分・実測上の制限](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#研究モデルrl-fgmginngreyfuzzy-gpr)

## Documentation

| ガイド | 内容 |
| --- | --- |
| [スクリーンショット付きの操作説明](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/README.ja.md) | インストール、プレビュー、即時計算、ファイル交換 |
| [GreyPCA](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#pca-と特徴選択) | 6 種類の PCA とパラメーター、成分選択 |
| [Images / trajectories](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#画像ファイルを読み込む) | 画像の読み込み、特徴、比較 |
| [Bruker](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#bruker-ファイルの読み込み) | SPX／BCF と検出器の校正 |
| [使い方と API](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md) | 予測、GRA、品質、バッチ、参考文献 |

## 開発とテスト

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest -q
python -m build
```

[Benchmarks](https://github.com/Kalvar/python-GreyTheory/tree/master/benchmarks/results/) · [Issues](https://github.com/Kalvar/python-GreyTheory/issues)

## ライセンス

[MIT](https://github.com/Kalvar/python-GreyTheory/blob/master/LICENSE) · [Third-party notices](https://github.com/Kalvar/python-GreyTheory/blob/master/THIRD_PARTY_NOTICES.md)

### 非公式実装と権利に関する声明

GreyTheory の論文を参考に開発したアルゴリズムは**非公式実装（Unofficial implementations）**であり、原著者や所属機関との提携関係はなく、推奨も受けていません。参照した研究とアルゴリズムの貢献は原研究者に帰属します。

実装がご自身の特許、著作権その他の権利に関わるとお考えの場合は、[ilovekalvar@gmail.com](mailto:ilovekalvar@gmail.com) へ、権利の根拠と対象のアルゴリズムまたはファイルをお知らせください。特許については特許番号と関連請求項をご提示ください。

通知を確認し、必要に応じて引用の修正、アルゴリズムの変更、利用停止または公開終了を行います。通知の受領や予防措置は侵害を認めるものではありません。オープンソースにおいても、参照した研究の著者の貢献を尊重します。

## 参考文献と実装

<details>
<summary>Grey と PCA の主要文献</summary>

Grey、PCA、実装済みのロバスト手法の主要文献です。スペクトル・工程分析の出典は[詳細ガイド](https://github.com/Kalvar/python-GreyTheory/blob/master/docs/guide.ja.md#参考文献と実装)を参照してください。

1. Deng, J. L. (1982). [Control problems of grey systems](https://doi.org/10.1016/S0167-6911(82)80025-X). *Systems & Control Letters*, 1(5), 288–294.
2. Liu, S. & Lin, Y. (2011). [Grey Systems: Theory and Applications](https://doi.org/10.1007/978-3-642-16158-2). Springer. Grey modelling and relational analysis.
3. Kayacan, E., Ulutas, B. & Kaynak, O. (2010). [Grey system theory-based models in time series prediction](https://doi.org/10.1016/j.eswa.2009.07.064). *Expert Systems with Applications*, 37(2), 1784–1789.
4. Jolliffe, I. T. & Cadima, J. (2016). [Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202). *Philosophical Transactions A*, 374, 20150202.
5. Candès, E. J., Li, X., Ma, Y. & Wright, J. (2011). [Robust Principal Component Analysis?](https://doi.org/10.1145/1970392.1970395). *Journal of the ACM*, 58(3), Article 11. Principal Component Pursuit.
6. Lin, Z., Chen, M. & Ma, Y. (2010). [The Augmented Lagrange Multiplier Method for Exact Recovery of Corrupted Low-Rank Matrices](https://arxiv.org/abs/1009.5055). Inexact ALM solver for PCP.
7. Erichson, N. B. et al. (2020). [Sparse Principal Component Analysis via Variable Projection](https://doi.org/10.1137/18M1211350), [author manuscript](https://arxiv.org/abs/1804.00341). *SIAM Journal on Applied Mathematics*, 80(2), 977–1002. Robust sparse model: equation (17), Algorithm 2.
8. Vävinggren, D. et al. (2026). [A Robust Optimization Approach to Sparse Principal Component Analysis](https://arxiv.org/abs/2606.03553). AdvPCA: Algorithms 1–2 and Appendix A.3.

</details>

### 研究モデルの出典と実装対応

以下の論文のモデル定義と着想は原著者の成果です。PCA 接続・固定成分オフセット・簡易関数は本プロジェクトの統合作業であり、論文の提案として扱いません。

- Xu, Zhenguo; Peng, Rui; Pang, Mengyi; Jiang, Jianming; Zhang, Rujing; & Liu, Caixia (2026). [A novel grey system model with discrete Riemann–Liouville fractional derivative and its applications](https://doi.org/10.1177/00368504261481032). *Science Progress*, 109(3). RL-FGM の累加算子と応答式の出典です。本実装は論文の PSO／MAPE と異なり、格子探索と学習末尾の検証で次数を選びます。
- Xie, Wanli; Zhao, Ruibin; Xu, Zhenguo; & Liang, Tingting (2025). [Grey-informed neural network for time-series forecasting](https://doi.org/10.1016/j.neucom.2025.130756). *Neurocomputing*, 649, 130756. [Public preprint, v2 (2024)](https://arxiv.org/abs/2403.15027v2). GINN と FGINN の出典です。公開プレプリントを参照し、ネットワーク・最適化法・予測と事前モデルの損失を変更した工学版で、著者の実験を再現していません。
- Lawal, Ahmad; Yang, Yingjie; Baisa, Nathanael L.; & He, Hongmei (2026). [Reservoir permeability prediction using Integrated Grey-Fuzzy Gaussian Process Regression: A comprehensive framework for uncertainty quantification and interpretability](https://doi.org/10.1016/j.engappai.2026.114777). *Engineering Applications of Artificial Intelligence*, 177, 114777. GRA・GPR・ファジー信頼度を組み合わせる着想の出典です。本実装の核重みと所属規則は独自設計で、著者の IGF-GPR の再現ではありません。
