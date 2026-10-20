"""Adapters for the local demo UI; calculations use the public GreyTheory API."""

import csv
from copy import deepcopy
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
import tempfile
from xml.etree import ElementTree as XML

import numpy as np

from greytheory.analysis import GreyFeatureSelector, GreyPCA, rank_quality
from .methods import ENGINES, GRA_FIELDS, GM_FIELDS, WINDOW_FIELDS, pca_params, validate
from greytheory.io.bruker import UnsupportedBCFError, read_bcf, read_spx
from greytheory.io.bruker.spx import calibration, parse_xml

METHODS = ("pca", "sparse", "kernel", "robust", "robust_sparse", "adv")
MAX_ROWS = 5000
MAX_FEATURES = 256


@dataclass
class Dataset:
    name: str
    values: np.ndarray
    columns: list
    labels: list
    kind: str = "doe"
    defaults: list = field(default_factory=list)
    targets: list = field(default_factory=list)
    note: str = ""
    spectrum: dict | None = None
    positions: list = field(default_factory=list)
    excluded: list = field(default_factory=list)

    def payload(self):
        return {
            "name": self.name,
            "columns": self.columns,
            "rows": len(self.values),
            "labels": self.labels,
            "values": self.values.tolist(),
            "kind": self.kind,
            "defaults": self.defaults or self.columns,
            "targets": self.targets,
            "note": self.note,
            "spectrum": self.spectrum,
            "positions": self.positions,
            "excluded": self.excluded,
        }


def read_csv(data, name="CSV", spec=None):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("CSV 請使用 UTF-8 編碼。") from error
    reader = csv.reader(StringIO(text))
    headers = next(reader, [])
    if not headers or len(set(headers)) != len(headers) or any(not h.strip() for h in headers):
        raise ValueError("CSV 需要不重複且非空白的欄名。")
    if len(headers) > MAX_FEATURES + 16:
        raise ValueError("CSV 欄位過多，請先篩選至 256 個數值欄位以內。")
    rows = []
    for row in reader:
        if not row:
            continue
        if len(row) != len(headers):
            raise ValueError(f"CSV 第 {len(rows) + 2} 列的欄位數不一致。")
        rows.append(row)
        if len(rows) > MAX_ROWS:
            raise ValueError("互動範例最多接受 5,000 列。")
    if not rows:
        raise ValueError("CSV 沒有資料列。")
    numeric, columns, excluded = [], [], []
    for i, column in enumerate(headers):
        try:
            values = np.array([float(row[i]) for row in rows])
            if not np.isfinite(values).all():
                raise ValueError("nonfinite")
        except ValueError:
            excluded.append(column)
            continue
        numeric.append(values)
        columns.append(column)
    if not columns or len(columns) > MAX_FEATURES:
        raise ValueError("需要 1 至 256 個完整、有限的數值欄位；缺值請先處理。")
    labels = (
        [row[headers.index("run_id")] for row in rows]
        if "run_id" in headers
        else [str(i + 1) for i in range(len(rows))]
    )
    defaults = list(spec["features"]) if spec else columns
    targets = list(spec["responses"]) if spec else []
    return Dataset(
        name,
        np.column_stack(numeric),
        columns,
        labels,
        defaults=defaults,
        targets=targets,
        excluded=excluded,
        note="模擬 DOE；只供操作與方法測試。" if spec else "CSV 資料；非數值或含缺值的欄位已排除。",
    )


