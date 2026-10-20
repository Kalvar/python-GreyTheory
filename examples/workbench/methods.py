"""Bounded form schemas for the local workbench; no executable parameter strings."""

import math


def number(key, label, default, low, high, hint, *, integer=False):
    return dict(
        key=key,
        label=label,
        default=default,
        min=low,
        max=high,
        type="int" if integer else "float",
        hint=hint,
    )


def choice(key, label, default, choices, hint):
    return dict(key=key, label=label, default=default, choices=choices, type="select", hint=hint)


ITER = number(
    "max_iter",
    "迭代上限",
    300,
    10,
    1000,
    "越大可能更接近收斂，但花費較久；先用 300，警告未收斂時再提高。",
    integer=True,
)
TOL = number("tol", "收斂容許誤差", 1e-6, 1e-9, 0.01, "越小越嚴格，也可能需要更多迭代。")
PCA_SCHEMAS = {
    "pca": dict(
        label="PCA · 標準線性投影",
        hint="先從這個開始。成分數越多，通常保留越多變異；變異量不是品質或預測準確率。",
        fields=[],
    ),
    "sparse": dict(
        label="Sparse PCA · 稀疏",
        hint="用稀疏成分整理較少的非零係數；不保證比標準 PCA 更準。",
        fields=[
            number("alpha", "稀疏強度 alpha", 1, 0, 20, "越大通常越稀疏；太大可能讓成分全為零。"),
            ITER,
            TOL,
        ],
    ),
    "kernel": dict(
        label="Kernel PCA · 非線性",
        hint="可展開彎曲的資料關係，沒有一般 PCA 的變異貢獻率。",
        fields=[
            choice(
                "kernel",
                "核函數",
                "rbf",
                ["rbf", "poly", "sigmoid", "linear"],
                "不知道先選 rbf；poly 使用多項式關係。",
            ),
            number("gamma", "gamma", 0.1, 1e-6, 10, "控制非線性尺度，和輸入標準化有關；先試 0.1。"),
            number("degree", "多項式次數", 3, 2, 5, "只在 poly 核函數生效。", integer=True),
        ],
    ),
    "robust": dict(
        label="Robust PCA · PCP 後投影",
        hint="把訓練矩陣拆成低秩與稀疏擾動，再做 PCA；新資料只投影，不會自動重新去除離群。",
        fields=[ITER, TOL],
    ),
    "robust_sparse": dict(
        label="Robust Sparse PCA",
        hint="同時估計稀疏編碼與訓練擾動；仍需檢查收斂。",
        fields=[
            number("alpha", "稀疏強度", 1, 0, 20, "越大越傾向稀疏。"),
            number("ridge", "L2 正則化", 0.001, 0, 10, "減少係數過度放大。"),
            number("kappa", "擾動懲罰", 1, 0.001, 20, "控制哪些差異留在稀疏擾動中。"),
            ITER,
            TOL,
        ],
    ),
    "adv": dict(
        label="Adv PCA · 擾動穩健",
        hint="在指定擾動半徑下求投影；適合測試擾動敏感度，不能取代製程驗證。",
        fields=[
            choice(
                "delta_mode",
                "擾動半徑",
                "adaptive",
                ["adaptive", "manual"],
                "adaptive 交由演算法估計；manual 使用下面的 delta。",
            ),
            number(
                "delta", "手動 delta", 0.1, 0, 10, "只有 manual 生效。數值和輸入尺度相關；DOE 已逐欄標準化。"
            ),
            number("smoothing", "更新平滑", 0.5, 0, 0.99, "0 到小於 1，先保留 0.5。"),
            ITER,
            number("inner_max_iter", "內層迭代上限", 200, 10, 1000, "與外層相乘會影響耗時。", integer=True),
            TOL,
        ],
    ),
}
ENGINES = {
    "pca": "GreyPCA + 特徵排序",
    "gra": "GRA / GreyFeatureSelector",
    "gm0n": "GM(0,N) 係數排序",
    "gm1n": "GM(1,N) 有序多變量分析",
    "quality": "BenefitNormalizer + 灰品質評分",
    "window_pca": "Grey 窗口特徵 → GreyPCA",
    "poisson": "GreyPCA + PoissonPCA（原始計數）",
}
GRA_FIELDS = [
    number("rho", "灰關聯辨識係數 rho", 0.5, 0.01, 1, "需大於 0 且不超過 1；通常先用 0.5。分數不是機率。"),
    choice(
        "normalization",
        "GRA 尺度處理",
        "zscore",
        ["zscore", "minmax", "none"],
        "不同單位先用 zscore；none 僅適合已可比較的尺度。",
    ),
    choice(
        "direction",
        "比較方向",
        "either",
        ["either", "positive"],
        "either 同時比較正負方向；不是宣稱因果方向。",
    ),
]
GM_FIELDS = [
    number("alpha", "背景係數 alpha", 0.5, 0, 1, "0.5 是相鄰累積值的平均。"),
    number(
        "ridge_alpha",
        "正則化 ridge",
        0.000001,
        0,
        10,
        "特徵太多或共線時可增加；係數大小仍受尺度和列順序影響。",
    ),
    choice(
        "background_mode",
        "背景值公式",
        "corrected",
        ["corrected", "legacy"],
        "corrected 為 alpha×目前值+(1-alpha)×前值；legacy 保留舊行為。",
    ),
]
WINDOW_FIELDS = [
    number("window_size", "窗口大小", 8, 3, 64, "連續通道／序列的筆數。不可大於輸入長度。", integer=True),
    number("stride", "窗口位移", 4, 1, 64, "每次移幾筆；不可大於窗口大小。", integer=True),
    number("alpha", "窗口背景係數", 0.5, 0, 1, "先用 0.5。"),
]


def validate(fields, supplied):
    if supplied is None:
        supplied = {}
    if not isinstance(supplied, dict) or set(supplied) - {f["key"] for f in fields}:
        raise ValueError("包含未支援的參數，請使用畫面列出的欄位。")
    result = {}
    for field in fields:
        value = supplied.get(field["key"], field["default"])
        if field["type"] == "select":
            if value not in field["choices"]:
                raise ValueError(f"{field['label']} 選項不正確。")
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field['label']} 需要有限數字。")
            if not field["min"] <= value <= field["max"] or (field["type"] == "int" and int(value) != value):
                raise ValueError(f"{field['label']} 範圍為 {field['min']} 至 {field['max']}。")
            if field["type"] == "int":
                value = int(value)
        result[field["key"]] = value
    return result


def pca_params(method, supplied=None):
    if method not in PCA_SCHEMAS:
        raise ValueError("不支援的 PCA 方法。")
    # Omitted forms preserve existing API defaults; an explicit form applies its displayed defaults.
    if supplied is None:
        return {}
    values = validate(PCA_SCHEMAS[method]["fields"], supplied)
    if method == "adv":
        mode = values.pop("delta_mode")
        if mode == "adaptive":
            values["delta"] = "adaptive"
    return values
