"""Mutation controls for draft identity and source admission; no network access."""

import copy
import unittest

import retain


class DraftAdmissionTests(unittest.TestCase):
    def test_each_exact_reviewed_draft_is_admitted(self):
        for release in retain.RELEASES.values():
            retain.admit_draft(self.record(release), release)

    @staticmethod
    def record(release):
        return {
            "id": release["id"],
            "tag_name": release["tag"],
            "target_commitish": release["source"],
            "draft": True,
            "prerelease": True,
            "assets": [],
        }

    def test_published_wrong_release_or_wrong_source_is_refused(self):
        for release in retain.RELEASES.values():
            for key, wrong in (
                ("id", 409220247),
                ("tag_name", "yamaa-py-0.3.0"),
                ("target_commitish", "main"),
                ("draft", False),
                ("prerelease", False),
            ):
                record = self.record(release)
                record[key] = wrong
                with (
                    self.subTest(release=release["id"], key=key),
                    self.assertRaises(ValueError),
                ):
                    retain.admit_draft(record, release)

    def test_unexpected_or_duplicate_asset_names_are_refused(self):
        for release in retain.RELEASES.values():
            for assets in (
                [{"name": "unreviewed.exe"}],
                [{"name": next(iter(release["assets"]))}] * 2,
            ):
                record = self.record(release)
                record["assets"] = assets
                with self.assertRaises(ValueError):
                    retain.admit_draft(record, release)

    def test_python_archive_cannot_be_relabelled_under_changed_source(self):
        source = retain.source_files(retain.PYTHON_SOURCE)
        changed = copy.copy(source)
        changed["python/src/yamaa/__init__.py"] += b"\n# altered source\n"
        with self.assertRaisesRegex(ValueError, "prior repository archive differs"):
            retain.check_python(retain.ROOT / "payload/python", changed)

    def test_r_archive_cannot_be_relabelled_under_changed_core(self):
        source = retain.source_files(retain.R_SOURCE)
        changed = copy.copy(source)
        changed["rust/crates/yamaa-core/src/lib.rs"] += b"\n// altered source\n"
        with self.assertRaisesRegex(ValueError, "R package source differs"):
            retain.check_r(retain.ROOT / "payload/r", changed)


if __name__ == "__main__":
    unittest.main()
