"""Smoke test of an installed yamaa wheel: build one public upstream benchmark and compare with its expected file."""
import os, pathlib, shutil, sys, tempfile
import yamaa
src = pathlib.Path(sys.argv[1]).resolve()
work = pathlib.Path(tempfile.mkdtemp()) / src.name
shutil.copytree(src, work)
os.chdir(work)
issues = yamaa.check("spec.yaml").issues
d = yamaa.domain("spec.yaml")
d.save()
out = pathlib.Path("adae.csv").read_bytes().replace(b"\r\n", b"\n")
exp = pathlib.Path("expected/adae.csv").read_bytes().replace(b"\r\n", b"\n")
print("yamaa", yamaa.__file__, "| check issues", len(issues), "| equal to expected:", out == exp, len(out), len(exp))
sys.exit(0 if out == exp else 1)
