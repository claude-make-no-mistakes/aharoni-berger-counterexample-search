# Strong Aharoni–Berger counterexample search

Every collection of at most five bipartite matchings, each with at least one more edge than the number of matchings, has a full rainbow matching. The case of five colours follows from a mixed-size lemma for sizes $4,4,5,5$ and two finite formulas on $6\times6$ and $6\times7$ endpoints. The proof allows shared edges across colours. It uses three DRAT refutations. [Paper](paper.pdf) · [LaTeX source](paper.tex) · [Certificate bundle](certificates.zip)

## Replay

Use Python 3.10 or newer, the pinned Python-SAT dependency, and a compiled DRAT-trim executable. Replay regenerates each formula, compares all clauses with the archive, and checks the corresponding refutation. The largest extracted pair uses about 76 MB of scratch disk. [DRAT-trim source](https://github.com/marijnheule/drat-trim)

```sh
python -m pip install -r requirements.txt
python check_certificates.py /path/to/drat-trim
python verify.py mixed-obstruction.json
```

The last command checks an explicit instance with no full rainbow and sizes (4,4,4,5), which shows why the mixed-size proof needs both larger matchings. The sizes fall below the strong conjecture's hypothesis. Use `search.py` to generate formulas for other size vectors. Its optional anchor requires a prior full-rainbow theorem for the initial colours. The six-colour run uses the five-colour result for that step.

```sh
python search.py 7 7 7 7 7 7 --anchor --conflicts 800000 --witness six-witness.json
```

That six-colour run reached its conflict budget without a proof or counterexample. A separate search of sizes (5,5,5,6,6) also reached its budget. The unrestricted conjecture remains open. [Original conjecture](https://doi.org/10.37236/208) · [2026 statement](https://doi.org/10.1112/jlms.70660)
