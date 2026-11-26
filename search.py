"""Search bipartite rainbow matching obstructions by endpoint equality."""

import argparse
import json
from itertools import combinations, product
from pathlib import Path
from time import perf_counter

from pysat.formula import CNF
from pysat.solvers import Solver

from verify import first_rainbow


def encode(sizes: tuple[int, ...], *, anchor: bool, mixed_reduction: bool = False
           ) -> tuple[CNF, list, list]:
    colours: list[list[int]] = []
    colour_of: list[int] = []
    for colour, size in enumerate(sizes):
        start = len(colour_of)
        colours.append(list(range(start, start + size)))
        colour_of.extend([colour] * size)
    occurrences = range(len(colour_of))
    cnf = CNF()
    variables: list[dict[tuple[int, int], int]] = []
    next_id = 1
    for _ in range(2):
        current: dict[tuple[int, int], int] = {}
        for i, j in combinations(occurrences, 2):
            if colour_of[i] != colour_of[j]:
                current[i, j] = next_id
                next_id += 1
        variables.append(current)
        for i, j, k in combinations(occurrences, 3):
            triangle = [current.get((i, j)), current.get((i, k)), current.get((j, k))]
            for t in range(3):
                first, second = [triangle[(t + offset) % 3] for offset in (1, 2)]
                if first is not None and second is not None:
                    clause = [-first, -second]
                    if triangle[t] is not None:
                        clause.append(triangle[t])
                    cnf.append(clause)

    for selection in product(*colours):
        pairs = list(combinations(selection, 2))
        cnf.append([current[pair] for current in variables for pair in pairs])

    if mixed_reduction:
        if sizes != (6,) * 5:
            raise ValueError("the mixed-size reduction applies to five colours of size six")
        # If an edge destroys fewer than two edges in two other colours,
        # the (4,4,5,5) theorem supplies a rainbow after deleting its endpoints.
        for occurrence in occurrences:
            hits = []
            for colour in colours:
                if occurrence in colour:
                    continue
                pairs = [tuple(sorted((occurrence, other))) for other in colour]
                good = next_id
                next_id += 1
                hits.append(good)
                for current in variables:
                    cnf.append([-good, *(current[pair] for pair in pairs)])
                for pair in pairs:
                    cnf.append([-good, -variables[0][pair], -variables[1][pair]])
            for good_pair in combinations(hits, 2):
                cnf.append(list(good_pair))

    if anchor:
        fixed = [colour[0] for colour in colours[:-1]]
        for current in variables:
            for pair in combinations(fixed, 2):
                cnf.append([-current[pair]])
        # Last-colour edges cannot go between two unused vertices. Because the
        # last colour is a matching, each side has at most len(fixed) occupied
        # endpoints. Relabel its edges to put these two disjoint classes first.
        surplus = sizes[-1] - len(fixed)
        if surplus < 0 or 2 * surplus > sizes[-1]:
            raise ValueError("requested anchor has no room for its edge classes")
        for side in (0, 1):
            for occurrence in colours[-1][side * surplus:(side + 1) * surplus]:
                for earlier in fixed:
                    cnf.append([-variables[side][earlier, occurrence]])
                cnf.append([variables[1 - side][earlier, occurrence] for earlier in fixed])
    return cnf, colours, variables


def decode(model: list[int], colours: list, variables: list) -> list:
    positive = {literal for literal in model if literal > 0}
    count = sum(map(len, colours))
    endpoints = []
    for current in variables:
        representative = list(range(count))
        for (i, j), literal in current.items():
            if literal in positive:
                representative[j] = min(representative[j], i)
        endpoints.append(representative)
    return [[(endpoints[0][i], endpoints[1][i]) for i in colour] for colour in colours]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sizes", type=int, nargs="+")
    parser.add_argument("--anchor", action="store_true",
                        help="requires a prior theorem for the colours except the last")
    parser.add_argument("--mixed-reduction", action="store_true",
                        help="adds necessary constraints from the (4,4,5,5) theorem")
    parser.add_argument("--solver", default="cadical195", choices=("cadical195", "glucose4"))
    parser.add_argument("--conflicts", type=int)
    parser.add_argument("--proof", type=Path, help="DIMACS/DRAT output stem")
    parser.add_argument("--witness", type=Path, help="save any explicit obstruction as JSON")
    args = parser.parse_args()
    if len(args.sizes) < 2 or min(args.sizes) < 1:
        parser.error("supply at least two positive sizes")
    if args.conflicts is not None and args.conflicts < 1:
        parser.error("the conflict budget must be positive")
    if args.proof and args.proof.suffix:
        parser.error("--proof takes a filename stem without an extension")
    cnf, colours, variables = encode(tuple(args.sizes), anchor=args.anchor,
                                    mixed_reduction=args.mixed_reduction)
    print(json.dumps({"sizes": args.sizes, "anchor": args.anchor, "solver": args.solver,
                      "variables": cnf.nv, "clauses": len(cnf.clauses),
                      "mixed_reduction": args.mixed_reduction,
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
            matchings = decode(solver.get_model(), colours, variables)
            if first_rainbow(matchings) is not None:
                raise RuntimeError("SAT model did not yield an obstruction")
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
