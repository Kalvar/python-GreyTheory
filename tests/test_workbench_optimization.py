import json

import numpy as np
import pytest

from examples.workbench.backend import Backend
from examples.workbench.scenarios import run_scenario


def test_optimization_scenario_runs_public_functions_and_exports_report():
    result = Backend().request("/api/scenario", {"scenario": "optimization"})
    assert result["diagram"]["type"] == "optimization"
    assert result["inputs"]["partitions"] == dict(training=120, calibration=60, test=60)
    assert result["analysis_report"]["format"] == "greytheory-feature-analysis-v1"
    assert len(result["diagram"]["ranking"]) == 6
    assert len(result["diagram"]["calibration"]["scores"]) == 60
    assert len(result["diagram"]["trials"]) == 8
    json.dumps(result, allow_nan=False)


def test_shift_does_not_change_training_calibration_or_prediction_evaluation():
    unchanged = run_scenario("optimization", {"shift": 0})
    shifted = run_scenario("optimization", {"shift": 4})
    a, b = unchanged["diagram"], shifted["diagram"]
    assert a["ranking"] == b["ranking"]
    assert a["trials"] == b["trials"]  # timing excluded from display rows
    assert a["calibration"]["threshold"] == b["calibration"]["threshold"]
    np.testing.assert_array_equal(a["calibration"]["scores"][:48], b["calibration"]["scores"][:48])
    assert not any(a["calibration"]["injected"])
    assert sum(b["calibration"]["injected"]) == 12

    def metrics(result):
        return {r["metric"]: r["value"] for r in result["tables"][0]["rows"]}

    assert metrics(unchanged)["independent_test_rmse"] == metrics(shifted)["independent_test_rmse"]


def test_cost_constraints_preserve_empty_front_and_monotone_threshold():
    empty = run_scenario("optimization", {"cost_limit": 0})
    assert not any(row["selected"] for row in empty["diagram"]["pareto"])
    permissive = run_scenario("optimization", {"false_alarm_rate": 0.2})
    conservative = run_scenario("optimization", {"false_alarm_rate": 0.02})
    assert (
        conservative["diagram"]["calibration"]["threshold"]
        >= permissive["diagram"]["calibration"]["threshold"]
    )
    assert np.all(
        np.array(conservative["diagram"]["calibration"]["flags"])
        <= np.array(permissive["diagram"]["calibration"]["flags"])
    )


@pytest.mark.parametrize(
    "parameters", [{"repeats": 201}, {"trials": 0}, {"cost_limit": -1}, {"search_family": "invalid"}]
)
def test_optimization_parameter_guard(parameters):
    with pytest.raises(ValueError):
        run_scenario("optimization", parameters)
