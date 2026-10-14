"""Observe the launched child's lifetime high-water RSS, never the controller's.

Unix wait4 returns the reaped child's original kernel observation. Windows
GetProcessMemoryInfo reads PeakWorkingSetSize while Popen retains the process
handle, including after exit. Neither provider samples RSS or estimates a peak.
"""

from __future__ import annotations

import os
import platform

SCOPE = "whole-child-lifetime; cumulative across warm repetitions; includes collector transport"

R_ORIGIN_PROBE = r"""
library(jsonlite)
stopifnot(as.character(getRversion()) == "4.6.1")
stopifnot(as.character(packageVersion("jsonlite")) == "2.0.0")
private <- strsplit(Sys.getenv("R_LIBS"), .Platform$path.sep, fixed=TRUE)[[1]]
private <- normalizePath(private[nzchar(private)], winslash="/", mustWork=TRUE)
codec <- normalizePath(find.package("jsonlite"), winslash="/", mustWork=TRUE)
stopifnot(dirname(codec) %in% private)
home <- normalizePath(R.home(), winslash="/", mustWork=TRUE)
bin <- normalizePath(R.home("bin"), winslash="/", mustWork=TRUE)
arch <- unique(c(.Platform$r_arch, sub("^/", "", Sys.getenv("R_ARCH")),
  if (R.version$arch %in% c("x86_64", "x86-64")) "x64" else character()))
arch <- arch[nzchar(arch)]
stopifnot(all(grepl("^[A-Za-z0-9_-]+$", arch)))
directories <- unique(c(if (basename(bin) != "bin") bin else character(),
  file.path(home, "bin", arch), bin))
candidates <- file.path(directories, "Rscript.exe")
existing <- candidates[file.exists(candidates)]
stopifnot(length(existing) > 0)
direct <- normalizePath(existing[1], winslash="/", mustWork=TRUE)
jsonlite::write_json(list(pid=Sys.getpid(), runtime_version=as.character(getRversion()),
  home=home, bin=bin, architecture=R.version$arch, r_arch=.Platform$r_arch,
  jsonlite_version=as.character(packageVersion("jsonlite")), private_libraries=I(private),
  codec_origin=codec, direct_executable=direct), commandArgs(TRUE)[1],
  auto_unbox=TRUE, pretty=TRUE)
"""


