"""Public model API, snapshot isolation, and transactional batch execution."""

import copy

import numpy as np
import pytest

from greytheory import GM0N, GM1N, GM11, ModelQueue, GreyTheory, run_models


X = np.array([[.75, .5], [1.22, 1], [.2, .7], [1, .66], [1, 1], [1, .5]])
Y = np.array([1., 2, 3, 4, 5, 6])
SERIES = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]


@pytest.mark.parametrize('model_type,legacy_name', [(GM0N, 'gm0n'), (GM1N, 'gm1n')])
def test_fit_matches_original_factor_interface(model_type, legacy_name):
    model = model_type(alpha=.8, background_mode='corrected', ridge_alpha=.01)
    assert model.fit(X, Y, feature_names=['a', 'b']) is model
    legacy = getattr(GreyTheory(), legacy_name)
    legacy.alpha = .8
    legacy.background_mode = 'corrected'
    legacy.ridge_alpha = .01
    legacy.add_outputs(Y, 'target')
    for name, column in zip(['a', 'b'], X.T):
        legacy.add_patterns(column, name)
    legacy.analyze()
    np.testing.assert_allclose(model.coefficients, legacy.coefficients)
    assert model.influence_degrees == legacy.influence_degrees
    assert model.keys == ['target', 'a', 'b']
    # Results remain usable through the public names after a deferred refit.
    model.set_data(X * 2, Y, feature_names=['a', 'b'])
    assert not hasattr(model, 'diagnostics')
    run_models([model])
    assert model.diagnostics['rank'] > 0
    assert sorted(model.ranks[model.ranks > 0]) == [1, 2]
    assert model.analyzed_results[-1].rank == 2


def test_set_data_copies_inputs_and_clears_previous_fit():
    X_input, y_input = X.copy(), Y.copy()
    model = GM0N().fit(X_input, y_input)
    assert model.set_data(X_input, y_input) is model
    X_input[:] = 0
    y_input[:] = 0
    np.testing.assert_array_equal(model.patterns, np.vstack([Y, X.T]))
    assert not hasattr(model, 'coefficients')
    series = SERIES.copy()
    forecast = GM11().fit(series).set_data(series)
    series[0] = -1
    assert forecast.patterns == SERIES
    assert not hasattr(forecast, 'coefficients')


@pytest.mark.parametrize('kwargs', [
    {'feature_names': ['a']}, {'feature_names': ['a', 'a']},
    {'feature_names': ['a', 'target']}, {'feature_names': ['a', ' ']},
    {'feature_names': 'ab'}, {'target_name': ''},
])
def test_invalid_names_do_not_replace_existing_model(kwargs):
    model = GM0N().fit(X, Y)
    original = model.coefficients.copy()
    with pytest.raises((ValueError, TypeError)):
        model.set_data(X, Y, **kwargs)
    np.testing.assert_array_equal(model.coefficients, original)


@pytest.mark.parametrize('X_bad,y_bad', [
    (X[:2], Y), (X.T, Y), (X, Y[:, None]),
    (np.full_like(X, np.nan), Y), (X, [1, 2, 3, 4, 5, np.inf]),
])
def test_invalid_fit_shapes_and_values(X_bad, y_bad):
    with pytest.raises((ValueError, TypeError)):
        GM0N().fit(X_bad, y_bad)


def test_queue_snapshots_reused_models_and_nested_state():
    model = GM0N().set_data(X, Y)
    queue = ModelQueue()
    queue.append(model)
    model.patterns[0][0] = 99
    queue.append(model)
    assert queue[0].patterns[0][0] == Y[0]
    assert queue[1].patterns[0][0] == 99
    assert queue[0] is not queue[1] and queue[0] is not model
    results = queue.run()
    assert results[0] is queue[0]
    assert not hasattr(model, 'coefficients')
    assert not np.allclose(queue[0].coefficients, queue[1].coefficients)
    queue[0].patterns[1][0] = -1
    assert queue[1].patterns[1][0] == X[0, 0]
    assert model.patterns[1][0] == X[0, 0]


