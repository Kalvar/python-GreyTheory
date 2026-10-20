# Documentation

[English](README.md) | [繁體中文](README.zh-TW.md) | **日本語**

[使い方と API](guide.ja.md) · [GreyTheory](../README.ja.md)

画面の操作はこのページ、Python の例・パラメーター・参考文献は詳細ガイドを参照してください。

> [!NOTE]
> コマンドはプロジェクトのルートで実行します。画像には合成データだけを使い、個人や私有 Bruker データは含みません。

デモ入力と結果は [data/demo/](../data/demo/README.md) にまとめています。[データ選択ページ](../data/demo/index.html)で各ファイルと操作を確認できます。

ローカル一覧には読込確認済みのファイルだけを表示します。読み込めないファイルと理由は別の折りたたみ欄に表示します。複数位置・試料の分析が可能なら ✓、3 件未満なら ✗ と表示します。単一スペクトルのグラフは表示できます。ファイルを追加・変更したら画面を再読込してください。

<a id="workbench"></a>

## 操作画面を開く

### 1. ブラウザーでプレビュー

[examples/workbench/index.html](../examples/workbench/index.html)

付属 HTML を直接開くと内蔵例を表示します。インストールや server は不要です。設定変更は Python 計算が必要であることを画面に表示します。

### 2. Python で即時計算

```bash
python3 run.py workbench
```

`workbench` は GreyTheory の分析画面を開きます。データの読込、手法とパラメーターの選択、分析、グラフや特徴順位の確認ができます。

初回は `.venv` を作成し、分析・画面用の依存パッケージをインストールします。次回からは同じ環境を使います。分析はローカルで実行され、サーバーは不要です。

- **スペクトル／DOE**：データを読み込み、Grey、GRA、PCA などを選び、パラメーターを調整して実行します。
- **筆跡画像**：比較画像と参照画像を読み込み、特徴距離の順位を確認します。
- **内蔵デモ**：合成データで操作を試してから、自分のデータに切り替えられます。

## PVD／CVD：読込・目標選択・実行

工程を選んで読み込み、thickness_nm などの目標を指定します。投影と GRA 順位を見て、上位の特徴を選び即時モードで再実行できます。各工程は合成実験 15 件です。

![PVD DOE analysis](images/workbench-doe.png)

[CSV: PVD](../data/demo/doe/pvd_15.csv) · [CSV: CVD](../data/demo/doe/cvd_15.csv) · [Data manifest](../data/demo/doe/manifest.json)

<a id="gallery"></a>

## デモとスクリーンショット

### 配送経路

3–8 地点と距離・時間・遅延の重みを選びます。経路は全列挙で探索し、Grey は選好を評価します。画像は既定の合成例です。

![Synthetic delivery routes](images/workbench-routes.png)

### 美術品の領域差

別に生成した参照光スペクトル図で学習し、観測図の差を表示します。右は模擬正解です。異常表示は補彩・年代・真贋の判定ではありません。

![Synthetic artwork spectral map](images/workbench-art.png)

### 筆跡画像

即時モードは比較画像 1 枚と参照画像 3–30 枚を使います。AI demo もあります。順位は特徴距離であり、同一作者の確率ではありません。

![AI handwriting feature comparison](images/workbench-handwriting.png)

## HTML と Python のファイル交換

HTML から変更した計算要求を保存し、以下を実行します。生成された .result.json を HTML に読み込んでください。

```bash
python3 run.py workbench --request greytheory-request.json
```

## 方法と API

| API | |
| --- | --- |
| [GM11 / Convolution](guide.ja.md#時系列予測) | **予測**：GM11 と二段階 Convolution。有序の多変量データは GM0N／GM1N。 |
| [GRA / GreyPCA](guide.ja.md#pca-と特徴選択) | 6 種類の PCA とパラメーター、成分選択 |
| [Quality](guide.ja.md#品質スコア) | BenefitNormalizer · grade_quality · rank_quality |
| [Images / trajectories](guide.ja.md#画像ファイルを読み込む) | 画像の読み込み、特徴、比較 |
| [Bruker](guide.ja.md#bruker-ファイルの読み込み) | SPX／BCF と検出器の校正 |
| [使い方と API](guide.ja.md) | 予測、GRA、品質、バッチ、参考文献 |
