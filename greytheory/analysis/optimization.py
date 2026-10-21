"""Finite-candidate Pareto screening; no weighted collapse or global guarantee."""

from dataclasses import dataclass

import numpy as np

from .._validation import array


@dataclass
class ParetoResult:
    indices: np.ndarray
    objectives: np.ndarray
    feasible: np.ndarray
    pareto_mask: np.ndarray


def pareto_front(objectives, directions, *, constraints=None):
    """Keep feasible nondominated rows; directions are 'smaller' or 'larger'.

    constraints, when provided, is (n_candidates, n_constraints) of signed
    violations: every entry must be <= 0 for feasibility. Equal objective rows
    are all retained. Dominance uses exact comparisons, with no unit-dependent
    tolerance. This screens supplied observations or predictions, not unseen
    designs; predicted feasibility needs physical verification.
    """
    values = array(objectives, name="objectives")
    if isinstance(directions, str):
        raise ValueError("provide one direction per objective")
    directions = tuple(directions)
    if len(directions) != values.shape[1] or any(d not in {"smaller", "larger"} for d in directions):
        raise ValueError("directions must match objectives and be smaller or larger")
    feasible = np.ones(len(values), dtype=bool)
    if constraints is not None:
        violations = array(constraints, name="constraints")
        if len(violations) != len(values):
            raise ValueError("constraints must have one row per candidate")
        feasible = np.all(violations <= 0, axis=1)
    costs = values * np.array([1 if d == "smaller" else -1 for d in directions])
    front = np.zeros(len(values), dtype=bool)
    eligible = np.flatnonzero(feasible)
    for i in eligible:
        dominated = np.all(costs[eligible] <= costs[i], axis=1) & np.any(costs[eligible] < costs[i], axis=1)
        front[i] = not dominated.any()
    indices = np.flatnonzero(front)
    return ParetoResult(indices, values[indices].copy(), feasible, front)


def optimize_candidates(parameters, evaluate, directions):
    """Evaluate a finite design table, then screen its Pareto front.

    evaluate receives a copy of the full parameter matrix and returns either an
    objective matrix, or (objectives, signed_constraint_violations). Candidate
    generation is explicit: e.g. semiconductor.latin_hypercube or a DOE table.
    """
    parameters = array(parameters, name="parameters")
    output = evaluate(parameters.copy())
    objectives, constraints = output if isinstance(output, tuple) else (output, None)
    objectives = array(objectives, name="objectives")
    if len(objectives) != len(parameters):
        raise ValueError("evaluate must return one objective row per candidate")
    front = pareto_front(objectives, directions, constraints=constraints)
    return dict(
        parameters=parameters[front.indices].copy(),
        front=front,
        evaluated_parameters=parameters.copy(),
        evaluated_objectives=objectives.copy(),
    )
