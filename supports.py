"""Check the remaining endpoint patterns after the mixed-size reduction."""

import argparse
import json
from itertools import combinations, permutations, product
from pathlib import Path
from time import perf_counter

from pysat.formula import CNF
from pysat.solvers import Solver

from verify import first_rainbow


def encode(right_size: int) -> tuple[CNF, dict[tuple[int, int, int], int]]:
    if right_size not in (6, 7):
        raise ValueError("right side must have size six or seven")
    colours = range(5)
    left = range(6)
    right = [tuple(v for v in range(right_size) if right_size == 6 or v != colour)
             for colour in colours]
    fixed = tuple(zip(left, right[0]))
    candidates = [(0, u, v) for u, v in fixed]
    candidates.extend((colour, u, v) for colour in range(1, 5)
                      for u, v in product(left, right[colour]))
    variables = {edge: index for index, edge in enumerate(candidates, 1)}
    cnf = CNF()
    for u, v in fixed:
        cnf.append([variables[0, u, v]])
    for colour in range(1, 5):
        rows = ([variables[colour, u, v] for v in right[colour]] for u in left)
        columns = ([variables[colour, u, v] for u in left] for v in right[colour])
        for matrix_line in (*rows, *columns):
            cnf.append(matrix_line)
            for i, j in combinations(matrix_line, 2):
                cnf.append([-i, -j])
    for u, v in product(left, range(right_size)):
        available = [variables[c, u, v] for c in colours if (c, u, v) in variables]
        max_multiplicity = 1 if right_size == 7 and v < 5 else 2
        for group in combinations(available, max_multiplicity + 1):
            cnf.append([-literal for literal in group])
    for u, v in fixed:
        left_orders = tuple(permutations((i for i in left if i != u), 4))
        for right_order in product(*(tuple(w for w in right[c] if w != v)
                                     for c in range(1, 5))):
            if len(set(right_order)) != 4:
                continue
            for left_order in left_orders:
                cnf.append([-variables[c, i, j] for c, i, j
                            in zip(range(1, 5), left_order, right_order)])
    return cnf, variables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("right_size", type=int, choices=(6, 7))
    parser.add_argument("--solver", default="cadical195", choices=("cadical195", "glucose4"))
    parser.add_argument("--conflicts", type=int)
    parser.add_argument("--proof", type=Path, help="DIMACS/DRAT output stem")
    parser.add_argument("--witness", type=Path)
    args = parser.parse_args()
    if args.conflicts is not None and args.conflicts < 1:
        parser.error("the conflict budget must be positive")
    if args.proof and args.proof.suffix:
        parser.error("--proof takes a filename stem without an extension")
    cnf, variables = encode(args.right_size)
    print(json.dumps({"right_size": args.right_size, "solver": args.solver,
                      "variables": cnf.nv, "clauses": len(cnf.clauses),
                      "conflict_budget": args.conflicts}), flush=True)
    start = perf_counter()
    with Solver(name=args.solver, bootstrap_with=cnf.clauses,
                with_proof=args.proof is not None) as solver:
        if args.conflicts is None:
            status = solver.solve()
        else:
            solver.conf_budget(args.conflicts)
            status = solver.solve_limited()
        report = {"status": {True: "sat", False: "unsat", None: "unknown"}[status],
                  "seconds": round(perf_counter() - start, 3), **solver.accum_stats()}
        if status is True:
            positive = {literal for literal in solver.get_model() if literal > 0}
            matchings: list[list[tuple[int, int]]] = [[] for _ in range(5)]
            for (c, u, v), literal in variables.items():
                if literal in positive:
                    matchings[c].append((u, v))
            if list(map(len, matchings)) != [6] * 5 or first_rainbow(matchings) is not None:
                raise RuntimeError("invalid counterexample extracted from SAT model")
            witness = {"matchings": matchings}
            if args.witness:
                args.witness.write_text(json.dumps(witness, indent=2) + "\n", encoding="ascii")
            report["verified_obstruction"] = witness
        if status is False and args.proof:
            proof = solver.get_proof()
            if not proof:
                raise RuntimeError("the solver did not export a refutation")
            cnf.to_file(str(args.proof.with_suffix(".cnf")))
            args.proof.with_suffix(".drat").write_bytes(("\n".join(proof) + "\n").encode("ascii"))
        print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
