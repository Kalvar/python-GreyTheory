"""Synthetic application experiments. Routing/assignment use explicit optimization, not grey forecasts."""

from itertools import permutations
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from greytheory import GM11
from greytheory.analysis import BenefitNormalizer, GreyPCA, grade_quality
from .methods import GM_FIELDS, WINDOW_FIELDS, choice, number, pca_params, validate

SEED = number(
    "seed",
    "模擬亂數種子",
    7,
    0,
    99999,
    "相同種子與參數產生相同情境；更換種子可測試另一批假資料。",
    integer=True,
)
PCA_METHOD = choice(
    "method",
    "PCA 方法",
    "pca",
    ["pca", "sparse", "kernel", "robust", "robust_sparse", "adv"],
    "下方會顯示此方法的專用參數。",
)
SCENARIOS = {
    "research": dict(
        label="研究模型 · RL-FGM / GINN / Grey–Fuzzy GPR",
        hint="選方法後保留預設值執行。這些是研究實作，請查看診斷與保留測試，不是已驗證的機台模型。",
        fields=[
            SEED,
            choice("pca_mode", "搭配 PCA", "off", ["off", "on"],
                   "on 先用訓練資料擬合 PCA；時序以三個合成通道示範，品質使用六個製程特徵。"),
            PCA_METHOD,
            number("components", "主成分數", 2, 1, 3,
                   "時序預測後還原三個通道；圖表顯示第一個通道。品質可靠度只反映保留的主成分。", integer=True),
            choice(
                "tool",
                "研究方法",
                "rlfgm",
                ["rlfgm", "ginn", "fginn", "grey_fuzzy_gpr"],
                "RL-FGM 為公式核心；GINN／FGINN 與 Grey–Fuzzy GPR 是有註明差異的工程版本。",
            ),
            choice(
                "order_mode",
                "階數選擇",
                "auto",
                ["auto", "fixed"],
                "auto 只用訓練資料內的時間保留段選階數，沒有使用最終回測資料。",
            ),
            number(
                "order",
                "分數階數",
                0.5,
                0.05,
                1,
                "RL-FGM 固定階數或 FGINN 生效；FGINN 的 1 與 beta=1 回到一般灰色先驗。",
            ),
            number("beta", "tM beta", 1, 0.1, 2, "FGINN 的算子尺度參數，先用 1。"),
            number("window", "歷史窗口", 3, 3, 8, "神經網路與灰色先驗各使用這幾筆過去值。", integer=True),
            number("grey_weight", "灰色先驗權重", 0.1, 0, 1, "0 只訓練一般網路；增加權重不保證預測更準。"),
            number(
                "iterations",
                "網路迭代上限",
                500,
                20,
                1500,
                "未收斂時會顯示警告，模型不會自動替換。",
                integer=True,
            ),
            number(
                "grey_strength",
                "GRA 核尺度強度",
                1,
                0,
                1,
                "0 對應相同設定的一般 GPR；模糊可靠度不會改寫預測值。",
            ),
        ],
    ),
    "optimization": dict(
        label="最佳化 · 快速分析四步驟",
        hint="先按執行，再切換四個圖表。訓練、正常校正與測試資料分開；這裡只使用合成資料。",
        fields=[
            SEED,
            number(
                "repeats",
                "排名重抽樣次數",
                40,
                10,
                200,
                "次數增加可減少抽樣波動，也會增加運算時間。",
                integer=True,
            ),
            choice(
                "search_family",
                "搜尋方法範圍",
                "pca",
                ["pca", "pca_sparse"],
                "先用一般 PCA；pca_sparse 加入 Sparse PCA 比較，通常較慢。",
            ),
            number(
                "trials",
                "最多比較幾組",
                8,
                2,
                12,
                "從有限候選隨機抽取；固定種子可重現候選，不保證全域最佳。",
                integer=True,
            ),
            number(
                "false_alarm_rate",
                "正常資料誤報率設定",
                0.05,
                0.02,
                0.2,
                "只在可交換的正常資料假設下控制邊際誤報；不是每批的保證。",
            ),
            number(
                "shift",
                "模擬偏移強度",
                2,
                0,
                4,
                "只改測試副本的最後 12 筆；0 代表沒有刻意偏移，不改訓練或校正。",
            ),
            number(
                "candidates",
                "多目標候選數",
                30,
                10,
                100,
                "產生合成候選設定，保留品質損失與成本的折衷方案。",
                integer=True,
            ),
            number(
                "cost_limit", "模擬成本上限", 2.5, 0, 3, "超過上限的候選排除；這是模擬單位，不是真實價格。"
            ),
        ],
    ),
    "routes": dict(
        label="運輸 · 配送路線",
        hint="Grey 品質評分比較路線偏好；路線本身由小規模完整枚舉求解。這不是即時導航或多車 VRP。",
        fields=[
            SEED,
            number("stops", "配送點數", 6, 3, 8, "最多 8 點，以完整枚舉比較所有拜訪順序。", integer=True),
            choice(
                "objective",
                "選路目標",
                "grey",
                ["grey", "distance"],
                "grey 使用三項偏好；distance 選最短幾何距離。",
            ),
            number("distance_weight", "距離權重", 1, 0, 10, "越重視省里程就調高。"),
            number("time_weight", "行駛時間權重", 1, 0, 10, "時間含模擬路段壅塞。"),
            number("late_weight", "遲到權重", 2, 0, 10, "時間窗是軟性偏好，並非禁止遲到的硬限制。"),
        ],
    ),
    "drivers": dict(
        label="運輸 · 司機與訂單媒合",
        hint="Grey 評分每個可行配對，再用匈牙利指派法最大化總分；單次每位司機最多接一單。",
        fields=[
            SEED,
            number(
                "drivers", "司機人數", 5, 2, 8, "不同司機有不同位置、載重、技能與可用時間。", integer=True
            ),
            number("jobs", "訂單數", 6, 2, 8, "訂單較多或不符合資格時會保留未媒合。", integer=True),
            number("distance_weight", "接貨距離權重", 2, 0, 10, "較大的值偏好離接貨點近的司機。"),
            number("reliability_weight", "歷史準時率權重", 1, 0, 10, "模擬準時率，不是模型預測。"),
            number("rating_weight", "評分權重", 1, 0, 10, "評分為模擬數值；硬性資格不會被高分補償。"),
        ],
    ),
    "art": dict(
        label="藝術品 · 模擬補畫區域線索",
        hint="參考光譜地圖訓練 PCA，再對另一張模擬地圖計算重建差異。異常區是調查線索，不能直接判定補畫或年代。",
        fields=[
            choice(
                "art_source",
                "示範資料來源",
                "spectral",
                ["spectral", "ai_images"],
                "spectral 使用合成光譜；ai_images 直接分析兩張 AI 絹畫圖片的顏色與紋理。",
            ),
            SEED,
            PCA_METHOD,
            number(
                "components",
                "主成分數",
                3,
                1,
                6,
                "用乾淨參考圖擬合；主成分太多也可能重建異常。",
                integer=True,
            ),
            number(
                "quantile",
                "參考誤差門檻分位",
                0.95,
                0.8,
                0.999,
                "以參考圖重建誤差分位數設門檻，不是已校準的信心水準。",
            ),
            number("strength", "模擬新增材料強度", 0.6, 0.1, 1, "越小越接近原始材料，偵測通常更困難。"),
        ],
    ),
    "forecast": dict(
        label="灰色預測 · 運輸訂單量",
        hint="先用最後 4 天做時間序列回測，再用全部歷史預測未來。Convolution 是兩層 GM11，不是 CNN。",
        fields=[
            SEED,
            choice(
                "forecast_method", "預測方法", "gm11", ["gm11", "convolution"], "一般 GM11 或兩層滑動窗口。"
            ),
            number("horizon", "預測幾期", 4, 1, 10, "越遠越不確定，先試 2–4 期。", integer=True),
            *GM_FIELDS,
            number(
                "window_size",
                "窗口大小",
                4,
                3,
                8,
                "只在 convolution 生效；每個窗口用幾筆歷史。",
                integer=True,
            ),
            number("stride", "窗口位移", 1, 1, 3, "只在 convolution 生效。", integer=True),
        ],
    ),
    "trajectory": dict(
        label="筆跡 / 移動軌跡 · 多維特徵",
        hint="模擬 2D／3D 軌跡 → 重採樣 → Grey 窗口 → PCA。這是軌跡形狀展示，沒有真實作者標籤。",
        fields=[
            SEED,
            PCA_METHOD,
            number("dimensions", "空間維度", 3, 2, 4, "2D、3D、4D 皆可；畫面只畫前兩維。", integer=True),
            number("n_points", "重採樣點數", 32, 16, 64, "把不同長度軌跡轉成固定長度。", integer=True),
            *WINDOW_FIELDS,
        ],
    ),
    "spectral": dict(
        label="光譜工具 · 分解 / 基線 / 擬峰",
        hint="使用明確的合成混合光譜，讓你實測已有的光譜工具；成分權重不是元素濃度。",
        fields=[
            SEED,
            choice(
                "tool",
                "光譜方法",
                "nmf",
                ["nmf", "mcr", "mnf", "mlpca", "baseline", "peaks", "element_lines"],
                "選擇後顯示用途、必要資料與條件。",
            ),
            number("components", "分解成分數", 3, 1, 4, "NMF、MCR、MNF、MLPCA 生效。", integer=True),
            number(
                "iterations", "迭代上限", 100, 10, 500, "迭代式分解生效；警告未收斂時可調高。", integer=True
            ),
            number("lam", "基線平滑 lam", 10000, 1, 1e8, "AsLS 基線使用，越大越平滑。"),
            number(
                "p",
                "基線不對稱 p",
                0.01,
                0.001,
                0.99,
                "AsLS 使用，先用 0.01；可能移除真實訊號，不會自動套用至 XRF。",
            ),
            number("sigma", "擬峰寬度", 0.12, 0.03, 0.5, "示範中的高斯峰寬；真實數據需由儀器校正取得。"),
            number(
                "atomic_number",
                "原子序",
                29,
                1,
                98,
                "element_lines 查 xraylib 譜線；不會推論濃度。",
                integer=True,
            ),
        ],
    ),
    "semiconductor": dict(
        label="半導體 · PLS / 監控 / 參數建議",
        hint="沿用已生成的 15 筆模擬 DOE；不是實際機台調參或製程驗證。",
        fields=[
            SEED,
            choice("process", "製程", "pvd", ["pvd", "cvd"], "兩種製程分開分析。"),
            choice(
                "tool",
                "製程工具",
                "pls",
                ["pls", "monitor", "suggest", "lhs"],
                "PLS 做保留資料預測；監控用 Q/T²；GP 提示候選；LHS 產生試驗設定。",
            ),
            number("components", "主成分 / 潛在變量", 2, 1, 4, "PLS、監控生效。", integer=True),
            number("quantile", "監控門檻分位", 0.95, 0.8, 0.999, "從訓練批次估計，並非製程規格線。"),
            number("candidates", "候選 / 試驗數", 32, 8, 256, "GP 候選點或 LHS 點數。", integer=True),
        ],
    ),
}


