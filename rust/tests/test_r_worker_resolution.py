"""Engine-free controls for Windows R's separate architecture launcher."""

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_r_child_peak_rss as control
import child_peak_rss as rss
import measure_public_lifecycle as lifecycle


class RWorkerResolution(unittest.TestCase):
    # Authored launcher fixture, not an original Actions qualification record.
    requested = "C:/R/bin/Rscript.exe"
    direct = "C:/R/bin/x64/Rscript.exe"
    private = "C:/private R library"

    def fixture(self):
        origin = {
            "pid": 5168,
            "runtime_version": "4.6.1",
            "home": "C:/R",
            "bin": "C:/R/bin/x64",
            "architecture": "x86_64",
            "r_arch": "x64",
            "jsonlite_version": "2.0.0",
            "private_libraries": [self.private],
            "codec_origin": self.private + "/jsonlite",
            "direct_executable": self.direct,
        }
        return origin, dict(origin, pid=5169)

    def probes(self, origins):
        calls = []

        def popen(command, stdout, stderr):
            number = len(calls)
            calls.append(command)
            stdout.write(b"original probe stdout\n")
            stderr.write(b"original probe stderr\n")
            Path(command[-1]).write_text(
                json.dumps(origins[number], indent=2) + "\n", encoding="utf-8"
            )
            return SimpleNamespace(pid=[9192, 5169][number], wait=lambda: 0)

        return calls, popen

    def test_resolves_real_architecture_child_and_keeps_all_original_arguments(self):
        requested, direct = self.fixture()
        calls, popen = self.probes([requested, direct])
        command = [self.requested, "--vanilla", "worker.R", "request with space.json"]
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch("platform.system", return_value="Windows"),
            mock.patch.dict("os.environ", {"R_LIBS": self.private}),
            mock.patch("subprocess.Popen", side_effect=popen),
        ):
            root = Path(directory)
            observed, resolution = rss.r_worker_command(command, root / "process.json")
            self.assertEqual(observed, [self.direct, *command[1:]])
            self.assertEqual(resolution["requested_command"], command)
            self.assertEqual(resolution["observed_command"], observed)
            self.assertEqual([call[0] for call in calls], [self.requested, self.direct])
            self.assertTrue(all(call[1] == "--vanilla" for call in calls))
            self.assertEqual(
                (root / "r-worker-origin-probe.R").read_text(), rss.R_ORIGIN_PROBE
            )
            for label, origin in [("requested", requested), ("direct", direct)]:
                raw = root / f"r-worker-{label}-origin.json"
                self.assertEqual(
                    raw.read_bytes(), (json.dumps(origin, indent=2) + "\n").encode()
                )
                receipt = json.loads(
                    (root / f"r-worker-{label}-probe.json").read_text()
                )
                self.assertEqual(
                    receipt["command"], calls[["requested", "direct"].index(label)]
                )
                self.assertEqual(receipt["origin"], origin)
                self.assertEqual(
                    (root / receipt["stdout"]).read_bytes(), b"original probe stdout\n"
                )
                self.assertEqual(
                    (root / receipt["stderr"]).read_bytes(), b"original probe stderr\n"
                )
            self.assertNotEqual(
                resolution["requested_origin"]["launcher_pid"], requested["pid"]
            )
            self.assertEqual(
                resolution["observed_origin"]["launcher_pid"], direct["pid"]
            )

    def test_wrong_direct_pid_namespace_or_runtime_refuses_without_worker_observation(
        self,
    ):
        for changed in [
            {"pid": 9192},
            {"home": "C:/another R"},
            {"jsonlite_version": "1.9.0"},
            {"private_libraries": ["C:/other library"]},
            {"codec_origin": "C:/other library/jsonlite"},
        ]:
            with (
                self.subTest(changed=changed),
                tempfile.TemporaryDirectory() as directory,
            ):
                requested, direct = self.fixture()
                direct.update(changed)
                calls, popen = self.probes([requested, direct])
                with (
                    mock.patch("platform.system", return_value="Windows"),
                    mock.patch.dict("os.environ", {"R_LIBS": self.private}),
                    mock.patch("subprocess.Popen", side_effect=popen),
                    self.assertRaises(ValueError),
                ):
                    rss.r_worker_command(
                        [self.requested, "--vanilla", "worker.R"],
                        Path(directory) / "process.json",
                    )
                root = Path(directory)
                self.assertEqual(len(calls), 2)
                self.assertEqual(
                    json.loads((root / "r-worker-direct-origin.json").read_text()),
                    direct,
                )
                self.assertFalse((root / "process.json").exists())

    def test_same_wrong_private_namespace_cannot_pass_both_probes(self):
        requested, direct = self.fixture()
        requested["private_libraries"] = direct["private_libraries"] = ["C:/another"]
        requested["codec_origin"] = direct["codec_origin"] = "C:/another/jsonlite"
        _, popen = self.probes([requested, direct])
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch("platform.system", return_value="Windows"),
            mock.patch.dict("os.environ", {"R_LIBS": self.private}),
            mock.patch("subprocess.Popen", side_effect=popen),
            self.assertRaises(ValueError),
        ):
            rss.r_worker_command(
                [self.requested, "worker.R"], Path(directory) / "process.json"
            )

    def test_failed_origin_launch_retains_original_flags_and_no_invented_pid_or_peak(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                mock.patch("platform.system", return_value="Windows"),
                mock.patch(
                    "subprocess.Popen", side_effect=OSError("authored launch refusal")
                ),
                self.assertRaises(OSError),
            ):
                rss.r_worker_command(
                    [self.requested, "--vanilla", "worker.R"], root / "process.json"
                )
            receipt = json.loads((root / "r-worker-requested-probe.json").read_text())
            self.assertEqual(receipt["command"][:2], [self.requested, "--vanilla"])
            self.assertIsNone(receipt["launcher_pid"])
            self.assertIsNone(receipt["exit_code"])
            self.assertEqual(receipt["failure"]["class"], "OSError")
            self.assertFalse((root / "process.json").exists())

    def test_plain_unix_r_never_runs_resolution_probes_or_python_redirects(self):
        command = ["/usr/bin/Rscript", "--vanilla", "worker.R"]
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch("platform.system", return_value="Linux"),
            mock.patch("subprocess.Popen") as popen,
        ):
            observed, resolution = rss.r_worker_command(
                command, Path(directory) / "process.json"
            )
            popen.assert_not_called()
            self.assertEqual(observed, command)
            self.assertEqual(
                resolution["requested_command"], resolution["observed_command"]
            )
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_real_worker_nonzero_exit_and_original_rss_remain_separate_from_probes(
        self,
    ):
        requested, direct = self.fixture()
        _, popen = self.probes([requested, direct])
        peak = {"provider": "authored actual-worker RSS", "bytes": 80 * 1024 * 1024}
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch("platform.system", return_value="Windows"),
            mock.patch.dict("os.environ", {"R_LIBS": self.private}),
            mock.patch("subprocess.Popen", side_effect=popen),
            mock.patch.object(
                rss, "launch", return_value=SimpleNamespace(pid=6000)
            ) as launch,
            mock.patch.object(rss, "wait", return_value=(7, copy.deepcopy(peak))),
            mock.patch(
                "sys.argv",
                [
                    "child_peak_rss",
                    "--r-worker",
                    "--command",
                    json.dumps([self.requested, "--vanilla", "worker.R"]),
                    "--record",
                    str(Path(directory) / "process.json"),
                ],
            ),
        ):
            self.assertEqual(rss.main(), 0)
            launch.assert_called_once_with(
                [self.direct, "--vanilla", "worker.R"], False
            )
            process = json.loads((Path(directory) / "process.json").read_text())
            self.assertEqual((process["pid"], process["exit_code"]), (6000, 7))
            self.assertEqual(process["peak_rss"], peak)
            self.assertEqual(
                process["r_worker"]["observed_origin"]["launcher_pid"], 5169
            )

    def test_lifecycle_launches_r_broker_with_actual_private_libraries(self):
        with tempfile.TemporaryDirectory() as directory:
            child = Path(directory)
            request = {
                "host": "r",
                "provenance": {
                    "installed_origins": {"package": "/private/yamaa"},
                    "collectors": {
                        "json": {"origin": "/private/jsonlite"},
                        "timer": {"origin": "/timer/microbenchmark"},
                    },
                },
            }
            (child / "request.json").write_text(json.dumps(request))
            process_record = {"exit_code": 7, "pid": 6000, "peak_rss": None}
            (child / "process.json").write_text(json.dumps(process_record))
            with mock.patch.object(lifecycle.subprocess, "Popen") as popen:
                popen.return_value.wait.return_value = 0
                self.assertEqual(
                    lifecycle.launch(["Rscript", "worker.R"], child), process_record
                )
            command = popen.call_args.args[0]
            self.assertIn("--r-worker", command)
            self.assertNotIn("--python-worker", command)
            self.assertEqual(
                popen.call_args.kwargs["env"]["R_LIBS"],
                os.pathsep.join(["/private", "/timer"]),
            )

    def test_process_preflight_uses_same_r_resolver_and_retains_exit7(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preflight"
            response = {
                "pid": 6000,
                "runtime_version": "4.6.1",
                "jsonlite_version": "2.0.0",
                "private_library": "/private",
                "allocation_bytes": control.ALLOCATION,
                "page_stride": control.PAGE_STRIDE,
                "touched_page_count": control.ALLOCATION // control.PAGE_STRIDE,
                "touched_byte_sum": 165 * (control.ALLOCATION // control.PAGE_STRIDE),
                "requested_exit_code": 7,
            }
            process = {
                "pid": 6000,
                "exit_code": 7,
                "peak_rss": {
                    "provider": "os.wait4(child_pid).ru_maxrss",
                    "raw": 81920,
                    "bytes": 80 * 1024 * 1024,
                    "original_unit": "KiB",
                    "system": "Linux",
                    "scope": rss.SCOPE,
                },
            }

            def run(command, **kwargs):
                self.assertIn("--r-worker", command)
                self.assertNotIn("--python-worker", command)
                (output / "process.json").write_text(json.dumps(process))
                (output / "r-process.json").write_text(json.dumps(response))

            with (
                mock.patch.dict("os.environ", {"R_LIBS": "/private"}),
                mock.patch("platform.system", return_value="Linux"),
                mock.patch.object(control.subprocess, "run", side_effect=run),
            ):
                control.check(
                    SimpleNamespace(rscript=Path("/usr/bin/Rscript"), output=output)
                )
            receipt = json.loads((output / "r-child-rss-control.json").read_text())
            self.assertTrue(receipt["accepted"])
            self.assertEqual(receipt["observed_exit_code"], 7)
