"""Retain reviewed bytes in two existing drafts; never publish or overwrite."""

import argparse
import io
import json
import os
import subprocess
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPOSITORY = "elong0527/yamaa"
PYTHON_SOURCE = "845a91ff9ba4ab6599efbd79fafe1c4e1dd14255"
R_SOURCE = "a1a9c2d216075f331ac108aa4d3638573f103cea"
RELEASES = {
    "r": {
        "id": 411979803,
        "tag": "yamaa-r-reference-a1a9c2d2",
        "source": R_SOURCE,
        "assets": {
            "yamaa_0.3.0.tar.gz": 3290128,
            "fresh-install-receipts.zip": 27653,
            "retention-manifest.json": 1008,
        },
    },
    "python": {
        "id": 411980272,
        "tag": "yamaa-py-reference-845a91ff",
        "source": PYTHON_SOURCE,
        "assets": {
            "yamaa-reference-845a91ff.tar.gz": 5444762,
            "yamaa-0.3.0.tar.gz": 1909336,
            "yamaa-0.3.0-cp312-abi3-linux_x86_64.whl": 6978344,
            "uv.lock": 556719,
            "baseline-dependencies.txt": 336,
            "fresh-install-receipts.zip": 463021,
            "fresh-source-rebuilt-wheel.zip": 6935822,
            "retention-manifest.json": 1766,
        },
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def tar_members(data, prefix):
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            require(
                not path.is_absolute() and ".." not in path.parts, "unsafe tar path"
            )
            require(
                member.name.startswith(prefix)
                or (member.isdir() and member.name == prefix.rstrip("/")),
                "unexpected tar root",
            )
            if member.isfile():
                name = member.name.removeprefix(prefix)
                require(name not in result, "duplicate tar member")
                result[name] = archive.extractfile(member).read()
    return result


def source_files(revision):
    return tar_members(
        subprocess.check_output(["git", "archive", "--prefix=source/", revision]),
        "source/",
    )


def zip_members(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(set(names)) == len(names), "duplicate ZIP member")
        for name in names:
            member = PurePosixPath(name)
            require(
                not member.is_absolute() and ".." not in member.parts, "unsafe ZIP path"
            )
        return {name: archive.read(name) for name in names if not name.endswith("/")}


def check_python(root, source):
    prior = tar_members(
        (root / "yamaa-reference-845a91ff.tar.gz").read_bytes(),
        "yamaa-reference-845a91ff/",
    )
    require(prior == source, "prior repository archive differs from exact source")
    require(
        (root / "uv.lock").read_bytes() == source["python/uv.lock"],
        "prior lock differs",
    )
    sdist = tar_members((root / "yamaa-0.3.0.tar.gz").read_bytes(), "yamaa-0.3.0/")
    require(
        not any(name.endswith((".so", ".pyd")) for name in sdist),
        "sdist contains native binary",
    )
    for name, data in source.items():
        if name.startswith("python/src/yamaa/"):
            packaged = name.removeprefix("python/")
        elif (
            name.startswith("rust/crates/")
            and ("/src/" in name or name.endswith("Cargo.toml"))
            or name
            in ("rust/Cargo.toml", "rust/Cargo.lock", "rust/rust-toolchain.toml")
        ):
            packaged = name
        else:
            continue
        require(sdist.get(packaged) == data, f"sdist source differs: {name}")
    proof = zip_members(root / "fresh-install-receipts.zip")
    for form in ("reinstall-proof", "source-reinstall-proof"):
        receipt = json.loads(proof[form + "/receipt.json"])
        require(
            receipt["source_revision"] == PYTHON_SOURCE
            and receipt["package_version"] == "0.3.0",
            "Python receipt source/version differs",
        )
        require(
            receipt["runtime_version"] == "3.12.14"
            and receipt["system"] == "Linux"
            and receipt["machine"] == "x86_64",
            "Python receipt tuple differs",
        )
        require(
            receipt["rehearsal"] == "pass"
            and receipt["version_checked_before_study_data"] is True
            and receipt["installed_wheel_members_compared"] == 135,
            "Python reinstall incomplete",
        )
        require(
            [case["case"] for case in receipt["cases"]]
            == ["schema-lookup", "adam-adlb-ordered-sum", "schema-window-functions"],
            "Python receipt case set differs",
        )
        for case in receipt["cases"]:
            require(
                case["result"] == "pass"
                and case["saves"] == 2
                and case["input_and_spec_removed_before_saves"] is True
                and case["output_unchanged_after_saves"] is True,
                "Python held Saves incomplete",
            )
            require(
                case["truth_source_revision"] == PYTHON_SOURCE,
                "Python truth source differs",
            )
            expected = source[case["truth_path"]]
            family = case["case"]
            artifact = Path(case["truth_path"]).name
            require(
                proof[f"{form}/{family}/committed-expected.csv"] == expected,
                "Python retained truth differs",
            )
            for attempt in ("first", "second"):
                require(
                    proof[f"{form}/{family}/{attempt}-{artifact}"] == expected,
                    "Python Save bytes differ",
                )
    wheel = zip_members(root / "yamaa-0.3.0-cp312-abi3-linux_x86_64.whl")
    for name, data in source.items():
        if name.startswith("python/src/yamaa/") and name.endswith(".py"):
            require(
                wheel.get(name.removeprefix("python/src/")) == data,
                "Python wheel source differs",
            )
    require(
        b"Version: 0.3.0\n" in wheel["yamaa-0.3.0.dist-info/METADATA"],
        "Python wheel version differs",
    )
    require(
        sum(name.endswith(".so") for name in wheel) == 1,
        "Python native wheel member differs",
    )
    rebuilt = zip_members(root / "fresh-source-rebuilt-wheel.zip")
    require(
        set(rebuilt) == {"yamaa-0.3.0-cp312-abi3-linux_x86_64.whl"},
        "rebuilt wheel bundle differs",
    )
    with zipfile.ZipFile(
        io.BytesIO(rebuilt["yamaa-0.3.0-cp312-abi3-linux_x86_64.whl"])
    ) as archive:
        for name, data in source.items():
            if name.startswith("python/src/yamaa/") and name.endswith(".py"):
                require(
                    archive.read(name.removeprefix("python/src/")) == data,
                    "rebuilt wheel source differs",
                )


def check_r(root, source):
    package = tar_members((root / "yamaa_0.3.0.tar.gz").read_bytes(), "yamaa/")
    fields = package["DESCRIPTION"].decode().splitlines()
    require(
        "Package: yamaa" in fields and "Version: 0.3.0" in fields,
        "R package version differs",
    )
    count = 0
    for name, data in source.items():
        if (
            name.startswith("rust/crates/")
            and ("/src/" in name or name.endswith("Cargo.toml"))
            or name
            in ("rust/Cargo.toml", "rust/Cargo.lock", "rust/rust-toolchain.toml")
        ):
            packaged = "src/" + name
        elif name.startswith("R/yamaa/") and (
            "/R/" in name or "/src/" in name or name.endswith("NAMESPACE")
        ):
            packaged = name.removeprefix("R/yamaa/")
        else:
            continue
        require(package.get(packaged) == data, f"R package source differs: {name}")
        count += 1
    require(count >= 395, "R source proof incomplete")
    proof = zip_members(root / "fresh-install-receipts.zip")
    summary = json.loads(proof["rehearsal-summary.json"])
    require(
        summary["run_id"] == 38435902670
        and summary["preparation_head"] == "d909928c94f308550c7f584c12b6b42506c4c84c"
        and summary["source_revision"] == R_SOURCE
        and summary["rehearsal"] == "pass"
        and summary["remaining_platforms"] == [],
        "R canonical rehearsal identity differs",
    )
    require(
        [row["platform"] for row in summary["platforms"]]
        == ["ubuntu-24.04", "macos-15", "windows-latest"],
        "R rehearsal platform set differs",
    )
    for row in summary["platforms"]:
        require(
            row["result"] == "pass"
            and row["source_archive_bytes_equal"] is True
            and row["version_checked_before_study_data"] is True
            and row["source_artifact_id"] == 11811851297,
            "R rehearsal incomplete",
        )
        prefix = f"r-source-rollback-{row['platform']}/r-rollback-proof/"
        receipt = json.loads(proof[prefix + "artifact-receipt.json"])
        require(
            receipt["source_revision"] == R_SOURCE
            and receipt["artifact_id"] == 11811851297
            and receipt["package_version"] == "0.3.0"
            and receipt["source_archive_bytes"] == 3290128,
            "R receipt source/artifact differs",
        )
        result = proof[prefix + "rehearsal-result.txt"].decode().splitlines()
        version = proof[prefix + "installed-version.txt"].decode().splitlines()
        require(
            "rehearsal=pass" in result
            and "version_checked_before_study_data=true" in version
            and "installed_package_version=0.3.0" in version,
            "R fresh install proof incomplete",
        )


def check_payloads():
    checks = {}
    for language, release in RELEASES.items():
        root = ROOT / "payload" / language
        require(
            {path.name for path in root.iterdir()} == set(release["assets"]),
            "asset allowlist differs",
        )
        for name, size in release["assets"].items():
            require(
                (root / name).is_file()
                and (root / name).stat().st_size == size
                and size < 8_000_000,
                "asset size/type differs",
            )
        manifest = json.loads((root / "retention-manifest.json").read_text())
        require(
            manifest["source_revision"] == release["source"]
            and manifest["package_version"] == "0.3.0"
            and manifest["draft_release_id"] == release["id"]
            and manifest["draft_tag_name"] == release["tag"],
            "retention manifest identity differs",
        )
        source = source_files(release["source"])
        (check_r if language == "r" else check_python)(root, source)
        checks[language] = {
            "source_revision": release["source"],
            "package_version": "0.3.0",
            "source_and_receipts": "pass",
            "assets": list(release["assets"]),
        }
    return checks


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


def github(path, *, data=None, binary=False, upload=False):
    host = "uploads.github.com" if upload else "api.github.com"
    headers = {
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "Accept": "application/octet-stream"
        if binary
        else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if data is not None:
        headers["Content-Type"] = "application/octet-stream"
    request = urllib.request.Request(
        "https://" + host + path, data=data, headers=headers
    )
    try:
        with urllib.request.build_opener(StripRedirectCredentials()).open(
            request, timeout=90
        ) as response:
            result = response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"GitHub asset operation failed with HTTP {error.code}"
        ) from None
    except urllib.error.URLError:
        raise RuntimeError("GitHub asset operation failed during transport") from None
    return result if binary else json.loads(result)


def admit_draft(record, release):
    require(
        record["id"] == release["id"]
        and record["tag_name"] == release["tag"]
        and record["target_commitish"] == release["source"]
        and record["draft"] is True
        and record["prerelease"] is True,
        "existing release is not the exact reviewed unpublished draft",
    )
    require(
        len({asset["name"] for asset in record["assets"]}) == len(record["assets"])
        and all(asset["name"] in release["assets"] for asset in record["assets"]),
        "draft has duplicate or unexpected assets",
    )


def retain(checks, output):
    receipt = {
        "repository": REPOSITORY,
        "publication": "unpublished drafts; no publication operation",
        "checks": checks,
        "releases": [],
    }
    for language, release in RELEASES.items():
        path = f"/repos/{REPOSITORY}/releases/{release['id']}"
        record = github(path)
        admit_draft(record, release)
        assets = {asset["name"]: asset for asset in record["assets"]}
        row = {
            "release_id": release["id"],
            "tag_name": release["tag"],
            "source_revision": release["source"],
            "draft": True,
            "assets": [],
        }
        for name, size in release["assets"].items():
            payload = (ROOT / "payload" / language / name).read_bytes()
            current = github(path)
            admit_draft(current, release)
            if name not in assets:
                asset = github(
                    path + "/assets?name=" + urllib.parse.quote(name),
                    data=payload,
                    upload=True,
                )
            else:
                asset = assets[name]
            require(
                asset["name"] == name and asset["size"] == size,
                "uploaded asset identity/size differs",
            )
            fetched = github(
                f"/repos/{REPOSITORY}/releases/assets/{asset['id']}", binary=True
            )
            require(fetched == payload, "authenticated retained asset bytes differ")
            row["assets"].append(
                {
                    "asset_id": asset["id"],
                    "name": name,
                    "bytes": size,
                    "authenticated_api_reference": f"https://api.github.com/repos/{REPOSITORY}/releases/assets/{asset['id']}",
                    "bytes_equal": True,
                    "reused_without_overwrite": name in assets,
                }
            )
        admit_draft(github(path), release)
        receipt["releases"].append(row)
        output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        "Both reviewed draft asset sets uploaded and authenticated bytes compared; no publication"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--upload", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    checks = check_payloads()
    if args.upload:
        require(args.output is not None, "upload requires a retained retrieval receipt")
        require(
            os.environ.get("GITHUB_REPOSITORY") == REPOSITORY
            and os.environ.get("GITHUB_REF")
            == "refs/heads/migration/rollback-draft-retention"
            and os.environ.get("GITHUB_EVENT_NAME") == "push",
            "upload is restricted to the reviewed isolated Actions branch",
        )
        retain(checks, args.output)
    else:
        print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
