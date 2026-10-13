"""Reinstall the retained prior Python package without publishing any release."""

import argparse
import gc
import importlib.metadata
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = "elong0527/yamaa"
SOURCE = "845a91ff9ba4ab6599efbd79fafe1c4e1dd14255"
RELEASE = 411980272
TAG = "yamaa-py-reference-845a91ff"
PACKAGE_VERSION = "0.3.0"
CORE_VERSION = "0.1.0"
BUILD_TOOLCHAIN = "Rust 1.90.0; maturin 1.9.6; locked Cargo; optimized release"
ASSETS = {
    "yamaa-reference-845a91ff.tar.gz": (637944446, 5444762),
    "yamaa-0.3.0.tar.gz": (637944563, 1909336),
    "yamaa-0.3.0-cp312-abi3-linux_x86_64.whl": (637944633, 6978344),
    "uv.lock": (637944703, 556719),
    "baseline-dependencies.txt": (637944785, 336),
}
REPOSITORY_ARCHIVE = "yamaa-reference-845a91ff.tar.gz"
SOURCE_ARCHIVE = "yamaa-0.3.0.tar.gz"
LINUX_WHEEL = "yamaa-0.3.0-cp312-abi3-linux_x86_64.whl"
PLATFORMS = {
    "ubuntu-24.04": ("Linux", "x86_64"),
    "macos-15": ("Darwin", "arm64"),
    "windows-latest": ("Windows", "AMD64"),
}
CASES = {
    "schema-lookup": "adsl.csv",
    "adam-adlb-ordered-sum": "adlb.csv",
    "schema-window-functions": "advs.csv",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, record):
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def run_identity():
    return {
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "preparation_head": os.environ["GITHUB_SHA"],
    }


class StripRedirectCredentials(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, newurl):
        redirected = super().redirect_request(
            request, file, code, message, headers, newurl
        )
        if (
            urllib.parse.urlparse(request.full_url).hostname
            != urllib.parse.urlparse(newurl).hostname
        ):
            redirected.remove_header("Authorization")
        return redirected


def github(path, binary=False):
    request = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.build_opener(StripRedirectCredentials()).open(
            request, timeout=90
        ) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub prior-asset retrieval failed with HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("GitHub prior-asset retrieval failed during transport") from None
    return data if binary else json.loads(data)


def admit_release(record):
    require(
        record["id"] == RELEASE
        and record["tag_name"] == TAG
        and record["target_commitish"] == SOURCE
        and record["draft"] is True
        and record["prerelease"] is True,
        "prior release is not the reviewed unpublished retention draft",
    )
    require(
        len({asset["name"] for asset in record["assets"]}) == len(record["assets"]),
        "duplicate retained asset names",
    )
    actual = {asset["name"]: asset for asset in record["assets"]}
    for name, (asset_id, size) in ASSETS.items():
        require(
            name in actual
            and actual[name]["id"] == asset_id
            and actual[name]["size"] == size
            and actual[name]["state"] == "uploaded",
            "prior asset identity/name/size/state differs: " + name,
        )


def download(root):
    root.mkdir(parents=True, exist_ok=False)
    admit_release(github(f"/repos/{REPOSITORY}/releases/{RELEASE}"))
    downloaded = []
    for name, (asset_id, size) in ASSETS.items():
        data = github(f"/repos/{REPOSITORY}/releases/assets/{asset_id}", binary=True)
        require(len(data) == size, "retrieved prior asset size differs: " + name)
        (root / name).write_bytes(data)
        downloaded.append({"id": asset_id, "name": name, "bytes": len(data)})
    write_json(root / "asset-retrieval.json", {
        **run_identity(), "repository": REPOSITORY, "release_id": RELEASE,
        "release_tag": TAG, "source_revision": SOURCE,
        "release_remained_draft": True, "assets": downloaded,
    })


def archive_entries(data, prefix, selected=lambda name: True):
    entries = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts, "unsafe tar path")
            require(
                member.name.startswith(prefix)
                or (member.isdir() and member.name == prefix.rstrip("/")),
                "unexpected prior archive root",
            )
            if member.isdir():
                continue
            name = member.name.removeprefix(prefix)
            if not selected(name):
                continue
            require(name not in entries, "duplicate prior archive entry")
            if member.isfile():
                entries[name] = {
                    "kind": "file", "executable": bool(member.mode & 0o111),
                    "bytes": archive.extractfile(member).read(),
                }
            elif member.issym():
                entries[name] = {"kind": "symlink", "target": member.linkname}
            else:
                raise ValueError("unexpected prior archive entry kind")
    return entries


