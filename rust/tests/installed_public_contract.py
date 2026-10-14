"""Installed public API contracts with independent authored inputs and truth."""

from __future__ import annotations

import gc
import inspect
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import polars as pl
import yamaa
from yamaa import _locked_functions as host

SPEC = """schema_version: '1.0'
domain: TEST
keys: [ID]
input: {SRC: input.csv}
columns:
  - {name: ID, type: str, derivation: SRC.ID}
  - {name: VALUE, type: int, derivation: SRC.VALUE}
output: {path: output.csv, columns: [ID, VALUE]}
"""
INPUT = b"ID,VALUE\na,-9223372036854775808\nb,9223372036854775807\nc,\n"
VALUES = [-9223372036854775808, 9223372036854775807, None]


class PublicContract(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="yamaa-public-contract-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.spec = self.root / "spec.yaml"
        self.spec.write_text(SPEC, encoding="utf-8")
        (self.root / "input.csv").write_bytes(INPUT)

    def test_bounded_clinical_width_inheritance_and_text_keep_complete_held_saves(self):
        # These authored correctness cases do not alter the timing campaign.
        def complete(document, names, rows, *, inherited=False):
            for artifact in ("output.csv", "parent.yaml"):
                (self.root / artifact).unlink(missing_ok=True)
            if inherited:
                (self.root / "parent.yaml").write_text(document, encoding="utf-8")
                self.spec.write_text("schema_version: '1.0'\nparents: [parent.yaml]\n", encoding="utf-8")
            else:
                self.spec.write_text(document, encoding="utf-8")
            self.assertTrue(yamaa.check(self.spec).issues.is_empty())
            result = yamaa.domain(self.spec)
            self.assertTrue(result.issues.is_empty(), result.issues)
            self.assertFalse((self.root / "output.csv").exists())
            self.assertEqual(result.output.columns, names)
            self.assertEqual(result.output.dtypes, [pl.String] * len(names))
            self.assertEqual(result.output.rows(), rows)
            self.assertIsNone(result.verification_log)
            self.assertIsNone(result.warning_log)
            expected = (",".join(names) + "\n" + "".join(
                ",".join("" if value is None else value for value in row) + "\n" for row in rows)).encode()
            for _ in range(2):
                self.assertTrue(result.save())
                self.assertEqual((self.root / "output.csv").read_bytes(), expected)
                self.assertEqual(result.output.rows(), rows)

        def edge_budget_refusal(document, *, inherited=False):
            # Exact original complex geometry; the unchanged arena separately
            # refuses this combination, before Build publication or either Save.
            for artifact in ("output.csv", "parent.yaml"):
                (self.root / artifact).unlink(missing_ok=True)
            if inherited:
                (self.root / "parent.yaml").write_text(document, encoding="utf-8")
                self.spec.write_text("schema_version: '1.0'\nparents: [parent.yaml]\n", encoding="utf-8")
            else:
                self.spec.write_text(document, encoding="utf-8")
            check = self.issues(yamaa.check(self.spec))
            self.assertFalse(check.is_empty())
            result = yamaa.domain(self.spec)
            issues = self.issues(result)
            self.assertFalse(issues.is_empty())
            self.assertTrue(all(row["phase"] == "engine" and row["condition"] == "engine_rejected"
                                for row in issues.to_dicts()))
            self.assertIsNone(result.output)
            self.assertFalse((self.root / "output.csv").exists())
            for _ in range(2):
                with self.assertRaises(yamaa.DomainError):
                    result.save()
                self.assertEqual(result.issues.to_dicts(), issues.to_dicts())
                self.assertIsNone(result.output)
                self.assertFalse((self.root / "output.csv").exists())

        for width in (40, 150, 256):
            names = ["ID"] + [f"F{i:03d}" for i in range(1, width)]
            columns = "  - {name: ID, type: str, derivation: SRC.ID}\n" + "".join(
                f"  - name: {name}\n    type: str\n    derivation:\n      case:\n"
                f"        - {{when: \"SRC.A = 'x' AND SRC.B = '{index % 3}'\", then: {{literal: P}}}}\n"
                "        - {when: \"SRC.A IS NULL\", then: {literal: Q}}\n"
                "        - {otherwise: SRC.A}\n" for index, name in enumerate(names[1:], 1))
            document = ("schema_version: '1.0'\ndomain: TEST\nkeys: [ID]\ninput: {SRC: input.csv}\n"
                        f"columns:\n{columns}output: {{path: output.csv, columns: [{', '.join(names)}]}}\n")
            (self.root / "input.csv").write_bytes(b"ID,A,B\nS-001,x,1\nS-002,y,2\nS-003,,3\n")
            rows = [tuple(["S-001"] + ["P" if i % 3 == 1 else "x" for i in range(1, width)]),
                    tuple(["S-002"] + ["y"] * (width - 1)), tuple(["S-003"] + ["Q"] * (width - 1))]
            for inherited in ((False, True) if width < 256 else (False,)):
                with self.subTest(width=width, inherited=inherited):
                    complete(document, names, rows, inherited=inherited)
            empty_parent_document = document.replace("domain: TEST", "parents: []\ndomain: TEST")
            if width < 256:
                with self.subTest(width=width, empty_parents=True):
                    complete(empty_parent_document, names, rows)
            else:
                with self.subTest(width=width, edge_budget_refusal="inherited"):
                    edge_budget_refusal(document, inherited=True)
                with self.subTest(width=width, edge_budget_refusal="empty-parents"):
                    edge_budget_refusal(empty_parent_document)

        # Separate complete 256-column headroom, with the original source rows.
        names = ["ID"] + [f"F{i:03d}" for i in range(1, 256)]
        columns = "  - {name: ID, type: str, derivation: SRC.ID}\n" + "".join(
            f"  - {{name: {name}, type: str, derivation: SRC.A}}\n" for name in names[1:])
        document = ("schema_version: '1.0'\ndomain: TEST\nkeys: [ID]\ninput: {SRC: input.csv}\n"
                    f"columns:\n{columns}output: {{path: output.csv, columns: [{', '.join(names)}]}}\n")
        rows = [tuple(["S-001"] + ["x"] * 255), tuple(["S-002"] + ["y"] * 255),
                tuple(["S-003"] + [None] * 255)]
        with self.subTest(width=256, simple_inherited=True):
            complete(document, names, rows, inherited=True)
        with self.subTest(width=256, simple_empty_parents=True):
            complete(document.replace("domain: TEST", "parents: []\ndomain: TEST"), names, rows)

        names = ["ID"] + [f"F{i:02d}" for i in range(1, 41)]
        rows = [tuple([f"S{i:06d}"] + ["Y" if i % 2 else "N"] * 40) for i in range(1, 4001)]
        (self.root / "input.csv").write_text("ID,T\n" + "".join(
            f"S{i:06d},{('a' if i % 2 else 'b') * 40}\n" for i in range(1, 4001)), encoding="utf-8")
        columns = "  - {name: ID, type: str, derivation: SRC.ID}\n" + "".join(
            f"  - name: {name}\n    type: str\n    derivation:\n      case:\n"
            f"        - {{when: \"SRC.T = '{'a' * 40}'\", then: {{literal: Y}}}}\n"
            "        - {otherwise: {literal: N}}\n" for name in names[1:])
        complete("schema_version: '1.0'\ndomain: TEST\nkeys: [ID]\ninput: {SRC: input.csv}\n"
                 f"columns:\n{columns}output: {{path: output.csv, columns: [{', '.join(names)}]}}\n", names, rows)

        rows = [(f"S{i:06d}", "t" * 80) for i in range(1, 30001)]
        (self.root / "input.csv").write_text("ID,T\n" + "".join(f"{key},{value}\n" for key, value in rows), encoding="utf-8")
        complete("schema_version: '1.0'\ndomain: TEST\nkeys: [ID]\ninput: {SRC: input.csv}\n"
                 "columns:\n  - {name: ID, type: str, derivation: SRC.ID}\n"
                 "  - {name: T, type: str, derivation: SRC.T}\n"
                 "output: {path: output.csv, columns: [ID, T]}\n", ["ID", "T"], rows)

    def issues(self, result):
        frame = result.issues
        self.assertEqual(
            frame.columns,
            ["phase", "condition", "requirement", "spec_paths", "context"],
        )
        self.assertEqual(
            frame.dtypes,
            [pl.String, pl.String, pl.String, pl.List(pl.String), pl.String],
        )
        for row in frame.to_dicts():
            self.assertIsInstance(json.loads(row["context"]), dict)
            self.assertTrue(row["condition"])
        return frame

    def test_component_endpoints_are_absent_from_the_installed_binding(self):
        from yamaa import _native
        for name in ('engine_info', 'analyze_aggregate', 'analyze_numeric', 'analyze_predicate', 'analyze_dependencies', 'analyze_column_dependencies', 'analyze_references', 'reference_capabilities', 'dataset_capabilities', 'scalar_round_trip', 'evaluate_numeric', 'evaluate_regex', 'table_round_trip', 'table_snapshot', 'execute_dataset', 'execute_dataset_sources', 'execute_dataset_functions', 'invoke_function', 'interpret_schema', 'decode_yaml', '_compile_schema', '_Schema', '_compile_reference_catalog', '_ReferenceCatalog', '_profile_dataset_functions'):
            with self.subTest(name=name):
                self.assertFalse(hasattr(_native, name))
        self.assertIsInstance(_native._CORE_VERSION, str)
        self.assertTrue(_native._CORE_VERSION)
        self.assertEqual(yamaa.__version__, "0.4.0")
        self.assertEqual(_native._CORE_VERSION, yamaa.__version__)

    def test_signatures_argument_types_and_removed_options(self):
        for function in (yamaa.domain, yamaa.check):
            parameters = inspect.signature(function).parameters
            self.assertEqual(list(parameters), ["specification", "environment"])
            self.assertEqual(
                parameters["environment"].kind, inspect.Parameter.KEYWORD_ONLY
            )
            self.assertIsNone(parameters["environment"].default)
            for value in (None, 7, True, [], object()):
                with self.subTest(
                    function=function.__name__, value=type(value).__name__
                ):
                    with self.assertRaises(TypeError):
                        function(value)
                    if value is not None:
                        with self.assertRaises(TypeError):
                            function(self.spec, environment=value)
            with self.assertRaises(TypeError):
                function(self.spec, None)
            for option in (
                "schema_root",
                "project_root",
                "data_roots",
                "read_project_configuration",
                "dispatcher",
                "study_document",
            ):
                with self.subTest(option=option), self.assertRaises(TypeError):
                    function(self.spec, **{option: None})

    def test_missing_specification_is_an_issue_and_failed_save_is_typed(self):
        absent = self.root / "absent.yaml"
        for function in (yamaa.check, yamaa.domain):
            result = function(absent)
            self.assertGreater(self.issues(result).height, 0)
            for name in ("spec", "specification", "resolved", "resolved_specification"):
                self.assertFalse(hasattr(result, name))
            if function is yamaa.domain:
                self.assertIsNone(result.output)
                before = result.issues.to_dicts()
                for _ in range(2):
                    with self.assertRaises(yamaa.DomainError):
                        result.save()
                    self.assertEqual(result.issues.to_dicts(), before)
        self.assertFalse((self.root / "output.csv").exists())

    def test_read_only_views_repeated_builds_and_owned_publication(self):
        first, second = yamaa.domain(self.spec), yamaa.domain(self.spec)
        for result in (first, second):
            self.assertTrue(self.issues(result).is_empty())
            self.assertEqual(result.output["VALUE"].to_list(), VALUES)
            self.assertIsNone(result.verification_log)
            self.assertIsNone(result.warning_log)
            for name in ("output", "issues", "verification_log", "warning_log"):
                with self.subTest(name=name), self.assertRaises(AttributeError):
                    setattr(result, name, None)
            with self.assertRaises(TypeError):
                result.save(self.root / "other.csv")
        self.assertFalse((self.root / "output.csv").exists())
        view = first.output
        view[0, "VALUE"] = 9
        self.assertEqual(first.output["VALUE"].to_list(), VALUES)
        self.spec.unlink()
        (self.root / "input.csv").unlink()
        gc.collect()
        for _ in range(2):
            self.assertIs(first.save(), True)
            self.assertEqual((self.root / "output.csv").read_bytes(), INPUT)
        del first
        gc.collect()
        self.assertEqual(second.output["VALUE"].to_list(), VALUES)
        self.assertIs(second.save(), True)

    def test_exact_nul_text_and_empty_literal_are_distinct_from_missing(self):
        self.spec.write_text(
            SPEC.replace("VALUE, type: int", "VALUE, type: str")
            .replace(
                "output: {",
                "  - {name: EMPTY, type: str, derivation: {literal: ''}}\noutput: {",
            )
            .replace("columns: [ID, VALUE]", "columns: [ID, VALUE, EMPTY]"),
            encoding="utf-8",
        )
        (self.root / "input.csv").write_bytes(b"ID,VALUE\na,a\x00b\nb,\xc3\xa9\nc,\n")
        result = yamaa.domain(self.spec)
        self.assertTrue(self.issues(result).is_empty())
        self.assertEqual(result.output["VALUE"].to_list(), ["a\x00b", "\u00e9", None])
        self.assertEqual(result.output["EMPTY"].to_list(), ["", "", ""])
        result.save()
        self.assertEqual(
            (self.root / "output.csv").read_bytes(),
            b'ID,VALUE,EMPTY\na,a\x00b,""\nb,\xc3\xa9,""\nc,,""\n',
        )

    def test_failed_verification_retains_owned_diagnostic_log(self):
        self.spec.write_text(
            SPEC.replace(
                "  - {name: VALUE, type: int, derivation: SRC.VALUE}",
                "  - name: VALUE\n    type: int\n    derivation: SRC.VALUE\n"
                "    verifications:\n"
                "      - range: {max: 0, severity: warning, id: warn}\n"
                "      - range: {max: 0, severity: error, id: fatal}",
            )
            .replace(
                "output: {",
                "verifications:\n  - row_count: {min: 0, id: unreached}\noutput: {",
            )
            .replace(
                "columns: [ID, VALUE]}",
                "columns: [ID, VALUE], verification_log: checks.csv, warning_log: warnings.csv}",
            ),
            encoding="utf-8",
        )
        (self.root / "input.csv").write_bytes(b"ID,VALUE\na,-3\nb,7\nc,\n")
        for name in ("output.csv", "warnings.csv"):
            (self.root / name).write_bytes(b"sentinel")
        result = yamaa.domain(self.spec)
        issues = self.issues(result).to_dicts()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["condition"], "range_failed")
        self.assertIsNone(result.output)
        # REQ-0396 builds the warning artifact only for successful runs;
        # REQ-1177 retains the evaluated diagnostic prefix on failure.
        self.assertIsNone(result.warning_log)
        view = result.verification_log
        self.assertEqual(view["VERIFICATION_ID"].to_list(), ["warn", "fatal"])
        self.assertEqual(view["OUTCOME"].to_list(), ["violated", "violated"])
        self.assertEqual(view["EVALUATED_COUNT"].to_list(), [3, 3])
        self.assertEqual(view["FAILURE_COUNT"].to_list(), [1, 1])
        self.assertEqual(view["REQUIREMENT"].to_list(), ["REQ-0377", "REQ-0377"])
        truth = view.to_dicts()
        view[0, "REPORT_VERSION"] = "changed"
        self.spec.unlink()
        (self.root / "input.csv").unlink()
        gc.collect()
        for _ in range(2):
            with self.assertRaises(yamaa.DomainError):
                result.save()
            self.assertEqual(result.issues.to_dicts(), issues)
            self.assertEqual(result.verification_log.to_dicts(), truth)
            self.assertEqual((self.root / "output.csv").read_bytes(), b"sentinel")
            self.assertEqual((self.root / "warnings.csv").read_bytes(), b"sentinel")
            lines = (self.root / "checks.csv").read_bytes().splitlines()
            self.assertEqual(len(lines), 3)
        held = result.verification_log
        del result
        gc.collect()
        self.assertEqual(held.to_dicts(), truth)

    def function_study(self):
        original = (
            Path(__file__).with_name("project-original") / "negative-function-contract"
        )
        case = self.root / "project"
        shutil.copytree(original, case)
        source = case / "spec.yaml"
        source.write_text(
            source.read_text(encoding="utf-8").replace(
                "args: {}", "args: {x: SOURCE.VALUE}"
            ),
            encoding="utf-8",
        )
        return source, case / "python/environment.yaml"

    def test_activation_interrupt_preserves_original_exception(self):
        source, environment = self.function_study()
        original = KeyboardInterrupt("public contract activation interrupt")
        with (
            patch.object(host, "verify_versions", side_effect=original),
            self.assertRaises(KeyboardInterrupt) as seen,
        ):
            yamaa.domain(source, environment=environment)
        self.assertIs(seen.exception, original)
        self.assertFalse((source.parent / "test.csv").exists())

    def test_callback_can_reenter_public_check_and_domain(self):
        source, environment = self.function_study()
        resolve = host.resolve_callable
        calls = []

        def resolve_reentrant(reference, parameters):
            invoke = resolve(reference, parameters)

            def callback(**arguments):
                checked = yamaa.check(self.spec)
                nested = yamaa.domain(self.spec)
                self.assertTrue(checked.issues.is_empty())
                self.assertTrue(nested.issues.is_empty())
                self.assertEqual(nested.output["VALUE"].to_list(), VALUES)
                calls.append(nested)
                return invoke(**arguments)

            return callback

        with patch.object(host, "resolve_callable", side_effect=resolve_reentrant):
            result = yamaa.domain(source, environment=environment)
        self.assertTrue(self.issues(result).is_empty(), result.issues)
        self.assertGreaterEqual(len(calls), 3)
        self.spec.unlink()
        gc.collect()
        self.assertEqual(calls[0].output["VALUE"].to_list(), VALUES)
        self.assertFalse((self.root / "output.csv").exists())

    def test_public_define_signature_and_missing_environment(self):
        parameters = inspect.signature(yamaa.define).parameters
        self.assertEqual(list(parameters), ["environment", "standard", "created"])
        self.assertEqual(parameters["created"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIsNone(parameters["created"].default)
        result = yamaa.define(
            self.root / "absent-environment.yaml", "sdtm", created="2026-09-11T00:00:00"
        )
        self.assertGreater(self.issues(result).height, 0)
        with self.assertRaises(yamaa.DefineError):
            result.save()
        with self.assertRaises(TypeError):
            yamaa.define(None, "sdtm")


if __name__ == "__main__":
    unittest.main()
