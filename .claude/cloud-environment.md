# Cloud environment for the Rust engine

A Claude Code cloud session for yamaa has two layers of setup:

- **The environment** is configured on claude.ai and provisions the VM. Its
  setup script runs once, and the resulting filesystem is cached for later
  sessions.
- **The SessionStart hook** in [`hooks/session-start.sh`](hooks/session-start.sh)
  is committed here and runs at the start of every cloud session, including
  resumed ones. It does nothing in local sessions.

The hook works on its own. The environment only means it has less to do.

## Create the environment

On [claude.ai/code](https://claude.ai/code), select the cloud icon above the
message box, select **Cloud**, then **Add cloud environment**. To change an
existing environment instead, hover over it and select its settings icon.

**Name:** `yamaa`

**Network access:** `Trusted`. It already allows everything the build needs:
`static.rust-lang.org` for the toolchain, crates.io, PyPI, and GitHub (through
the session's GitHub proxy) for the `saphyr` git dependency.

**Environment variables:**

```text
BASH_DEFAULT_TIMEOUT_MS=600000
BASH_MAX_TIMEOUT_MS=1800000
```

Foreground commands normally time out after 2 minutes. A cold `cargo test`
build of the default members takes about 3 minutes, and the `release-test`
profile takes longer still.

**Setup script:**

```bash
#!/bin/bash
# Bake the toolchain pinned by rust/rust-toolchain.toml into the cached image.
# The session hook installs any other pin itself, so a stale version here only
# costs time.
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
rustup toolchain install 1.90.0 --profile minimal --component clippy,rustfmt --no-self-update
rustup default 1.90.0
```

Start sessions for this repository in the `yamaa` environment.

## What the hook does

1. It sets `CARGO_PROFILE_DEV_DEBUG=0` for the session. The three default
   members have about 240 integration-test binaries. With full debug
   information each adapters binary is about 100 MB, and a plain
   `cargo test --locked` ran out of the 30 GB session disk. Debug information
   changes nothing CI asserts, and panics still report file and line.
2. It installs the toolchain and components that `rust/rust-toolchain.toml`
   pins, then makes that toolchain the default. Cargo started outside `rust/`,
   such as maturin from `python/`, then uses the same compiler, as
   `RUSTUP_TOOLCHAIN` does in CI.
3. It runs `cargo fetch --locked`.
4. It starts a warm build in the background, at low priority:
   `cargo test --locked --no-run`, then the CI clippy command, then
   `uv sync --locked --no-install-project` for `python/`. The log is
   `/tmp/yamaa-warm-build.log`. Cargo locks the build directory, so a cargo
   command started meanwhile waits for the warm build and then reuses its
   output. Set `YAMAA_WARM_BUILD=0` in the environment variables to skip this.

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

## Not covered

- **R.** `yamaa-r` is not a default workspace member, and building it needs R
  itself. The R package checks also install packages from CRAN, which is not on
  the `Trusted` list. To work on R, switch the environment to `Custom` network
  access, keep the default list, add `cloud.r-project.org`, and install
  `r-base-dev` in the setup script.
- **Sessions with several repositories.** The cloud does not run repository
  hooks in these sessions, so only the environment's setup applies.