def r_worker_command(command, record):
    """Resolve Windows R's architecture launcher without measuring that wrapper."""
    import json
    import ntpath
    import subprocess

    resolution = {
        "protocol": "r-worker-resolution/1",
        "system": platform.system(),
        "requested_executable": command[0],
        "requested_command": command,
        "observed_executable": command[0],
        "observed_command": command,
        "private_library_environment": os.environ.get("R_LIBS", ""),
        "resolution": "plain Unix Rscript",
    }
    if resolution["system"] != "Windows":
        return command, resolution
    root = record.parent
    probe = root / "r-worker-origin-probe.R"
    probe.write_text(R_ORIGIN_PROBE, encoding="utf-8", newline="\n")

    def origin(executable, label):
        destination = root / f"r-worker-{label}-origin.json"
        argv = [executable, "--vanilla", str(probe), str(destination)]
        value = {
            "command": argv,
            "source": probe.name,
            "stdout": f"r-worker-{label}-stdout.txt",
            "stderr": f"r-worker-{label}-stderr.txt",
            "response": destination.name,
            "launcher_pid": None,
            "exit_code": None,
            "origin": None,
        }
        try:
            with (
                (root / value["stdout"]).open("xb") as stdout,
                (root / value["stderr"]).open("xb") as stderr,
            ):
                process = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
                value["launcher_pid"] = process.pid
                value["exit_code"] = process.wait()
            if destination.is_file():
                value["origin"] = json.loads(destination.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            value["failure"] = {"class": type(error).__name__, "reason": str(error)}
            raise
        finally:
            (root / f"r-worker-{label}-probe.json").write_text(
                json.dumps(value, indent=2) + "\n", encoding="utf-8"
            )
        if value["exit_code"] or value["origin"] is None:
            raise ValueError("installed R architecture origin probe failed")
        return value

    requested = origin(command[0], "requested")
    direct = requested["origin"]["direct_executable"]
    observed = origin(direct, "direct")
    invariant = (
        "runtime_version",
        "home",
        "bin",
        "architecture",
        "r_arch",
        "jsonlite_version",
        "private_libraries",
        "codec_origin",
        "direct_executable",
    )
    private = [
        ntpath.normcase(ntpath.normpath(path))
        for path in os.environ.get("R_LIBS", "").split(";")
        if path
    ]
    installed = requested["origin"]
    expected_bin = ntpath.join(installed["home"], "bin")
    if (
        requested["origin"]["runtime_version"] != "4.6.1"
        or requested["origin"]["jsonlite_version"] != "2.0.0"
        or not private
        or [
            ntpath.normcase(ntpath.normpath(path))
            for path in installed["private_libraries"]
        ]
        != private
        or ntpath.normcase(ntpath.dirname(installed["codec_origin"])) not in private
        or ntpath.basename(direct).lower() != "rscript.exe"
        or ntpath.normcase(ntpath.commonpath([expected_bin, direct]))
        != ntpath.normcase(expected_bin)
        or any(requested["origin"][key] != observed["origin"][key] for key in invariant)
        or type(observed["origin"]["pid"]) is not int
        or observed["origin"]["pid"] != observed["launcher_pid"]
    ):
        raise ValueError(
            "direct Rscript PID or installed R/private namespace origin differs"
        )
    observed_command = [direct, *command[1:]]
    resolution.update(
        observed_executable=direct,
        observed_command=observed_command,
        resolution="installed R architecture executable",
        requested_origin=requested,
        observed_origin=observed,
    )
    return observed_command, resolution


def launch(command, python_worker=False):
    """Hold the actual interpreter handle rather than a Windows venv redirector."""
    import json
    import subprocess

    if platform.system() == "Windows" and python_worker:
        # CPython's Windows venv redirector launches the base interpreter with
        # this environment marker and waits. Skip only that extra process,
        # retaining the requested interpreter's exact venv/site configuration.
        invoked, base = json.loads(
            subprocess.check_output(
                [
                    command[0],
                    "-I",
                    "-c",
                    "import json, sys; print(json.dumps([sys.executable, sys._base_executable]))",
                ],
                text=True,
                encoding="utf-8",
            )
        )
        if os.path.normcase(os.path.abspath(invoked)) != os.path.normcase(
            os.path.abspath(base)
        ):
            return subprocess.Popen(
                [base, *command[1:]],
                env={**os.environ, "__PYVENV_LAUNCHER__": invoked},
            )
    return subprocess.Popen(command)


def wait(process):
    system = platform.system()
    if system in {"Linux", "Darwin"} and hasattr(os, "wait4"):
        pid, status, usage = os.wait4(process.pid, 0)
        if pid != process.pid:
            raise RuntimeError("wait4 returned another process")
        process.returncode = os.waitstatus_to_exitcode(status)
        raw = usage.ru_maxrss
        observation = {
            "provider": "os.wait4(child_pid).ru_maxrss",
            "raw": raw,
            "original_unit": "KiB" if system == "Linux" else "bytes",
            "bytes": raw * (1024 if system == "Linux" else 1),
            "scope": SCOPE,
            "system": system,
        }
    elif system == "Windows":
        process.wait()
        observation = windows(process)
    else:
        process.wait()
        observation = None
    return process.returncode, observation


def windows(process):
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            *[
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ],
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    query = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    query.restype = wintypes.BOOL
    if not query(
        wintypes.HANDLE(int(process._handle)), ctypes.byref(counters), counters.cb
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    raw = counters.PeakWorkingSetSize
    return {
        "provider": "GetProcessMemoryInfo(child_handle).PeakWorkingSetSize",
        "raw": raw,
        "original_unit": "bytes",
        "bytes": raw,
        "scope": SCOPE,
        "system": "Windows",
    }


def validate(observation, system):
    if system not in {"Linux", "Darwin", "Windows"}:
        if observation is not None:
            raise ValueError("unexpected RSS for an unadmitted provider")
        return
    if not isinstance(observation, dict):
        raise ValueError("child peak RSS provider unavailable")  # noqa: TRY004 - admission error contract
    provider = (
        "GetProcessMemoryInfo(child_handle).PeakWorkingSetSize"
        if system == "Windows"
        else "os.wait4(child_pid).ru_maxrss"
    )
    raw = observation.get("raw")
    if (
        isinstance(raw, bool)
        or not isinstance(raw, (int, float))
        or raw <= 0
        or observation.get("provider") != provider
        or observation.get("system") != system
        or observation.get("original_unit") != ("KiB" if system == "Linux" else "bytes")
        or observation.get("bytes") != raw * (1024 if system == "Linux" else 1)
        or observation.get("scope") != SCOPE
    ):
        raise ValueError("invalid child peak RSS observation")


def main():
    # Launch from this small, newly exec'd broker. A large controller's fork RSS
    # otherwise survives exec as the child's ru_maxrss, contaminating even the
    # worker's own getrusage observation with workload-generation memory.
    import argparse
    import json
    import signal
    import subprocess
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", required=True)
    parser.add_argument("--record", type=Path, required=True)
    worker = parser.add_mutually_exclusive_group()
    worker.add_argument("--python-worker", action="store_true")
    worker.add_argument("--r-worker", action="store_true")
    args = parser.parse_args()
    command = json.loads(args.command)
    resolution = None
    if args.r_worker:
        command, resolution = r_worker_command(command, args.record)
        (args.record.parent / "r-worker-resolution.json").write_text(
            json.dumps(resolution, indent=2) + "\n", encoding="utf-8"
        )
    process = launch(command, args.python_worker)
    running = {"state": "running", "pid": process.pid, "peak_rss": None}
    if resolution is not None:
        running["r_worker"] = resolution
    args.record.write_text(
        json.dumps(running) + "\n",
        encoding="utf-8",
    )
    if os.name != "nt":

        def interrupted(signum, frame):
            raise KeyboardInterrupt("RSS broker interrupted")

        signal.signal(signal.SIGTERM, interrupted)
    try:
        code, peak = wait(process)
        record = {
            "exit_code": code,
            "pid": process.pid,
            "peak_rss": peak,
            "launcher": "fresh small broker; controller fork RSS excluded",
        }
        if resolution is not None:
            record["r_worker"] = resolution
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
