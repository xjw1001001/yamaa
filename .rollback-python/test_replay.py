"""Mutate actual rollback admissions without changing independent truth."""

import copy
import json
import shutil
import tempfile
import unittest
import urllib.request
from pathlib import Path

import audit
import polars as pl
import replay

IDENTITY = {"run_id": "unit-run", "run_attempt": "1", "preparation_head": "unit-head"}
PINS = ["dependency==1.0"]


def build_record(os_name, python, form, name, size):
    retained = os_name == "ubuntu-24.04" and form == "wheel"
    return {
        **IDENTITY, "source_revision": replay.SOURCE,
        "source_asset_id": replay.ASSETS[replay.SOURCE_ARCHIVE][0],
        "repository_asset_id": replay.ASSETS[replay.REPOSITORY_ARCHIVE][0],
        "package_version": replay.PACKAGE_VERSION, "core_version": replay.CORE_VERSION,
        "os": os_name, "build_python": (python if form == "source" else "3.12") + ".9",
        "role": "independent-source-rebuild" if form == "source" else "platform-wheel",
        "method": "retained source-built Linux wheel" if retained else "independent locked optimized source rebuild",
        "wheel": name, "wheel_bytes": size, "packaged_sources_compared": 408,
        "build_succeeded": True,
        "build_toolchain": replay.BUILD_TOOLCHAIN,
        "retained_wheel_asset_id": replay.ASSETS[replay.LINUX_WHEEL][0] if retained else None,
    }


