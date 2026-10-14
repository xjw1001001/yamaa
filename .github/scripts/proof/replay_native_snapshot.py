"""Proof-only replay of an immutable historical Actions artifact."""

import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import subprocess
import sys
import zipfile

RUN = 38497098490
SOURCE = "89b1fa90b0edfa03bc367f73426b630b36b20e85"
ARTIFACT = 11866226197


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def lane_id(row):
    return tuple(row.get(key) for key in ("kind", "os", "runtime_version", "package_form"))


def disposition(record):
    return {
        "complete": record["complete"],
        "summary": record["summary"],
        "failed_lanes": [
            {
                "identity": lane_id(row),
                "result": row["result"],
                "findings": [check for check in row["checks"] if check["result"] != "pass"],
            }
            for row in record["lanes"]
            if row["result"] != "pass"
        ],
    }


def extract(root):
    directory = root / "original"
    directory.mkdir()
    with zipfile.ZipFile(root / "original.zip") as archive:
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            windows = PureWindowsPath(item.filename)
            if (path.is_absolute() or ".." in path.parts or windows.drive
                    or "\\" in item.filename or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError(f"unsafe original ZIP member: {item.filename!r}")
        archive.extractall(directory)
    inputs = list(directory.glob("**/input/run.json"))
    if len(inputs) != 1:
        raise ValueError(f"expected one original snapshot, found {len(inputs)}")
    snapshot = inputs[0].parent
    run, source = read(snapshot / "run.json"), read(snapshot / "source.json")
    assert run["id"] == RUN and run["run_attempt"] == 1
    assert run["head_sha"] == SOURCE and source["sha"] == SOURCE
    assert run["repository"] == "elong0527/yamaa"
    assert (snapshot.parent / "qualification.json").is_file()
    write(root / "original-identity.json", {
        "artifact_id": ARTIFACT,
        "run": run,
        "source": source,
        "snapshot_relative_path": str(snapshot.relative_to(root)),
        "original_record": disposition(read(snapshot.parent / "qualification.json")),
        "proof_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "proof_head": os.environ["GITHUB_SHA"],
    })
    print(json.dumps(read(root / "original-identity.json"), indent=2))


def replay(root):
    identity = read(root / "original-identity.json")
    snapshot = root / identity["snapshot_relative_path"]
    original = read(snapshot.parent / "qualification.json")
    result = {"original": disposition(original), "readers": {}}
    failures = []
    for name, reader in (
        ("original", root / "original-source/rust/tools/audit_native_run.py"),
        ("current", Path("rust/tools/audit_native_run.py")),
    ):
        output = root / f"{name}-replay"
        with (root / f"{name}-replay.log").open("w", encoding="utf-8") as log:
            run = subprocess.run([sys.executable, str(reader), "--input", str(snapshot),
                                  "--output", str(output), "--check"],
                                 stdout=log, stderr=subprocess.STDOUT, check=False)
        record_path = output / "qualification.json"
        if not record_path.is_file():
            failures.append(f"{name} reader did not produce a record (exit {run.returncode})")
            result["readers"][name] = {"exit_code": run.returncode, "reader_error": True}
            print((root / f"{name}-replay.log").read_text())
            continue
        record = read(record_path)
        assert record["run"] == original["run"] and record["source"] == original["source"]
        assert run.returncode == int(not record["complete"])
        result["readers"][name] = {"exit_code": run.returncode, **disposition(record)}
        if name == "original":
            same = record_path.read_bytes() == (snapshot.parent / "qualification.json").read_bytes()
            result["original_record_exact_bytes"] = same
            if not same:
                failures.append("original algorithm did not replay original record bytes")
            earlier_replay = snapshot.parent / "replay/qualification.json"
            if earlier_replay.is_file():
                result["original_archived_replay_exact_bytes"] = record_path.read_bytes() == earlier_replay.read_bytes()
                if not result["original_archived_replay_exact_bytes"]:
                    failures.append("archived original replay differs")
        else:
            old = {lane_id(row): row for row in original["lanes"]}
            new = {lane_id(row): row for row in record["lanes"]}
            result["current_same_lane_identities"] = old.keys() == new.keys()
            changes = [{"identity": key, "original": old[key]["result"],
                        "current": new[key]["result"]}
                       for key in old.keys() & new.keys()
                       if old[key]["result"] != new[key]["result"]]
            result["current_disposition_changes"] = changes
            if old.keys() != new.keys() or changes:
                failures.append("current reader changes original lane identities/dispositions; inspect proof")
    result["reader_failures"] = failures
    write(root / "replay-comparison.json", result)
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    {"extract": extract, "replay": replay}[sys.argv[1]](Path(sys.argv[2]))