def spectra_dataset(name, counts, energy, *, positions=None, note=""):
    counts = np.atleast_2d(counts)
    if counts.shape[0] > MAX_ROWS or counts.size > 25_000_000:
        raise ValueError("此互動範例的光譜資料過大，請先裁切 ROI。")
    calibrated = energy is not None
    energy = np.arange(counts.shape[1]) if energy is None else np.asarray(energy)
    keep = energy >= 0 if calibrated else np.ones(len(energy), dtype=bool)
    indices = np.flatnonzero(keep)
    if not len(indices):
        raise ValueError("沒有可使用的光譜通道。")
    bins = np.array_split(indices, min(64, len(indices)))
    values = np.column_stack([counts[:, b].sum(axis=1, dtype=np.float64) for b in bins])
    unit = "keV" if calibrated else "channel"
    names = [f"{energy[b[0]]:.3f}–{energy[b[-1]]:.3f} {unit}" for b in bins]
    # Keep the raw display light while preserving narrow peaks with per-bin maxima.
    display = np.array_split(np.arange(counts.shape[1]), min(1024, counts.shape[1]))
    mean = counts.mean(axis=0)
    peaks = np.array([b[np.argmax(mean[b])] for b in display])
    positions = [] if positions is None else np.asarray(positions).tolist()
    spectrum = {
        "x": energy[peaks].tolist(),
        "mean": mean[peaks].tolist(),
        "unit": unit,
        "traces": [row[peaks].astype(float).tolist() for row in counts[:9]],
        "totals": counts.sum(axis=1, dtype=np.float64).tolist(),
        "raw_channels": counts.shape[1],
    }
    return Dataset(
        name,
        values,
        names,
        [f"位置 {i + 1}" for i in range(len(values))],
        kind="spectrum",
        note=note + " 分析使用最多 64 個加總能量區間；圖表最多顯示前 9 條光譜。",
        spectrum=spectrum,
        positions=positions,
    )


