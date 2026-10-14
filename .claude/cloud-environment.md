# Cloud environment for the Rust engine and the R package

A Claude Code cloud session for yamaa has two layers of setup:

- **The environment** is configured on claude.ai and provisions the VM. Its
  setup script runs once, and the resulting filesystem is cached for later
  sessions.
- **The SessionStart hook** in [`hooks/session-start.sh`](hooks/session-start.sh)
  is committed here and runs at the start of every cloud session, including
  resumed ones. It does nothing in local sessions.

The hook handles the Rust engine on its own, and the setup script only saves it
time there. R comes from the setup script alone.

## Create the environment

On [claude.ai/code](https://claude.ai/code), select the cloud icon above the
message box, select **Cloud**, then **Add cloud environment**. To change an
existing environment instead, hover over it and select its settings icon.

**Name:** `yamaa`

**Network access:** the setup script downloads R from `cdn.posit.co` and CRAN
packages from `packagemanager.posit.co`. Neither host is on the published
`Trusted` list, but both were reachable from the environment this was tested
in. If the setup fails on those downloads, select `Custom`, check **Also
include default list of common package managers**, and add both hosts. The
`Trusted` list already covers the rest: `static.rust-lang.org` for the
toolchain, crates.io, PyPI, Ubuntu's archive, and GitHub (through the session's
GitHub proxy) for the `saphyr` git dependency.

**Environment variables:**

```text
BASH_DEFAULT_TIMEOUT_MS=600000
BASH_MAX_TIMEOUT_MS=1800000
```

Foreground commands normally time out after 2 minutes. A cold `cargo test`
build of the default members takes about 3 minutes, as does installing the R
package, and the `release-test` profile takes longer still.

**Setup script:**

```bash
#!/bin/bash
# Provision a yamaa cloud session. The environment caches the result.
set -euo pipefail

# Rust: the toolchain rust/rust-toolchain.toml pins. The session hook installs
# any other pin itself, so a stale version here only costs time.
export PATH="$HOME/.cargo/bin:$PATH"
rustup toolchain install 1.90.0 --profile minimal --component clippy,rustfmt --no-self-update
rustup default 1.90.0

# R: Posit's build of the version the R workflows install with
# r-lib/actions/setup-r. Ubuntu's own r-base is too old for R/yamaa.
R_VERSION=4.6.1
deb=$(mktemp --suffix=.deb)
curl -fsSL --retry 3 -o "$deb" "https://cdn.posit.co/r/ubuntu-2404/pkgs/r-${R_VERSION}_1_amd64.deb"
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends "$deb"
rm -f "$deb"
ln -sf "/opt/R/$R_VERSION/bin/R" /usr/local/bin/R
ln -sf "/opt/R/$R_VERSION/bin/Rscript" /usr/local/bin/Rscript

# The latest CRAN packages, as Ubuntu binaries from Posit Package Manager. The
# set is the one evaluations/harbor/Dockerfile installs for the reference
# solutions.
cat >> "/opt/R/$R_VERSION/lib/R/etc/Rprofile.site" <<'EOF'
options(
  repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/noble/latest"),
  HTTPUserAgent = sprintf("R/%s R (%s)", getRversion(),
    paste(getRversion(), R.version["platform"], R.version["arch"], R.version["os"]))
)
EOF
Rscript -e 'pkgs <- c("dplyr", "tidyr", "readr", "stringr", "lubridate", "purrr", "haven", "xml2", "nanoparquet")
install.packages(pkgs, Ncpus = 4)
stopifnot(all(vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)))'
```

From a clean state the whole script took under 30 seconds, with every CRAN
package installed as a binary, so it stays well inside the five minutes a setup script
has to finish in to be cached. If any step fails, the session doesn't start,
so a blocked download shows up straight away.

The Rust and R versions in the script copy `rust/rust-toolchain.toml` and the R
workflows. When those change, change the script too. Editing it rebuilds the
cache.

CRAN packages are the latest at the time the cache was built, and the cache is
rebuilt about every seven days. `install.packages()` and `update.packages()` in
a session also fetch the latest, because the script sets that repository in
`Rprofile.site`. `Rscript --vanilla`, which the CI commands use, skips that
file.