def packaged_path(name):
    if name.startswith("python/src/yamaa/"):
        return name.removeprefix("python/")
    if (
        name.startswith("rust/crates/")
        and ("/src/" in name or name.endswith("Cargo.toml"))
    ) or name in ("rust/Cargo.toml", "rust/Cargo.lock", "rust/rust-toolchain.toml"):
        return name
    if name in ("python/pyproject.toml", "python/yamaa_build_backend.py"):
        return name.removeprefix("python/")
    return None


def check_packaged_sources(assets):
    # This preflight reads package source and locks, without extracting study fixtures.
    prior = archive_entries(
        (assets / REPOSITORY_ARCHIVE).read_bytes(), "yamaa-reference-845a91ff/",
        lambda name: packaged_path(name) is not None or name == "python/uv.lock",
    )
    package = archive_entries((assets / SOURCE_ARCHIVE).read_bytes(), "yamaa-0.3.0/")
    require(not any(name.endswith((".so", ".pyd")) for name in package), "source package carries a binary")
    count = 0
    for name, entry in prior.items():
        if name == "python/uv.lock":
            require(entry["bytes"] == (assets / "uv.lock").read_bytes(), "prior Python lock differs")
            continue
        target = packaged_path(name)
        expected = entry.get("bytes")
        if name == "python/pyproject.toml":
            # maturin stages this one manifest path inside the standalone sdist.
            # Compare the exact packaging edit, preserving every other byte.
            original = b'manifest-path = "../rust/crates/yamaa-python/Cargo.toml"\n'
            staged = b'manifest-path = "rust/crates/yamaa-python/Cargo.toml"\n'
            require(expected.count(original) == 1, "prior manifest path is ambiguous")
            expected = expected.replace(original, b"", 1).replace(
                b"\n\n[tool.pytest.ini_options]", b"\n" + staged + b"\n[tool.pytest.ini_options]", 1
            )
        require(
            entry["kind"] == "file" and package.get(target, {}).get("bytes") == expected,
            "source package differs from retained prior source: " + name,
        )
        count += 1
    require(count >= 400, "prior packaged-source comparison incomplete")
    return count


def check_lane(os_name, python_minor):
    require(
        (platform.system(), platform.machine()) == PLATFORMS[os_name],
        "actual platform differs from requested prior lane",
    )
    require(
        ".".join(platform.python_version().split(".")[:2]) == python_minor,
        "actual interpreter differs from requested prior lane",
    )


def build(assets, output, os_name, python_minor, role):
    check_lane(os_name, python_minor)
    count = check_packaged_sources(assets)
    output.mkdir(parents=True, exist_ok=False)
    retained = role == "platform-wheel" and os_name == "ubuntu-24.04"
    if retained:
        shutil.copyfile(assets / LINUX_WHEEL, output / LINUX_WHEEL)
        method = "retained source-built Linux wheel"
    else:
        require(
            subprocess.check_output(["rustc", "--version"], text=True).startswith("rustc 1.90.0 "),
            "prior rebuild Rust toolchain differs",
        )
        require(importlib.metadata.version("maturin") == "1.9.6", "prior build backend differs")
        with (output / "build.log").open("wb") as log:
            completed = subprocess.run([
                sys.executable, "-m", "pip", "wheel", "--no-cache-dir", "--no-deps",
                "--no-build-isolation", "--wheel-dir", str(output), str(assets / SOURCE_ARCHIVE),
            ], stdout=log, stderr=subprocess.STDOUT, check=False)
        require(completed.returncode == 0, "prior source rebuild failed; retained build.log has details")
        method = "independent locked optimized source rebuild"
    wheels = list(output.glob("*.whl"))
    require(len(wheels) == 1 and wheels[0].name.startswith("yamaa-0.3.0-cp312-abi3-"), "prior wheel identity differs")
    write_json(output / "wheel-build.json", {
        **run_identity(), "source_revision": SOURCE, "source_asset_id": ASSETS[SOURCE_ARCHIVE][0],
        "repository_asset_id": ASSETS[REPOSITORY_ARCHIVE][0], "package_version": PACKAGE_VERSION,
        "core_version": CORE_VERSION, "os": os_name,
        "build_python": "3.12.14" if retained else platform.python_version(),
        "role": role, "method": method, "wheel": wheels[0].name,
        "wheel_bytes": wheels[0].stat().st_size, "packaged_sources_compared": count,
        "build_succeeded": True,
        "retained_wheel_asset_id": ASSETS[LINUX_WHEEL][0] if retained else None,
        "build_toolchain": BUILD_TOOLCHAIN,
    })