def read_spectrum_file(path, *, detector=0, spectrum_index=0, name=None):
    path = Path(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("單檔上限為 32 MiB。")
    if path.suffix.lower() == ".bcf":
        try:
            m = read_bcf(path)
        except UnsupportedBCFError as error:
            with path.open("rb") as handle:
                signature = handle.read(8)
            if signature == b"AAMVHFSS":
                message = (
                    "檔頭符合 BCF，但目前讀取器不支援這份檔案的內部結構或編碼；"
                    "這則訊息本身不代表檔案損毀。請先選內建「合成 XRF」，"
                    "或用儀器軟體匯出 SPX 查看單筆光譜。"
                )
            else:
                message = (
                    "無法辨識這個檔案的 BCF 檔頭。請確認選的是原始 .bcf，"
                    "而不是網頁、下載指標檔或未下載完成的檔案；改副檔名無法轉換格式。"
                )
            raise ValueError(message) from error
        if detector not in m.detectors:
            raise ValueError(f"可用偵測器：{m.detectors}")
        if np.prod(m.shape) > 25_000_000 or m.shape[0] * m.shape[1] > MAX_ROWS:
            raise ValueError("BCF 地圖過大，請先裁切 ROI。")
        cube = m.get_spectra(detector=detector)
        positions = np.indices(cube.shape[:2]).reshape(2, -1).T
        return spectra_dataset(
            name or path.name,
            cube.reshape(-1, cube.shape[-1]),
            m.energy_axes[detector],
            positions=positions,
            note=f"偵測器 {detector}；可用偵測器 {m.detectors}。各偵測器分開分析，未直接相加。",
        )
    # Isolate one spectrum for the existing single-spectrum API; do not silently merge backgrounds.
    root = parse_xml(path.read_bytes())
    if root.tag != "TRTSpectrum":
        raise ValueError("不支援的 SPX 根節點。")
    entries = root.findall(".//ClassInstance[@Type='TRTSpectrum']")
    if not 0 <= spectrum_index < len(entries):
        raise ValueError(f"光譜索引需為 0 至 {len(entries) - 1}。")
    choices = [e.get("Name", f"spectrum {i}") for i, e in enumerate(entries)]
    selected = XML.Element("TRTSpectrum")
    entry = deepcopy(entries[spectrum_index])
    # Background spectra can be nested inside the main spectrum.
    for parent in tuple(entry.iter()):
        for child in list(parent):
            if child.tag == "ClassInstance" and child.get("Type") == "TRTSpectrum":
                parent.remove(child)
    selected.append(entry)
    with tempfile.TemporaryDirectory() as folder:
        isolated = Path(folder) / "selected.spx"
        isolated.write_bytes(XML.tostring(selected, encoding="utf-8"))
        if choices[spectrum_index].casefold() == "background":
            # Fitted background intensities may be fractional; they are not raw photon counts.
            count = int(entry.findtext(".//ChannelCount", "0"))
            if not 0 < count <= 1_000_000:
                raise ValueError("SPX 背景通道數超出範圍。")
            values = np.array([float(t) for t in entry.findtext(".//Channels", "").split(",")])
            if len(values) != count or not np.isfinite(values).all() or np.any(values < 0):
                raise ValueError("SPX 背景強度需為有限非負數，且符合通道數。")
            energy = calibration(entry, count)
        else:
            spectrum = read_spx(isolated)
            values, energy = spectrum.counts, spectrum.energy
    return spectra_dataset(
        name or path.name,
        values,
        energy,
        note=(
            "背景為估計強度，可含小數，不是原始光子計數。"
            if choices[spectrum_index].casefold() == "background"
            else ""
        )
        + f"光譜 {spectrum_index}: {choices[spectrum_index]}；檔案內光譜：{choices}。單一位置可看圖，需要至少 3 個位置才能執行此介面的 PCA。",
    )


def analyze(dataset, options):
    names = options.get("features", dataset.defaults or dataset.columns)
    if (
        not isinstance(names, list)
        or not names
        or len(names) != len(set(names))
        or any(n not in dataset.columns for n in names)
    ):
        raise ValueError("請選擇不重複且存在的特徵欄位。")
    target = options.get("target") or None
    if target and target not in dataset.columns:
        raise ValueError("目標欄位不存在。")
    if target in names:
        raise ValueError("目標欄位不能同時當成輸入特徵。")
    engine = options.get("engine", "pca")
    if engine not in ENGINES:
        raise ValueError("不支援的分析方法。")
    method = options.get("method", "pca")
    if method not in METHODS:
        raise ValueError("不支援的 PCA 方法。")
    if method != "pca" and (len(dataset.values) > 1000 or len(names) > 128):
        raise ValueError("進階 PCA 的互動上限為 1,000 列、128 個特徵；請縮小資料或改用標準 PCA。")
    values = dataset.values[:, [dataset.columns.index(n) for n in names]].copy()
    if len(values) < 3:
        raise ValueError("PCA 需要至少 3 筆資料；單筆 SPX 可以看光譜，請改用地圖或多筆 CSV。")
    if dataset.kind == "spectrum" and options.get("normalize_counts", True) and engine != "poisson":
        # Normalize by ALL retained bins, so unchecking a bin does not change the denominator.
        bin_columns = dataset.defaults or dataset.columns
        totals = dataset.values[:, [dataset.columns.index(n) for n in bin_columns]].sum(axis=1, keepdims=True)
        if np.any(totals == 0):
            raise ValueError("存在零總計數光譜，無法做總計數正規化。")
        values /= totals
    eligible = np.ptp(values, axis=0) > 0
    constant = [n for n, ok in zip(names, eligible) if not ok]
    values = values[:, eligible]
    names = [n for n, ok in zip(names, eligible) if ok]
    if not names:
        raise ValueError("選取的特徵全部為常數。")
    if engine in {"gra", "gm0n", "gm1n", "quality"}:
        return analyze_direct(dataset, options, names, values, constant)
    if engine == "window_pca":
        if dataset.kind != "spectrum":
            raise ValueError("窗口分析需要依序排列的通道；DOE 欄位不應任意當作連續序列。")
        from greytheory.features import GreyWindowFeatures

        window = GreyWindowFeatures(**validate(WINDOW_FIELDS, options.get("window_params")))
        values = window.fit_transform(values)
        names = list(map(str, window.get_feature_names_out()))
        active = np.ptp(values, axis=0) > 0
        values = values[:, active]
        names = [n for n, ok in zip(names, active) if ok]
    k = options.get("components", 2)
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= min(8, len(values) - 1, len(names)):
        raise ValueError(f"主成分數需介於 1 與 {min(8, len(values) - 1, len(names))}。")
    y = dataset.values[:, dataset.columns.index(target)] if target else None
    params = pca_params(method, options.get("method_params"))
    gra = validate(GRA_FIELDS, options.get("gra_params"))
    top = options.get("component_top_k", 0)
    if isinstance(top, bool) or not isinstance(top, int) or not 0 <= top <= k:
        raise ValueError("主成分篩選數需為 0（關閉）至主成分數。")
    if top and y is None:
        raise ValueError("GRA 篩選主成分需要目標。")
    kwargs = dict(
        n_components=k,
        method=method,
        method_params=params or None,
        top_k=top or None,
        rho=gra["rho"],
        normalization=gra["normalization"],
        component_direction=gra["direction"],
        standardize=dataset.kind != "spectrum" or bool(options.get("standardize", False)),
    )
    if engine == "poisson":
        if dataset.kind != "spectrum":
            raise ValueError("PoissonPCA 僅用於非負原始計數光譜。")
        from greytheory.spectroscopy import PoissonPCA

        kwargs.update(method="pca", method_params=None, estimator=PoissonPCA(k), standardize=False)
    model = GreyPCA(**kwargs)
    # No target in PCA fit: ranking input features and fitting the projection are separate operations.
    with np.errstate(over="raise", invalid="raise"):
        coordinates = model.fit_transform(values, y if top else None)
    if not np.isfinite(coordinates).all():
        raise ValueError("分解結果包含非有限值，請調整輸入尺度。")
    if target:
        selector = GreyFeatureSelector(
            k=None,
            rho=gra["rho"],
            normalization=gra["normalization"],
            direction=gra["direction"],
            constant_policy="exclude",
        ).fit(values, y)
        scores = selector.scores
        signs = selector.directions
        ranking_label = f"輸入特徵與 {target} 的 GRA（方向：{gra['direction']}）"
    else:
        # Model-independent association with the displayed projection, also available for kernel PCA.
        centered = values - values.mean(axis=0)
        z = coordinates - coordinates.mean(axis=0)
        norm = np.linalg.norm(centered, axis=0)[:, None] * np.linalg.norm(z, axis=0)[None, :]
        correlations = np.divide(
            centered.T @ z, norm, out=np.zeros((len(names), coordinates.shape[1])), where=norm > 0
        )
        scores = np.max(np.abs(correlations), axis=1)
        signs = np.zeros(len(names), dtype=int)
        ranking_label = "特徵與所保留主成分的最大絕對相關（非 GRA、非因果重要度）"
    order = np.argsort(-scores, kind="stable")
    ranking = [{"feature": names[i], "score": float(scores[i]), "direction": int(signs[i])} for i in order]
    try:
        ratios = np.asarray(model.explained_variance_ratio, dtype=float)
        variance = ratios[model.selected_components].tolist() if np.isfinite(ratios).all() else None
    except (AttributeError, NotImplementedError):
        variance = None
    warnings = ["此結果是同一批資料的探索分析；沒有保留測試集，不能當成預測準確率或因果證據。"]
    if dataset.kind == "spectrum":
        warnings.append("計數／能量區間的差異不是元素濃度；量化需要校正、標準品及獨立驗證。")
    if constant:
        warnings.append(
            "已排除常數欄位："
            + ", ".join(constant[:6])
            + (f" …共 {len(constant)} 欄（完整清單見下載 JSON）。" if len(constant) > 6 else "")
        )
    return {
        "coordinates": coordinates.tolist(),
        "ranking": ranking,
        "ranking_label": ranking_label,
        "variance": variance,
        "method": method,
        "target": target,
        "features": names,
        "components": coordinates.shape[1],
        "ranking_type": "derived_features" if engine == "window_pca" else "features",
        "engine": engine,
        "method_params": params,
        "gra_params": gra,
        "selected_components": model.selected_components.tolist(),
        "component_scores": None if model.component_scores is None else model.component_scores.tolist(),
        "rows": len(values),
        "excluded_constants": constant,
        "warnings": warnings,
    }


def analyze_direct(dataset, options, names, values, constant):
    engine = options["engine"]
    target = options.get("target") or None
    y = dataset.values[:, dataset.columns.index(target)] if target else None
    gra = validate(GRA_FIELDS, options.get("gra_params"))
    warnings = ["同批資料探索分析；分數不是因果、機率或預測準確率。"]
    extra = {}
    coordinates = values[:, : min(2, values.shape[1])]
    coordinate_labels = names[: min(2, len(names))]
    ranking_type = "features"
    if engine == "quality":
        settings = options.get("quality")
        if not isinstance(settings, list) or len(settings) != len(names):
            raise ValueError("請逐欄提供品質方向、權重、上下界與必要的目標值。")
        r = rank_quality(
            values,
            [v["direction"] for v in settings],
            bounds=[[v["lower"], v["upper"]] for v in settings],
            targets=[v.get("target") if v["direction"] == "target" else None for v in settings],
            weights=[v["weight"] for v in settings],
            rho=gra["rho"],
        )
        scores = r.scores
        labels = dataset.labels
        signs = np.zeros(len(scores), dtype=int)
        coordinates = scores[:, None]
        coordinate_labels = ["灰品質分數"]
        label = "樣本對宣告理想值的灰品質分數（不是特徵重要度）"
        ranking_type = "samples"
        extra = {"benefits": r.normalized_values.tolist(), "quality_settings": settings}
        warnings.append(
            "上下界是偏好正規化範圍，不是合格規格。加權平均允許指標互補；先確認望大、望小、目標與權重。"
        )
    else:
        if y is None:
            raise ValueError("此方法需要先選擇比較目標。")
        labels = names
        if engine == "gra":
            selector = GreyFeatureSelector(k=None, constant_policy="exclude", **gra).fit(values, y)
            scores = selector.scores
            signs = selector.directions
            label = "原始特徵的 GRA 分數；圖是前兩個輸入欄位，不是 PCA"
        else:
            if options.get("ordered_rows") is not True:
                raise ValueError(
                    "GM 會使用累積與列順序；請確認樣本有合理序列，再勾選「資料列有先後順序」。無序 DOE 請用 GRA 或 PCA。"
                )
            from greytheory import GM0N, GM1N

            params = validate(GM_FIELDS, options.get("gm_params"))
            model = (GM0N if engine == "gm0n" else GM1N)(**params).fit(values, y, feature_names=names)
            coefficients = np.asarray(model.coefficients if engine == "gm0n" else model.driving_coefficients)
            scores = np.abs(coefficients) / max(float(np.max(np.abs(coefficients))), 1e-15)
            signs = np.sign(coefficients).astype(int)
            label = "GM 絕對係數相對排序（最大值=1；非因果重要度）"
            extra = {
                "coefficients": coefficients.tolist(),
                "diagnostics": {
                    key: value.tolist()
                    if isinstance(value, np.ndarray)
                    else str(value)
                    if isinstance(value, (float, np.floating)) and not np.isfinite(value)
                    else value
                    for key, value in model.diagnostics.items()
                },
                "gm_params": params,
            }
            warnings.append("係數受單位、共線性與列順序影響；圖是前兩個輸入欄位，不是 PCA。")
    order = np.argsort(-scores, kind="stable")
    ranking = [dict(feature=labels[i], score=float(scores[i]), direction=int(signs[i])) for i in order]
    return dict(
        coordinates=coordinates.tolist(),
        coordinate_labels=coordinate_labels,
        ranking=ranking,
        ranking_type=ranking_type,
        ranking_label=label,
        variance=None,
        method=engine,
        engine=engine,
        target=target,
        features=names,
        components=coordinates.shape[1],
        rows=len(values),
        excluded_constants=constant,
        warnings=warnings,
        **extra,
    )