Start sessions for this repository in the `yamaa` environment.

## What the hook does

1. It sets `CARGO_PROFILE_DEV_DEBUG=0` for the session. The three default
   members have about 240 integration-test binaries. With full debug
   information each adapters binary is about 100 MB, and a plain
   `cargo test --locked` ran out of the 30 GB session disk. Debug information
   changes nothing CI asserts, and panics still report file and line.

   When no locale is set, which is the VM's default, it also sets
   `LANG=C.UTF-8`, as GitHub's runners have. In the C locale, `R CMD check`
   fails reading the package's UTF-8 fixtures.
2. It installs the toolchain and components that `rust/rust-toolchain.toml`
   pins, then makes that toolchain the default. Cargo started outside `rust/`,
   such as maturin from `python/`, then uses the same compiler, as
   `RUSTUP_TOOLCHAIN` does in CI.
3. It runs `cargo fetch --locked`.
4. It starts a warm build in the background, at low priority:
   `uv sync --locked --no-install-project` for `python/`, then
   `cargo test --locked --no-run`, then the CI clippy command. The log is
   `/tmp/yamaa-warm-build.log`. Cargo locks the build directory, so a cargo
   command started meanwhile waits for the warm build and then reuses its
   output. Set `YAMAA_WARM_BUILD=0` in the environment variables to skip this.
5. When `Rscript` is on the path, it adds how to build the R package to its
   summary.

The hook prints a short summary of all this, which the session receives as
context.

Select tests at workspace scope, for example `cargo test --locked --test rounding`,
to reuse the warm build. `-p yamaa-adapters` reuses it as well. `-p yamaa-core`
or `-p yamaa-engine` on its own resolves dependency features differently and
recompiles, which took about 25 and 50 seconds when measured.

Measured in a fresh session with no toolchain installed: the hook returned in
17 seconds. The warm build then took 2m41s for the tests, 36 seconds for
clippy and a few seconds for `uv`, leaving 6.8 GB in `rust/target`. After that,
the full `cargo test --locked` took 35 seconds.

## Working on the R package

`R/yamaa` cannot be installed in place, because its Rust sources are copied in
when it is staged. Build and test it as `.github/workflows/r.yml` and
`native.yml` do, from the repository root:

```bash
cargo clippy --manifest-path rust/Cargo.toml --locked -p yamaa-r -- -D warnings
work=$(mktemp -d)
python/.venv/bin/python rust/tools/stage_r_package.py "$work/stage/yamaa"
(cd "$work" && R CMD build --no-build-vignettes --no-manual stage/yamaa)
mkdir "$work/library"
R CMD INSTALL --library="$work/library" rust/tests/project-programs/r
R CMD INSTALL --library="$work/library" "$work/yamaa_0.4.0.tar.gz"
R_LIBS="$work/library" Rscript --vanilla R/yamaa/tests/public_grammar.R
(cd "$work" && _R_CHECK_CRAN_INCOMING_REMOTE_=false R_LIBS="$work/library" R CMD check --no-manual yamaa_0.4.0.tar.gz)
```

The staging tool needs `py-yaml12`, which the warm build's `python/.venv`
provides. Each install compiles the engine in release mode from scratch: it
took 2m43s, and clippy on the binding took 41 seconds after the warm build.
The test scripts in `R/yamaa/tests` then take a second or two each.
`R CMD check` builds the engine again and runs every one of those scripts; it
took 3m09s and reported `Status: OK`, which `native.yml` requires.

To run the R reference solutions the CRAN packages are there for, as
`.github/workflows/harbor-evaluation.yml` does:

```bash
uv sync --project python --extra test --locked --no-editable
YAMAA_REQUIRE_R=1 uv run --project python --no-sync pytest python/tests/test_harbor_evaluation.py -k reference_solution_scores_one
```

All 272 passed in about 4 minutes. Keep `--no-editable`: an editable install
leaves the compiled `python/src/yamaa/_native.abi3.so` in the checkout.

## Not covered

- **Sessions with several repositories.** The cloud does not run repository
  hooks in these sessions, so only the environment's setup applies.
