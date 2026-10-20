"""Application constraints, model assumptions, parameter validation, and API contracts."""

from itertools import permutations
import json

import numpy as np
import pytest

from examples.workbench.analysis import analyze, read_csv, spectra_dataset
from examples.workbench.doe import DATA, SPECS
from examples.workbench.methods import PCA_SCHEMAS, pca_params, validate
from examples.workbench.scenarios import SCENARIOS, art_data, inputs, run_scenario


def test_routes_exact_small_distance_problem_and_determinism():
    result = run_scenario("routes", {"stops": 4, "objective": "distance"})
    points = np.array(result["diagram"]["points"])
    order = result["diagram"]["route"]
    assert order[0] == order[-1] == 0 and sorted(order[1:-1]) == [1, 2, 3, 4]

    def length(route):
        return sum(np.linalg.norm(points[a] - points[b]) for a, b in zip(route, route[1:]))

    optimum = min(length([0, *p, 0]) for p in permutations(range(1, 5)))
    assert length(order) == pytest.approx(optimum)
    assert result == run_scenario("routes", {"stops": 4, "objective": "distance"})
    with pytest.raises(ValueError, match="positive|權重|weights"):
        run_scenario("routes", {"distance_weight": 0, "time_weight": 0, "late_weight": 0})


def test_matching_obeys_hard_constraints_and_unique_assignments():
    result = run_scenario("drivers", {"drivers": 3, "jobs": 8})
    people = result["diagram"]["drivers"]
    jobs = result["diagram"]["jobs"]
    edges = result["diagram"]["edges"]
    assert len({a for a, b in edges}) == len(edges)
    assert len({b for a, b in edges}) == len(edges)
    assert len(edges) <= 3
    for a, b in edges:
        driver, job = people[a], jobs[b]
        distance = np.hypot(driver["x"] - job["x"], driver["y"] - job["y"])
        assert job["load_kg"] <= driver["capacity_kg"] and job["skill"] <= driver["skill"]
        assert job["duration_min"] + distance * 2 <= driver["available_min"]
    assert any(r["driver"] == "未媒合" for r in result["tables"][0]["rows"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("key", SCENARIOS)
def test_scenario_contracts(key):
    result = run_scenario(key)
    assert result["title"] and result["summary"] and result["warnings"]
    assert result["tables"]
    json.dumps(result, allow_nan=False)


def test_forecast_holdout_does_not_leak_and_windows_are_distinct():
    values = inputs()["orders"]
    changed = values[:-4] + [v * 2 for v in values[-4:]]
    a = run_scenario("forecast", series=values)
    b = run_scenario("forecast", series=changed)
    np.testing.assert_allclose(a["diagram"]["backtest"], b["diagram"]["backtest"])
    assert a["diagram"]["forecast"] != b["diagram"]["forecast"]
    convolution = run_scenario("forecast", {"forecast_method": "convolution"})
    assert convolution["diagram"]["forecast"] != a["diagram"]["forecast"]


def test_art_training_is_independent_of_changes_and_threshold_monotone():
    _, reference_a, _, _, _ = art_data(strength=0.2)
    _, reference_b, _, _, _ = art_data(strength=0.9)
    np.testing.assert_array_equal(reference_a, reference_b)
    a = run_scenario("art", {"quantile": 0.8})
    b = run_scenario("art", {"quantile": 0.99})
    assert np.all(np.array(b["diagram"]["flags"]) <= np.array(a["diagram"]["flags"]))


@pytest.mark.parametrize("method", PCA_SCHEMAS)
def test_pca_forms_match_supported_backend(method):
    dataset = read_csv((DATA / "pvd_15.csv").read_bytes(), spec=SPECS["pvd"])
    result = analyze(dataset, {"features": dataset.defaults, "method": method, "method_params": {}})
    assert np.isfinite(result["coordinates"]).all()


def test_parameter_validation_and_adv_delta():
    assert pca_params("adv", {})["delta"] == "adaptive"
    assert pca_params("adv", {"delta_mode": "manual", "delta": 0.2})["delta"] == 0.2
    with pytest.raises(ValueError):
        pca_params("adv", {"delta": float("nan")})
    with pytest.raises(ValueError):
        pca_params("sparse", {"max_iter": 10**9})
    with pytest.raises(ValueError):
        validate(SCENARIOS["routes"]["fields"], {"__class__": "unsafe"})
    with pytest.raises(ValueError):
        validate(SCENARIOS["routes"]["fields"], {"stops": True})


@pytest.mark.parametrize("engine", ["gra", "gm0n", "gm1n", "quality"])
def test_main_grey_engines_and_explicit_quality_directions(engine):
    dataset = read_csv((DATA / "pvd_15.csv").read_bytes(), spec=SPECS["pvd"])
    options = dict(engine=engine, features=dataset.defaults, target="thickness_nm", ordered_rows=True)
    if engine == "quality":
        options["target"] = None
        options["quality"] = [
            dict(
                direction="smaller",
                lower=float(dataset.values[:, i].min()),
                upper=float(dataset.values[:, i].max()),
                weight=1,
            )
            for i in range(6)
        ]
    result = analyze(dataset, options)
    json.dumps(result, allow_nan=False)
    assert result["ranking"]
    assert result["coordinate_labels"]
    if engine.startswith("gm"):
        with pytest.raises(ValueError, match="先後順序"):
            analyze(dataset, {**options, "ordered_rows": False})


def test_component_selection_and_window_poisson_paths():
    dataset = read_csv((DATA / "pvd_15.csv").read_bytes(), spec=SPECS["pvd"])
    result = analyze(dataset, dict(features=dataset.defaults, target="thickness_nm", component_top_k=1))
    assert np.asarray(result["coordinates"]).shape == (15, 1)
    assert len(result["variance"]) == 1 and len(result["component_scores"]) == 2
    rng = np.random.default_rng(8)
    counts = rng.poisson(np.linspace(2, 20, 64), (12, 64))
    spectrum = spectra_dataset("generated", counts, np.arange(64) * 0.1)
    for engine in ["window_pca", "poisson"]:
        result = analyze(spectrum, dict(engine=engine))
        assert np.isfinite(result["coordinates"]).all()
    with pytest.raises(ValueError, match="通道"):
        analyze(dataset, dict(engine="window_pca", features=dataset.defaults))
    with pytest.raises(ValueError, match="原始計數"):
        analyze(dataset, dict(engine="poisson", features=dataset.defaults))


@pytest.mark.parametrize("tool", ["mcr", "mnf", "mlpca", "baseline", "peaks", "element_lines"])
def test_spectral_adapters(tool):
    result = run_scenario("spectral", {"tool": tool})
    json.dumps(result, allow_nan=False)
    assert result["diagram"]["curves"] or result["tables"]


@pytest.mark.parametrize("tool", ["monitor", "suggest", "lhs"])
def test_process_adapters(tool):
    result = run_scenario("semiconductor", {"tool": tool})
    assert result["tables"][0]["rows"]
    json.dumps(result, allow_nan=False)