def admit_build(record, wheel_name, wheel_bytes, os_name, python_minor, form, identity):
    require(all(record[key] == value for key, value in identity.items()), "wheel build run/head owner differs")
    require(
        record["source_revision"] == SOURCE
        and record["source_asset_id"] == ASSETS[SOURCE_ARCHIVE][0]
        and record["repository_asset_id"] == ASSETS[REPOSITORY_ARCHIVE][0]
        and record["package_version"] == PACKAGE_VERSION and record["core_version"] == CORE_VERSION
        and record["os"] == os_name and record["wheel"] == wheel_name
        and record["wheel_bytes"] == wheel_bytes
        and record["build_succeeded"] is True
        and record["build_toolchain"] == BUILD_TOOLCHAIN
        and type(record["packaged_sources_compared"]) is int and record["packaged_sources_compared"] >= 400,
        "prior wheel provenance differs",
    )
    require(
        record["role"] == ("independent-source-rebuild" if form == "source" else "platform-wheel")
        and record["build_python"].startswith((python_minor if form == "source" else "3.12") + "."),
        "prior distribution form or build-interpreter owner differs",
    )
    retained = form == "wheel" and os_name == "ubuntu-24.04"
    require(
        record["method"] == ("retained source-built Linux wheel" if retained else "independent locked optimized source rebuild")
        and record["retained_wheel_asset_id"] == (ASSETS[LINUX_WHEEL][0] if retained else None),
        "prior wheel authority differs",
    )


