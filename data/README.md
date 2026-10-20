# 資料入口

```text
data/
├── demo/    # 專案附的合成資料、AI 圖片及分析報告
└── test/    # 自己的 Bruker、光譜或圖片資料；不上傳 GitHub
```

- **先試範例**：開啟 [demo/index.html](demo/index.html)，依用途選資料與操作方式。[檔案對照表](demo/README.md)列出各檔案的用途。
- **放自己的資料**：放進 `data/test/`，可依儀器或用途建立子資料夾，例如 `data/test/bruker/`、`data/test/images/`。
- **開始分析**：在專案根目錄執行 `python3 run.py workbench`。新增儀器檔案後按「重整頁面」，會更新「內建與本機資料」清單；只列可讀取的檔案，未支援的另列原因。圖片從「圖片比較」選取。

`data/demo/` 隨專案公開；`data/test/` 由 `.gitignore` 與打包設定排除。沒有範例檔時，可自行建立 `data/test/`。不要將未取得公開授權的量測資料放進 `data/demo/`。


## 依本機 M4 資料產生模擬變體

已有 `data/test/m4_tornado/minBcf.bcf` 時，可執行：

```bash
python -m scripts.make_m4_variant
```

會產生 `data/test/m4_tornado/minBcf_simulated.bcf`。Workbench 重整後選這份檔案，偵測器先用 0，按載入，再選「不指定目標」、標準 PCA、2 個主成分執行。與原檔分別分析時，可比較光譜形狀和位置分布；兩次各自擬合的 PC 座標不宜直接相減。

變體保留 3×3 地圖、兩個偵測器與各自能量軸，加入計數擾動及人工能量峰；`.changes.json` 記錄各位置的變更強度，`.simulation.json` 記錄來源雜湊與生成方式。這是依本機量測衍生的模擬資料，仍留在不上傳的 `data/test/`。輸出只驗證能由 GreyTheory 讀取，未驗證 Bruker 儀器軟體相容性。
