from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from ortools.linear_solver import pywraplp

from .domain import NetworkData


class ExecutableIRValidationError(ValueError):
    pass


@dataclass
class LinearForm:
    coeffs: dict[Any, float] = field(default_factory=dict)
    constant: float = 0.0

    def add(self, other: "LinearForm") -> "LinearForm":
        coeffs = dict(self.coeffs)
        for var, coeff in other.coeffs.items():
            coeffs[var] = coeffs.get(var, 0.0) + coeff
        return LinearForm(coeffs=coeffs, constant=self.constant + other.constant)

    def sub(self, other: "LinearForm") -> "LinearForm":
        coeffs = dict(self.coeffs)
        for var, coeff in other.coeffs.items():
            coeffs[var] = coeffs.get(var, 0.0) - coeff
        return LinearForm(coeffs=coeffs, constant=self.constant - other.constant)

    def mul_scalar(self, scalar: float) -> "LinearForm":
        return LinearForm(
            coeffs={var: coeff * scalar for var, coeff in self.coeffs.items()},
            constant=self.constant * scalar,
        )

    def to_solver_expr(self):
        expr = self.constant
        for var, coeff in self.coeffs.items():
            expr += coeff * var
        return expr


@dataclass
class SetDefinition:
    name: str
    type: str
    records: list[dict[str, Any]]
    key_aliases: list[str]


@dataclass
class BuildContext:
    ir: dict[str, Any]
    solver: pywraplp.Solver
    sets: dict[str, SetDefinition]
    parameters: dict[str, Any]
    variables: dict[str, dict[tuple[Any, ...], Any]]
    iterator_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    iterator_values: dict[str, Any] = field(default_factory=dict)

    def nested(self) -> "BuildContext":
        return BuildContext(
            ir=self.ir,
            solver=self.solver,
            sets=self.sets,
            parameters=self.parameters,
            variables=self.variables,
            iterator_records=dict(self.iterator_records),
            iterator_values=dict(self.iterator_values),
        )


