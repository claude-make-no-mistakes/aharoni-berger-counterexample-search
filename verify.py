"""Check explicit coloured matchings without a SAT dependency."""

import argparse
import json
from itertools import product
from pathlib import Path


def first_rainbow(matchings: list) -> tuple[int, ...] | None:
    if not matchings or any(not colour for colour in matchings):
        raise ValueError("supply at least one edge in every colour")
    for colour in matchings:
        if any(len(edge) != 2 or any(type(v) is not int or v < 0 for v in edge)
               for edge in colour):
            raise ValueError("every edge needs two nonnegative integer endpoints")
        for side in (0, 1):
            if len({edge[side] for edge in colour}) != len(colour):
                raise ValueError("a colour repeats an endpoint")
    for indices in product(*(range(len(colour)) for colour in matchings)):
        edges = [colour[index] for colour, index in zip(matchings, indices)]
        if all(len({edge[side] for edge in edges}) == len(edges) for side in (0, 1)):
            return indices
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path)
    args = parser.parse_args()
    matchings = json.loads(args.instance.read_text(encoding="utf-8"))["matchings"]
    rainbow = first_rainbow(matchings)
    sizes = [len(colour) for colour in matchings]
    print(json.dumps({"sizes": sizes, "rainbow": rainbow,
                      "refutes_strong_conjecture": rainbow is None
                      and min(sizes) >= len(sizes) + 1}))


if __name__ == "__main__":
    main()