def test_queue_all_insertions_snapshot_and_slices_are_independent():
    model = GM11().set_data(SERIES)
    queue = ModelQueue([model, model])
    queue.extend([model])
    queue.insert(1, model)
    queue[0] = model
    queue[1:3] = [model, model]
    queue += [model]
    assert len({id(m) for m in queue}) == len(queue) == 5
    model.patterns[0] = -1
    assert all(m.patterns == SERIES for m in queue)
    sliced = queue[:2]
    assert isinstance(sliced, ModelQueue)
    sliced[0].patterns[0] = -2
    assert queue[0].patterns == SERIES
    last = queue[-1]
    queue.reverse()
    assert queue[0] is last
    assert queue.pop(0) is last
    del queue[:1]
    assert len(queue) == 3
    queue.clear()
    assert len(queue) == 0


def test_queue_rejects_bad_items_without_partial_extension():
    model = GM11().set_data(SERIES)
    queue = ModelQueue([model])
    for mutate in [
        lambda: queue.append(object()), lambda: queue.extend([model, None]),
        lambda: queue.insert(0, None), lambda: queue.__setitem__(0, None),
        lambda: queue.__setitem__(slice(None), [model, None]),
    ]:
        with pytest.raises(TypeError, match='model'):
            mutate()
        assert len(queue) == 1 and queue[0].patterns == SERIES


@pytest.mark.parametrize('workers', [1, 2])
def test_mixed_batches_order_isolation_and_inplace_modes(workers):
    source = [GM0N().set_data(X, Y), GM1N().set_data(X, Y), GM11().set_data(SERIES)]
    queue = ModelQueue(source)
    copies = queue.run(workers=workers, inplace=False)
    assert not any(hasattr(m, 'coefficients') for m in queue)
    results = queue.run(workers=workers)
    for original, stored, result, independent in zip(source, queue, results, copies):
        assert result is stored and independent is not stored
        assert not hasattr(original, 'coefficients')
        np.testing.assert_allclose(result.coefficients, independent.coefficients)
    assert [type(m) for m in results] == [GM0N, GM1N, GM11]
    np.testing.assert_allclose(results[-1].predict(2), GM11().fit(SERIES).predict(2))
    assert GreyTheory().run(queue)[0] is queue[0]


@pytest.mark.parametrize('workers', [1, 2])
def test_batch_failure_does_not_commit_partial_results(workers):
    good = GM11().set_data(SERIES)
    bad = GM0N()  # No data.
    queue = ModelQueue([good, bad])
    before = copy.deepcopy(queue[0].__dict__)
    with pytest.raises(ValueError):
        queue.run(workers=workers)
    assert queue[0].patterns == before['patterns']
    assert not hasattr(queue[0], 'coefficients')
    assert not hasattr(good, 'coefficients')


def test_run_models_plain_list_keeps_normal_list_semantics():
    model = GM11().set_data(SERIES)
    models = [model]
    result = run_models(models, inplace=False)
    assert result[0] is not model and not hasattr(model, 'coefficients')
    assert run_models(models)[0] is model
    assert hasattr(model, 'coefficients')
    assert run_models([]) == []
    with pytest.raises(TypeError):
        run_models([object()])
    with pytest.raises(ValueError):
        ModelQueue().run(workers=0)


@pytest.mark.parametrize('window_size', [None, 4])
def test_forecast_constructor_and_predict_do_not_mutate_fit(window_size):
    model = GM11(alpha=.8, background_mode='corrected', horizon=0, window_size=window_size).fit(SERIES)
    before = copy.deepcopy(model.analyzed_results)
    coefficients = model.coefficients.copy()
    future = model.predict(3)
    assert future.shape == (3,)
    expected = copy.deepcopy(model)
    expected.horizon = 3
    expected.forecast()
    np.testing.assert_allclose(future, [r.forecast_value for r in expected.analyzed_results[-3:]])
    assert model.horizon == model.period == 0
    assert model.analyzed_results == before
    np.testing.assert_array_equal(model.coefficients, coefficients)
    assert model.predict(0).size == 0
    assert model.window_size == window_size
    assert model.metrics['rmse'] >= 0
    model.reset()
    assert not hasattr(model, 'coefficients')
    assert not hasattr(model, 'diagnostics')
    assert not hasattr(model, 'metrics')


@pytest.mark.parametrize('kwargs', [
    {'alpha': 2}, {'ridge_alpha': -1}, {'rank_policy': 'bad'}, {'solver': 'bad'},
    {'horizon': -1}, {'window_size': 2}, {'stride': 0}, {'correction_mode': 'bad'},
])
def test_invalid_constructor_settings(kwargs):
    with pytest.raises((ValueError, TypeError)):
        GM11(**kwargs)
