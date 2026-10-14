"""Temporary Windows probe of venv launcher identity and original kernel RSS."""

import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "rss", root / "rust/tools/child_peak_rss.py"
)
rss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rss)

assert platform.system() == "Windows"
marker = Path(sys.prefix) / "Lib/site-packages/rss_probe_marker.py"
marker.write_text("VALUE = 'original venv site bytes'\n", encoding="utf-8")
program = """
import json, os, sys, time
from pathlib import Path
import rss_probe_marker
a = bytearray(64 * 1024 * 1024)
a[::4096] = b'x' * len(a[::4096])
Path(sys.argv[1]).write_text(json.dumps({
    'pid': os.getpid(), 'executable': sys.executable,
    'base_executable': sys._base_executable, 'prefix': sys.prefix,
    'base_prefix': sys.base_prefix, 'sys_path': sys.path,
    'marker': rss_probe_marker.VALUE,
}), encoding='utf-8')
time.sleep(0.1)
raise SystemExit(7)
"""

with tempfile.TemporaryDirectory() as directory:
    records = {}
    for kind in ("ordinary-venv", "direct-base-with-venv-launcher"):
        output = Path(directory) / (kind + ".json")
        command = [sys.executable, "-I", "-c", program, str(output)]
        options = {}
        if kind == "direct-base-with-venv-launcher":
            command[0] = sys._base_executable
            options = {
                "env": {**os.environ, "__PYVENV_LAUNCHER__": sys.executable},
            }
        process = subprocess.Popen(command, **options)
        code, observation = rss.wait(process)
        record = json.loads(output.read_text(encoding="utf-8"))
        record.update(launched_pid=process.pid, exit_code=code, peak_rss=observation)
        records[kind] = record
        print(json.dumps({"kind": kind, **record}, indent=2), flush=True)

    ordinary = records["ordinary-venv"]
    direct = records["direct-base-with-venv-launcher"]
    assert ordinary["launched_pid"] != ordinary["pid"], "probe lacks redirector witness"
    assert ordinary["peak_rss"]["bytes"] < 64 * 1024 * 1024
    assert direct["launched_pid"] == direct["pid"]
    assert direct["exit_code"] == ordinary["exit_code"] == 7
    assert direct["peak_rss"]["bytes"] >= 64 * 1024 * 1024
    for field in (
        "executable",
        "base_executable",
        "prefix",
        "base_prefix",
        "sys_path",
        "marker",
    ):
        assert direct[field] == ordinary[field], (field, direct[field], ordinary[field])
    print(
        "Direct Python launch preserves venv context, actual worker PID, exit and kernel RSS"
    )