def inputs(seed=7):
    rng = np.random.default_rng(seed)
    stops = np.vstack([[5, 5], rng.uniform(0, 10, (8, 2))])
    drivers = [
        dict(
            id=f"D{i + 1}",
            x=float(rng.uniform(0, 10)),
            y=float(rng.uniform(0, 10)),
            capacity_kg=int(rng.integers(200, 1000)),
            skill=int(rng.integers(1, 4)),
            available_min=int(rng.integers(60, 240)),
            reliability=float(rng.uniform(0.8, 0.99)),
            rating=float(rng.uniform(3.5, 5)),
        )
        for i in range(8)
    ]
    jobs = [
        dict(
            id=f"J{i + 1}",
            x=float(rng.uniform(0, 10)),
            y=float(rng.uniform(0, 10)),
            load_kg=int(rng.integers(100, 900)),
            skill=int(rng.integers(1, 4)),
            duration_min=int(rng.integers(30, 150)),
        )
        for i in range(8)
    ]
    days = np.arange(28)
    demand = 80 * np.exp(0.018 * days) + 4 * np.sin(days * 2 * np.pi / 7) + rng.normal(0, 1.2, len(days))
    return dict(
        seed=seed,
        synthetic=True,
        units="Coordinates are synthetic km, not roads. Demand is simulated orders/day.",
        stops=stops.tolist(),
        drivers=drivers,
        jobs=jobs,
        orders=demand.round(4).tolist(),
    )


