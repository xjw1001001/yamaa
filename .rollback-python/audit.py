"""Admit only all eighteen actual retained-prior package reinstall receipts."""

import argparse
import csv
import io
import json
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath

from replay import (
    ASSETS,
    CASES,
    CORE_VERSION,
    LINUX_WHEEL,
    PACKAGE_VERSION,
    PLATFORMS,
    RELEASE,
    REPOSITORY,
    REPOSITORY_ARCHIVE,
    SOURCE,
    SOURCE_ARCHIVE,
    TAG,
    admit_build,
    archive_entries,
    check_packaged_sources,
    require,
    run_identity,
    write_json,
)

PYTHONS = ("3.12", "3.13", "3.14")
FORMS = ("wheel", "source")
LANES = tuple((os_name, python, form) for os_name in PLATFORMS for python in PYTHONS for form in FORMS)


def exactly(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def admit_retrieval(record, identity):
    require(all(record[key] == value for key, value in identity.items()), "asset retrieval run/head differs")
    require(
        record["repository"] == REPOSITORY and record["release_id"] == RELEASE
        and record["release_tag"] == TAG and record["source_revision"] == SOURCE
        and record["release_remained_draft"] is True
        and exactly(record["assets"], [
            {"id": asset_id, "name": name, "bytes": size} for name, (asset_id, size) in ASSETS.items()
        ]),
        "prior asset retrieval identity differs",
    )


def admit_version(record, os_name, python, form, identity, pins):
    require(all(record[key] == value for key, value in identity.items()), "receipt run/head differs")
    require(
        record["os"] == os_name and record["python"] == python and record["installed_form"] == form
        and record["source_tag"] == "yamaa-py-0.3.0" and record["source_revision"] == SOURCE
        and record["release_id"] == RELEASE and record["release_tag"] == TAG
        and record["source_asset_id"] == ASSETS[SOURCE_ARCHIVE][0]
        and record["repository_asset_id"] == ASSETS[REPOSITORY_ARCHIVE][0]
        and record["package_version"] == PACKAGE_VERSION and record["core_version"] == CORE_VERSION,
        "prior receipt tuple/source/package/core differs",
    )
    require(
        record["runtime_version"].startswith(python + ".")
        and (record["system"], record["machine"]) == PLATFORMS[os_name]
        and record["version_checked_before_study_data"] is True
        and isinstance(record["platform"], str) and bool(record["platform"])
        and isinstance(record["runner_image"], str) and bool(record["runner_image"])
        and isinstance(record["runner_image_version"], str) and bool(record["runner_image_version"])
        and type(record["installed_wheel_members_compared"]) is int
        and record["installed_wheel_members_compared"] > 10
        and exactly(record["dependency_pins_verified"], pins),
        "fresh prior runtime/installation admission incomplete",
    )
    path_type = PureWindowsPath if os_name == "windows-latest" else PurePosixPath
    environment = path_type(record["environment"])
    require(
        environment.is_absolute() and environment.name == "prior-package-env"
        and path_type(record["package_location"]).is_relative_to(environment)
        and path_type(record["native_location"]).is_relative_to(path_type(record["package_location"])),
        "prior Python/native ownership differs",
    )
    require(
        record["wheel_name"].startswith("yamaa-0.3.0-cp312-abi3-")
        and type(record["wheel_bytes"]) is int and record["wheel_bytes"] > 10000
        and record["association"] == "source-built prior-release package; no published prior binary asset",
        "prior installed wheel authority differs",
    )


def check_raw_tables(root, record, expected):
    import polars as pl

    require(
        (root / "output-before-save.arrow").read_bytes()
        == (root / "output-after-saves.arrow").read_bytes(),
        "retained prior raw output bytes changed after held Saves",
    )
    output = pl.read_ipc(root / "output-before-save.arrow", memory_map=False)
    issues = pl.read_ipc(root / "issues.arrow", memory_map=False)
    rows = list(csv.reader(io.StringIO(expected.decode("utf-8"))))
    require(
        issues.is_empty() and output.height == record["rows"] == len(rows) - 1
        and output.columns == record["columns"] == rows[0],
        "retained prior raw table/issues/ordered shape differs",
    )


def audit_receipts(artifacts, truth, pins, identity):
    expected_directories = {f"prior-rollback-{os_name}-{python}-{form}" for os_name, python, form in LANES}
    expected_directories |= {f"prior-wheel-{os_name}" for os_name in PLATFORMS}
    require({path.name for path in artifacts.iterdir()} == expected_directories, "prior rollback artifact lane set differs")
    shared = {}
    for os_name in PLATFORMS:
        root = artifacts / f"prior-wheel-{os_name}"
        wheels = list(root.glob("*.whl"))
        require(len(wheels) == 1, "platform prior wheel artifact is ambiguous")
        record = json.loads((root / "wheel-build.json").read_text())
        admit_build(record, wheels[0].name, wheels[0].stat().st_size, os_name, "3.12", "wheel", identity)
        if os_name == "ubuntu-24.04":
            require(wheels[0].name == LINUX_WHEEL, "retained Linux wheel name differs")
        shared[os_name] = record
    qualified = []
    for os_name, python, form in LANES:
        root = artifacts / f"prior-rollback-{os_name}-{python}-{form}"
        record = json.loads((root / "receipt.json").read_text())
        version = json.loads((root / "version-before-study-data.json").read_text())
        admit_version(version, os_name, python, form, identity, pins)
        require(all(key in record and exactly(record[key], value) for key, value in version.items()), "before-data version proof differs from final receipt")
        require(record["rehearsal"] == "pass", "prior reinstall did not pass")
        admit_retrieval(json.loads((root / "asset-retrieval.json").read_text()), identity)
        build = json.loads((root / "wheel-build.json").read_text())
        admit_build(build, version["wheel_name"], version["wheel_bytes"], os_name, python, form, identity)
        if form == "wheel":
            require(exactly(build, shared[os_name]), "installed platform wheel belongs to another build")
        else:
            require(build["build_python"] == version["runtime_version"], "independent source rebuild belongs to another interpreter")
            require((root / "build.log").is_file(), "independent prior source build log missing")
        require([case["case"] for case in record["cases"]] == list(CASES), "prior receipt authored case inventory differs")
        for case in record["cases"]:
            name = case["case"]
            path = f"benchmarks/{name}/expected/{CASES[name]}"
            expected = truth[path]
            require(
                case["truth_source_revision"] == SOURCE and case["truth_path"] == path
                and case["result"] == "pass" and type(case["saves"]) is int and case["saves"] == 2
                and case["input_and_spec_removed_before_saves"] is True
                and case["output_unchanged_after_saves"] is True
                and type(case["expected_bytes"]) is int and case["expected_bytes"] == len(expected),
                "prior authored truth or held Save admission differs",
            )
            require(not (root / "execution" / name).exists(), "prior study inputs remain for held Save")
            for filename in ("committed-expected.csv", "first-" + CASES[name], "second-" + CASES[name]):
                require((root / name / filename).read_bytes() == expected, "retained prior Save/truth bytes differ")
            check_raw_tables(root / name, case, expected)
        qualified.append({"os": os_name, "python": python, "form": form, "runtime_version": version["runtime_version"], "result": "pass"})
    return qualified


def audit(assets, artifacts, output):
    identity = run_identity()
    admit_retrieval(json.loads((assets / "asset-retrieval.json").read_text()), identity)
    source = archive_entries(
        subprocess.check_output(["git", "archive", "--prefix=source/", SOURCE]), "source/",
    )
    retained = archive_entries((assets / REPOSITORY_ARCHIVE).read_bytes(), "yamaa-reference-845a91ff/")
    require(retained == source, "retained repository regular bytes, symlinks or executable modes differ from exact prior source")
    check_packaged_sources(assets)
    require((artifacts / "prior-wheel-ubuntu-24.04" / LINUX_WHEEL).read_bytes() == (assets / LINUX_WHEEL).read_bytes(), "retained Linux platform wheel bytes differ")
    truth = {name: entry["bytes"] for name, entry in source.items() if entry["kind"] == "file"}
    lanes = audit_receipts(artifacts, truth, (assets / "baseline-dependencies.txt").read_text().splitlines(), identity)
    write_json(output, {
        **identity, "repository": REPOSITORY, "source_revision": SOURCE,
        "source_tag": "yamaa-py-0.3.0", "release_id": RELEASE, "release_tag": TAG,
        "package_version": PACKAGE_VERSION, "core_version": CORE_VERSION,
        "rehearsal": "pass", "required_lanes": 18, "qualified_lanes": lanes,
        "repository_entries_compared": len(source), "retained_linux_wheel_bytes_equal": True,
        "scope": "18 fresh prior wheel/source installations; three committed domains and six held Saves per lane",
        "remaining_scope": ["full producer graph Save baseline", "published rollback pin", "transition approval"],
    })
    print("All 18 prior Python rollback tuples passed exact source/ownership and held Save admission.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.assets, args.artifacts, args.output)


if __name__ == "__main__":
    main()
