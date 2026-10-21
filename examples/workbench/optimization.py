"""Four-step GUI demonstration backed by the public quick functions."""

import numpy as np

from greytheory import analyze_features, choose_options
from greytheory.semiconductor import latin_hypercube


def run_optimization(p):
    random = np.random.default_rng(p["seed"])
    # Fictional correlated process factors. This is not a physical equipment model.
    factors = random.normal(size=(240, 3))
    loading = np.array([[1, 0.3, 0, 0.5, -0.2, 0.4], [0, 1, 0.2, -0.4, 0.7, 0.1], [0.2, 0, 1, 0.2, 0.1, 0.5]])
    features = factors @ loading + random.normal(scale=0.15, size=(240, 6))
    names = ["power", "pressure", "gas_flow", "temperature", "bias", "duration"]
    target = 100 + 8 * factors[:, 0] - 4 * factors[:, 1] + random.normal(scale=0.3, size=240)
    train, calibration, test = features[:120], features[120:180], features[180:]
    settings = [
        dict(method="pca", n_components=n, top_k=k, standardize=True) for n in (2, 3, 4, 6) for k in (None, 2)
    ]
    if p["search_family"] == "pca_sparse":
        settings += [
            dict(
                method="sparse",
                n_components=n,
                standardize=True,
                method_params=dict(alpha=0.1, max_iter=200, random_state=p["seed"]),
            )
            for n in (2, 3, 4)
        ]
    result = analyze_features(
        train,
        target[:120],
        feature_names=names,
        top=2,
        repeats=p["repeats"],
        normal_data=calibration,
        false_alarm_rate=p["false_alarm_rate"],
        random_state=p["seed"],
        search_options=dict(candidates=settings, max_trials=p["trials"]),
    )
    # The test target evaluates the untouched test set. Injection is a separate copy.
    predicted = result.predict(test)
    test_rmse = float(np.sqrt(np.mean((predicted - target[180:]) ** 2)))
    observed = test.copy()
    injected = (np.arange(len(test)) >= 48) & (p["shift"] > 0)
    observed[injected, 4] += p["shift"]
    differences = result.find_differences(observed)
    flags = differences["flags"]
    parameters = latin_hypercube([[0, 1], [0, 1]], p["candidates"], random_state=p["seed"])
    loss = (parameters[:, 0] - 0.8) ** 2 + (parameters[:, 1] - 0.7) ** 2
    cost = parameters[:, 0] + 2 * parameters[:, 1]
    options = [
        dict(
            name=f"DOE-{i + 1:02}",
            setting_a=float(row[0]),
            setting_b=float(row[1]),
            quality_loss=float(loss[i]),
            cost=float(cost[i]),
        )
        for i, row in enumerate(parameters)
    ]
    alternatives = choose_options(
        options, smaller=["quality_loss", "cost"], limits={"cost": (None, p["cost_limit"])}
    )
    chosen = {row["name"] for row in alternatives}
    feasible = cost <= p["cost_limit"]
    trials = []
    for i, trial in enumerate(result.search.trials):
        setting = trial["parameters"]
        trials.append(
            dict(
                trial=i + 1,
                method=setting.get("method", "pca"),
                components=setting["n_components"],
                top_k=setting.get("top_k"),
                validation_rmse=trial.get("mean_rmse"),
                status=trial["status"],
                diagnostics="; ".join(trial.get("warnings", []) + [trial.get("error", "")]).strip("; "),
            )
        )
    threshold = differences["threshold"]
    diagram = dict(
        type="optimization",
        ranking=result.ranking,
        calibration=dict(
            scores=differences["scores"].tolist(),
            flags=flags.tolist(),
            injected=injected.tolist(),
            threshold=float(threshold) if np.isfinite(threshold) else None,
        ),
        trials=trials,
        pareto=[
            dict(**row, feasible=bool(ok), selected=row["name"] in chosen)
            for row, ok in zip(options, feasible)
        ],
    )
    return dict(
        title="快速分析 · 排序、校正、搜尋與折衷方案",
        summary="120 筆訓練、60 筆正常校正、60 筆獨立測試。請按圖表上方的四個步驟查看結果。",
        warnings=[
            "全部為合成資料；選擇頻率不是因果機率，重建異常不是補畫證據，候選配方不能直接送入機台。",
            "驗證 RMSE 用於選設定；測試 RMSE 使用未加擾動的獨立測試資料。監測 PCA 與預測模型分開。",
        ],
        inputs=dict(
            synthetic=True,
            seed=p["seed"],
            features=names,
            partitions=dict(training=120, calibration=60, test=60),
            monitoring_components=result.monitor.n_components,
        ),
        tables=[
            dict(
                title="結果摘要",
                rows=[
                    dict(metric="successful_repeats", value=result.stability.successful_repeats),
                    dict(
                        metric="calibration_threshold",
                        value=float(threshold) if np.isfinite(threshold) else None,
                    ),
                    dict(metric="normal_false_alarms", value=int(np.sum(flags & ~injected))),
                    dict(metric="injected_detected", value=int(np.sum(flags & injected))),
                    dict(metric="injected_total", value=int(injected.sum())),
                    dict(metric="tuning_rmse", value=result.validation_rmse),
                    dict(metric="independent_test_rmse", value=test_rmse),
                    dict(metric="pareto_options", value=len(alternatives)),
                    dict(metric="selected_prediction", value=str(result.best_parameters)),
                ],
            ),
            dict(title="特徵排名穩定性", rows=result.ranking),
            dict(title="候選模型驗證結果", rows=trials),
            dict(title="多目標折衷方案", rows=alternatives or [dict(note="沒有符合成本限制的候選方案。")]),
        ],
        diagram=diagram,
        # Preserve the full public report for JSON export and auditing.
        analysis_report=result.to_dict(),
    )