def table(title, rows):
    return dict(title=title, rows=rows)


def routes(p):
    data = inputs(p["seed"])
    points = np.array(data["stops"])[: p["stops"] + 1]
    n = len(points)
    distance = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
    rng = np.random.default_rng(p["seed"] + 11)
    congestion = rng.uniform(1, 2, (n, n))
    times = distance * congestion * 2.2
    deadlines = np.r_[0, np.linspace(25, 65, n - 1)]
    orders = list(permutations(range(1, n)))
    costs = []
    for order in orders:
        route = (0, *order, 0)
        elapsed = late = km = 0.0
        for a, b in zip(route, route[1:]):
            km += distance[a, b]
            elapsed += times[a, b]
            if b:
                late += max(0, elapsed - deadlines[b])
                elapsed += 4
        costs.append([km, elapsed, late])
    costs = np.asarray(costs)
    weights = [p["distance_weight"], p["time_weight"], p["late_weight"]]
    bounds = np.column_stack((costs.min(axis=0), costs.max(axis=0)))
    bounds[:, 1] = np.maximum(bounds[:, 1], bounds[:, 0] + 1)
    benefits = BenefitNormalizer(["smaller"] * 3, bounds=bounds).fit_transform(costs)
    grades = grade_quality(benefits, weights=weights)
    best = int(np.argmin(costs[:, 0])) if p["objective"] == "distance" else int(grades.ranking[0])
    baseline = 0
    order = [0, *orders[best], 0]
    rows = [
        dict(
            candidate="選取路線",
            distance_km=round(costs[best, 0], 3),
            duration_min=round(costs[best, 1], 3),
            lateness_min=round(costs[best, 2], 3),
            grey_score=float(grades.scores[best]),
        ),
        dict(
            candidate="原始點順序",
            distance_km=round(costs[baseline, 0], 3),
            duration_min=round(costs[baseline, 1], 3),
            lateness_min=round(costs[baseline, 2], 3),
            grey_score=float(grades.scores[baseline]),
        ),
    ]
    return dict(
        title="配送路線比較",
        summary=f"完整比較 {len(orders):,} 條路線；選路目標：{p['objective']}。",
        tables=[table("成本與偏好", rows)],
        diagram=dict(type="route", points=points.tolist(), route=order, baseline=[0, *orders[baseline], 0]),
        warnings=[
            "距離是平面直線，時間為模擬壅塞；沒有實際道路、載重、休息、多車或硬性時間窗。Grey 用於候選偏好評分；完整枚舉負責搜尋。這個結果不代表真實配送的最佳路徑。"
        ],
        inputs=data,
    )