class PriorRollbackAdmissions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.truth = {f"benchmarks/{name}/expected/{filename}": b"x,y\n42,ok\n" for name, filename in replay.CASES.items()}
        wheel_names = {
            "ubuntu-24.04": replay.LINUX_WHEEL,
            "macos-15": "yamaa-0.3.0-cp312-abi3-macosx_11_0_arm64.whl",
            "windows-latest": "yamaa-0.3.0-cp312-abi3-win_amd64.whl",
        }
        for os_name in replay.PLATFORMS:
            root = self.root / f"prior-wheel-{os_name}"
            root.mkdir()
            name = wheel_names[os_name]
            (root / name).write_bytes(b"wheel" * 4000)
            replay.write_json(root / "wheel-build.json", build_record(os_name, "3.12", "wheel", name, 20000))
        for os_name, python, form in audit.LANES:
            root = self.root / f"prior-rollback-{os_name}-{python}-{form}"
            root.mkdir()
            environment = "C:/fresh/prior-package-env" if os_name == "windows-latest" else "/fresh/prior-package-env"
            package = environment + "/lib/yamaa"
            version = {
                **IDENTITY, "source_tag": "yamaa-py-0.3.0", "source_revision": replay.SOURCE,
                "release_id": replay.RELEASE, "release_tag": replay.TAG,
                "source_asset_id": replay.ASSETS[replay.SOURCE_ARCHIVE][0],
                "repository_asset_id": replay.ASSETS[replay.REPOSITORY_ARCHIVE][0],
                "os": os_name, "python": python, "installed_form": form,
                "runtime_version": python + ".9", "system": replay.PLATFORMS[os_name][0],
                "machine": replay.PLATFORMS[os_name][1], "package_version": replay.PACKAGE_VERSION,
                "platform": "unit-platform", "runner_image": "unit-image", "runner_image_version": "unit-image-version",
                "core_version": replay.CORE_VERSION, "environment": environment,
                "package_location": package, "native_location": package + "/_native.abi3.so",
                "wheel_name": wheel_names[os_name], "wheel_bytes": 20000,
                "installed_wheel_members_compared": 135, "dependency_pins_verified": PINS,
                "version_checked_before_study_data": True,
                "association": "source-built prior-release package; no published prior binary asset",
            }
            replay.write_json(root / "version-before-study-data.json", version)
            replay.write_json(root / "wheel-build.json", build_record(os_name, python, form, wheel_names[os_name], 20000))
            replay.write_json(root / "asset-retrieval.json", {
                **IDENTITY, "repository": replay.REPOSITORY, "release_id": replay.RELEASE,
                "release_tag": replay.TAG, "source_revision": replay.SOURCE, "release_remained_draft": True,
                "assets": [{"id": asset_id, "name": name, "bytes": size} for name, (asset_id, size) in replay.ASSETS.items()],
            })
            if form == "source":
                (root / "build.log").write_text("successful locked source build\n")
            cases = []
            for name, filename in replay.CASES.items():
                family = root / name
                family.mkdir()
                expected = self.truth[f"benchmarks/{name}/expected/{filename}"]
                for saved in ("committed-expected.csv", "first-" + filename, "second-" + filename):
                    (family / saved).write_bytes(expected)
                pl.DataFrame({"x": [42], "y": ["ok"]}).write_ipc(family / "output-before-save.arrow")
                shutil.copyfile(family / "output-before-save.arrow", family / "output-after-saves.arrow")
                pl.DataFrame({"phase": pl.Series([], dtype=pl.String)}).write_ipc(family / "issues.arrow")
                cases.append({
                    "case": name, "truth_source_revision": replay.SOURCE,
                    "truth_path": f"benchmarks/{name}/expected/{filename}", "result": "pass",
                    "rows": 1, "columns": ["x", "y"], "expected_bytes": len(expected), "saves": 2,
                    "input_and_spec_removed_before_saves": True, "output_unchanged_after_saves": True,
                })
            replay.write_json(root / "receipt.json", {**version, "rehearsal": "pass", "cases": cases})
        self.lane = self.root / "prior-rollback-ubuntu-24.04-3.12-source"

    def admit(self):
        return audit.audit_receipts(self.root, self.truth, PINS, IDENTITY)

    def change(self, filename, update):
        path = self.lane / filename
        record = json.loads(path.read_text())
        update(record)
        replay.write_json(path, record)

    def change_version(self, key, value):
        for filename in ("version-before-study-data.json", "receipt.json"):
            self.change(filename, lambda record: record.update({key: value}))

    def test_complete_actual_lane_inventory_is_admitted(self):
        self.assertEqual(len(self.admit()), 18)

    def test_missing_or_extra_lane_is_refused(self):
        shutil.rmtree(self.lane)
        with self.assertRaisesRegex(ValueError, "lane set"):
            self.admit()
        self.lane.mkdir()
        (self.root / "prior-rollback-unapproved-form").mkdir()
        with self.assertRaisesRegex(ValueError, "lane set"):
            self.admit()

    def test_wrong_source_package_core_form_and_lane_are_refused(self):
        for key, value in (
            ("source_revision", "wrong-source"), ("source_asset_id", 637944446),
            ("package_version", "0.4.0"), ("core_version", "0.4.0"),
            ("installed_form", "wheel"), ("python", "3.14"), ("os", "macos-15"),
            ("runtime_version", "3.14.9"), ("run_attempt", "2"),
        ):
            with self.subTest(key=key):
                original = {name: (self.lane / name).read_bytes() for name in ("version-before-study-data.json", "receipt.json")}
                self.change_version(key, value)
                with self.assertRaises(ValueError):
                    self.admit()
                for name, data in original.items():
                    (self.lane / name).write_bytes(data)

    def test_final_receipt_cannot_relabel_before_data_version(self):
        self.change("receipt.json", lambda record: record.update(runtime_version="3.12.99"))
        with self.assertRaisesRegex(ValueError, "before-data"):
            self.admit()

    def test_false_or_numeric_version_check_is_refused(self):
        for value in (False, 1):
            self.change_version("version_checked_before_study_data", value)
            with self.assertRaises(ValueError):
                self.admit()

    def test_foreign_module_or_native_owner_is_refused(self):
        for key in ("package_location", "native_location"):
            with self.subTest(key=key):
                original = {name: (self.lane / name).read_bytes() for name in ("version-before-study-data.json", "receipt.json")}
                self.change_version(key, "/foreign/yamaa/_native.so")
                with self.assertRaisesRegex(ValueError, "ownership"):
                    self.admit()
                for name, data in original.items():
                    (self.lane / name).write_bytes(data)

    def test_source_form_requires_own_interpreter_and_build_role(self):
        for key, value in (("role", "platform-wheel"), ("build_python", "3.12.8"), ("build_succeeded", 1)):
            original = (self.lane / "wheel-build.json").read_bytes()
            self.change("wheel-build.json", lambda record, key=key, value=value: record.update({key: value}))
            with self.assertRaises(ValueError):
                self.admit()
            (self.lane / "wheel-build.json").write_bytes(original)

    def test_missing_source_build_log_is_refused(self):
        (self.lane / "build.log").unlink()
        with self.assertRaisesRegex(ValueError, "build log"):
            self.admit()

    def test_shared_wheel_cannot_belong_to_another_run(self):
        path = self.root / "prior-wheel-macos-15" / "wheel-build.json"
        record = json.loads(path.read_text())
        record["run_id"] = "foreign-run"
        replay.write_json(path, record)
        with self.assertRaisesRegex(ValueError, "run/head"):
            self.admit()

    def test_source_retrieval_cannot_relabel_asset(self):
        self.change("asset-retrieval.json", lambda record: record["assets"][0].update(id=637944563))
        with self.assertRaisesRegex(ValueError, "retrieval identity"):
            self.admit()

    def test_case_inventory_order_and_truth_owner_are_refused(self):
        for update in (
            lambda record: record["cases"].reverse(),
            lambda record: record["cases"][0].update(truth_path="benchmarks/other/expected/adsl.csv"),
            lambda record: record["cases"][0].update(truth_source_revision="wrong-truth"),
            lambda record: record["cases"][0].update(saves=2.0),
        ):
            original = (self.lane / "receipt.json").read_bytes()
            self.change("receipt.json", update)
            with self.assertRaises(ValueError):
                self.admit()
            (self.lane / "receipt.json").write_bytes(original)

    def test_altered_truth_and_each_save_are_refused(self):
        for name in ("committed-expected.csv", "first-adsl.csv", "second-adsl.csv"):
            path = self.lane / "schema-lookup" / name
            original = path.read_bytes()
            path.write_bytes(b"x,y\n43,ok\n")
            with self.assertRaisesRegex(ValueError, "Save/truth bytes"):
                self.admit()
            path.write_bytes(original)

    def test_raw_issue_and_ordered_output_shape_are_refused(self):
        family = self.lane / "schema-lookup"
        pl.DataFrame({"phase": ["error"]}).write_ipc(family / "issues.arrow")
        with self.assertRaisesRegex(ValueError, "raw table"):
            self.admit()
        pl.DataFrame({"phase": pl.Series([], dtype=pl.String)}).write_ipc(family / "issues.arrow")
        pl.DataFrame({"y": ["ok"], "x": [42]}).write_ipc(family / "output-before-save.arrow")
        shutil.copyfile(family / "output-before-save.arrow", family / "output-after-saves.arrow")
        with self.assertRaisesRegex(ValueError, "raw table"):
            self.admit()

    def test_changed_raw_value_or_numeric_bits_are_refused(self):
        family = self.lane / "schema-lookup"
        pl.DataFrame({"x": [43], "y": ["ok"]}).write_ipc(family / "output-before-save.arrow")
        with self.assertRaisesRegex(ValueError, "raw output bytes"):
            self.admit()

    def test_inputs_retained_for_held_save_are_refused(self):
        (self.lane / "execution" / "schema-lookup").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "study inputs remain"):
            self.admit()

    def test_missing_raw_output_is_refused(self):
        (self.lane / "schema-lookup" / "output-before-save.arrow").unlink()
        with self.assertRaises(FileNotFoundError):
            self.admit()

    def test_exact_draft_target_asset_and_publication_state_are_required(self):
        record = {
            "id": replay.RELEASE, "tag_name": replay.TAG, "target_commitish": replay.SOURCE,
            "draft": True, "prerelease": True,
            "assets": [{"id": asset_id, "name": name, "size": size, "state": "uploaded"} for name, (asset_id, size) in replay.ASSETS.items()],
        }
        replay.admit_release(record)
        for update in (
            lambda value: value.update(draft=False),
            lambda value: value.update(target_commitish="wrong-source"),
            lambda value: value["assets"][0].update(id=637944563),
            lambda value: value["assets"][0].update(size=1),
        ):
            mutated = copy.deepcopy(record)
            update(mutated)
            with self.assertRaises(ValueError):
                replay.admit_release(mutated)

    def test_redirect_strips_credentials_before_another_host(self):
        request = urllib.request.Request("https://api.github.com/asset", headers={"Authorization": "Bearer unit-token"})
        redirected = replay.StripRedirectCredentials().redirect_request(request, None, 302, "", {}, "https://storage.example/asset")
        self.assertIsNone(redirected.get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
