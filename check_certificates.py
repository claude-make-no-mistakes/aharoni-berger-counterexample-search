"""Regenerate the three formulas and check the archived DRAT refutations."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from pysat.formula import CNF

import search
import supports


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checker", type=Path)
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    checker = args.checker.resolve(strict=True)
    archive = Path(__file__).with_name("certificates.zip")
    formulas = (("mixed44", search.encode((4, 4, 5, 5), anchor=True)[0]),
                ("six-by-six", supports.encode(6)[0]),
                ("six-by-seven", supports.encode(7)[0]))
    with ZipFile(archive) as bundle:
        for name, expected in formulas:
            with TemporaryDirectory(dir=args.scratch) as directory:
                cnf_path = Path(directory, name + ".cnf")
                proof_path = Path(directory, name + ".drat")
                for path in (cnf_path, proof_path):
                    with bundle.open(path.name) as data, path.open("wb") as output:
                        shutil.copyfileobj(data, output)
                archived = CNF(from_file=str(cnf_path))
                if archived.clauses != expected.clauses or archived.nv != expected.nv:
                    raise ValueError(f"formula regeneration differs for {name}")
                result = subprocess.run([str(checker), str(cnf_path), str(proof_path)],
                                        capture_output=True, text=True)
                if result.returncode or "s VERIFIED" not in result.stdout.splitlines():
                    raise RuntimeError(f"DRAT check failed for {name}\n{result.stdout}\n{result.stderr}")
                print(json.dumps({"case": name, "variables": archived.nv,
                                  "clauses": len(archived.clauses),
                                  "cnf_sha256": sha256(cnf_path),
                                  "drat_sha256": sha256(proof_path),
                                  "drat_verified": True}), flush=True)


if __name__ == "__main__":
    main()