def drivers(p):
    data = inputs(p["seed"])
    people = data["drivers"][: p["drivers"]]
    jobs = data["jobs"][: p["jobs"]]
    features = []
    feasible = []
    for job in jobs:
        for driver in people:
            distance = float(np.hypot(driver["x"] - job["x"], driver["y"] - job["y"]))
            features.append([distance, driver["reliability"], driver["rating"]])
            feasible.append(
                job["load_kg"] <= driver["capacity_kg"]
                and job["skill"] <= driver["skill"]
                and job["duration_min"] + distance * 2 <= driver["available_min"]
            )
    benefits = BenefitNormalizer(
        ["smaller", "larger", "larger"], bounds=[[0, 15], [0, 1], [1, 5]]
    ).fit_transform(features)
    grades = grade_quality(
        benefits, weights=[p["distance_weight"], p["reliability_weight"], p["rating_weight"]]
    ).scores
    grades = grades.reshape(len(jobs), len(people))
    eligible = np.array(feasible).reshape(grades.shape)
    score = np.column_stack([np.where(eligible, grades, -1e6), np.zeros((len(jobs), len(jobs)))])
    ii, jj = linear_sum_assignment(score, maximize=True)
    rows = []
    edges = []
    for i, j in zip(ii, jj):
        matched = j < len(people) and eligible[i, j]
        rows.append(
            dict(
                job=jobs[i]["id"],
                driver=people[j]["id"] if matched else "未媒合",
                grey_score=float(grades[i, j]) if matched else None,
                reason="符合載重、技能、可用時間" if matched else "資格不足或整體指派保留資源",
            )
        )
        if matched:
            edges.append([int(j), int(i)])
    return dict(
        title="司機 × 訂單配對",
        summary=f"{len(edges)} / {len(jobs)} 筆訂單媒合。每位司機最多一單；未媒合不會被強制指派。",
        tables=[table("配對結果", rows), table("司機條件", people), table("訂單條件", jobs)],
        diagram=dict(type="matching", drivers=people, jobs=jobs, edges=edges),
        warnings=[
            "品質加權可互補，但不符合載重、技能或時間的配對已排除。這是單批次、單司機單訂單的指派示範，未處理多站路線、法定工時或即時交通。"
        ],
        inputs=data,
    )