def replay(assets, wheel_root, proof, os_name, python_minor, form):
    check_lane(os_name, python_minor)
    require(Path(sys.prefix).name == "prior-package-env", "fresh prior environment name differs")
    distribution = importlib.metadata.distribution("yamaa")
    require(distribution.version == PACKAGE_VERSION, "prior package version differs")
    installed = Path(distribution.locate_file("")).resolve()
    require(installed.is_relative_to(Path(sys.prefix).resolve()), "prior distribution belongs to another environment")
    import yamaa
    from yamaa import _native

    require(yamaa.__version__ == PACKAGE_VERSION, "prior module version differs")
    # engine_info is historical metadata of this exact prior package, not a candidate endpoint.
    require(_native.engine_info()["core_version"] == CORE_VERSION, "prior native core version differs")
    require(
        Path(yamaa.__file__).resolve().is_relative_to(installed)
        and Path(_native.__file__).resolve().is_relative_to(installed),
        "prior Python/native module owner differs",
    )
    wheels = list(wheel_root.glob("*.whl"))
    require(len(wheels) == 1, "fresh prior install wheel is ambiguous")
    wheel = wheels[0]
    build_record = json.loads((wheel_root / "wheel-build.json").read_text())
    admit_build(build_record, wheel.name, wheel.stat().st_size, os_name, python_minor, form, run_identity())
    if form == "wheel" and os_name == "ubuntu-24.04":
        require(wheel.read_bytes() == (assets / LINUX_WHEEL).read_bytes(), "retained Linux wheel bytes differ")
    compared = 0
    with zipfile.ZipFile(wheel) as archive:
        require(len(set(archive.namelist())) == len(archive.namelist()), "duplicate wheel members")
        for member in archive.infolist():
            if member.is_dir() or member.filename.endswith("/RECORD"):
                continue
            path = PurePosixPath(member.filename)
            require(not path.is_absolute() and ".." not in path.parts, "unsafe wheel member")
            require(distribution.locate_file(member.filename).read_bytes() == archive.read(member), "freshly installed wheel member bytes differ")
            compared += 1
    require(compared > 10, "fresh prior wheel comparison incomplete")
    pins = (assets / "baseline-dependencies.txt").read_text().splitlines()
    require(len(pins) == 17 and len(set(pins)) == 17, "prior dependency pin set differs")
    for pin in pins:
        name, version = pin.split("==")
        require(importlib.metadata.version(name) == version, "prior installed dependency version differs: " + name)
    proof.mkdir(parents=True, exist_ok=False)
    version = {
        **run_identity(), "source_tag": "yamaa-py-0.3.0", "source_revision": SOURCE,
        "release_id": RELEASE, "release_tag": TAG, "source_asset_id": ASSETS[SOURCE_ARCHIVE][0],
        "repository_asset_id": ASSETS[REPOSITORY_ARCHIVE][0], "installed_form": form,
        "os": os_name, "python": python_minor, "runtime_version": platform.python_version(),
        "system": platform.system(), "machine": platform.machine(),
        "platform": platform.platform(), "runner_image": os.environ["ImageOS"],
        "runner_image_version": os.environ["ImageVersion"],
        "package_version": distribution.version, "core_version": CORE_VERSION,
        "environment": str(Path(sys.prefix).resolve()), "package_location": str(installed / "yamaa"),
        "native_location": str(Path(_native.__file__).resolve()),
        "wheel_name": wheel.name, "wheel_bytes": wheel.stat().st_size,
        "installed_wheel_members_compared": compared, "dependency_pins_verified": pins,
        "version_checked_before_study_data": True,
        "association": "source-built prior-release package; no published prior binary asset",
    }
    write_json(proof / "version-before-study-data.json", version)
    shutil.copyfile(wheel_root / "wheel-build.json", proof / "wheel-build.json")
    shutil.copyfile(assets / "asset-retrieval.json", proof / "asset-retrieval.json")
    if (wheel_root / "build.log").exists():
        shutil.copyfile(wheel_root / "build.log", proof / "build.log")
    prior = proof / "prior-inputs"
    entries = archive_entries(
        (assets / REPOSITORY_ARCHIVE).read_bytes(), "yamaa-reference-845a91ff/",
        lambda name: name.startswith("yaml/") or any(name.startswith(f"benchmarks/{case}/") for case in CASES) or name == "python/uv.lock",
    )
    for name, entry in entries.items():
        require(entry["kind"] == "file", "unexpected non-regular selected prior fixture")
        target = prior / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(entry["bytes"])
    require((prior / "python/uv.lock").read_bytes() == (assets / "uv.lock").read_bytes(), "prior fixture lock differs")
    reports = []
    for name, output_name in CASES.items():
        authored = prior / "benchmarks" / name
        expected = (authored / "expected" / output_name).read_bytes()
        case = proof / "execution" / name
        shutil.copytree(authored, case, ignore=shutil.ignore_patterns("expected"))
        built = yamaa.yamaa_domain(case / "spec.yaml", schema_root=prior / "yaml")
        require(built.output is not None and built.issues.is_empty(), "prior authored domain replay failed: " + name)
        output_before = built.output
        destination_root = proof / name
        destination_root.mkdir()
        output_before.write_ipc(destination_root / "output-before-save.arrow")
        built.issues.write_ipc(destination_root / "issues.arrow")
        shutil.rmtree(case)
        gc.collect()
        for attempt in ("first", "second"):
            destination = destination_root / (attempt + "-" + output_name)
            require(built.save(destination) == destination.resolve(), "prior held Save path differs")
            require(destination.read_bytes() == expected, "prior held Save bytes differ from independently committed truth")
        require(built.output.equals(output_before), "prior result changed after held Saves")
        built.output.write_ipc(destination_root / "output-after-saves.arrow")
        require(
            (destination_root / "output-before-save.arrow").read_bytes()
            == (destination_root / "output-after-saves.arrow").read_bytes(),
            "prior raw output bytes changed after held Saves",
        )
        (destination_root / "committed-expected.csv").write_bytes(expected)
        reports.append({
            "case": name, "truth_source_revision": SOURCE,
            "truth_path": f"benchmarks/{name}/expected/{output_name}", "result": "pass",
            "rows": output_before.height, "columns": list(output_before.columns),
            "expected_bytes": len(expected), "saves": 2,
            "input_and_spec_removed_before_saves": True, "output_unchanged_after_saves": True,
        })
    write_json(proof / "receipt.json", {
        **version, "rehearsal": "pass", "cases": reports,
        "scope": "fresh prior package installation, three committed domains and six post-input-removal Saves",
        "remaining_scope": ["full producer graph Save baseline", "published rollback pin", "transition approval"],
    })
    print(f"Prior Python {PACKAGE_VERSION} {os_name}/{python_minor}/{form}: three committed cases and six held Saves passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    fetch = subcommands.add_parser("download")
    fetch.add_argument("--assets", type=Path, required=True)
    for command in ("build", "replay"):
        subparser = subcommands.add_parser(command)
        subparser.add_argument("--assets", type=Path, required=True)
        subparser.add_argument("--os", choices=PLATFORMS, required=True)
        subparser.add_argument("--python", choices=("3.12", "3.13", "3.14"), required=True)
        if command == "build":
            subparser.add_argument("--output", type=Path, required=True)
            subparser.add_argument("--role", choices=("platform-wheel", "independent-source-rebuild"), required=True)
        else:
            subparser.add_argument("--wheel-root", type=Path, required=True)
            subparser.add_argument("--proof", type=Path, required=True)
            subparser.add_argument("--form", choices=("wheel", "source"), required=True)
    args = parser.parse_args()
    if args.command == "download":
        download(args.assets)
    elif args.command == "build":
        build(args.assets.resolve(), args.output.resolve(), args.os, args.python, args.role)
    else:
        replay(args.assets.resolve(), args.wheel_root.resolve(), args.proof.resolve(), args.os, args.python, args.form)


if __name__ == "__main__":
    main()
