# Demo 資料包

所有公開展示用的資料、圖片與結果都放在這裡。**先開 [index.html](index.html)**，依用途選資料；要執行分析，從專案根目錄啟動 `python3 run.py workbench`。

| 想試什麼 | 用哪個檔案／資料 | 在哪裡操作 |
| --- | --- | --- |
| PVD 製程特徵排序 | [doe/pvd_15.csv](doe/pvd_15.csv)，15 筆實驗 | 光譜 / DOE → 內建 PVD → 載入 → 目標選 `thickness_nm` → 執行分析 |
| CVD 製程特徵排序 | [doe/cvd_15.csv](doe/cvd_15.csv)，15 筆實驗 | 光譜 / DOE → 內建 CVD → 載入 → 選目標 → 執行分析 |
| 光譜差異與能量區間排序 | 內建「合成 XRF · 144 個位置」；原始檔在 [results/xrf/](results/xrf/) | 光譜 / DOE → 合成 XRF → 載入 → 執行分析 |
| 單筆 SPX 讀取 | [map00_y00_x00.spx](results/xrf/spx/map00_y00_x00.spx) | 光譜 / DOE → 選擇檔案。單筆只看光譜圖；多筆分析先用內建 XRF |
| 筆跡風格比較 | [handwriting/handwriting_ai_sheet.png](handwriting/handwriting_ai_sheet.png) 是來源拼貼圖 | 圖片比較 → 試跑 AI 筆跡 demo。GUI 自動比較 1 張查詢與 12 張參考，無須手動選檔；完整報告含 6 張查詢 |
| 配送、司機媒合、藝術品、軌跡、訂單預測 | [scenarios/synthetic_inputs.json](scenarios/synthetic_inputs.json) 是合成輸入的參考檔 | 應用實驗室 → 選情境 → 執行情境。這個 JSON 不要放進「匯入 Python 結果」 |
| 只看已完成的結果 | [results/index.html](results/index.html) | 直接用瀏覽器開啟，不需執行 Python |

## 自己選檔時

- **DOE**：用「選擇 CSV / SPX / BCF」挑 `doe/` 裡的一個 CSV。手動匯入不會帶入內建的欄位建議，請自行選比較目標，輸入特徵只勾製程參數。
- **自己的筆跡**：選一張待比較圖片，另選 3–30 張分開儲存的參考圖片。不要把這裡的整張來源拼貼圖當成多張參考。
- **光譜**：`results/xrf/spectra.csv` 是「每列一個能量、每欄一個位置」的匯出表，不符合 GUI 的「每列一個樣本」格式。想直接分析這組資料，選內建 XRF；不要直接匯入這張表。
- **結果**：`ranking.csv`、`summary.json` 等是分析輸出，不是輸入資料；GUI 的「匯入 Python 結果」只接受檔案交換流程產生的 `.result.json`。

## 資料夾

```text
data/demo/
├── index.html        # 資料選擇入口，可直接雙擊
├── README.md         # 檔案與操作對照
├── catalog.json      # 資料包目錄與用途
├── doe/              # PVD／CVD CSV 與公式、單位說明
├── handwriting/      # AI 筆跡來源圖與生成紀錄
├── scenarios/        # 配送、司機、藝術品與序列的合成輸入
└── results/          # 已跑好的光譜／筆跡報告與結果數據
```

## 重新產生

在專案根目錄、已安裝分析套件的環境執行：

```bash
python -m examples.workbench.doe
python -m examples.workbench.scenarios
python -m examples.synthetic_demos --output data/demo/results
```

這些指令會更新對應的 demo 檔案；不會重新生成 AI 筆跡來源圖。一般操作不需要先重新產生資料。

所有資料都是合成／AI 展示資料，沒有真實 Bruker 量測、作者身分或機台配方。用途與來源見各組的 manifest、summary 或生成紀錄；專案授權與第三方聲明見 [LICENSE](../../LICENSE)、[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。自己的儀器資料仍放在不上傳 GitHub 的 `data/test/`，不混入公開 demo 資料包。

[完整操作手冊](../../docs/README.zh-TW.md#workbench-操作手冊) · [Workbench HTML 預覽](../../examples/workbench/index.html)

English: All public demo inputs and results are collected here. Open `index.html` to choose a dataset, or run `python3 run.py workbench` from the repository root for live analysis. CSVs in `doe/` are ready to import; scenario JSON and exported result tables are not GUI result-import files.

## AI 絹畫展示

開啟 [圖片、數值與案例來源](artwork/index.html)，或在 Workbench 的藝術品情境選「AI 絹畫圖片」。預設以兩張 PNG 擷取 RGB 區塊特徵，經 Grey 窗口與 GreyPCA 標記差異。不是 XRF，也沒有精確變更真值。

`python3 run.py artwork` 可重新輸出 `artifacts/artwork/` 的分析 JSON 與 CSV。自己的對齊圖片可加 `--reference reference.png --observed observed.png`。

[專家查看與實測報告](artwork/review/index.html) 包含兩套搭配、同圖負對照、光譜保留測試，以及四個區域的模擬判讀。可下載本機查驗筆記。