def art_data(seed=7, strength=0.6):
    rng = np.random.default_rng(seed)
    h = w = 12
    energy = np.arange(256) * 0.05
    templates = np.array([np.exp(-0.5 * ((energy - c) / 0.12) ** 2) for c in (2.2, 5.8, 8.1)])
    yy, xx = np.mgrid[:h, :w]
    groups = np.minimum(xx // 4, 2).ravel()
    weights = np.eye(3)[groups] * 0.7 + 0.1
    expected = 4 + 180 * weights @ templates
    reference = rng.poisson(expected)
    mask = ((xx >= 7) & (xx <= 9) & (yy >= 3) & (yy <= 8)).ravel()
    changed = expected + strength * 160 * mask[:, None] * np.exp(-0.5 * ((energy - 10.4) / 0.12) ** 2)
    observed = rng.poisson(changed)
    return energy, reference, observed, mask, (h, w)


def art_images(p, params):
    from examples.demos.artwork import ASSETS, compare_artwork_images

    result = compare_artwork_images(
        ASSETS / "silk_reference.png",
        ASSETS / "silk_observed.png",
        method=p["method"],
        components=p["components"],
        quantile=p["quantile"],
        method_params=params,
    )
    ranking = np.argsort(result["observed_errors"])[::-1][:12]
    return dict(
        title="AI 絹畫圖片差異：顏色與紋理線索",
        summary=f"標記 {result['flagged_positions']} / 144 個區塊；直接讀取兩張 AI PNG，模型只用參考圖擬合。",
        tables=[
            table(
                "圖片差異指標",
                [
                    dict(
                        threshold=result["threshold"],
                        flagged_positions=result["flagged_positions"],
                        regions=144,
                    )
                ],
            ),
            table(
                "優先查看的區塊",
                [
                    dict(
                        row=int(i // 12),
                        column=int(i % 12),
                        reconstruction_error=result["observed_errors"][i],
                        paired_feature_distance=result["paired_feature_distance"][i],
                    )
                    for i in ranking
                ],
            ),
        ],
        diagram=dict(
            type="art_images",
            shape=[12, 12],
            values=result["observed_errors"],
            flags=result["flags"],
            reference="../../data/demo/artwork/silk_reference.png",
            observed="../../data/demo/artwork/silk_observed.png",
        ),
        warnings=[
            "同圖比較也可能產生高重建誤差圈選；請用「專家查看」的成對差異排序覆核，不能把圈選數當成變更數。這是 AI 虛構絹畫，分析 RGB 圖片區塊的顏色、紋理與 Grey 窗口特徵，不是 XRF、元素濃度或真實館藏。AI 編輯可能改變指定區域以外的像素；沒有精確真值，不能計算補畫辨識準確率。拍攝、光線與對位差異也會影響標記。"
        ],
        inputs=dict(
            synthetic=True,
            source="AI-generated fictional silk painting pair",
            provenance=result["provenance"],
            ground_truth=None,
            pipeline="RGB patches → Grey windows → reference-only GreyPCA → reconstruction error",
            sources="../../data/demo/artwork/provenance.json",
        ),
    )


def art(p, params):
    if p.get("art_source") == "ai_images":
        return art_images(p, params)
    from .analysis import spectra_dataset

    energy, reference, observed, truth, shape = art_data(p["seed"], p["strength"])
    ref = spectra_dataset("reference", reference, energy).values
    obs = spectra_dataset("observed", observed, energy).values
    ref /= ref.sum(axis=1, keepdims=True)
    obs /= obs.sum(axis=1, keepdims=True)
    model = GreyPCA(n_components=p["components"], method=p["method"], method_params=params).fit(ref)

    def error(x):
        return np.mean((x - model.inverse_transform(model.transform(x))) ** 2, axis=1)

    train_error = error(ref)
    test_error = error(obs)
    threshold = float(np.quantile(train_error, p["quantile"]))
    flag = test_error > threshold
    return dict(
        title="藝術品區域差異：先標記，再由專家查證",
        summary=f"標記 {int(flag.sum())} / {len(flag)} 個位置。模型只使用另一張模擬參考圖擬合。",
        tables=[
            table(
                "僅對此模擬例有效的數值",
                [
                    dict(
                        threshold=threshold,
                        simulated_changed_pixels=int(truth.sum()),
                        true_positive=int(np.sum(flag & truth)),
                        false_positive=int(np.sum(flag & ~truth)),
                        missed=int(np.sum(~flag & truth)),
                    )
                ],
            )
        ],
        diagram=dict(
            type="heatmap",
            shape=list(shape),
            values=test_error.tolist(),
            truth=truth.astype(int).tolist(),
            flags=flag.astype(int).tolist(),
        ),
        warnings=[
            "假資料只有人為設定的材料峰，未模擬真實顏料、層厚、底材、老化或儀器效應。標記的是光譜差異，不是補畫、偽作、年代或修復結論。門檻來自訓練誤差，尚未用獨立標準品校準。"
        ],
        inputs=dict(
            synthetic=True,
            energy_keV=energy.tolist(),
            reference_counts=reference.tolist(),
            observed_counts=observed.tolist(),
            synthetic_changed_mask=truth.tolist(),
        ),
    )


def forecast(p, series=None):
    values = np.array(inputs(p["seed"])["orders"] if series is None else series, dtype=float)
    if (
        values.ndim != 1
        or not 12 <= len(values) <= 120
        or not np.isfinite(values).all()
        or np.any(values <= 0)
    ):
        raise ValueError("請提供 12–120 個有限正數，依時間先後排列。")
    settings = {key: p[key] for key in ("alpha", "ridge_alpha", "background_mode")}
    if p["forecast_method"] == "convolution":
        settings.update(window_size=p["window_size"], stride=p["stride"])
    training = values[:-4]
    model = GM11(**settings).fit(training)
    backtest = np.asarray(model.predict(4), dtype=float)
    future = np.asarray(GM11(**settings).fit(values).predict(p["horizon"]), dtype=float)
    mae = float(np.mean(np.abs(backtest - values[-4:])))
    return dict(
        title="灰色序列預測與回測",
        summary=f"最後 4 期先保留不參與回測訓練；MAE = {mae:.3f}。之後用完整歷史預測未來 {p['horizon']} 期。",
        tables=[
            table(
                "保留 4 期回測",
                [
                    dict(period=len(training) + i + 1, observed=float(a), predicted=float(b))
                    for i, (a, b) in enumerate(zip(values[-4:], backtest))
                ],
            ),
            table(
                "未來預測",
                [dict(period=len(values) + i + 1, predicted=float(v)) for i, v in enumerate(future)],
            ),
        ],
        diagram=dict(
            type="series", observed=values.tolist(), forecast=future.tolist(), backtest=backtest.tolist()
        ),
        warnings=[
            "模擬訂單含趨勢與週期，GM11 不會自動建模假日、季節性或突發事件。單次 4 期回測不代表未來表現；用自己的數據時請依時間順序輸入。"
        ],
        inputs=dict(orders=values.tolist(), synthetic=series is None),
    )


def trajectory(p, params):
    from greytheory.features import GreyWindowFeatures, TrajectoryFeatures

    rng = np.random.default_rng(p["seed"])
    paths = []
    for i in range(18):
        t = np.linspace(0, 1, 40 + i % 7)
        style = i % 3
        channels = [t, np.sin(t * (style + 1) * np.pi) + rng.normal(0, 0.02, len(t))]
        for d in range(2, p["dimensions"]):
            channels.append(np.cos(t * (d + style) * np.pi) * 0.3 + rng.normal(0, 0.01, len(t)))
        paths.append(np.column_stack(channels))
    ref = np.arange(18) < 12
    extractor = TrajectoryFeatures(n_points=p["n_points"], center=True, scale=True)
    sequence = extractor.fit(paths[:12]).transform(paths)
    windows = GreyWindowFeatures(
        window_size=p["window_size"], stride=p["stride"], alpha=p["alpha"], boundary_channel=-1
    )
    values = windows.fit(sequence[:12]).transform(sequence)
    model = GreyPCA(n_components=2, standardize=True, method=p["method"], method_params=params).fit(
        values[ref]
    )
    coordinates = model.transform(values)
    return dict(
        title="多維軌跡 → Grey 窗口 → PCA",
        summary=f"18 條 {p['dimensions']}D 假軌跡；12 條擬合、6 條只轉換。抽出 {values.shape[1]} 個窗口特徵。",
        tables=[
            table(
                "投影",
                [
                    dict(
                        sample=i + 1,
                        split="reference" if i < 12 else "query",
                        PC1=float(v[0]),
                        PC2=float(v[1]),
                    )
                    for i, v in enumerate(coordinates)
                ],
            )
        ],
        diagram=dict(
            type="trajectories",
            paths=[path[:, :2].tolist() for path in paths[:6]],
            coordinates=coordinates.tolist(),
        ),
        warnings=[
            "前三類形狀是生成器設定，不是真實作者。沒有從圖片推測速度、壓力或時間；這裡只提供有空間座標的軌跡。圖只顯示前兩個空間維度，但特徵擷取使用全部維度。"
        ],
        inputs=dict(synthetic=True, paths=[v.tolist() for v in paths]),
    )


def spectral(p):
    from greytheory.spectroscopy import (
        baseline_correct,
        element_lines,
        fit_mcr_als,
        fit_mlpca,
        fit_mnf,
        fit_nmf,
        fit_peaks,
    )

    rng = np.random.default_rng(p["seed"])
    energy = np.linspace(0, 8, 96)
    templates = np.array([np.exp(-0.5 * ((energy - c) / 0.12) ** 2) for c in (1.2, 4, 6.3, 7.2)])
    expected = 5 + 100 * rng.dirichlet([1, 1, 1, 1], size=32) @ templates
    counts = rng.poisson(expected).astype(float)
    tool = p["tool"]
    tables = []
    curves = []
    note = ""
    diagnostics = {}
    input_data = dict(synthetic=True, counts=counts.tolist(), energy_keV=energy.tolist())
    messages = ["所有輸入都是合成數值。分解成分、峰幅及參考譜線不能直接當成材料身分或元素濃度。"]
    if tool == "baseline":
        corrected, baseline = baseline_correct(counts, lam=p["lam"], p=p["p"], x=energy)
        curves = [counts[0].tolist(), baseline[0].tolist(), corrected[0].tolist()]
        note = "原始、AsLS 基線、扣除基線後的第一條光譜。扣除後可出現負值。"
    elif tool == "peaks":
        r = fit_peaks(energy, counts[0], [1.2, 4, 6.3, 7.2], sigma=p["sigma"])
        curves = [counts[0].tolist(), r["fitted_counts"].tolist()]
        tables = [
            table(
                "峰幅（不是濃度）",
                [dict(center_keV=c, amplitude=float(a)) for c, a in zip([1.2, 4, 6.3, 7.2], r["amplitudes"])],
            )
        ]
    elif tool == "element_lines":
        tables = [table("xraylib 參考線", element_lines(p["atomic_number"], energy_range=(0, 1000)))]
        curves = [counts[0].tolist()]
        note = "參考譜線查詢與這組任意峰位置的假資料無對應關係。"
    elif tool == "mnf":
        # Enough independent noisy pixels for a full-rank, 16-band noise covariance.
        cube = rng.normal(0, 1, (20, 20, 16)) + np.linspace(0, 4, 20)[:, None, None]
        z, _ = fit_mnf(cube, p["components"])
        tables = [table("MNF 資料形狀", [dict(height=20, width=20, bands=16, retained=p["components"])])]
        input_data = dict(
            synthetic=True, cube=cube.tolist(), noise_assumption="stationary adjacent-pixel differences"
        )
        energy = np.arange(16)
        curves = [cube[0, 0].tolist()]
        note = f"MNF 實際轉換為 {z.shape}；鄰近像素差用於估噪，需符合平穩雜訊假設。此例不是 XRF 計數。"
    else:
        if tool == "nmf":
            r = fit_nmf(counts, p["components"], max_iter=p["iterations"])
        elif tool == "mcr":
            r = fit_mcr_als(counts, templates[: p["components"]] + 0.01, max_iter=p["iterations"])
        else:
            r = fit_mlpca(counts, expected, p["components"], max_iter=p["iterations"])
        diagnostics = r.diagnostics
        if diagnostics.get("converged") is False or diagnostics.get("exit_flags", {}).get(
            "exit_max_iter_reached"
        ):
            messages.append("分解尚未確認收斂或已達迭代上限；請調整參數，並查看下載 JSON 的 diagnostics。")
        curves = [counts[0].tolist(), r.reconstruction[0].tolist()]
        tables = [
            table(
                "分解診斷",
                [dict(mse=float(np.mean((counts - r.reconstruction) ** 2)), components=p["components"])],
            )
        ]
        note = "MCR 使用生成器已知峰形初始化；MLPCA 使用生成器已知的正值 Poisson 方差，真實資料需另提供噪聲模型。"
    return dict(
        title=f"光譜工具：{tool}",
        summary=note or "比較原始與重建光譜。",
        tables=tables,
        diagram=dict(type="curves", x=energy.tolist(), curves=curves),
        warnings=messages,
        diagnostics=diagnostics,
        inputs=input_data,
    )


def semiconductor(p):
    from greytheory.semiconductor import (
        ProcessMonitor,
        QualityPLS,
        latin_hypercube,
        rank_features,
        suggest_parameters,
    )
    from .analysis import read_csv
    from .doe import DATA, SPECS

    process = p["process"]
    d = read_csv((DATA / f"{process}_15.csv").read_bytes(), spec=SPECS[process])
    X = d.values[:, :6]
    y = d.values[:, 6]
    rng = np.random.default_rng(p["seed"])
    order = rng.permutation(len(X))
    train = order[:11]
    test = order[11:]
    tool = p["tool"]
    bounds = list(SPECS[process]["features"].values())
    diagram = None
    if tool == "pls":
        model = QualityPLS(p["components"]).fit(X[train], y[train])
        pred = model.predict(X[test]).ravel()
        rows = [
            dict(sample=d.labels[i], observed=float(y[i]), predicted=float(v)) for i, v in zip(test, pred)
        ]
        rank = rank_features(X[train], y[train])
        extra = table(
            "僅訓練資料的 rank_features（正向 GRA）",
            [dict(feature=name, score=float(score)) for name, score in zip(d.defaults, rank["scores"])],
        )
        summary = f"11 筆訓練、4 筆保留測試；膜厚 MAE {np.mean(np.abs(pred - y[test])):.3f} nm。"
        tables = [table("PLS 保留測試", rows), extra]
    elif tool == "monitor":
        model = ProcessMonitor(p["components"], quantile=p["quantile"]).fit(X[train])
        stats = model.score_samples(X[test])
        flag = model.predict(X[test])
        tables = [
            table(
                "Q / T² 監控",
                [
                    dict(sample=d.labels[i], q=float(q), t2=float(t), flag=bool(f))
                    for i, q, t, f in zip(test, stats["q"], stats["t2"], flag)
                ],
            )
        ]
        summary = f"Q 門檻 {model.q_limit_:.3g}；T² 門檻 {model.t2_limit_:.3g}。DOE 本身涵蓋多種設定，偏離不代表不良。"
    elif tool == "suggest":
        # Example objective: minimize measured uniformity error, never maximize thickness blindly.
        r = suggest_parameters(
            X, d.values[:, 7], bounds, n_candidates=p["candidates"], maximize=False, random_state=p["seed"]
        )
        rows = [dict(parameter=k, candidate=float(v)) for k, v in zip(d.defaults, r["parameters"])]
        tables = [table("候選設定（只供模擬）", rows)]
        summary = f"以均勻度誤差越小越好搜尋；預測 {r['predicted_quality']:.3f}%，GP 標準差 {r['model_std']:.3f}。不保證候選比現有設定更好。"
    else:
        candidates = latin_hypercube(bounds, p["candidates"], random_state=p["seed"])
        tables = [
            table(
                "LHS 設定（未量測，沒有品質結果）",
                [dict(zip(d.defaults, map(float, row))) for row in candidates],
            )
        ]
        summary = f"生成 {len(candidates)} 個界限內設定，不會自動知道其品質。"
    return dict(
        title=f"{process.upper()} 製程工具：{tool}",
        summary=summary,
        tables=tables,
        diagram=diagram,
        warnings=[
            "僅 15 筆人造資料，4 筆保留測試不能代表量產能力。監控門檻不是產品規格；參數候選沒有安全性保證，不能直接送入真實機台。"
        ],
        inputs=dict(synthetic=True, source=f"{process}_15.csv"),
    )


def run_scenario(key, options=None, *, method_parameters=None, series=None):
    if key not in SCENARIOS:
        raise ValueError("不支援的情境。")
    p = validate(SCENARIOS[key]["fields"], options)
    params = pca_params(p["method"], method_parameters) if "method" in p else {}
    if key == "routes":
        result = routes(p)
    elif key == "drivers":
        result = drivers(p)
    elif key == "art":
        result = art(p, params)
    elif key == "forecast":
        result = forecast(p, series)
    elif key == "trajectory":
        result = trajectory(p, params)
    elif key == "spectral":
        result = spectral(p)
    elif key == "research":
        from .research import run_research

        result = run_research(p, params)
    elif key == "optimization":
        from .optimization import run_optimization

        result = run_optimization(p)
    else:
        result = semiconductor(p)
    return dict(scenario=key, parameters=p, method_parameters=params, **result)


def generate(output=None):
    output = Path(output or Path(__file__).resolve().parents[2] / "data/demo" / "scenarios")
    output.mkdir(parents=True, exist_ok=True)
    energy, reference, observed, mask, shape = art_data()
    data = inputs()
    data["art"] = dict(
        shape=shape,
        energy_keV=energy.tolist(),
        reference_counts=reference.tolist(),
        observed_counts=observed.tolist(),
        changed_mask=mask.tolist(),
    )
    data["provenance"] = (
        "Generated by examples.workbench.scenarios with numpy RNG seed 7; all toy data, MIT; no real drivers, addresses, artworks, or handwriting authors."
    )
    (output / "synthetic_inputs.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


if __name__ == "__main__":
    print(generate())
