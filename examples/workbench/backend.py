"""In-process analysis bridge. No sockets or HTTP service."""

import base64
from collections import OrderedDict
import json
import secrets
from pathlib import Path
import tempfile
import threading
import warnings

import numpy as np

from .analysis import METHODS, analyze, read_csv, read_spectrum_file, spectra_dataset
from .doe import DATA, SPECS
from .methods import ENGINES, PCA_SCHEMAS, GRA_FIELDS, GM_FIELDS, WINDOW_FIELDS, pca_params
from .scenarios import SCENARIOS, run_scenario

ROOT = Path(__file__).resolve().parents[2]


class Backend:
    def __init__(self):
        self.datasets = OrderedDict()
        self.busy = threading.Lock()
        self._file_checks = {}
        self.unavailable = []

    def catalog(self):
        entries = [
            {"id": f"doe:{key}", "name": f"{key.upper()} · 15 筆模擬 DOE", "kind": "doe"} for key in SPECS
        ]
        entries.append(
            {"id": "synthetic:xrf", "name": "合成 XRF · 144 個位置（非儀器量測）", "kind": "spectrum"}
        )
        folder = ROOT / "data/test"
        self.unavailable = []
        active_checks = {}
        if folder.exists():
            for path in sorted(folder.rglob("*")):
                if (
                    path.suffix.lower() in {".bcf", ".spx", ".csv"}
                    and path.is_file()
                    and path.resolve().is_relative_to(folder.resolve())
                ):
                    rel = path.relative_to(folder).as_posix()
                    fingerprint = None
                    try:
                        stat = path.stat()
                        fingerprint = (str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
                        check = self._file_checks.get(fingerprint)
                        if check is None:
                            if stat.st_size > 32 * 1024 * 1024:
                                raise ValueError("單檔上限為 32 MiB。")
                            data = (
                                read_csv(path.read_bytes(), path.name)
                                if path.suffix.lower() == ".csv"
                                else read_spectrum_file(path)
                            )
                            check = {"rows": len(data.values)}
                    except Exception as error:
                        check = {"reason": str(error) or "無法讀取這個檔案。"}
                        # Stat failures have no fingerprint and are retried on refresh.
                    if fingerprint is not None:
                        active_checks[fingerprint] = check
                    if "reason" in check:
                        self.unavailable.append({"name": rel, "reason": check["reason"]})
                        continue
                    is_spectrum = path.suffix.lower() != ".csv"
                    detail = (
                        "單筆光譜"
                        if is_spectrum and check["rows"] == 1
                        else f"{check['rows']} 個位置"
                        if is_spectrum
                        else f"{check['rows']} 筆資料"
                    )
                    analysis = "多位置分析" if is_spectrum else "多樣本分析"
                    symbol = "✓" if check["rows"] >= 3 else "✗"
                    label = f"{rel} · {detail} → {analysis} {symbol}"
                    entries.append(
                        {
                            "id": "local:" + rel,
                            "name": label,
                            "kind": "doe" if path.suffix.lower() == ".csv" else "spectrum",
                            "rows": check["rows"],
                        }
                    )
        self._file_checks = active_checks
        return entries

    def remember(self, dataset):
        key = secrets.token_urlsafe(12)
        self.datasets[key] = dataset
        while len(self.datasets) > 4:
            self.datasets.popitem(last=False)
        return {"id": key, **dataset.payload()}

    def config(self):
        return dict(
            catalog=self.catalog(),
            unavailable=self.unavailable.copy(),
            methods=METHODS,
            pca_schemas=PCA_SCHEMAS,
            engines=ENGINES,
            gra_fields=GRA_FIELDS,
            gm_fields=GM_FIELDS,
            window_fields=WINDOW_FIELDS,
            scenarios=SCENARIOS,
        )

    def request(self, endpoint, options):
        if not isinstance(options, dict):
            raise ValueError("請傳入物件參數。")
        if not self.busy.acquire(blocking=False):
            raise ValueError("另一個分析正在執行，請稍候。")
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                if endpoint == "/api/load":
                    result = self.load(options)
                elif endpoint == "/api/analyze":
                    dataset = self.datasets.get(options.get("dataset"))
                    if dataset is None:
                        raise ValueError("請重新載入資料。")
                    result = analyze(dataset, options)
                elif endpoint == "/api/scenario":
                    result = run_scenario(
                        options.get("scenario"),
                        options.get("parameters"),
                        method_parameters=options.get("method_params"),
                        series=options.get("series"),
                    )
                elif endpoint == "/api/handwriting":
                    result = self.handwriting(options)
                else:
                    raise ValueError("不支援的分析操作。")
            if caught:
                result.setdefault("warnings", []).extend(dict.fromkeys(str(w.message) for w in caught))
            return json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False))
        finally:
            self.busy.release()

    def load(self, options):
        key = options.get("id", "")
        if key not in {row["id"] for row in self.catalog()} and "upload" not in options:
            raise ValueError("請從清單選擇檔案或使用上傳按鈕。")
        if key.startswith("doe:"):
            process = key.split(":", 1)[1]
            dataset = read_csv(
                (DATA / f"{process}_15.csv").read_bytes(), f"{process.upper()} 模擬 DOE", SPECS[process]
            )
        elif key == "synthetic:xrf":
            from examples.demos.xrf import make_xrf_data

            s = make_xrf_data()
            dataset = spectra_dataset(
                "合成 XRF",
                s.counts,
                s.energy_keV,
                note="144 個位置、4 張獨立模擬地圖。混合權重不是元素重量濃度。",
            )
            dataset.values = np.column_stack([dataset.values, s.mixing_weights[:, 2]])
            dataset.defaults = dataset.columns.copy()
            dataset.columns.append("synthetic_Cu_mixing_weight")
            dataset.targets = ["synthetic_Cu_mixing_weight"]
        else:
            detector = options.get("detector", 0)
            index = options.get("spectrum_index", 0)
            if (
                isinstance(detector, bool)
                or not isinstance(detector, int)
                or isinstance(index, bool)
                or not isinstance(index, int)
            ):
                raise ValueError("偵測器與光譜索引需為整數。")
            if "upload" in options:
                upload = options["upload"]
                name = str(upload["name"])[:200]
                suffix = Path(name).suffix.lower()
                data = base64.b64decode(upload["data"], validate=True)
                if len(data) > 32 * 1024 * 1024:
                    raise ValueError("單檔上限為 32 MiB。")
                if suffix not in {".csv", ".spx", ".bcf"}:
                    raise ValueError("請選擇 CSV、SPX 或 BCF。")
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / ("input" + suffix)
                    path.write_bytes(data)
                    dataset = (
                        read_csv(data, name)
                        if suffix == ".csv"
                        else read_spectrum_file(path, detector=detector, spectrum_index=index, name=name)
                    )
            else:
                path = (ROOT / "data/test" / key[6:]).resolve()
                if not path.is_relative_to((ROOT / "data/test").resolve()):
                    raise ValueError("資料路徑超出範圍。")
                dataset = (
                    read_csv(path.read_bytes(), path.name)
                    if path.suffix.lower() == ".csv"
                    else read_spectrum_file(path, detector=detector, spectrum_index=index)
                )
        return self.remember(dataset)

    def handwriting(self, options):
        from PIL import Image
        from greytheory.handwriting import compare_handwriting

        method = options.get("method", "pca")
        if method not in METHODS:
            raise ValueError("不支援的 PCA 方法。")
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            refs = folder / "references"
            refs.mkdir()
            if options.get("demo"):
                from examples.demos.handwriting import ASSETS, _sheet_cells

                cells, records = _sheet_cells(ASSETS / "handwriting_ai_sheet.png")
                query = folder / "query.png"
                Image.fromarray(np.rint(cells[12].clip(0, 1) * 255).astype("uint8")).save(query)
                for cell, record in zip(cells[:12], records[:12]):
                    Image.fromarray(np.rint(cell.clip(0, 1) * 255).astype("uint8")).save(
                        refs / (record["sample"] + ".png")
                    )
            else:
                uploads = options.get("references", [])
                if not isinstance(uploads, list) or not 3 <= len(uploads) <= 30:
                    raise ValueError("請選擇 3 至 30 張參考圖片。")
                query = folder / "query.png"
                for i, upload in enumerate([options["query"], *uploads]):
                    data = base64.b64decode(upload["data"], validate=True)
                    if len(data) > 8 * 1024 * 1024:
                        raise ValueError("每張圖片最多 8 MiB。")
                    from io import BytesIO

                    with Image.open(BytesIO(data)) as image:
                        if image.width * image.height > 16_000_000:
                            raise ValueError("每張圖片最多 1,600 萬像素。")
                        image.convert("L").save(query if i == 0 else refs / f"{i:02}.png")
            result = compare_handwriting(
                query,
                refs,
                output=folder / "result",
                pca=method,
                pca_params=pca_params(method, options.get("method_params")),
            )

            def thumbnail(path):
                from io import BytesIO

                image = Image.open(path).convert("RGB")
                image.thumbnail((576, 192))
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

            labels = None if options.get("demo") else [str(u.get("name", "image"))[:200] for u in uploads]
            return {
                "query": thumbnail(query),
                "matches": [
                    {
                        "rank": m.rank,
                        "name": m.reference.stem if labels is None else labels[int(m.reference.stem) - 1],
                        "distance": m.distance,
                        "image": thumbnail(m.reference),
                    }
                    for m in result.matches
                ],
                "note": "圖片 → 區塊特徵 → Grey 窗口 → PCA → 距離排序。只用參考圖片擬合；距離不是作者機率。內建範例是 AI 合成風格，不能當成筆跡鑑識準確率。",
            }