def load_executable_ir(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_executable_ir(ir: dict[str, Any]) -> None:
    required = ["ir_version", "model_name", "problem_type", "backend_class", "objective", "sets", "parameters", "variables", "constraints"]
    missing = [name for name in required if name not in ir]
    if missing:
        raise ExecutableIRValidationError(f"Executable IR is missing required fields: {missing}")
    if ir["backend_class"] not in {"linear_mip", "linear_cp_sat"}:
        raise ExecutableIRValidationError(f"Unsupported backend_class: {ir['backend_class']}")
    if ir["backend_class"] != "linear_mip":
        raise ExecutableIRValidationError("Current builder only supports backend_class='linear_mip'.")


def build_model_from_ir(
    ir: dict[str, Any],
    data: NetworkData,
    solver_name: str,
    external_inputs: dict[str, Any] | None = None,
):
    validate_executable_ir(ir)
    solver = pywraplp.Solver.CreateSolver(solver_name)
    if solver is None:
        raise RuntimeError(f"Failed to create OR-Tools solver: {solver_name}")

    tables = _network_tables(data)
    sets = _build_sets(ir.get("sets", []), tables, external_inputs or {})
    parameters = _build_parameters(ir.get("parameters", []), tables, external_inputs or {})
    variables = _build_variables(ir.get("variables", []), solver, sets, parameters)
    context = BuildContext(ir=ir, solver=solver, sets=sets, parameters=parameters, variables=variables)

    for constraint in ir.get("constraints", []):
        _add_constraint(context, constraint)

    _set_objective(context, ir["objective"])
    return solver, {"sets": sets, "parameters": parameters, "variables": variables}


def _network_tables(data: NetworkData) -> dict[str, pd.DataFrame]:
    simulation = pd.DataFrame(
        [
            {
                "Simulation Name": data.simulation.simulation_name,
                "Structure": data.simulation.structure,
                "Warehouse Qty": data.simulation.warehouse_qty,
                "Speed (km/h)": data.simulation.speed_kmh,
                "Coverage (hour)": data.simulation.coverage_hours,
            }
        ]
    )
    return {
        "simulation": simulation,
        "plant": data.plants.copy(),
        "warehouse": data.warehouses.copy(),
        "customer": data.customers.copy(),
        "plantWarehouseCost": data.plant_warehouse_cost.copy(),
        "warehouseCustomerCost": data.warehouse_customer_cost.copy(),
    }


def _build_sets(set_defs: list[dict[str, Any]], tables: dict[str, pd.DataFrame], external_inputs: dict[str, Any]) -> dict[str, SetDefinition]:
    built: dict[str, SetDefinition] = {}
    for set_def in set_defs:
        source = set_def["source"]
        records = _resolve_source_records(source, tables, external_inputs)
        key_aliases = _resolve_key_aliases(set_def, source)
        built_records: list[dict[str, Any]] = []
        for record in records:
            materialized = dict(record)
            for column, alias in source.get("field_aliases", {}).items():
                materialized[alias] = record[column]
            if set_def["type"] == "entity":
                materialized[key_aliases[0]] = record[source["key"][0]]
            built_records.append(materialized)
        built[set_def["name"]] = SetDefinition(
            name=set_def["name"],
            type=set_def["type"],
            records=built_records,
            key_aliases=key_aliases,
        )
    return built


def _resolve_source_records(source: dict[str, Any], tables: dict[str, pd.DataFrame], external_inputs: dict[str, Any]) -> list[dict[str, Any]]:
    kind = source["kind"]
    if kind == "table":
        frame = tables[source["table"]].copy()
        for filter_def in source.get("filters", []):
            column = filter_def["column"]
            op = filter_def["op"]
            value = filter_def["value"]
            if op == "eq":
                if value is None:
                    frame = frame[frame[column].isna()]
                else:
                    frame = frame[frame[column] == value]
            elif op == "ne":
                if value is None:
                    frame = frame[frame[column].notna()]
                else:
                    frame = frame[frame[column] != value]
            elif op == "in":
                frame = frame[frame[column].isin(value)]
            else:
                raise ExecutableIRValidationError(f"Unsupported source filter op: {op}")
        return frame.to_dict(orient="records")
    if kind == "input":
        input_name = source["table"]
        values = external_inputs.get(input_name, [])
        if not isinstance(values, list):
            raise ExecutableIRValidationError(f"External input '{input_name}' must be a list of records.")
        return values
    raise ExecutableIRValidationError(f"Unsupported source kind: {kind}")


def _resolve_key_aliases(set_def: dict[str, Any], source: dict[str, Any]) -> list[str]:
    if "key_aliases" in source:
        return list(source["key_aliases"])
    if set_def["type"] == "entity":
        return [set_def["name"][:-1] if set_def["name"].endswith("s") else set_def["name"]]
    return list(source.get("key", []))


def _build_parameters(parameter_defs: list[dict[str, Any]], tables: dict[str, pd.DataFrame], external_inputs: dict[str, Any]) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    for parameter_def in parameter_defs:
        binding = parameter_def["binding"]
        if binding["kind"] == "scalar":
            frame = tables[binding["table"]]
            parameters[parameter_def["name"]] = frame.iloc[binding.get("row", 0)][binding["value_column"]]
        elif binding["kind"] == "column":
            frame = tables[binding["table"]]
            key_cols = binding["key"]
            value_col = binding["value_column"]
            values: dict[tuple[Any, ...], Any] = {}
            for _, row in frame.iterrows():
                key = tuple(row[col] for col in key_cols)
                values[key] = row[value_col]
            parameters[parameter_def["name"]] = values
        elif binding["kind"] == "input":
            parameters[parameter_def["name"]] = external_inputs.get(binding["table"])
        else:
            raise ExecutableIRValidationError(f"Unsupported parameter binding kind: {binding['kind']}")
    return parameters


def _build_variables(
    variable_defs: list[dict[str, Any]],
    solver: pywraplp.Solver,
    sets: dict[str, SetDefinition],
    parameters: dict[str, Any],
) -> dict[str, dict[tuple[Any, ...], Any]]:
    built: dict[str, dict[tuple[Any, ...], Any]] = {}
    for variable_def in variable_defs:
        index_records = _expand_variable_indices(variable_def, sets)
        variables_for_def: dict[tuple[Any, ...], Any] = {}
        for index_values, record in index_records:
            domain = variable_def["domain"]
            lb = _eval_bound(domain.get("lb"), domain.get("lb_expr"), record, parameters)
            ub = _eval_bound(domain.get("ub"), domain.get("ub_expr"), record, parameters)
            name = f"{variable_def['symbol']}[{','.join(str(v) for v in index_values)}]" if index_values else variable_def["symbol"]
            if variable_def["var_type"] == "binary":
                var = solver.BoolVar(name)
            elif variable_def["var_type"] == "integer":
                var = solver.IntVar(int(lb), int(ub), name)
            elif variable_def["var_type"] == "continuous":
                var = solver.NumVar(float(lb), float(ub), name)
            else:
                raise ExecutableIRValidationError(f"Unsupported var_type: {variable_def['var_type']}")
            variables_for_def[index_values] = var
        built[variable_def["name"]] = variables_for_def
    return built


def _expand_variable_indices(variable_def: dict[str, Any], sets: dict[str, SetDefinition]) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    if not variable_def["index_sets"]:
        return [(tuple(), {})]
    if len(variable_def["index_sets"]) != 1:
        raise ExecutableIRValidationError("Current builder only supports a single index_set per variable.")
    set_def = sets[variable_def["index_sets"][0]]
    results: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for record in set_def.records:
        index_values = tuple(record[key] for key in set_def.key_aliases)
        results.append((index_values, record))
    return results


def _eval_bound(
    constant_bound: float | int | None,
    expr_bound: dict[str, Any] | None,
    record: dict[str, Any],
    parameters: dict[str, Any],
) -> float:
    if constant_bound is not None:
        return float(constant_bound)
    if expr_bound is None:
        raise ExecutableIRValidationError("Variable domain must define either a constant bound or an expression bound.")
    if expr_bound["op"] == "min":
        values = [_eval_bound(None, arg, record, parameters) for arg in expr_bound["args"]]
        return min(values)
    if expr_bound["op"] == "param":
        name = expr_bound["name"]
        index = tuple(record[idx] for idx in expr_bound["index"])
        return float(parameters[name][index])
    raise ExecutableIRValidationError(f"Unsupported bound expression op: {expr_bound['op']}")


def _add_constraint(context: BuildContext, constraint_def: dict[str, Any]) -> None:
    for scoped_context in _iterate_iterators(context, constraint_def.get("forall", [])):
        lhs = _eval_linear_expr(scoped_context, constraint_def["lhs"])
        rhs = _eval_linear_expr(scoped_context, constraint_def["rhs"])
        expr = lhs.sub(rhs).to_solver_expr()
        sense = constraint_def["sense"]
        if sense == "eq":
            context.solver.Add(expr == 0)
        elif sense == "le":
            context.solver.Add(expr <= 0)
        elif sense == "ge":
            context.solver.Add(expr >= 0)
        else:
            raise ExecutableIRValidationError(f"Unsupported constraint sense: {sense}")


def _iterate_iterators(base_context: BuildContext, iterator_defs: list[dict[str, Any]]) -> list[BuildContext]:
    contexts = [base_context]
    for iterator_def in iterator_defs:
        next_contexts: list[BuildContext] = []
        set_def = base_context.sets[iterator_def["set"]]
        for context in contexts:
            for record in set_def.records:
                candidate = context.nested()
                candidate.iterator_records[iterator_def["name"]] = record
                if set_def.key_aliases:
                    if len(set_def.key_aliases) == 1:
                        candidate.iterator_values[iterator_def["name"]] = record[set_def.key_aliases[0]]
                    else:
                        candidate.iterator_values[iterator_def["name"]] = tuple(record[key] for key in set_def.key_aliases)
                if _predicates_hold(candidate, iterator_def.get("where", [])):
                    next_contexts.append(candidate)
        contexts = next_contexts
    return contexts


def _predicates_hold(context: BuildContext, predicates: list[dict[str, Any]]) -> bool:
    for predicate in predicates:
        left = _eval_scalar(context, predicate["left"])
        right = _eval_scalar(context, predicate["right"])
        cmp_op = predicate["cmp"]
        if cmp_op == "eq" and left != right:
            return False
        if cmp_op == "ne" and left == right:
            return False
        if cmp_op == "in" and left not in right:
            return False
    return True


def _eval_scalar(context: BuildContext, expr: Any) -> Any:
    if not isinstance(expr, dict):
        return expr
    op = expr["op"]
    if op == "const":
        return expr["value"]
    if op == "index":
        return context.iterator_values[expr["name"]]
    if op == "item":
        return context.iterator_records[expr["name"]][expr["field"]]
    if op == "param":
        values = context.parameters[expr["name"]]
        if not isinstance(values, dict):
            return values
        index = tuple(_eval_scalar(context, idx) for idx in expr.get("index", []))
        return values[index]
    raise ExecutableIRValidationError(f"Unsupported scalar op: {op}")


def _eval_linear_expr(context: BuildContext, expr: Any) -> LinearForm:
    if not isinstance(expr, dict):
        if isinstance(expr, (int, float)):
            return LinearForm(constant=float(expr))
        raise ExecutableIRValidationError(f"Unsupported literal in linear expression: {expr!r}")

    op = expr["op"]
    if op == "const":
        return LinearForm(constant=float(expr["value"]))
    if op == "param":
        value = _eval_scalar(context, expr)
        return LinearForm(constant=float(value))
    if op == "index":
        return LinearForm(constant=float(_eval_scalar(context, expr)))
    if op == "item":
        return LinearForm(constant=float(_eval_scalar(context, expr)))
    if op == "var":
        key = _resolve_var_index(context, expr)
        variable = context.variables[expr["name"]][key]
        return LinearForm(coeffs={variable: 1.0})
    if op == "add":
        result = LinearForm()
        for term in expr["terms"]:
            result = result.add(_eval_linear_expr(context, term))
        return result
    if op == "sub":
        return _eval_linear_expr(context, expr["left"]).sub(_eval_linear_expr(context, expr["right"]))
    if op == "mul":
        left = _eval_linear_expr(context, expr["left"])
        right = _eval_linear_expr(context, expr["right"])
        if left.coeffs and right.coeffs:
            raise ExecutableIRValidationError("Nonlinear term detected: var * var is not supported.")
        if left.coeffs:
            return left.mul_scalar(right.constant)
        if right.coeffs:
            return right.mul_scalar(left.constant)
        return LinearForm(constant=left.constant * right.constant)
    if op == "sum":
        result = LinearForm()
        for scoped_context in _iterate_iterators(context, expr.get("over", [])):
            result = result.add(_eval_linear_expr(scoped_context, expr["expr"]))
        return result
    raise ExecutableIRValidationError(f"Unsupported linear expression op: {op}")


def _resolve_var_index(context: BuildContext, expr: dict[str, Any]) -> tuple[Any, ...]:
    if "index" in expr:
        return tuple(_eval_scalar(context, idx) for idx in expr["index"])
    if "index_from" in expr:
        iterator_name, fields = next(iter(expr["index_from"].items()))
        record = context.iterator_records[iterator_name]
        return tuple(record[field] for field in fields)
    raise ExecutableIRValidationError(f"Variable expression is missing index/index_from: {expr}")


def _set_objective(context: BuildContext, objective_def: dict[str, Any]) -> None:
    expr = _eval_linear_expr(context, objective_def["expr"]).to_solver_expr()
    if objective_def["sense"] == "min":
        context.solver.Minimize(expr)
    elif objective_def["sense"] == "max":
        context.solver.Maximize(expr)
    else:
        raise ExecutableIRValidationError(f"Unsupported objective sense: {objective_def['sense']}")
