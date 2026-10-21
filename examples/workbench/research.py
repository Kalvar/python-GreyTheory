"""Research-model demonstrations with explicit implementation provenance."""

import numpy as np

from greytheory.research import RLFGM, GINN, FGINN, GreyPCAForecast
from ..research_models import make_series, quality_comparison


def run_research(p, method_params=None):
    use_pca = p.get("pca_mode", "off") == "on"
    pca_options = dict(pca_method=p["method"], n_components=p["components"], method_params=method_params) if use_pca else {}
    tool = p["tool"]
    if tool == "grey_fuzzy_gpr":
        result = quality_comparison(p["seed"], p["grey_strength"], **pca_options)
        selected = result["models"][1]
        tables = [
            dict(
                title="保留資料比較",
                rows=[
                    {
                        k: r[k]
                        for k in [
                            "model",
                            "rmse",
                            "in_domain_rmse",
                            "shifted_domain_rmse",
                            "heuristic_2std_coverage",
                        ]
                    }
                    for r in result["models"]
                ],
            ),
            dict(
                title="預測與模糊可靠度",
                rows=[
                    dict(
                        sample=i + 1,
                        observed=float(actual),
                        prediction=float(pred),
                        std=float(std),
                        reliability=float(grade),
                        input_support=float(support),
                        label=label,
                    )
                    for i, (actual, pred, std, grade, support, label) in enumerate(
                        zip(
                            result["observed"],
                            selected["prediction"],
                            selected["std"],
                            selected["reliability"]["grade"],
                            selected["reliability"]["input_support"],
                            selected["reliability"]["label"],
                        )
                    )
                ],
            ),
        ]
        return dict(
            title="Grey–Fuzzy GPR · 獨立設計",
            summary="60 筆訓練、40 筆保留測試；最後 10 筆刻意偏離訓練範圍。",
            diagram=dict(type="research_gpr", **result),
            tables=tables,
            warnings=[
                "可靠度是模糊規則評分，不是正確率或校準機率。±2 標準差是 GP 模型範圍，不保證實際涵蓋率。",
                "GRA 核尺度與模糊規則為本專案設計，尚未重現 IGF-GPR 論文；結果不保證優於一般 GPR。",
                *(["PCA 與 GRA 只擬合訓練資料；可靠度只在保留的主成分空間計算，可能看不到被捨棄方向的異常。"] if use_pca else []),
            ],
            inputs=dict(synthetic=True, seed=p["seed"]),
            report=result,
        )
    values = make_series(p["seed"])
    parameters = (
        {}
        if tool == "rlfgm"
        else dict(
            window=p["window"], grey_weight=p["grey_weight"], max_iter=p["iterations"], random_state=p["seed"]
        )
    )
    if tool == "rlfgm":
        parameters["order"] = "auto" if p["order_mode"] == "auto" else p["order"]
    elif tool == "fginn":
        parameters.update(order=p["order"], beta=p["beta"])
    constructor = {"rlfgm": RLFGM, "ginn": GINN, "fginn": FGINN}[tool]
    if use_pca:
        time = np.arange(len(values))
        channels = np.column_stack([values, 20 + 0.3 * values + np.sin(time * 0.4),
                                    10 + 0.15 * values + np.cos(time * 0.3)])
        def fit(history):
            return GreyPCAForecast(tool, p["method"], p["components"],
                                   {"method_params": method_params}, parameters).fit(history)
        model = fit(channels[:-8])
        backtest = model.predict(8)[:, 0]
        future_model = fit(channels)
        forecast = future_model.predict(4)[:, 0]
    else:
        model = constructor(**parameters).fit(values[:-8])
        backtest = model.predict(8)
        future_model = constructor(**parameters).fit(values)
        forecast = future_model.predict(4)
    rmse = float(np.sqrt(np.mean((backtest - values[-8:]) ** 2)))
    return dict(
        title="研究模型 · " + tool.upper() + (" + " + p["method"] if use_pca else ""),
        summary="40 筆訓練、8 筆保留回測；未來 4 期另外用全部歷史重新擬合。",
        diagram=dict(
            type="series", observed=values.tolist(), backtest=backtest.tolist(), forecast=forecast.tolist()
        ),
        tables=[
            dict(
                title="回測結果與診斷",
                rows=[
                    dict(
                        model=tool,
                        holdout_rmse=rmse,
                        converged=model.diagnostics.get("converged", True),
                        order=model.diagnostics.get("order"),
                        implementation=model.diagnostics["implementation"],
                    )
                ],
            )
        ],
        warnings=[
            "等間隔單變量研究模型；不支援非等間隔日期。GINN／FGINN 使用明確的先驗引導損失與輕量網路，並非作者模型的完整重現。",
            "回測只用過去資料；未來預測可能失準或出現負值，沒有裁切或自動退回其他模型。",
            *(["PCA 只擬合訓練資料；各主成分使用固定正值平移後預測，再還原原欄位。平移會影響灰色模型，圖表只顯示第一個通道。"] if use_pca else []),
        ],
        inputs=dict(synthetic=True, seed=p["seed"], parameters=parameters),
        diagnostics=dict(backtest=model.diagnostics, future=future_model.diagnostics),
    )
